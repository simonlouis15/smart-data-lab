"""VD (viscosity / density) sensor measurement, ported from the V9 code.

This mirrors ``start_dv_sensor_and_get_queue()``, ``get_dv_measurement()`` and
``main()`` in ``V9-TC-EC/Campaign_26Jars-V9.py`` (the XtalX ``z_sensor`` D/V
sensor), but with two important differences that make it usable as a bundled
CLI sidecar:

1. No import-time side effects. The XtalX SDK (``xtalx.z_sensor``) is imported
   lazily inside :func:`open_sensor`, so this module -- and the rest of the CLI
   and the test suite -- import fine on machines without the sensor SDK or any
   hardware attached.

2. The statistical acquisition loop (:func:`collect_statistics`) is a pure
   function driven by a ``sampler`` callable, so it can be unit tested without a
   sensor by feeding it canned measurements.

The peak-center / peak-width references and tolerances (see
``backend/config/config.json`` -> "VD Routine") are used here to *validate* each
resonance fit: a reading whose peak frequency or width strays outside the
configured tolerance band is rejected and not counted, analogous to the
``m.fw_fit is not None`` guard in the original ``get_dv_measurement()``.

Cleaning, and the concurrent refill / thermal-conductivity coupling from the
original ``datagather()`` flow, are intentionally out of scope: this drives the
sensor only.
"""

from dataclasses import dataclass, asdict
import statistics
import time


@dataclass
class Measurement:
    """One accepted D/V reading."""

    viscosity_cp: float
    density_g_per_ml: float
    temp_c: float
    peak_hz: float
    peak_fwhm: float


@dataclass
class SensorConfig:
    """Sensor identification + resonance-peak validation window.

    Mirrors the "Sensor" block of the "VD Routine" config. An empty
    ``serial_number`` means auto-detect (``find_one`` with no serial).
    """

    serial_number: str = ""
    verbose: bool = False
    track_impedance: bool = False
    peak_center_reference: float = 32776.181
    peak_center_tolerance: float = 100.0
    peak_width_reference: float = 2.174
    peak_width_tolerance: float = 20.0


@dataclass
class RoutineConfig:
    """Statistical-sampling parameters. Mirrors the "Routine" config block."""

    measurements: int = 5          # initial samples to seed the window
    batch_size: int = 5            # rolling window size for the std-dev check
    viscosity_std: float = 0.1     # convergence threshold on viscosity std
    density_std: float = 0.1       # convergence threshold on density std
    warmup_secs: float = 25.0      # settle time before the first read
    max_samples: int = 100         # safety cap so we never loop forever


def is_valid(m: Measurement, cfg: SensorConfig) -> bool:
    """Reject fits whose resonance peak is outside the configured tolerance."""
    return (
        abs(m.peak_hz - cfg.peak_center_reference) <= cfg.peak_center_tolerance
        and abs(m.peak_fwhm - cfg.peak_width_reference) <= cfg.peak_width_tolerance
    )


def collect_statistics(sampler, sensor_cfg: SensorConfig, routine_cfg: RoutineConfig) -> dict:
    """Run the V9 adaptive-averaging loop against a ``sampler`` callable.

    ``sampler`` is called with no arguments and returns a :class:`Measurement`
    or ``None`` (no reading yet / bad fit). Ported from ``main()``:

      1. Seed ``measurements`` valid readings.
      2. Slide a window of ``batch_size`` readings; if both the viscosity and
         density std devs are within threshold, stop and average that window.
      3. Otherwise take another reading and slide the window forward.

    Unlike the original (which could loop forever), this stops after
    ``max_samples`` total accepted readings and reports ``converged: False``.
    """
    batch_size = max(1, routine_cfg.batch_size)
    seed = max(routine_cfg.measurements, batch_size)

    samples: list[Measurement] = []
    attempts = [0]  # total sampler() calls, so we terminate even if it never
    # returns a valid (or any) reading.

    def next_valid():
        """Pull readings until one passes validation, bounded by max_samples.

        Every call to ``sampler`` counts against ``max_samples`` -- including
        ``None`` (no reading) and rejected fits -- so an unresponsive or badly
        calibrated sensor can never spin forever.
        """
        while attempts[0] < routine_cfg.max_samples:
            attempts[0] += 1
            m = sampler()
            if m is None:
                continue
            if not is_valid(m, sensor_cfg):
                continue
            samples.append(m)
            return m
        return None

    for _ in range(seed):
        if next_valid() is None:
            break

    start, end = 0, batch_size
    converged = False
    v_std = d_std = float("nan")

    while len(samples) >= end:
        window = samples[start:end]
        v_std = statistics.pstdev([m.viscosity_cp for m in window])
        d_std = statistics.pstdev([m.density_g_per_ml for m in window])

        if v_std <= routine_cfg.viscosity_std and d_std <= routine_cfg.density_std:
            converged = True
            break

        if len(samples) >= routine_cfg.max_samples:
            break

        if next_valid() is None:
            break

        start += 1
        end += 1

    window = samples[start:end] if samples else []
    if not window:
        return {
            "converged": False,
            "num_samples": len(samples),
            "samples": [],
            "error": "No valid measurements collected",
        }

    return {
        "converged": converged,
        "num_samples": len(samples),
        "mean_viscosity_cp": statistics.fmean(m.viscosity_cp for m in window),
        "mean_density_g_per_ml": statistics.fmean(m.density_g_per_ml for m in window),
        "mean_temp_c": statistics.fmean(m.temp_c for m in window),
        "viscosity_std": v_std,
        "density_std": d_std,
        "samples": [
            {"trial": i + 1, **asdict(m)} for i, m in enumerate(samples)
        ],
    }


