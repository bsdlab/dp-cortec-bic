import threading
import numpy as np
import tomllib
from pathlib import Path

from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log
from ct_bic.utils.logging import logger
from ct_bic.listener import CTListener
from ct_bic.lsl import CTtoLSLStream, get_stream_outlet
from ct_bic.stimulation_cmds import (
    get_single_pulse_stim_cmd,
    get_nsec_130Hz_stim,
)
from ct_bic.controller import threshold_single_control


from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher
from dareplane_utils.general.ringbuffer import RingBuffer


CFG = tomllib.load(open("./config/config.toml", "rb"))


class CTManager:
    """
    The manager class to provide interaction functionality with the CorTec BIC
    device.
    """

    def __init__(
        self,
        buffer_size_s: float = CFG["lsl"]["buffer_size_s"],
        stream_name: str = CFG["lsl"]["stream_name"],
        ref_channels: list[int] = [4],  # if empty -> global ref is used
    ):
        self.ref_channels = ref_channels
        self.buffer_size_s = buffer_size_s
        self.stop_event = threading.Event()
        self.trigger_stop_event = threading.Event()
        self.i_pulse = 0

        # CT implant

        # using a function call just returning the implant does not work
        # most likely the info object is required to share a life time with
        # the implant ... (indeed event the factory needs to be kept alive)
        self.implant = None
        self.init_implant()

        # CT BIC samples at 1kHz
        rb = RingBuffer(shape=(buffer_size_s * 1000, 32))

        self.outlet, self.stream_info = get_stream_outlet(
            stream_name, sfreq=1000, n_channels=32
        )
        self.listener = CTListener(rb, outlet=self.outlet)
        self.implant.register_listener(self.listener)

        # # LSL
        # self.stop_event = threading.Event()
        # self.streamer = CTtoLSLStream(
        #     stream_name=stream_name, stop_event=self.stop_event
        # )
        #
        # self.streamer.add_listener(self.listener)
        #
        # stim control
        self.trigger_stop_event = threading.Event()

    def init_implant(self):
        log_file_pth = Path(log_file_name)
        log_file_pth.parent.mkdir(exist_ok=True)
        factory = pyapi.ImplantFactory(enable_log, log_file_name)
        ext_unit_infos = factory.load_external_unit_infos()
        implant_info = None
        ext_unit_info = None

        # You have to load the info - else creating the implant object will fail
        for info in ext_unit_infos:
            try:
                implant_info = factory.load_implant_info(info)
                ext_unit_info = info
            except RuntimeError as e:
                raise e

        assert (
            implant_info is not None
        ), "No implant info found - is implant connected with other process?"

        # Keep all to ensure object life time
        self.factory = factory
        self.implant_info = implant_info
        self.ext_unit_info = ext_unit_info
        self.implant = factory.create(ext_unit_info, implant_info)

    def start_recording(
        self,
        ) -> int:
        #-> tuple[threading.Thread | None, threading.Event]:
        self.stop_event.clear()

        self.implant.start_measurement(
            self.ref_channels,
            # amplification_factor=pyapi.RecordingAmplificationFactor.AMPLIFICATION_57_5dB,
            amplification_factor=pyapi.RecordingAmplificationFactor.AMPLIFICATION_39_5dB,
            use_ground_electrode=True,
        )

        # # start streaming to LSL
        # self.streamer.start_streaming_thread()

        # Return the lsls side thread
        # return self.streamer.thread, self.stop_event
        return 0

    def stop_recording(self):
        self.implant.stop_measurement()
        self.stop_event.set()

    def listen_for_stim_trigger(
        self,
    ) -> tuple[threading.Thread, threading.Event]:
        # TODO: If the listener is started, the module does not stop properly
        # implement a better stopping for this
        self.trigger_stop_event.clear()
        sw = StreamWatcher(
            name=CFG["stim_control"]["stream_name"],
            buffer_size_s=CFG["stim_control"]["buffer_size_s"],
        )

        callback = self.start_stimulation

        th = threading.Thread(
            target=threshold_single_control,
            args=(sw, callback, self.trigger_stop_event),
            kwargs={"threshold": 127},
        )
        th.start()

        self.listen_th = th
        self.sw = sw

        return th, self.trigger_stop_event

    def is_recording(self) -> bool:
        return not self.stop_event.isSet()

    def init_stim_cmds(
        self,
        cmds: list[pyapi.stimulationcommand.StimulationCommand] | None = None,
    ):
        if cmds is not None:
            self.cmds = cmds
        else:
            self.cmds = get_single_pulse_stim_cmd(self.implant)

        # Enqueue directly to not require another function call
        # --> Note the preloading version should give the fastest response time
        self.implant.enqueue_stimulation_command(
            self.cmds,
            pyapi.StimulationMode.STIMMODE_PERSISTENT_CMD_PRELOADING,
        )

    def start_stimulation(self) -> int:
        self.i_pulse += 1
        logger.debug("Starting stimulation - {self.i_pulse}")
        self.implant.start_stimulation()
        return 0

    def stop_stimulation(self) -> int:
        self.implant.stop_stimulation()
        return 0

    def __del__(self):
        logger.debug("CTManager closing implant")
        self.stop_event.set()
        self.trigger_stop_event.set()
        if self.implant:
            try:
                self.implant.stop_measurement()
            except RuntimeError:
                logger.debug("Measurement already stopped")
            self.implant.set_implant_power(False)


if __name__ == "__main__":

    logger.setLevel(10)

    # Using ch4 as ref, 1 = stim, 2 = ret, 3 = sinus input
    ctm = CTManager(ref_channels=[4])

    # cmds = get_nsec_130Hz_stim(ctm.implant, 0.5)
    # ctm.init_stim_cmds(cmds=cmds)

    # Default single stimulation pulse
    ctm.init_stim_cmds()

    # manually trigger single stimulation pulses
    _ = ctm.start_recording()
    thl, sel = ctm.listen_for_stim_trigger()
    q = ""
    while q != "q":
        q = input(
            "Press q to quit or send anything else to trigger a stim pulse: "
        )
        if q != "q":
            ctm.start_stimulation()
        print(f"{q=}")

    print("Stopping stimulation")
    ctm.stop_stimulation()

    print("Stopping recording")
    ctm.stop_recording()

    print("Closing threads")
    ctm.stop_event.set()
    ctm.trigger_stop_event.set()

    # waiting for the threads to stop
    import time

    time.sleep(5)
    print("setting power to false")
    ctm.implant.set_implant_power(False)

    print("deleting variable")
    del ctm

    print("deleted")

    # Run full time
    # import time
    #
    # time.sleep(5)
    #
    # ctm.start_stimulation()
    #
    # time.sleep(10)
    #
    # ctm.start_stimulation()
    #
    # time.sleep(10)
    #
    # ctm.stop_stimulation()
    #
    # time.sleep(5)
    # ctm.stop_recording()
    # se.set()
    #
    # del ctm
