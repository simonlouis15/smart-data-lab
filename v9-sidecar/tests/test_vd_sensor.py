"""Tests for the VD (viscosity/density) sensor logic in ``vd_sensor.py``.

The hardware-facing helpers (``open_sensor``/``measure``/``detect``) need the
XtalX SDK and a physical sensor, so they're not exercised here. Instead we test
the two pieces that carry the real logic and are hardware-free:

  - :func:`vd_sensor.is_valid` -- the resonance-peak validation window.
  - :func:`vd_sensor.collect_statistics` -- the V9 adaptive-averaging loop,
    driven by a fake ``sampler`` that yields canned measurements.

We also check the ``vd`` CLI wiring by faking ``vd_sensor.measure``/``detect``.
"""

import json

import pytest

import vd_sensor
from vd_sensor import Measurement, SensorConfig, RoutineConfig


def _meas(v, d, t=25.0, peak_hz=32776.181, peak_fwhm=2.174):
    return Measurement(
        viscosity_cp=v, density_g_per_ml=d, temp_c=t,
        peak_hz=peak_hz, peak_fwhm=peak_fwhm,
    )


def _sampler_from(values):
    """A sampler that yields the given measurements in order, then None."""
    it = iter(values)

    def sample():
        return next(it, None)

    return sample


# ---------------------------------------------------------------------------
# is_valid: resonance-peak validation window
# ---------------------------------------------------------------------------

def test_is_valid_accepts_reading_inside_tolerance():
    cfg = SensorConfig()
    assert vd_sensor.is_valid(_meas(1.0, 0.8, peak_hz=32800.0, peak_fwhm=2.2), cfg)


def test_is_valid_rejects_off_center_peak():
    cfg = SensorConfig()  # center ref 32776.181, tol 100
    assert not vd_sensor.is_valid(_meas(1.0, 0.8, peak_hz=33000.0), cfg)


def test_is_valid_rejects_wide_peak():
    cfg = SensorConfig()  # width ref 2.174, tol 20
    assert not vd_sensor.is_valid(_meas(1.0, 0.8, peak_fwhm=40.0), cfg)


# ---------------------------------------------------------------------------
# collect_statistics: convergence behaviour
# ---------------------------------------------------------------------------

def test_converges_on_stable_readings():
    # Five identical readings -> std devs are 0 -> converges immediately.
    sampler = _sampler_from([_meas(1.0, 0.80) for _ in range(5)])
    result = vd_sensor.collect_statistics(
        sampler, SensorConfig(), RoutineConfig(measurements=5, batch_size=5)
    )

    assert result["converged"] is True
    assert result["num_samples"] == 5
    assert result["mean_viscosity_cp"] == pytest.approx(1.0)
    assert result["mean_density_g_per_ml"] == pytest.approx(0.80)
    assert result["viscosity_std"] == pytest.approx(0.0)


def test_slides_window_until_noisy_readings_settle():
    # First readings are noisy (window std too high), later ones are stable.
    noisy = [_meas(1.0, 0.80), _meas(2.0, 0.90), _meas(1.0, 0.80),
             _meas(2.0, 0.90), _meas(1.0, 0.80)]
    stable = [_meas(1.5, 0.85) for _ in range(5)]
    sampler = _sampler_from(noisy + stable)

    result = vd_sensor.collect_statistics(
        sampler, SensorConfig(),
        RoutineConfig(measurements=5, batch_size=5, viscosity_std=0.1, density_std=0.1),
    )

    assert result["converged"] is True
    # The converged window is the trailing stable block.
    assert result["mean_viscosity_cp"] == pytest.approx(1.5)
    assert result["viscosity_std"] == pytest.approx(0.0)


def test_reports_not_converged_when_capped():
    # Perpetually noisy readings; max_samples stops the loop.
    def sample():
        sample.n += 1
        return _meas(1.0 if sample.n % 2 else 5.0, 0.80)
    sample.n = 0

    result = vd_sensor.collect_statistics(
        sampler=sample, sensor_cfg=SensorConfig(),
        routine_cfg=RoutineConfig(measurements=5, batch_size=5, max_samples=12),
    )

    assert result["converged"] is False
    assert result["num_samples"] == 12


def test_invalid_readings_are_skipped_not_counted():
    # Two off-center (invalid) readings interleaved; only valid ones count.
    seq = [
        _meas(1.0, 0.80),
        _meas(9.9, 9.9, peak_hz=99999.0),   # invalid -> skipped
        _meas(1.0, 0.80),
        _meas(9.9, 9.9, peak_fwhm=99.0),    # invalid -> skipped
        _meas(1.0, 0.80),
        _meas(1.0, 0.80),
        _meas(1.0, 0.80),
    ]
    result = vd_sensor.collect_statistics(
        _sampler_from(seq), SensorConfig(),
        RoutineConfig(measurements=5, batch_size=5),
    )

    assert result["converged"] is True
    assert result["num_samples"] == 5  # the 5 valid readings
    assert result["mean_viscosity_cp"] == pytest.approx(1.0)


def test_no_valid_measurements_returns_error():
    result = vd_sensor.collect_statistics(
        _sampler_from([]), SensorConfig(), RoutineConfig()
    )
    assert result["converged"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# CLI wiring for the `vd` subcommand (measure/detect), sensor faked out
# ---------------------------------------------------------------------------

def test_cli_vd_detect_prints_serial(monkeypatch, capsys):
    import cli

    monkeypatch.setattr(vd_sensor, "detect", lambda: {"serial_number": "ABC123"})
    cli.main(["vd", "--action", "detect"])

    out = json.loads(capsys.readouterr().out)
    assert out == {"serial_number": "ABC123"}


def test_cli_vd_measure_forwards_config(monkeypatch, capsys):
    import cli

    captured = {}

    def fake_measure(sensor_cfg, routine_cfg):
        captured["sensor"] = sensor_cfg
        captured["routine"] = routine_cfg
        return {"converged": True, "mean_viscosity_cp": 1.2,
                "mean_density_g_per_ml": 0.81, "mean_temp_c": 25.0,
                "viscosity_std": 0.0, "density_std": 0.0, "num_samples": 5,
                "samples": []}

    monkeypatch.setattr(vd_sensor, "measure", fake_measure)

    cli.main([
        "vd", "--action", "measure",
        "--serial", "SN9", "--verbose", "true", "--track-impedance", "true",
        "--measurements", "6", "--batch-size", "4",
        "--viscosity-std", "0.05", "--density-std", "0.02",
        "--peak-center-reference", "32000", "--peak-center-tolerance", "50",
    ])

    out = json.loads(capsys.readouterr().out)
    assert out["converged"] is True

    assert captured["sensor"].serial_number == "SN9"
    assert captured["sensor"].verbose is True
    assert captured["sensor"].track_impedance is True
    assert captured["sensor"].peak_center_reference == 32000
    assert captured["sensor"].peak_center_tolerance == 50
    assert captured["routine"].measurements == 6
    assert captured["routine"].batch_size == 4
    assert captured["routine"].viscosity_std == 0.05
    assert captured["routine"].density_std == 0.02
