"""
Create redline, yellowline, blueline, and greenline traces.

FullPlot roles are visualization hints only. A redline here is not an abort
condition; it is just a Trace with role="redline" so it is styled clearly on the
plot.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

pc = file.trace(y="PCMC_1", x="time", name="PCMC_1")

redline = fplt.Trace.constant("PCMC Abort Redline", x=pc.x, y=400.0, role="redline")
yellowline = fplt.Trace.constant("PCMC Warning", x=pc.x, y=350.0, role="yellowline")
blueline = fplt.Trace.constant("PCMC Low Reference", x=pc.x, y=100.0, role="blueline")
greenline = fplt.Trace.constant("PCMC Nominal Target", x=pc.x, y=300.0, role="greenline")

fplt.plot(
    [pc, redline, yellowline, blueline, greenline],
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    title="Generated Limit/Reference Traces",
    save=example_dir / "3_create_redlines_bluelines.png",
    show=False,
)
