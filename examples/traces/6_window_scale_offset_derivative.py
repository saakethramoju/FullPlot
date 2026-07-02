"""
Trace windowing, scaling, offsetting, and derivatives.

These helpers are intentionally simple. FullPlot does not manage units; scale()
and offset() are just numeric transformations chosen by the user.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

pc_psia = file.trace(y="PCMC_1", x="time", name="PCMC [psia]")
mainstage_pc = pc_psia.window(start=0.0, stop=12.5, name="Mainstage PCMC")
pc_pa = mainstage_pc.scale(6894.76, name="Mainstage PCMC [Pa]")
pc_psig = mainstage_pc.offset(-14.7, name="Mainstage PCMC [psig]")
dpc_dt = mainstage_pc.derivative(name="dPCMC/dt")

fplt.plot(
    [mainstage_pc, pc_psig],
    xlabel="Time [s]",
    ylabel="Pressure",
    title="Windowed Pressure with Offset",
    save=example_dir / "6_window_offset.png",
    show=False,
)

fplt.plot(
    pc_pa,
    xlabel="Time [s]",
    ylabel="Pressure [Pa]",
    title="Scaled Pressure Trace",
    save=example_dir / "6_scale.png",
    show=False,
)

fplt.plot(
    dpc_dt,
    xlabel="Time [s]",
    ylabel="dP/dt [psia/s]",
    title="Pressure Derivative",
    save=example_dir / "6_derivative.png",
    show=False,
)