# ---------------------------------------------------------------------------
# Hardware-facing helpers (lazy XtalX import; not exercised by the test suite)
# ---------------------------------------------------------------------------

def _ensure_usb_backend():
    """Make a libusb backend available to pyusb's default device lookup.

    XtalX enumerates its USB sensor via ``usb.core.find()`` with the default
    backend, which relies on the OS being able to locate ``libusb-1.0``. On a
    frozen build (and on machines without a system-wide libusb) that lookup
    fails with "No backend available". We ship the DLL through the
    ``libusb-package`` wheel and prime pyusb's *cached* libusb1 backend from it
    here; pyusb caches the backend module-globally, so every subsequent default
    ``usb.core.find()`` (including the ones inside XtalX) reuses it.

    Best-effort: if anything is missing we stay silent and let XtalX surface its
    own error.
    """
    try:
        import libusb_package
        import usb.backend.libusb1

        usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    except Exception:
        pass


def _default_sweep_args(serial_number: str, verbose: bool, track_impedance: bool):
    """Recreate the argparse namespace the V9 code fed to z_common.

    The original built a parser via ``z_common.add_arguments(parser)`` and used
    the library defaults for the sweep parameters (amplitude, nfreqs, sweep /
    search times, settle_ms). We do the same so behaviour matches V9, then
    override just the serial number and the two boolean flags.
    """
    import argparse
    from xtalx.tools.z_sensor import z_common

    parser = argparse.ArgumentParser()
    z_common.add_arguments(parser)
    args = parser.parse_args([])
    args.sensor = serial_number or None
    args.verbose = verbose
    args.track_impedance = track_impedance
    return args


def _probe_usb_strings(dev):
    """Read the sensor's USB string descriptors up front, surfacing the real error.

    The XtalX SDK's ``usbcmd.Device.__init__`` reads ``usb_dev.serial_number``
    inside a ``try/except ValueError`` that only re-raises the specific
    ``'The device has no langid'`` case -- any *other* ``ValueError`` from the
    string-descriptor read is silently swallowed, leaving ``fw_version`` unset.
    The next line (``assert self.fw_version >= 0x200`` in ``tcsc_2xx.Comms``)
    then fails with the misleading ``'Comms' object has no attribute
    'fw_version'``. We do the same read here first so we can report the true
    cause and an actionable fix instead.
    """
    try:
        serial = dev.serial_number
    except ValueError as e:
        raise RuntimeError(
            f"Could not read the D/V sensor's USB string descriptors ({e}). "
            "On Windows this usually means the WinUSB/libusb driver isn't bound "
            "to the sensor, another program still has it open, or it needs a "
            "replug. Fixes: close any other XtalX software, unplug and replug "
            "the sensor, then (re)install the WinUSB driver for it (e.g. with "
            "Zadig)."
        ) from e
    if not serial:
        raise RuntimeError(
            "The D/V sensor returned an empty serial number; its USB string "
            "descriptors could not be read. Replug the sensor and ensure the "
            "WinUSB/libusb driver is installed (e.g. with Zadig)."
        )
    return serial


