"""Tests for the heat-capacity logic in ``hc_measurement.py``.

The hardware-facing helpers (``DaqReader``/``run_measurement``/
``measure_from_payload``) need the NI-DAQ SDK and physical pumps, so they're not
exercised here. Instead we test the hardware-free pieces that carry the real
logic:

  - :func:`hc_measurement.within_variation_limit` -- the stabilization test.
  - :func:`hc_measurement.collect_step` -- the per-flow-rate acquisition loop,
    driven by a fake ``sampler`` that yields canned voltages.
  - :func:`hc_measurement.compute_heat_capacity` -- baseline subtraction +
    regression into a heat capacity.

We also check the ``hc`` CLI wiring by faking ``measure_from_payload``.
"""

import json

import pytest

import hc_measurement
from hc_measurement import StabilizationConfig, ExperimentConfig, FluidProperties


def _sampler_from(values):
    """A sampler that yields the given voltages in order, then None."""
    it = iter(values)

    def sample():
        return next(it, None)

    return sample


# ---------------------------------------------------------------------------
# within_variation_limit
# ---------------------------------------------------------------------------

def test_within_variation_limit_all_tight():
    assert hc_measurement.within_variation_limit([1.0, 1.0, 1.0, 1.0, 1.0], 0.1)


def test_within_variation_limit_too_scattered():
    # Only 2 of 5 are within 0.1 of the mean -> below the default min_within=4.
    assert not hc_measurement.within_variation_limit([0.0, 0.0, 5.0, 5.0, 5.0], 0.1)


# ---------------------------------------------------------------------------
# collect_step
# ---------------------------------------------------------------------------

def _stab(**kw):
    base = dict(
        daq_frequency=1.0,
        segment_duration=1.0,        # 1 reading per segment (rate*duration)
        required_stable_segments=3,
        max_segments=6,
        voltage_threshold=1e-6,
        min_within=3,
    )
    base.update(kw)
    return StabilizationConfig(**base)


def test_collect_step_stabilizes_on_flat_signal():
    # 1 reading/segment; after 3 seed segments the 4th triggers the check on the
    # last 3 (all identical) -> stable.
    stab = _stab()
    result = hc_measurement.collect_step(_sampler_from([2.0] * 10), stab)
    assert result["stable"] is True
    assert result["average"] == pytest.approx(2.0)


def test_collect_step_unstable_when_noisy():
    # Alternating values never put min_within of the window inside threshold.
    stab = _stab()
    noisy = [0.0, 10.0] * 10
    result = hc_measurement.collect_step(_sampler_from(noisy), stab)
    assert result["stable"] is False
    assert result["average"] is None


def test_collect_step_records_full_trace():
    stab = _stab(segment_duration=2.0)  # 2 readings per segment
    result = hc_measurement.collect_step(_sampler_from([1.0] * 20), stab)
    assert len(result["voltages"]) == len(result["times"])
    assert result["voltages"][0] == 1.0


# ---------------------------------------------------------------------------
# compute_heat_capacity
# ---------------------------------------------------------------------------

def _step(flow_rate, average, stable=True):
    return {"flow_rate": flow_rate, "average": average, "stable": stable}


def test_compute_heat_capacity_basic():
    exp = ExperimentConfig(ref_rate=0.15, sample_flow_rates=[0.0, 0.2, 0.3, 0.4])
    fluid = FluidProperties(density_ref=1000.0, hc_ref=4000.0, density_sample=800.0)
    # Non-zero baseline is subtracted before regressing flow rate on the signal.
    steps = [
        _step(0.0, 0.5),
        _step(0.2, 1.5),
        _step(0.3, 1.9),
        _step(0.4, 2.6),
    ]
    out = hc_measurement.compute_heat_capacity(steps, exp, fluid)
    assert out["baseline"] == pytest.approx(0.5)
    # Slightly non-collinear signal -> finite intercept -> a real heat capacity.
    slope, intercept = hc_measurement._linfit([1.0, 1.4, 2.1], [0.2, 0.3, 0.4])
    expected = (0.15 * 4000.0 * 1000.0) / (800.0 * intercept)
    assert out["heat_capacity"] == pytest.approx(expected)


def test_compute_heat_capacity_with_offset_intercept():
    exp = ExperimentConfig(ref_rate=0.15)
    fluid = FluidProperties(density_ref=1000.0, hc_ref=4000.0, density_sample=800.0, ref_hc=1000.0)
    # Signal has a non-zero intercept when regressed onto flow rate.
    steps = [
        _step(0.0, 0.0),
        _step(0.2, 0.5),
        _step(0.4, 0.6),
    ]
    out = hc_measurement.compute_heat_capacity(steps, exp, fluid)
    assert out["heat_capacity"] is not None
    assert out["error_pct"] is not None


def test_compute_heat_capacity_no_baseline():
    exp = ExperimentConfig()
    fluid = FluidProperties(density_sample=800.0)
    steps = [_step(0.2, 1.0), _step(0.4, 2.0)]  # no zero-flow step
    out = hc_measurement.compute_heat_capacity(steps, exp, fluid)
    assert out["heat_capacity"] is None
    assert "baseline" in out["message"].lower()


def test_compute_heat_capacity_zero_density_guard():
    exp = ExperimentConfig()
    fluid = FluidProperties(density_sample=0.0)  # unknown density
    steps = [_step(0.0, 0.0), _step(0.2, 0.5), _step(0.4, 0.6)]
    out = hc_measurement.compute_heat_capacity(steps, exp, fluid)
    assert out["heat_capacity"] is None
    assert "density" in out["message"].lower()


# ---------------------------------------------------------------------------
# CLI wiring for the `hc` subcommand (measurement faked out)
# ---------------------------------------------------------------------------

def test_cli_hc_forwards_payload(monkeypatch, capsys):
    import cli

    captured = {}

    def fake_measure(payload, logger=None):
        captured["payload"] = payload
        return {"success": True, "converged": True, "heat_capacity": 1950.0,
                "error_pct": -1.0, "steps": [], "trace": []}

    monkeypatch.setattr(hc_measurement, "measure_from_payload", fake_measure)

    payload = {"sample_pump": {"Port": "COM14"}, "ref_pump": {"Port": "COM5"},
               "daq": {"Port": "NI9210/ai0", "Frequency": 3},
               "ref_rate": 0.15, "sample_flow_rates": [0.0, 0.2, 0.3, 0.4]}
    cli.main(["hc", "--payload", json.dumps(payload)])

    out = json.loads(capsys.readouterr().out)
    assert out["heat_capacity"] == 1950.0
    assert captured["payload"]["sample_pump"]["Port"] == "COM14"
