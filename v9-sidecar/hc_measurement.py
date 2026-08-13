"""Heat-capacity (HC) measurement, ported from the V9 code.

This mirrors ``run_experiment()`` in ``V9-TC-EC/HCV9.py`` -- a differential
flow-calorimetry measurement: two syringe pumps (a *reference* fluid pump held
at a fixed rate and a *sample* fluid pump stepped through several flow rates)
feed a mixing cell whose temperature difference is read as a voltage from an NI
DAQ. For each sample flow rate the acquisition dwells until the voltage
stabilizes, the stabilized "step average" is recorded, and a linear regression
of (step_average - baseline) against flow rate yields the sample heat capacity.

Like ``vd_sensor.py``, this module is written so it can be bundled into the
Tauri sidecar:

1. **No import-time side effects.** ``nidaqmx`` (the DAQ SDK) is imported lazily
   inside :class:`DaqReader`, and the pumps are the hardware-free
   :class:`devices.Pump` drivers, so this module -- and the test suite -- import
   fine on machines without the DAQ SDK or any hardware attached.

2. **The stabilization + regression logic is pure.** :func:`collect_step` is
   driven by a ``sampler`` callable and :func:`compute_heat_capacity` works on
   plain numbers, so both can be unit tested without a DAQ by feeding canned
   voltages.

The exact V9 behaviour is preserved: segment means, the "at least ``min_within``
of the last ``required_stable_segments`` segments within ``voltage_threshold`` of
their mean" stabilization test, the ``EV<rate*20>A0`` pump injection scaling, and
the ``Cp = (ref_rate * Cp_ref * rho_ref) / (rho_sample * intercept)`` formula
(regressing flow rate on the baseline-subtracted signal, as the original did).
"""

from dataclasses import dataclass, field, asdict
import time


# ---------------------------------------------------------------------------
# Configuration (mirrors the hyperparameters at the top of run_experiment())
# ---------------------------------------------------------------------------

@dataclass
class StabilizationConfig:
    """Smart-injection stabilization hyperparameters.

    Mirrors ``daq_freq`` and the "Smart Injection Hyperparameters" block:
    ``seg_step_duration``, ``num_consecutive_seg``, ``max_num_seg`` and
    ``segment_variation_abs``.
    """

    daq_frequency: float = 3.0            # DAQ sample rate (Hz)
    segment_duration: float = 10.0        # seconds per stabilization segment
    required_stable_segments: int = 5     # V9 num_consecutive_seg
    max_segments: int = 15                # V9 max_num_seg (safety cap)
    voltage_threshold: float = 0.4e-6     # V9 segment_variation_abs (volts)
    min_within: int = 4                   # V9 hardcoded "count_within_threshold >= 4"


@dataclass
class ExperimentConfig:
    """Flow-rate protocol. Mirrors ``ref_pump_rate`` / ``exp_sample_pump_rates``
    / ``exp_step_duration`` in run_experiment()."""

    ref_rate: float = 0.15
    sample_flow_rates: list = field(default_factory=lambda: [0.0, 0.2, 0.3, 0.4])
    step_duration: float = 120.0  # informational; segments drive actual dwell


@dataclass
class FluidProperties:
    """Reference + sample fluid properties used in the heat-capacity formula.

    ``density_sample`` is normally taken from a preceding V/D measurement;
    ``ref_hc`` is an optional known sample heat capacity used only to report a
    validation error percentage.
    """

    density_ref: float = 988.8      # kg/m^3
    hc_ref: float = 4176.5          # J/(kg.K)
    density_sample: float = 0.0     # kg/m^3 (0 = unknown / from V/D)
    ref_hc: float = 0.0             # J/(kg.K), optional validation target


# ---------------------------------------------------------------------------
# Pure stabilization logic (hardware-free, unit tested)
# ---------------------------------------------------------------------------

