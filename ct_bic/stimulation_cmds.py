from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log
from ct_bic.utils.logging import logger


def check_implant(implant: pyapi.implant.Implant):
    try:
        _ = implant.humidity
    except RuntimeError as err:
        logger.error("Implant is most likely not connected - please validate")
        raise err


def get_single_pulse_stim_cmd(
    implant: pyapi.implant.Implant,
    amplitude_uA: int = 3060,
    pulsewidth_us: int = 60,
    dz0_us: int = 10,
    dz1_us: int = 7360,
    stim_channel: int = 0,
    return_channel: int = 1,
) -> pyapi.stimulationcommand.StimulationCommand:
    check_implant(implant)

    stimFactory = pyapi.StimulationCommandFactory()
    cmd = stimFactory.create_stimulation_command()
    cmd.name = "130Hz"
    #
    # # negative int in increments of 12 (>= 3060) or 24 (< 3060)
    # amplitude_uA = -3060
    # pulsewidth_us = 60
    # dz0_us = 10
    # dz1_us = 7360

    pulse_func = stimFactory.create_stimulation_function(
        amplitude_uA, pulsewidth_us, dz0_us, dz1_us
    )
    pulse_func.set_repetitions(1, 1)

    # src, dest, use_ground
    pulse_func.set_virtual_stim_electrodes(
        ([stim_channel], [return_channel]), False
    )
    cmd.append(pulse_func)

    # validate the cmd
    cmd_check = implant.is_stimulation_command_valid(cmd)

    # cmd_check will be a tuple with the last element being an ''
    assert all(
        [e or e == "" for e in cmd_check]
    ), f"Stim command not valid: {cmd_check=}"

    return cmd


def get_nsec_130Hz_stim(
    implant: pyapi.implant.Implant,
    time_s: float = 2,
    stim_channel: int = 0,
    return_channel: int = 1,
) -> pyapi.stimulationcommand.StimulationCommand:
    check_implant(implant)

    stimFactory = pyapi.StimulationCommandFactory()
    cmd = stimFactory.create_stimulation_command()
    cmd.name = "130Hz"

    # negative int in increments of 12 (>= 3060) or 24 (< 3060)
    amplitude_uA = 3060
    pulsewidth_us = 60
    dz0_us = 10
    dz1_us = 7360

    pulse_func = stimFactory.create_stimulation_function(
        amplitude_uA, pulsewidth_us, dz0_us, dz1_us
    )

    pulse_func.set_virtual_stim_electrodes(
        ([stim_channel], [return_channel]), True
    )

    npulses, nbursts, nrep, act_time = calc_npulse_nbust_nrep(time_s)
    pulse_func.set_repetitions(npulses, nbursts)

    # pulse repetitions, burst repetitions
    for i in range(nrep):
        # src, dest, use_ground
        cmd.append(pulse_func)

        # TODO: Adjust the last npulse and nbursts to match the final difference
        # Also put this into a separate function

    # validate the cmd
    cmd_check = implant.is_stimulation_command_valid(cmd)

    # cmd_check will be a tuple with the last element being an ''
    assert all(
        [e or e == "" for e in cmd_check]
    ), f"Stim command not valid: {cmd_check=}"

    return cmd


def calc_npulse_nbust_nrep(
    time_s: float, target_freq: float = 130
) -> tuple[int, int, int, float]:
    """
    Calculate the number of pulses, bursts, and repetitions for a given
    stimulation time in seconds. Note: this will output value potentially
    rounded to an integer multiple of the npulses.

    Parameters
    ----------
    time_s : float

    target_freq : float


    Returns
    -------
    tuple[int, int, int, float]
        (npulses, nbursts, nreps, actual_time_s)
    """

    dt = 1 / target_freq
    if time_s < dt:
        return 1, 1, 1, dt  # one pulse, just once
    else:
        ntotal = int(time_s // dt)
        npulses = min(ntotal, 255)
        nbursts = min(ntotal // npulses + 1, 255)
        ntimes = (ntotal // npulses // nbursts) + 1

        return npulses, nbursts, ntimes, (npulses * nbursts * ntimes * dt)


if __name__ == "__main__":
    from ct_bic.device import get_device
    import time

    nsec = 30
    with get_device() as implant:
        cmd = get_nsec_130Hz_stim(implant, nsec)
        implant.enqueue_stimulation_command(
            cmd,
            pyapi.StimulationMode.STIMMODE_PERSISTENT_CMD_PRELOADING,
        )

        implant.start_stimulation()

        time.sleep(nsec)

        implant.stop_stimulation()
