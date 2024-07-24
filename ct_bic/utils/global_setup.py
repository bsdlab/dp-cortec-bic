# Some global setup for the project, as pip installs would also miss the C-API libraries
import os
import sys

# Although the python stuff was installed, it seems the C-API is required to be in the path
sys.path.append(
    os.path.abspath(r"C:\Program Files\Cortec\Bicapi\pythonapi\src")
)

import pythonapi as pyapi

from ctypes import c_bool

enable_log: c_bool = c_bool(True)
log_file_name = "./logs/test.log"
