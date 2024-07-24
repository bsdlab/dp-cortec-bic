import pytest
import time

import plotly.express as px


from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log
from ct_bic.listener import buffers_to_df, TestListener


# Cannot work with cached fixture as otherwise the tests will fail with CorTecs API
@pytest.fixture
def implant_and_listener():
    factory = pyapi.ImplantFactory(enable_log, log_file_name)
    ext_unit_infos = factory.load_external_unit_infos()
    implant_info = None
    ext_unit_info = None

    for info in ext_unit_infos:
        try:
            implant_info = factory.load_implant_info(info)
            ext_unit_info = info
        except RuntimeError as e:
            raise e

    assert (
        implant_info is not None
    ), "No implant info found - is implant connected with other process?"
    implant = factory.create(ext_unit_info, implant_info)

    listener = TestListener()
    implant.register_listener(listener)

    yield (implant, listener)

    # destructor part
    try:
        implant.stop_measurement()
    except RuntimeError:
        print("Measurement already stopped")

    implant.set_implant_power(False)


def test_impedances(implant_and_listener: pyapi.implant.Implant):
    implant, listener = implant_and_listener
    imps = [
        implant.calculate_impedance(i)
        for i in range(implant.implant_info.channel_count)
    ]

    assert all(
        [isinstance(i, float) for i in imps]
    ), f"Impedances are not all floats, {imps=}"


def test_data_recording(implant_and_listener: pyapi.implant.Implant):
    implant, listener = implant_and_listener
    listener.reset_buffers()

    # Systems needs a bit to get ready, else to many samples are missing
    time.sleep(1)

    implant.start_measurement(
        [], pyapi.RecordingAmplificationFactor.AMPLIFICATION_57_5dB, True
    )
    time.sleep(2)
    implant.stop_measurement()

    buffer = listener.buffer
    cntr_buffer = listener.cntr_buffer

    try:
        assert len(buffer) > 1800, f"Buffer too short, {len(buffer)=}"
        assert cntr_buffer[-1] > 1800, f"Buffer too short, {len(buffer)=}"
        assert cntr_buffer[-1] > len(
            buffer
        ), "Counter is shorter than data received"
    except AssertionError as e:
        df = buffers_to_df(buffer, cntr_buffer)
        df.to_csv(
            f"./tests/test_data/recording_test_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            index=False,
        )
        raise e


def test_n_sec_drop_rate(
    implant_and_listener: pyapi.implant.Implant,
    plot: bool = True,
    nsleep: float = 30,
):
    implant, listener = implant_and_listener
    listener.reset_buffers()
    # Systems needs a bit to get ready, else to many samples are missing
    time.sleep(1)

    implant.start_measurement(
        [], pyapi.RecordingAmplificationFactor.AMPLIFICATION_57_5dB, True
    )

    time.sleep(nsleep)
    implant.stop_measurement()

    buffer = listener.buffer
    cntr_buffer = listener.cntr_buffer

    print(f"{len(buffer) = }")
    print(f"{len(cntr_buffer) = }")
    try:
        assert (
            len(buffer) / cntr_buffer[-1] > 0.9
        ), f"Drop rate too high, {len(buffer)/cntr_buffer[-1]:.2%}"
    except AssertionError as e:
        df = buffers_to_df(buffer, cntr_buffer)
        df.to_csv(
            f"./tests/test_data/recording_test_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            index=False,
        )
        raise e

    # Create a histogram plot of the dropped packages
    if plot:
        df = buffers_to_df(buffer, cntr_buffer)
        df["pkg_dropped"] = df["cntr"].diff().fillna(1) - 1
        dg = df.loc[df.pkg_dropped != 0, ["cntr", "pkg_dropped"]]
        dg["type"] = "single_drops"

        fig = px.histogram(
            dg,
            x="pkg_dropped",
            hover_data=["cntr"],
            nbins=int(dg.pkg_dropped.max()),
            #     points="all",
        )
        fig = fig.add_annotation(
            x=dg.pkg_dropped.max(),
            y=dg.pkg_dropped.value_counts().max(),
            text=f"Total number of dropped in {nsleep}s:<br>{int(dg.pkg_dropped.sum())} [{int(dg.pkg_dropped.sum()) / dg.cntr.max():.2%}]",
            showarrow=False,
        )
        fig.show()

        df.to_csv(
            f"./tests/test_data/recording_test_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            index=False,
        )


def plot_test_recording_psd():
    import numpy as np
    from scipy import signal
    import matplotlib.pyplot as plt

    scale = 1e-6
    fs = 1000
    td = np.load("./tests/test_data/test_recording_with_ref.npy")
    td = np.asarray(listener.buffer)

    fig, axs = plt.subplots(8, 4)

    for i in range(td.shape[1]):
        ax = axs.flatten()[i]
        f, Pxx_den = signal.welch(td[:, i] * scale, fs, nperseg=2048 * 16)
        ax.semilogy(f, Pxx_den, label=f"channel {i + 1}")
        ax.set_xlabel("frequency [Hz]")
        ax.set_ylabel("PSD [V^2/Hz]")
        ax.legend()

    plt.show()
