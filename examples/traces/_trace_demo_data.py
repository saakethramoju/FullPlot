"""
Synthetic hotfire-style trace data for FullPlot trace examples.

The file layout is intentionally flat and generic:

    trace_demo.h5
        time
        PCMC_1
        PCMC_2
        PCMC_3
        PCMC_NOISY
        PCMC_DROPOUT
        PBTC_1
        SHAFT_RPM_1
        MOV_CMD
        ...

Every channel is just an HDF5 dataset. FullPlot does not need special test-data
objects, unit conversion, or DAQ metadata to plot and process these traces.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


EXAMPLE_DIR = Path(__file__).resolve().parent
TRACE_FILE = EXAMPLE_DIR / "trace_demo.h5"


def smooth_step(t, start, stop):
    x = np.clip((t - start) / (stop - start), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def command_pulse(t, start, stop, level=1.0):
    return level * (smooth_step(t, start, start + 0.05) - smooth_step(t, stop, stop + 0.05))


def first_order_lag(signal, tau, dt):
    y = np.empty_like(signal)
    y[0] = signal[0]
    alpha = dt / (tau + dt)

    for i in range(1, len(signal)):
        y[i] = y[i - 1] + alpha * (signal[i] - y[i - 1])

    return y


def noisy(rng, signal, sigma, drift=0.0, spike_probability=0.0, spike_sigma=0.0):
    signal = np.asarray(signal, dtype=float)
    y = signal + rng.normal(0.0, sigma, signal.size)

    if drift:
        y += np.cumsum(rng.normal(0.0, drift, signal.size))

    if spike_probability:
        spikes = rng.random(signal.size) < spike_probability
        y[spikes] += rng.normal(0.0, spike_sigma, spikes.sum())

    return y


def write_channel(h5, name, value, units="", description=""):
    dataset = h5.create_dataset(name, data=np.asarray(value, dtype=float), compression="gzip", shuffle=True)
    dataset.attrs["units"] = units
    dataset.attrs["description"] = description


def create_trace_demo_file(filename: str | Path = TRACE_FILE, overwrite: bool = True) -> Path:
    filename = Path(filename)

    if filename.exists() and not overwrite:
        return filename

    rng = np.random.default_rng(42)
    dt = 0.005
    time = np.arange(-5.0, 20.0 + dt, dt)

    # Commands and operating envelope.
    purge_cmd = command_pulse(time, -4.5, 14.0)
    ign_cmd = command_pulse(time, 0.0, 0.6)
    mov_cmd = command_pulse(time, -0.30, 12.00)
    mfv_cmd = command_pulse(time, 0.05, 11.85)
    vent_cmd = command_pulse(time, 12.1, 18.0)

    startup = smooth_step(time, 0.05, 0.55)
    shutdown = 1.0 - smooth_step(time, 11.8, 12.4)
    mainstage = startup * shutdown
    throttle = 1.0 + mainstage * (0.018 * np.sin(2.0 * np.pi * 0.32 * time) + 0.006 * np.sin(2.0 * np.pi * 1.20 * time + 0.5))
    ignition_bump = 1.0 + 0.18 * np.exp(-((time - 0.42) / 0.13) ** 2)

    # Chamber pressure sensors in psia.
    pc_nominal = 14.7 + mainstage * (300.0 * throttle * ignition_bump)
    pc_nominal += (time > 12.2) * 35.0 * np.exp(-np.maximum(time - 12.2, 0.0) / 0.65)
    pc_nominal = first_order_lag(pc_nominal, tau=0.025, dt=dt)
    roughness = mainstage * (2.0 * np.sin(2.0 * np.pi * 180.0 * time) + 0.8 * np.sin(2.0 * np.pi * 74.0 * time + 1.1))

    pcmc_1 = noisy(rng, pc_nominal + roughness, sigma=0.85, drift=0.0005, spike_probability=0.0006, spike_sigma=10.0)
    pcmc_2 = noisy(rng, first_order_lag(pc_nominal * 0.997 + roughness * 0.7, tau=0.035, dt=dt), sigma=1.10, drift=0.0004)
    pcmc_3 = noisy(rng, first_order_lag(pc_nominal * 1.006 + roughness * 0.5, tau=0.045, dt=dt), sigma=0.95, drift=0.0007)
    pcmc_noisy = noisy(rng, pc_nominal, sigma=4.5, spike_probability=0.001, spike_sigma=25.0)

    pcmc_dropout = pcmc_1.copy()
    pcmc_dropout[(time > 0.15) & (time < 0.25)] = np.nan

    pcmc_stuck = pcmc_2.copy()
    stuck_index = np.searchsorted(time, 12.8)
    pcmc_stuck[stuck_index:] = pcmc_stuck[stuck_index]

    # Injector/manifold pressures.
    oipt = 14.7 + mainstage * (390.0 * throttle) + 20.0 * smooth_step(time, -3.8, -1.2)
    fipt = 14.7 + mainstage * (360.0 * throttle) + 15.0 * smooth_step(time, -3.5, -1.0)
    oipt += mainstage * 4.0 * np.sin(2.0 * np.pi * 34.0 * time)
    fipt += mainstage * 3.2 * np.sin(2.0 * np.pi * 29.0 * time + 0.7)
    oipt = noisy(rng, first_order_lag(oipt, tau=0.05, dt=dt), sigma=1.0, drift=0.0004)
    fipt = noisy(rng, first_order_lag(fipt, tau=0.05, dt=dt), sigma=1.0, drift=0.0004)

    # Preburner/turbine temperatures in K.
    pbtc_base = 295.0 + mainstage * (880.0 + 18.0 * np.sin(2.0 * np.pi * 0.22 * time))
    pbtc_base += 120.0 * np.exp(-((time - 0.35) / 0.18) ** 2) * mainstage
    pbtc_1 = noisy(rng, first_order_lag(pbtc_base, tau=0.18, dt=dt), sigma=3.0, drift=0.0003)
    pbtc_2 = noisy(rng, first_order_lag(pbtc_base * 0.985 + 12.0, tau=0.22, dt=dt), sigma=3.5, drift=0.0003)
    pbtc_3 = noisy(rng, first_order_lag(pbtc_base * 1.015 - 8.0, tau=0.16, dt=dt), sigma=4.0, drift=0.0004)
    titc_1 = noisy(rng, first_order_lag(330.0 + mainstage * 720.0, tau=0.25, dt=dt), sigma=2.8)
    egt_1 = noisy(rng, first_order_lag(300.0 + mainstage * 520.0, tau=0.35, dt=dt), sigma=2.5)

    # Shaft speed and flow meters.
    shaft_speed = first_order_lag(mainstage * (28500.0 * throttle) + mainstage * 850.0 * np.exp(-((time - 0.65) / 0.22) ** 2), tau=0.16, dt=dt)
    shaft_rpm_1 = noisy(rng, shaft_speed, sigma=22.0, drift=0.004)
    shaft_rpm_2 = noisy(rng, shaft_speed * 1.002 - 35.0, sigma=28.0, drift=0.004)

    ox_mdot = noisy(rng, first_order_lag(mainstage * (3.25 * throttle) + mainstage * 0.20 * np.exp(-((time - 0.45) / 0.18) ** 2), tau=0.08, dt=dt), sigma=0.012)
    fuel_mdot = noisy(rng, first_order_lag(mainstage * (1.52 * throttle) + mainstage * 0.08 * np.exp(-((time - 0.55) / 0.20) ** 2), tau=0.08, dt=dt), sigma=0.008)
    mr = np.divide(ox_mdot, fuel_mdot, out=np.full_like(ox_mdot, np.nan), where=fuel_mdot > 0.05)

    # Temperature traces.
    lox_line_tc_1 = noisy(rng, first_order_lag(295.0 - 205.0 * smooth_step(time, -3.8, -0.4) + 8.0 * mainstage, tau=0.35, dt=dt), sigma=0.8)
    fuel_line_tc_1 = noisy(rng, first_order_lag(295.0 + 18.0 * mainstage, tau=0.70, dt=dt), sigma=0.5)
    chamber_wall_tc_1 = noisy(rng, first_order_lag(295.0 + 175.0 * mainstage, tau=1.10, dt=dt), sigma=0.7)
    nozzle_wall_tc_1 = noisy(rng, first_order_lag(295.0 + 115.0 * mainstage, tau=1.40, dt=dt), sigma=0.7)

    # Vibration traces.
    vibe_x = mainstage * (0.25 * np.sin(2.0 * np.pi * 180.0 * time) + 0.12 * np.sin(2.0 * np.pi * 360.0 * time + 0.4))
    vibe_y = mainstage * (0.20 * np.sin(2.0 * np.pi * 175.0 * time + 0.2) + 0.10 * np.sin(2.0 * np.pi * 350.0 * time + 1.1))
    vibe_z = mainstage * (0.30 * np.sin(2.0 * np.pi * 190.0 * time + 0.7) + 0.15 * np.sin(2.0 * np.pi * 380.0 * time + 0.3))
    vibe_x = noisy(rng, vibe_x, sigma=0.035, spike_probability=0.0005, spike_sigma=1.0)
    vibe_y = noisy(rng, vibe_y, sigma=0.035, spike_probability=0.0005, spike_sigma=1.0)
    vibe_z = noisy(rng, vibe_z, sigma=0.040, spike_probability=0.0005, spike_sigma=1.2)

    # Stored reference limit traces. These are still plain datasets.
    pcmc_redline = np.full_like(time, 400.0)
    pcmc_yellowline = np.full_like(time, 350.0)
    pcmc_blueline = np.full_like(time, 100.0)
    pbtc_redline = np.full_like(time, 1300.0)
    shaft_rpm_redline = np.full_like(time, 32000.0)

    channels = {
        "PURGE_CMD": (purge_cmd, "fraction", "Purge command"),
        "IGN_CMD": (ign_cmd, "fraction", "Igniter command"),
        "MOV_CMD": (mov_cmd, "fraction", "Main oxidizer valve command"),
        "MFV_CMD": (mfv_cmd, "fraction", "Main fuel valve command"),
        "VENT_CMD": (vent_cmd, "fraction", "Vent command"),
        "PCMC_1": (pcmc_1, "psia", "Chamber pressure 1"),
        "PCMC_2": (pcmc_2, "psia", "Chamber pressure 2"),
        "PCMC_3": (pcmc_3, "psia", "Chamber pressure 3"),
        "PCMC_NOISY": (pcmc_noisy, "psia", "High-noise chamber pressure"),
        "PCMC_DROPOUT": (pcmc_dropout, "psia", "Chamber pressure with missing samples"),
        "PCMC_STUCK": (pcmc_stuck, "psia", "Chamber pressure with post-shutdown stuck value"),
        "OIPT": (oipt, "psia", "Oxidizer injector pressure"),
        "FIPT": (fipt, "psia", "Fuel injector pressure"),
        "PBTC_1": (pbtc_1, "K", "Preburner temperature 1"),
        "PBTC_2": (pbtc_2, "K", "Preburner temperature 2"),
        "PBTC_3": (pbtc_3, "K", "Preburner temperature 3"),
        "TITC_1": (titc_1, "K", "Turbine inlet temperature"),
        "EGT_1": (egt_1, "K", "Exhaust gas temperature"),
        "SHAFT_RPM_1": (shaft_rpm_1, "rpm", "Turbopump shaft speed 1"),
        "SHAFT_RPM_2": (shaft_rpm_2, "rpm", "Turbopump shaft speed 2"),
        "OX_MDOT": (ox_mdot, "kg/s", "Oxidizer mass flow"),
        "FUEL_MDOT": (fuel_mdot, "kg/s", "Fuel mass flow"),
        "MR": (mr, "", "Mixture ratio"),
        "LOX_LINE_TC_1": (lox_line_tc_1, "K", "LOX line temperature"),
        "FUEL_LINE_TC_1": (fuel_line_tc_1, "K", "Fuel line temperature"),
        "CHAMBER_WALL_TC_1": (chamber_wall_tc_1, "K", "Chamber wall temperature"),
        "NOZZLE_WALL_TC_1": (nozzle_wall_tc_1, "K", "Nozzle wall temperature"),
        "VIBE_X": (vibe_x, "g", "Vibration X"),
        "VIBE_Y": (vibe_y, "g", "Vibration Y"),
        "VIBE_Z": (vibe_z, "g", "Vibration Z"),
        "PCMC_REDLINE": (pcmc_redline, "psia", "Chamber pressure redline"),
        "PCMC_YELLOWLINE": (pcmc_yellowline, "psia", "Chamber pressure warning line"),
        "PCMC_BLUELINE": (pcmc_blueline, "psia", "Chamber pressure lower reference line"),
        "PBTC_REDLINE": (pbtc_redline, "K", "Preburner temperature redline"),
        "SHAFT_RPM_REDLINE": (shaft_rpm_redline, "rpm", "Shaft speed redline"),
    }

    filename.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(filename, "w") as h5:
        h5.attrs["description"] = "Synthetic rocket engine hotfire sensor traces"
        h5.attrs["sample_rate_hz"] = 1.0 / dt
        h5.attrs["time_units"] = "s"

        write_channel(h5, "time", time, units="s", description="Time")

        for name, (value, units, description) in channels.items():
            write_channel(h5, name, value, units=units, description=description)

    return filename


def ensure_trace_demo_file() -> Path:
    if not TRACE_FILE.exists():
        create_trace_demo_file(TRACE_FILE, overwrite=True)

    return TRACE_FILE
