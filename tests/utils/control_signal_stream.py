# A simple stream providing a control signal for testing

import time
import pylsl
from ct_bic.utils.logging import logger

import numpy as np

SRATE_HZ = 100
data = np.zeros(SRATE_HZ * 10)
for i in range(1, 5):
    data[SRATE_HZ * (2 * i) : SRATE_HZ * (2 * i + 1)] = 150


info = pylsl.StreamInfo(
    name="control_signal",
    type="EEG",
    channel_count=1,
    nominal_srate=SRATE_HZ,
    channel_format="float32",
    source_id=f"control_signal",
)

outlet = pylsl.StreamOutlet(info, max_buffered=1)

i = 0
dt = 1 / SRATE_HZ * 1e9
t0 = time.time_ns()
while True:
    ndt = time.time_ns() - t0
    if ndt > dt:
        t0 = time.time_ns()
        req_samples = int((ndt * 1e-9) // SRATE_HZ + 1)

        if i + req_samples > len(data):
            i = 0

        for j in range(req_samples):
            d = data[i + j]
            # logger.debug(f"Pushing: {d}")
            outlet.push_sample([d])

        i += req_samples
        i = i % len(data)
