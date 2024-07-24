from dareplane_utils.logging.logger import get_logger

logger = get_logger("CorTec Logger")


# --- For debugging without network print
from logging import StreamHandler, Formatter
from dareplane_utils.logging.logger import default_dareplane_config

for hdl in logger.handlers:
    logger.removeHandler(hdl)

sh = StreamHandler()
sh.formatter = Formatter(
    default_dareplane_config["formatters"]["dareplane_standard"]["format"]
)
logger.addHandler(sh)
logger.setLevel(10)
logger.debug("Debug is on")
