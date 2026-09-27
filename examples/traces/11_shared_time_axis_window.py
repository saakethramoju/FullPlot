"""Window one shared TimeAxis so every attached trace follows the same range."""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
file = fplt.open(ensure_trace_demo_file())

time = file.time("time")
time.zero_at(0.05)

pcmc = file.trace(y="PCMC_1", x=time, name="PCMC")
oipt = file.trace(y="OIPT", x=time, name="OIPT")
fipt = file.trace(y="FIPT", x=time, name="FIPT")

time.window(2.0, 8.0)

fplt.plot(
    [pcmc, oipt, fipt],
    xlabel="Model Time [s]",
    ylabel="Pressure [psia]",
    title="Shared TimeAxis Window",
    save=example_dir / "11_shared_time_axis_window.png",
    show=False,
)
