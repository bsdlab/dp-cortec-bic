import pyxdf
from pathlib import Path

xdfs = list(Path(r"C:\Users\matth\data\sub-P001").rglob("*.xdf"))

data = pyxdf.load_xdf(xdfs[0])

b = bb.unfold_buffer()
a = data[0][1]["time_series"]

import matplotlib.pyplot as plt
import numpy as np


def plot_first_n(a, b, n=4, dt=0):
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(n, 1, sharex=True, sharey=True)
    for ax, d, da in zip(axs, b.T, a.T):
        ax.plot(np.arange(len(d)), d)
        ax.plot(np.arange(len(da)) + 6882, da)

    plt.show()
