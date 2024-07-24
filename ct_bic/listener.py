import numpy as np
from dataclasses import dataclass, field
import pandas as pd
from ct_bic.utils.global_setup import pyapi

# Using a streamwatcher instance for its ring buffer
from dareplane_utils.stream_watcher.lsl_stream_watcher import (
    StreamWatcher,
)


def buffers_to_df(
    data_buffer: list[list], cntr_buffer: list[int]
) -> pd.DataFrame:
    df = pd.DataFrame(
        data_buffer, columns=[f"Ch_{i}" for i in range(len(data_buffer[0]))]
    )
    df["cntr"] = cntr_buffer

    return df


# -- Making use of the ring buffer implemented in the StreamWatcher
class BootstrappedRingBuffer(StreamWatcher):
    def _init_buffer(self):
        n_samples = int(self.buffer_size_s * 1000)  # CT BIC samples at 1kHz
        self.n_buffer = n_samples

        # Using numpy buffers
        self.buffer = np.empty((n_samples, 32))
        self.buffer_t = np.empty(n_samples)
        self.last_t = 0
        self.curr_i = 0


class CTListener(pyapi.ImplantListener):
    def __init__(
        self,
        sw: BootstrappedRingBuffer = BootstrappedRingBuffer(
            name="ct_bic", buffer_size_s=5
        ),
        is_measument_active: bool = False,
        n_new: int = 0,
        news: list[int] = [],
        latest_samples: list[float] = [],
    ):
        self.sw = sw
        self.is_measument_active = is_measument_active
        self.n_new = n_new
        self.news = news
        self.latest_samples = latest_samples

        self.sw._init_buffer()

    def reset_buffers(self):
        # Overwrite by reinit
        self.sw._init_buffer()

    def on_measurement_state_changed(self, is_measuring: bool):
        self.is_measument_active = is_measuring

    def on_data(self, sample: pyapi.Sample):
        samples = sample.measurements

        # samples to list of lists as would be delivered by lsl
        # In [90]: %timeit [a[i: i+32] for i in range(0, len(a), 32)]
        # 543 ns ± 10.8 ns per loop (mean ± std. dev. of 7 runs, 1,000,000 loops each)
        # In [84]: %timeit np.asarray(a).reshape(-1, 32)
        # 4.18 µs ± 18.3 ns per loop (mean ± std. dev. of 7 runs, 100,000 loops each)
        samples = [samples[i : i + 32] for i in range(0, len(samples), 32)]

        self.latest_samples = samples

        # The stream watcher tracks data and times, use the times ring buffer
        # for tracking the package count - second arg here
        self.sw.add_samples(
            samples, [sample.measurement_counter] * len(samples)
        )
        self.n_new += len(samples)

    def get_new_data(self):
        n = self.n_new
        self.news.append(n)
        self.n_new = 0
        return self.sw.unfold_buffer()[-n:]

    def on_data_processing_too_slow(self):
        pass

    def on_humidity_changed(self, humidity):
        pass

    def on_implant_control_value_changed(self, control_value):
        pass

    def on_implant_voltage_changed(self, voltage_V):
        pass

    def on_primary_coil_current_changed(self, current_mA):
        pass

    def on_stimulation_function_finished(self, num_executed_functions):
        pass

    def on_stimulation_state_changed(self, is_stimulating):
        pass

    def on_temperature_changed(self, temperature):
        pass

    def on_connection_state_changed(self, connection_type, connection_state):
        pass

    def on_error(self, error_description):
        pass


# NOTE: I am not using global variables for the buffers
#
@dataclass
class TestListener(pyapi.ImplantListener):
    buffer: list = field(default_factory=list)
    cntr_buffer: list = field(default_factory=list)
    is_measument_active: bool = False
    n_new: int = 0
    news: list[int] = field(default_factory=list)

    def reset_buffers(self):
        self.buffer = []
        self.cntr_buffer = []

    def on_measurement_state_changed(self, is_measuring: bool):
        self.is_measument_active = is_measuring

    def on_data(self, sample: pyapi.Sample):
        samples = sample.measurements
        self.buffer.append(samples)
        self.cntr_buffer.append(sample.measurement_counter)
        self.n_new += len(samples)

    def get_new_data(self):
        n = self.n_new
        self.news.append(n)
        self.n_new = 0

        return self.buffer[-n:]

    # NOTE: for this abstract class we need to implement some dummies
    # TODO: --> Ask why this structure is necessary (IMHO no need for abstract classes if there is no multiple inheritance, use protocols instead!)
    def on_data_processing_too_slow(self):
        pass

    def on_humidity_changed(self, humidity):
        pass

    def on_implant_control_value_changed(self, control_value):
        pass

    def on_implant_voltage_changed(self, voltage_V):
        pass

    def on_primary_coil_current_changed(self, current_mA):
        pass

    def on_stimulation_function_finished(self, num_executed_functions):
        pass

    def on_stimulation_state_changed(self, is_stimulating):
        pass

    def on_temperature_changed(self, temperature):
        pass

    def on_connection_state_changed(self, connection_type, connection_state):
        pass

    def on_error(self, error_description):
        pass


if __name__ == "__main__":
    from ct_bic.device import get_device
    import time

    with get_device() as implant:
        listener = CTListener()
        implant.register_listener(listener)
        listener.reset_buffers()
        # Systems needs a bit to get ready, else to many samples are missing
        time.sleep(1)

        implant.start_measurement(
            [], pyapi.RecordingAmplificationFactor.AMPLIFICATION_57_5dB, True
        )

        time.sleep(5)
        implant.stop_measurement()

        buffer = listener.sw.unfold_buffer()
        cntr_buffer = listener.sw.unfold_buffer_t()

        print(f"{len(buffer)=}")
        print(f"{len(cntr_buffer)=}")