def within_variation_limit(seg_means, abs_threshold, min_within=4) -> bool:
    """V9 ``within_linient_segment_variation_limit``.

    True when at least ``min_within`` of the given segment means are within
    ``abs_threshold`` (absolute) of their overall mean.
    """
    if not seg_means:
        return False
    overall_mean = sum(seg_means) / len(seg_means)
    count = sum(1 for m in seg_means if abs(m - overall_mean) <= abs_threshold)
    return count >= min_within


def collect_step(sampler, stab: StabilizationConfig) -> dict:
    """Acquire one flow-rate step until the voltage stabilizes.

    ``sampler`` is called with no arguments and returns a single voltage
    reading (float), or ``None`` when no more data is available. Ported from the
    inner ``while not step_master_cond`` loop of run_experiment():

      1. Read ``segment_duration * daq_frequency`` voltages and take their mean.
      2. Collect ``required_stable_segments`` seed segments.
      3. Then, each further segment, test the last ``required_stable_segments``
         segment means with :func:`within_variation_limit`; if they pass, the
         step is *stable* and its average is the mean of that window.
      4. Give up (step *unstable*) once ``max_segments`` is reached.

    Returns a dict with the stabilization outcome plus the full voltage/time
    trace so the frontend can plot it.
    """
    samples_per_seg = max(1, int(round(stab.segment_duration * stab.daq_frequency)))
    dt = 1.0 / stab.daq_frequency if stab.daq_frequency else 0.0

    seg_means: list[float] = []
    voltages: list[float] = []
    seg_counter = 0
    stable = False
    average = None

    while True:
        segment: list[float] = []
        for _ in range(samples_per_seg):
            v = sampler()
            if v is None:
                break
            voltages.append(float(v))
            segment.append(float(v))

        if not segment:
            break  # sampler exhausted

        seg_means.append(sum(segment) / len(segment))

        if seg_counter < stab.required_stable_segments:
            seg_counter += 1
        elif seg_counter < stab.max_segments:
            window = seg_means[-stab.required_stable_segments:]
            if within_variation_limit(window, stab.voltage_threshold, stab.min_within):
                stable = True
                average = sum(window) / len(window)
                break
            seg_counter += 1
        else:
            break  # failed to stabilize within max_segments

    times = [i * dt for i in range(len(voltages))]
    return {
        "stable": stable,
        "average": average,
        "num_segments": len(seg_means),
        "voltages": voltages,
        "times": times,
    }


def _linfit(xs, ys):
    """Least-squares slope/intercept for ``ys = slope*xs + intercept``.

    Pure-Python (no numpy) so the pure core stays dependency-free and testable.
    """
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def compute_heat_capacity(step_results, exp: ExperimentConfig, fluid: FluidProperties) -> dict:
    """Regress the stabilized step averages into a sample heat capacity.

    ``step_results`` is a list of per-step dicts each carrying ``flow_rate``,
    ``stable`` and ``average`` (as produced by :func:`collect_step` plus the
    step's flow rate). Mirrors the regression block of run_experiment():

      - baseline  = mean step-average of the valid zero-flow step(s)
      - signal    = step_average - baseline for each valid non-zero step
      - regress flow_rate onto signal (V9 fits X=signal, y=rate)
      - Cp_sample = (ref_rate * Cp_ref * rho_ref) / (rho_sample * intercept)
    """
    result = {
        "heat_capacity": None,
        "error_pct": None,
        "baseline": None,
        "slope": None,
        "intercept": None,
        "message": "",
    }

    valid = [
        (float(r["flow_rate"]), float(r["average"]))
        for r in step_results
        if r.get("stable") and r.get("average") is not None
    ]

    baseline_vals = [avg for fr, avg in valid if fr == 0]
    if not baseline_vals:
        result["message"] = "No valid baseline (zero-flow) step; cannot compute heat capacity."
        return result
    baseline = sum(baseline_vals) / len(baseline_vals)
    result["baseline"] = baseline

    sample_steps = [(fr, avg) for fr, avg in valid if fr != 0]
    if len(sample_steps) < 2:
        result["message"] = "Not enough stabilized sample-flow steps for regression (need >= 2)."
        return result

    signal = [avg - baseline for fr, avg in sample_steps]
    rates = [fr for fr, avg in sample_steps]
    slope, intercept = _linfit(signal, rates)
    result["slope"] = slope
    result["intercept"] = intercept

    if intercept == 0:
        result["message"] = "Regression intercept is zero; cannot compute heat capacity."
        return result
    if fluid.density_sample == 0:
        result["message"] = "Sample density is 0 (unknown); provide a density to compute heat capacity."
        return result

    hc = (exp.ref_rate * fluid.hc_ref * fluid.density_ref) / (fluid.density_sample * intercept)
    result["heat_capacity"] = hc
    if fluid.ref_hc:
        result["error_pct"] = (hc - fluid.ref_hc) / fluid.ref_hc * 100.0
    return result


# ---------------------------------------------------------------------------
# Hardware-facing DAQ reader (lazy nidaqmx import; not exercised by tests)
# ---------------------------------------------------------------------------

class DaqReader:
    """Thin wrapper around an NI-DAQ analog-input voltage channel.

    Direct port of the ``LoggerNI`` class in HCV9.py, but with the channel,
    sample rate and voltage range passed in instead of hardcoded, and with
    ``nidaqmx`` imported lazily so this module stays import-safe without it.
    """

    def __init__(self, port_name: str, daq_frequency: float,
                 min_val: float = -0.08, max_val: float = 0.08):
        import nidaqmx  # lazy: only needed when actually driving hardware

        self._nidaqmx = nidaqmx
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_voltage_chan(port_name, min_val=min_val, max_val=max_val)
        self.task.timing.cfg_samp_clk_timing(
            rate=daq_frequency,
            sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        )

    def read_voltage(self) -> float:
        return self.task.read()

    def close(self):
        try:
            self.task.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Orchestration: drive the pumps + DAQ through the full protocol
# ---------------------------------------------------------------------------

def _hc_inject(pump, rate: float):
    """Reproduce ``PumpInjection_pump*_HC``: stop, then ``EV<rate*20>A0``.

    The V9 HC pumps issue a plain ``T`` (stop) followed by ``EV<int(rate*20)>A0``
    (full injection toward position 0 at a speed proportional to the flow rate).
    :meth:`devices.Pump.full_injection` emits exactly that command string.
    """
    pump.stop()
    pump.full_injection(rate, position=0)


def run_measurement(
    sample_pump,
    ref_pump,
    daq: "DaqReader",
    exp: ExperimentConfig,
    stab: StabilizationConfig,
    fluid: FluidProperties,
    logger=None,
) -> dict:
    """Run the full HC protocol and return a JSON-serializable result.

    For each sample flow rate: start both pumps (sample at that rate, reference
    at ``exp.ref_rate`` -- both 0 for the baseline step), dwell until the DAQ
    voltage stabilizes, stop the pumps, and record the stabilized step average.
    Finally regress the step averages into a heat capacity.
    """
    def log(msg):
        if logger is not None:
            logger.info(msg)

    steps = []
    trace_time_offset = 0.0

    def sampler():
        return daq.read_voltage()

    try:
        for i, sample_rate in enumerate(exp.sample_flow_rates):
            ref_rate = exp.ref_rate if sample_rate != 0 else 0.0
            log(
                f"Starting step {i + 1}/{len(exp.sample_flow_rates)}: "
                f"sample rate {sample_rate} mL/min, ref rate {ref_rate} mL/min"
            )

            _hc_inject(sample_pump, sample_rate)
            _hc_inject(ref_pump, ref_rate)

            step = collect_step(sampler, stab)

            sample_pump.stop()
            ref_pump.stop()

            duration_s = round(len(step["voltages"]) / stab.daq_frequency) if stab.daq_frequency else 0
            step_record = {
                "index": i,
                "flow_rate": sample_rate,
                "ref_rate": ref_rate,
                "stable": step["stable"],
                "voltage": step["average"],
                "status": "Stable" if step["stable"] else "Unstable",
                "time_s": duration_s,
                "num_segments": step["num_segments"],
                "time_offset": trace_time_offset,
                "times": step["times"],
                "voltages": step["voltages"],
            }
            steps.append(step_record)
            trace_time_offset += duration_s

            if step["stable"]:
                log(f"Flow rate {sample_rate} mL/min -> STABLE (avg {step['average']:.4e} V)")
            else:
                log(f"Flow rate {sample_rate} mL/min -> failed to stabilize; excluded from regression")
    finally:
        try:
            sample_pump.stop()
        except Exception:
            pass
        try:
            ref_pump.stop()
        except Exception:
            pass
        daq.close()

    regression = compute_heat_capacity(steps, exp, fluid)
    if regression.get("heat_capacity") is not None:
        log(f"Heat Capacity = {regression['heat_capacity']:.6g} J/(kg.K)")
    elif regression.get("message"):
        log(regression["message"])

    return {
        "success": True,
        "converged": regression.get("heat_capacity") is not None,
        "heat_capacity": regression.get("heat_capacity"),
        "error_pct": regression.get("error_pct"),
        "baseline_voltage": regression.get("baseline"),
        "slope": regression.get("slope"),
        "intercept": regression.get("intercept"),
        "message": regression.get("message", ""),
        "steps": [
            {k: v for k, v in s.items() if k not in ("times", "voltages")}
            for s in steps
        ],
        "trace": [
            {"index": s["index"], "flow_rate": s["flow_rate"],
             "times": s["times"], "voltages": s["voltages"]}
            for s in steps
        ],
    }


def measure_from_payload(payload: dict, logger=None) -> dict:
    """Build the pumps + DAQ from a JSON payload and run a measurement.

    ``payload`` keys (all device configs use the same shape as
    ``backend/config/config.json``):

      - ``sample_pump`` / ``ref_pump``: pump device configs (Port, Baudrate, ...)
      - ``daq``: {"Port", "Frequency", "VolumeMin", "VolumeMax"}
      - ``ref_rate``, ``sample_flow_rates``, ``step_duration``
      - ``segment_duration``, ``required_stable_segments``, ``max_segments``,
        ``voltage_threshold``
      - ``fluid``: {"density_ref", "hc_ref", "density_sample", "ref_hc"}
    """
    from devices import pump_from_config

    daq_cfg = payload["daq"]
    daq_freq = float(daq_cfg.get("Frequency", 3))

    stab = StabilizationConfig(
        daq_frequency=daq_freq,
        segment_duration=float(payload.get("segment_duration", 10.0)),
        required_stable_segments=int(payload.get("required_stable_segments", 5)),
        max_segments=int(payload.get("max_segments", 15)),
        voltage_threshold=float(payload.get("voltage_threshold", 0.4e-6)),
    )
    exp = ExperimentConfig(
        ref_rate=float(payload.get("ref_rate", 0.15)),
        sample_flow_rates=[float(r) for r in payload.get("sample_flow_rates", [0.0, 0.2, 0.3, 0.4])],
        step_duration=float(payload.get("step_duration", 120.0)),
    )
    fluid_cfg = payload.get("fluid", {})
    fluid = FluidProperties(
        density_ref=float(fluid_cfg.get("density_ref", 988.8)),
        hc_ref=float(fluid_cfg.get("hc_ref", 4176.5)),
        density_sample=float(fluid_cfg.get("density_sample", 0.0)),
        ref_hc=float(fluid_cfg.get("ref_hc", 0.0)),
    )

    sample_pump = pump_from_config(payload["sample_pump"])
    ref_pump = pump_from_config(payload["ref_pump"])
    daq = DaqReader(
        daq_cfg["Port"],
        daq_freq,
        min_val=float(daq_cfg.get("VolumeMin", -0.08)),
        max_val=float(daq_cfg.get("VolumeMax", 0.08)),
    )

    try:
        return run_measurement(sample_pump, ref_pump, daq, exp, stab, fluid, logger=logger)
    finally:
        sample_pump.close()
        ref_pump.close()
