#######################################################################
# Copyright 2015-2022, CorTec GmbH
# All rights reserved.
#
# Redistribution, modification, adaptation or translation is not permitted.
#
# CorTec shall be liable a) for any damage caused by a willful, fraudulent or grossly
# negligent act, or resulting in injury to life, body or health, or covered by the
# Product Liability Act, b) for any reasonably foreseeable damage resulting from
# its breach of a fundamental contractual obligation up to the amount of the
# licensing fees agreed under this Agreement.
# All other claims shall be excluded.
# CorTec excludes any liability for any damage caused by Licensee's
# use of the Software for regular medical treatment of patients.
#######################################################################
"""This is the sixth tutorial in a series of tutorials to get the users
more familiar with the Python API. We will discuss in this tutorial the
stimulation functions and the stimulation command.
"""

# First, Import the essential modules and dependencies.
import os
import sys

# Locate the Python API
sys.path.append(os.path.abspath("../../pythonapi/src"))

import os
import sys

# Although the python stuff was installed, it seems the C-API is required to be in the path
sys.path.append(
    os.path.abspath(r"C:\Program Files\Cortec\Bicapi\pythonapi\src")
)


# Import the necessary modules from the Python API
from pythonapi import (
    ImplantFactory,
    ImplantListener,
    Sample,
    ConnectionType,
    ConnectionState,
    StimulationCommandFactory,
)


# A function to check if any external units were discovered.
def check_external_unit_available(unit_infos):
    """Check if any external unit information were discovered.

    :param unit_infos: A list of the discovered ext unit info objects.
    :return: True if any external unit were discoverd, false otherwise.
    :rtype: bool
    """

    if len(unit_infos) == 0:
        print("No External Unit was discoverable")
        return False

    print("External Units discovered")
    return True


# A function to create 4rect atoms.
def append4RectAtom(factory, sFunction, amp, duration):
    atom = factory.create_4rect_stimulation_atom(float(amp), 0, 0, 0, duration)
    sFunction.append(atom)


# A function to create a stimulation pulse function
def create_stimulation_pulse_function(
    factory, pulseAmp, pulseDuration, deadZone0Dur, deadZone1Dur
):
    stimFunc = factory.create_stimulation_function()
    counterPulseAmp = -1 / 4 * pulseAmp
    counterPulseDuration = 4 * pulseDuration

    append4RectAtom(factory, stimFunc, pulseAmp, pulseDuration)
    append4RectAtom(factory, stimFunc, 0.0, deadZone0Dur)
    append4RectAtom(factory, stimFunc, counterPulseAmp, counterPulseDuration)
    append4RectAtom(factory, stimFunc, 0.0, deadZone0Dur)
    append4RectAtom(factory, stimFunc, 0.0, deadZone1Dur)

    return stimFunc


if __name__ == "__main__":
    # Create an instance of the implant factory by enabling the log mode and
    # writting all events in example_log.log.
    log_file_name = "example_log.log"
    factory = ImplantFactory(True, log_file_name)

    # Load discoverable external unit information
    ext_unit_infos = factory.load_external_unit_infos()

    # Declare help variables.
    implant_info = None
    ext_unit_info = None

    # Retrieve the implant information for all discoverable
    # external units, if any were discovered.
    if check_external_unit_available(ext_unit_infos):
        for info in ext_unit_infos:
            try:
                implant_info = factory.load_implant_info(info)
                ext_unit_info = info
            except RuntimeError as e:
                print(f"{info.device_id}/???")
                raise e

    # Connect to the implant.
    print("Trying to connect to implant")
    implant = factory.create(ext_unit_info, implant_info)
    print("Connection successful")

    stim_factory = StimulationCommandFactory()
    cmd = stim_factory.create_stimulation_command()

    pulse_func = stim_factory.create_stimulation_function(
        3000.0,
        60,
        10,
        7360
        # 1000.0, 400, 2550, 2550
    )
    pulse_func.set_repetitions(10, 1)
    pulse_func.set_virtual_stim_electrodes(([0], [1]), False)
    pulse_func.name = "PulseExample"
    cmd.append(pulse_func)

    pause_func = stim_factory.create_stimulation_pause_function(30000)
    cmd.append(pause_func)

    # Start stimulating the command
    faults = implant.start_stimulation(cmd)

    # Command control
    while True:
        user_command = input("Choose an option: ")

        # Quit command.
        if "q" in user_command:
            implant.set_implant_power(False)
            sys.exit(0)