def _make_sensor(z_sensor, dev, **kwargs):
    """``z_sensor.make()`` wrapper that reports USB-descriptor failures clearly.

    Probes the string descriptors first, then translates the SDK's swallowed
    error (which otherwise surfaces later as ``'Comms' object has no attribute
    'fw_version'``) into an actionable message.
    """
    _probe_usb_strings(dev)
    try:
        return z_sensor.make(dev, **kwargs)
    except AttributeError as e:
        if "fw_version" in str(e):
            raise RuntimeError(
                "The D/V sensor was found on USB but its firmware/serial "
                f"descriptors could not be read (XtalX SDK error: '{e}'). This "
                "is a USB driver/permission issue on Windows: install the "
                "WinUSB driver for the sensor (e.g. via Zadig), close any other "
                "XtalX software, and replug the sensor."
            ) from e
        raise


def open_sensor(cfg: SensorConfig):
    """Find and start the D/V sensor. Returns ``(tc, pq, pt)``.

    Direct port of ``start_dv_sensor_and_get_queue()``; imports the XtalX SDK
    lazily so this module stays import-safe without it.
    """
    _ensure_usb_backend()
    import xtalx.z_sensor
    from xtalx.tools.z_sensor import z_common

    args = _default_sweep_args(cfg.serial_number, cfg.verbose, cfg.track_impedance)

    dev = _find_one(xtalx.z_sensor, args.sensor)
    tc = _make_sensor(
        xtalx.z_sensor, dev, verbose=args.verbose, yield_Y=not args.track_impedance
    )
    za, zl = z_common.parse_args(tc, args)

    pq = xtalx.z_sensor.PredicateQueue(delegate=z_common.ZDelegate(zl))
    pt = xtalx.z_sensor.PeakTracker(
        tc, za.amplitude, za.nfreqs, za.search_time_secs,
        za.sweep_time_secs, settle_ms=za.settle_ms, delegate=pq,
    )
    pt.start_threaded()
    return tc, pq, pt


def make_sampler(pq, poll_interval: float = 0.1, timeout: float = 30.0):
    """Build a ``sampler`` callable that reads one measurement off the queue.

    Mirrors ``get_dv_measurement()``: block (up to ``timeout``) for a reading
    with a valid firmware fit, then map it onto a :class:`Measurement`.
    """
    def sample():
        deadline = time.time() + timeout
        while time.time() < deadline:
            m = pq.get_measurement()
            pq.clear()
            if m is not None and m.fw_fit is not None:
                return Measurement(
                    viscosity_cp=m.viscosity_cp,
                    density_g_per_ml=m.density_g_per_ml,
                    temp_c=m.fw_fit.temp_c,
                    peak_hz=m.peak_hz,
                    peak_fwhm=m.peak_fwhm,
                )
            time.sleep(poll_interval)
        return None

    return sample


def _find_one(z_sensor, serial_number):
    """Find exactly one D/V sensor, with a clear error when none is present.

    XtalX's ``find_one`` assumes a device is attached and raises a cryptic
    ``'NoneType' object has no attribute 'bcdDevice'`` when the USB enumeration
    comes back empty. Translate that (and a ``None`` result) into a friendly
    message so the frontend can show something actionable.
    """
    try:
        dev = z_sensor.find_one(serial_number=serial_number)
    except AttributeError:
        dev = None
    if dev is None:
        target = f" (serial '{serial_number}')" if serial_number else ""
        raise RuntimeError(
            f"No XtalX D/V sensor found{target}. Is it connected and powered?"
        )
    return dev


def detect() -> dict:
    """Auto-detect a connected D/V sensor and return its serial number."""
    _ensure_usb_backend()
    import xtalx.z_sensor

    dev = _find_one(xtalx.z_sensor, None)
    tc = _make_sensor(xtalx.z_sensor, dev)
    return {"serial_number": str(tc.serial_num)}


def measure(sensor_cfg: SensorConfig, routine_cfg: RoutineConfig) -> dict:
    """Open the sensor, warm up, run the averaging loop, and return results."""
    tc, pq, pt = open_sensor(sensor_cfg)
    try:
        if routine_cfg.warmup_secs > 0:
            time.sleep(routine_cfg.warmup_secs)
        sampler = make_sampler(pq)
        result = collect_statistics(sampler, sensor_cfg, routine_cfg)
        result["serial_number"] = str(tc.serial_num)
        return result
    finally:
        stop = getattr(pt, "stop", None) or getattr(pt, "stop_threaded", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass
