import pytest
import os

print(os.getcwd())
print(os.listdir())

from ct_bic.utils.global_setup import pyapi, log_file_name, enable_log


@pytest.fixture
def factory():
    return pyapi.ImplantFactory(enable_log, log_file_name)


def test_indentification(factory: pyapi.ImplantFactory):
    ext_unit_infos = factory.load_external_unit_infos()
    implant_info = None
    ext_unit_info = None

    for info in ext_unit_infos:
        try:
            implant_info = factory.load_implant_info(info)
            ext_unit_info = info
        except RuntimeError as e:
            raise e

    assert isinstance(
        implant_info, pyapi.implantinfo.ImplantInfo
    ), f"Could not retreive an implant info - {implant_info=}"

    assert isinstance(
        ext_unit_info, pyapi.externalunitinfo.ExternalUnitInfo
    ), f"Could not retreive an external unit info - {ext_unit_info=}"


def test_creating_the_implant(factory: pyapi.ImplantFactory):
    ext_unit_infos = factory.load_external_unit_infos()
    implant_info = None
    ext_unit_info = None

    for info in ext_unit_infos:
        try:
            implant_info = factory.load_implant_info(info)
            ext_unit_info = info
        except RuntimeError as e:
            raise e

    implant = factory.create(ext_unit_info, implant_info)
    assert isinstance(
        implant, pyapi.implant.Implant
    ), f"Could not create implant with - {implant=}, {ext_unit_info=}, {implant_info}"
    implant.set_implant_power(False)
