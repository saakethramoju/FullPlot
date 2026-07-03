"""
Plot command traces from HDF5 and create new command traces from points.

role="command" uses a dash-dot step-style plot. Trace.from_points(..., mode="previous")
is useful for commands, valve positions, sequence states, and on/off histories.
"""

from pathlib import Path

import fullplot as fplt
from _trace_demo_data import ensure_trace_demo_file


example_dir = Path(__file__).resolve().parent
filename = ensure_trace_demo_file()
file = fplt.open(filename)

pc = file.trace(y="PCMC_1", x="time", name="PCMC_1")
mov_cmd = file.trace(y="MOV_CMD", x="time", name="MOV Command", role="command")
mfv_cmd = file.trace(y="MFV_CMD", x="time", name="MFV Command", role="command")

# Create a simple synthetic throttle command from time/value points.
throttle = fplt.Trace.from_points(
    "Throttle Command",
    points=[(-5.0, 0.0), (0.0, 0.0), (0.8, 1.0), (8.0, 0.95), (11.8, 0.95), (12.2, 0.0), (20.0, 0.0)],
    x=pc.x,
    mode="linear",
    role="command",
)

fplt.plot(
    [pc],
    y2=[mov_cmd, mfv_cmd, throttle],
    xlabel="Time [s]",
    ylabel="Pressure [psia]",
    y2label="Command / Fraction",
    title="Pressure with Command Traces",
    save=example_dir / "4_command_and_sequence_traces.png",
    show=False,
)
