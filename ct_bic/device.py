import contextlib
from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log
from ct_bic.utils.logging import logger


@contextlib.contextmanager
def get_device() -> pyapi.implant.Implant:
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

    try:
        yield implant

    finally:
        logger.debug("Closing down implant")
        try:
            implant.stop_measurement()
        except RuntimeError:
            logger.debug("Measurement already stopped")
        implant.set_implant_power(False)
