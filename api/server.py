import time
from fire import Fire
from dareplane_utils.default_server.server import DefaultServer

from ct_bic.utils.logging import logger
from ct_bic.main import CTManager
from ct_bic.stimulation_cmds import get_single_pulse_stim_cmd


def main(port: int = 8080, ip: str = "127.0.0.1", loglevel: int = 10):
    logger.setLevel(loglevel)

    ctm = CTManager()
    cmds = get_single_pulse_stim_cmd(ctm.implant)
    ctm.init_stim_cmds(cmds)

    # preload the stimulation command with a single pulse

    pcommand_map = {
        "START": ctm.start_recording,
        "STIM": ctm.start_stimulation,
        "STOPSTIM": ctm.stop_stimulation,
        "LISTEN": ctm.listen_for_stim_trigger,
    }

    server = DefaultServer(
        port,
        ip=ip,
        pcommand_map=pcommand_map,
        name="CorTecServer",
    )

    # initialize to start the socket
    server.init_server()
    # start processing of the server
    server.start_listening()

    # Set stop events, just in case they are not properly set
    ctm.trigger_stop_event.set()
    ctm.stop_event.set()

    # Wait a bit for the threads to be stopped
    ctm.implant.set_implant_power(False)
    time.sleep(2)
    del ctm

    return 0


if __name__ == "__main__":
    Fire(main)
