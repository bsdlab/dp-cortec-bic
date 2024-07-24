import time
import threading
import pylsl

from ct_bic.listener import CTListener
from ct_bic.utils.global_setup import pyapi
from ct_bic.utils.logging import logger


STREAM_NAME = "ct_bic"


def get_stream_outlet(
    stream_name: str = STREAM_NAME,
    sfreq: int = 1000,
    n_channels: int = 32,
    max_buffer_s: int = 5,
) -> tuple[pylsl.StreamOutlet, pylsl.StreamInfo]:
    info = pylsl.StreamInfo(
        name=stream_name,
        type="EEG",
        channel_count=n_channels,
        nominal_srate=sfreq,
        channel_format="float32",
        source_id=f"{stream_name}_id",
    )

    outlet = pylsl.StreamOutlet(info, max_buffered=max_buffer_s)

    return outlet, info


def stream_results(
    outlet: pylsl.StreamOutlet,
    listener: CTListener,
    stop_event: threading.Event,
):
    logger.debug("Starting streaming thread")
    dt = 1 / outlet.get_info().nominal_srate() * 10**9  # in nano seconds

    while not stop_event.is_set():
        t0 = time.time_ns()
        if listener.n_new > 0 and (time.time_ns() - t0) > dt:
            for s in listener.get_new_data():
                outlet.push_sample(s)
            # outlet.push_chunk(listener.get_new_data())


class CTtoLSLStream:
    def __init__(
        self,
        stream_name: str = STREAM_NAME,
        sfreq: int = 1000,
        n_channels: int = 32,
        stop_event: threading.Event = threading.Event(),
    ):
        self.outlet, self.stream_info = get_stream_outlet(
            stream_name, sfreq, n_channels
        )
        self.stop_event = stop_event
        self.listener: CTListener | None = None
        self.thread: threading.Thread | None = None

    def add_listener(self, listener: CTListener):
        self.listener = listener

    def start_streaming_thread(self):
        if self.listener is None:
            raise ValueError(
                "No listener attached to the streamer - call "
                "self.add_listener(listener)."
            )

        self.stop_event.clear()
        self.thread = threading.Thread(
            target=stream_results,
            args=(self.outlet, self.listener, self.stop_event),
        )
        self.thread.start()

    def stop_streaming_thread(self):
        self.stop_event.set()
        self.thread.join()

    def __del__(self):
        # Manual clean-up to avoid cluttering of leftover streams
        del self.outlet
        del self.stream_info


if __name__ == "__main__":
    from ct_bic.device import get_device
    from ct_bic.listener import BootstrappedRingBuffer

    bb = BootstrappedRingBuffer(buffer_size_s=5)

    with get_device() as implant:
        listener = CTListener(bb)
        # listener = TestListener()
        implant.register_listener(listener)
        listener.reset_buffers()
        # Systems needs a bit to get ready, else to many samples are missing
        time.sleep(1)

        streamer = CTtoLSLStream()
        streamer.add_listener(listener)

        implant.start_measurement(
            [31], pyapi.RecordingAmplificationFactor.AMPLIFICATION_57_5dB, True
        )
        streamer.start_streaming_thread()

        q = input("Provide any input to stop streaming: ")
        streamer.stop_streaming_thread()
        implant.stop_measurement()
