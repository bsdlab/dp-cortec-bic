import time
from dareplane_utils.default_server.server import threading
from dareplane_utils.stream_watcher.lsl_stream_watcher import StreamWatcher
from ct_bic.utils.logging import logger

import pylsl

from typing import Callable
import threading


def get_marker_outlet():
    info = pylsl.StreamInfo(
        name="CTBicControl",
        type="Markers",
        channel_count=1,
        nominal_srate=pylsl.IRREGULAR_RATE,
        channel_format="string",
    )
    return pylsl.StreamOutlet(info)


def threshold_single_control(
    sw: StreamWatcher,
    callback: Callable,
    stop_event: threading.Event,
    threshold: float = 128,
    channel: int = 0,
    dt_s: float = 0.0002,
    grace_period_s: float = 1.5,  # the device seems rather slow after a stimulation was trigggered -> have a larger grace period
):
    """
    Single threshold control which will fire the callback if value is above
    threshold for the specified channel at the last position in the
    StreamWatchers buffer
    """
    moutlet = get_marker_outlet()

    logger.debug(f"Starting threshold control - {grace_period_s=}")
    # Connecting has to happen here - so that only the sub thread waits for the
    # LSL stream and not the main
    if not stop_event.is_set():
        sw.connect_to_stream()

    i = 0

    t0 = time.time_ns()
    while not stop_event.is_set():
        if time.time_ns() - t0 > dt_s * 1e9:
            sw.update()
            lastn = sw.unfold_buffer()[-10:, channel]
            cval = lastn[-1]
            t0 = time.time_ns()
            time.sleep(0.001)

            if cval > threshold:
                t0 = time.time_ns()
                logger.debug(
                    f"Threshold control firing callback: {lastn=} -{callback}"
                )
                moutlet.push_sample(["firing_callback"])
                callback()
                t_gp = time.time_ns()
                moutlet.push_sample(["callback_fired"])

                # now wait for the grace period to pass by
                dtt = time.time_ns() - t_gp
                while not (dtt > grace_period_s * 1e9 and cval < threshold):
                    dtt = time.time_ns() - t_gp

                    # grab new data with the same frequency to be able to evaluate
                    # the second condition in the why statement
                    if dtt > dt_s * 1e9:
                        sw.update()
                        cval = sw.unfold_buffer()[-1:, channel]
                        t0 = time.time_ns()
                        time.sleep(0.001)

                    pass


                moutlet.push_sample(["listening"])
                logger.debug("Grace period passed - looking for control again")

    logger.debug("Threshold control done")
