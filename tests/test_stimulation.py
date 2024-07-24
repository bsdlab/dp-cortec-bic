import pytest

from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log
from ct_bic.listener import TestListener


# Cannot work with cached fixture as otherwise the tests will fail with CorTecs API
@pytest.fixture
def implant():
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
    implant = factory.create(ext_unit_info, implant_info)

    listener = TestListener()
    implant.register_listener(listener)

    yield implant

    # destructor part
    try:
        implant.stop_measurement()
    except RuntimeError:
        print("Measurement already stopped")

    implant.set_implant_power(False)


@pytest.fixture
def stimulation_command_130Hz():
    stimFactory = pyapi.StimulationCommandFactory()
    cmd = stimFactory.create_stimulation_command()
    cmd.name = "130Hz"

    # negative int in increments of 12 (>= 3060) or 24 (< 3060)
    amplitude_uA = -3060
    pulsewidth_us = 60
    dz0_us = 10
    dz1_us = 7360

    for i in range(16):
        puls_func = stimFactory.create_stimulation_function(
            amplitude_uA, pulsewidth_us, dz0_us, dz1_us
        )
        puls_func.set_repetitions(255, 1)
        puls_func.set_virtual_stim_electrodes(([0], [1]), False)
        puls_func.name = f"StandardPulses_{i}"
        cmd.append(puls_func)

    stimulation_command_130Hz = cmd

    return cmd


def test_valid_stimulation(
    implant: pyapi.Implant,
    stimulation_command_130Hz: pyapi.stimulationcommand.StimulationCommand,
):
    implant.enqueue_stimulation_command(
        stimulation_command_130Hz,
        pyapi.StimulationMode.STIMMODE_PERSISTENT_CMD_PRELOADING,
    )

    implant.start_stimulation()

    pass
