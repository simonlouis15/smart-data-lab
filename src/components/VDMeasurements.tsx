import { useEffect, useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/16/solid';
import { invoke } from '@tauri-apps/api/core';

// ---- Config shape (mirrors the "VD Routine" section of config.json) ----
interface VdSensorConfig {
  'Serial number': string;
  Verbose: boolean;
  'Track impedance': boolean;
  'Peak center tolerance': number;
  'Peak width tolerance': number;
  'Peak center reference': number;
  'Peak width reference': number;
}

interface VdRoutineConfig {
  Measurements: number;
  'Batch size': number;
  'VSTD range': number;
  'DSTD range': number;
  'Syringe volume': number;
  'Injection time': number;
}

interface VdConfig {
  'Base Routine': { Sensor: VdSensorConfig; Routine: VdRoutineConfig };
}

// ---- Result returned by the run_vd tauri command ----
interface SidecarResult {
  success: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
}

// ---- Parsed JSON emitted by the sidecar `vd` subcommand on stdout ----
interface VdSample {
  trial: number;
  viscosity_cp: number;
  density_g_per_ml: number;
  temp_c: number;
  peak_hz: number;
  peak_fwhm: number;
}

interface VdMeasurement {
  converged: boolean;
  num_samples: number;
  serial_number?: string;
  mean_viscosity_cp?: number;
  mean_density_g_per_ml?: number;
  mean_temp_c?: number;
  viscosity_std?: number;
  density_std?: number;
  samples?: VdSample[];
  error?: string;
}

// ---- Shared style tokens (kept consistent with the rest of the app) ----
const inputCls =
  'block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6';
const checkboxCls =
  'col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto';
const submitBtnCls =
  'inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';

// Default sensor + routine values, matching config.json "VD Routine". Used
// until the saved config loads (and as a fallback if it can't be read).
const DEFAULTS = {
  serial: '',
  verbose: false,
  trackImpedance: false,
  peakCenterReference: '32776.181',
  peakCenterTolerance: '100',
  peakWidthReference: '2.174',
  peakWidthTolerance: '20',
  measurements: '5',
  batchSize: '5',
  viscosityStd: '0.1',
  densityStd: '0.1',
  warmup: '25',
  maxSamples: '100',
};

function Checkbox({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex h-6 shrink-0 items-center">
        <div className="group grid size-4 grid-cols-1">
          <input
            id={id}
            name={id}
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className={checkboxCls}
          />
          <svg
            fill="none"
            viewBox="0 0 14 14"
            className="pointer-events-none col-start-1 row-start-1 size-3.5 self-center justify-self-center stroke-white group-has-disabled:stroke-gray-950/25"
          >
            <path
              d="M3 8L6 11L11 3.5"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="opacity-0 group-has-checked:opacity-100"
            />
          </svg>
        </div>
      </div>
      <div className="text-sm/6">
        <label htmlFor={id} className="font-medium text-gray-900">
          {label}
        </label>
      </div>
    </div>
  );
}

// A labelled numeric input used across the parameter grids.
function NumberField({
  label,
  value,
  onChange,
  step = '1',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  step?: string;
}) {
  return (
    <div className="flex items-center gap-4">
      <p className="text-sm/6 text-gray-900 whitespace-nowrap">{label}:</p>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputCls}
      />
    </div>
  );
}

function ResultPanel({ result }: { result: SidecarResult | null }) {
  if (!result) return null;

  // The measurement JSON is emitted on stdout; logs go to stderr.
  let parsed: VdMeasurement | null = null;
  try {
    const line = result.stdout.trim().split('\n').filter(Boolean).pop();
    if (line) parsed = JSON.parse(line) as VdMeasurement;
  } catch {
    parsed = null;
  }

  return (
    <div className="mt-6 rounded-md border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block size-2 rounded-full ${result.success ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <p className="text-sm font-medium text-gray-900">
          {result.success ? 'Measurement complete' : 'Measurement failed'}
          {result.code !== null ? ` (exit ${result.code})` : ''}
        </p>
      </div>

      {parsed && parsed.mean_viscosity_cp !== undefined && (
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Mean Viscosity</dt>
            <dd className="text-lg font-semibold text-gray-900">
              {parsed.mean_viscosity_cp.toFixed(4)} cP
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Mean Density</dt>
            <dd className="text-lg font-semibold text-gray-900">
              {parsed.mean_density_g_per_ml?.toFixed(5)} g/mL
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Mean Temp</dt>
            <dd className="text-lg font-semibold text-gray-900">
              {parsed.mean_temp_c?.toFixed(3)} °C
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Viscosity σ</dt>
            <dd className="text-sm text-gray-700">{parsed.viscosity_std?.toFixed(4)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Density σ</dt>
            <dd className="text-sm text-gray-700">{parsed.density_std?.toFixed(5)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-widest text-gray-400">Samples</dt>
            <dd className="text-sm text-gray-700">
              {parsed.num_samples}{' '}
              <span className={parsed.converged ? 'text-green-600' : 'text-amber-600'}>
                ({parsed.converged ? 'converged' : 'not converged'})
              </span>
            </dd>
          </div>
        </dl>
      )}

      {parsed?.error && <p className="mt-3 text-sm text-red-600">{parsed.error}</p>}

      {result.stdout.trim() && (
        <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-gray-700">
          {result.stdout}
        </pre>
      )}
      {result.stderr.trim() && (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-gray-500">
          {result.stderr}
        </pre>
      )}
    </div>
  );
}

export default function VD_Measurements() {
  // ---- Sensor configuration ----
  const [serial, setSerial] = useState(DEFAULTS.serial);
  const [verbose, setVerbose] = useState(DEFAULTS.verbose);
  const [trackImpedance, setTrackImpedance] = useState(DEFAULTS.trackImpedance);
  const [peakCenterReference, setPeakCenterReference] = useState(DEFAULTS.peakCenterReference);
  const [peakCenterTolerance, setPeakCenterTolerance] = useState(DEFAULTS.peakCenterTolerance);
  const [peakWidthReference, setPeakWidthReference] = useState(DEFAULTS.peakWidthReference);
  const [peakWidthTolerance, setPeakWidthTolerance] = useState(DEFAULTS.peakWidthTolerance);

  // ---- Measurement parameters ----
  const [measurements, setMeasurements] = useState(DEFAULTS.measurements);
  const [batchSize, setBatchSize] = useState(DEFAULTS.batchSize);
  const [viscosityStd, setViscosityStd] = useState(DEFAULTS.viscosityStd);
  const [densityStd, setDensityStd] = useState(DEFAULTS.densityStd);
  const [warmup, setWarmup] = useState(DEFAULTS.warmup);
  const [maxSamples, setMaxSamples] = useState(DEFAULTS.maxSamples);

  // ---- Run state ----
  const [running, setRunning] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SidecarResult | null>(null);

  // Seed the form from the saved config on mount.
  useEffect(() => {
    (async () => {
      try {
        const cfg = await invoke<VdConfig>('get_vd_config');
        const base = cfg['Base Routine'];
        if (!base) return;
        const s = base.Sensor;
        const r = base.Routine;
        if (s) {
          setSerial(s['Serial number'] ?? DEFAULTS.serial);
          setVerbose(Boolean(s.Verbose));
          setTrackImpedance(Boolean(s['Track impedance']));
          setPeakCenterReference(String(s['Peak center reference']));
          setPeakCenterTolerance(String(s['Peak center tolerance']));
          setPeakWidthReference(String(s['Peak width reference']));
          setPeakWidthTolerance(String(s['Peak width tolerance']));
        }
        if (r) {
          setMeasurements(String(r.Measurements));
          setBatchSize(String(r['Batch size']));
          setViscosityStd(String(r['VSTD range']));
          setDensityStd(String(r['DSTD range']));
        }
      } catch (err) {
        // Non-fatal: fall back to the DEFAULTS already in state.
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  async function autoDetect() {
    setDetecting(true);
    setError(null);
    try {
      const res = await invoke<SidecarResult>('run_vd', { params: { action: 'detect' } });
      if (!res.success) {
        setError(res.stderr.trim() || 'Auto-detect failed');
        return;
      }
      const line = res.stdout.trim().split('\n').filter(Boolean).pop();
      const parsed = line ? (JSON.parse(line) as { serial_number?: string }) : null;
      if (parsed?.serial_number) setSerial(parsed.serial_number);
      else setError('No sensor detected');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetecting(false);
    }
  }

  async function runMeasurement() {
    // Validate numeric inputs up front so we fail before hitting hardware.
    const numeric: Record<string, string> = {
      'Peak center reference': peakCenterReference,
      'Peak center tolerance': peakCenterTolerance,
      'Peak width reference': peakWidthReference,
      'Peak width tolerance': peakWidthTolerance,
      'Initial samples': measurements,
      'Statistical batch size': batchSize,
      'Viscosity std dev': viscosityStd,
      'Density std dev': densityStd,
      'Warm-up': warmup,
      'Max samples': maxSamples,
    };
    for (const [label, raw] of Object.entries(numeric)) {
      if (raw.trim() === '' || Number.isNaN(Number(raw))) {
        setError(`${label} must be a number`);
        return;
      }
    }

    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await invoke<SidecarResult>('run_vd', {
        params: {
          action: 'measure',
          serial: serial.trim(),
          verbose,
          trackImpedance,
          peakCenterReference: Number(peakCenterReference),
          peakCenterTolerance: Number(peakCenterTolerance),
          peakWidthReference: Number(peakWidthReference),
          peakWidthTolerance: Number(peakWidthTolerance),
          measurements: Math.floor(Number(measurements)),
          batchSize: Math.floor(Number(batchSize)),
          viscosityStd: Number(viscosityStd),
          densityStd: Number(densityStd),
          warmup: Number(warmup),
          maxSamples: Math.floor(Number(maxSamples)),
        },
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">
            Viscosity / Density Measurement
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Configure and run viscosity and density measurements using the XtalX
            sensor.
          </h3>
        </div>
      </header>

      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">
          Sensor Configuration
        </h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <fieldset>
            <div className="flex mt-6 space-x-6">
              <Checkbox id="verbose" label="Verbose Mode" checked={verbose} onChange={setVerbose} />
              <Checkbox
                id="track-impedance"
                label="Track Impedance"
                checked={trackImpedance}
                onChange={setTrackImpedance}
              />
            </div>
          </fieldset>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8 mt-4">
            <div className="flex items-center gap-4 sm:col-span-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Serial Number:
              </p>
              <input
                id="serial-number"
                name="serial-number"
                type="text"
                autoComplete="off"
                placeholder="Blank = auto-detect"
                value={serial}
                onChange={(e) => setSerial(e.target.value)}
                className={inputCls}
              />
              <button
                type="button"
                onClick={autoDetect}
                disabled={detecting}
                className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 whitespace-nowrap"
              >
                {detecting ? 'Detecting…' : 'Auto-Detect'}
              </button>
            </div>
          </div>

          {/* Resonance-peak validation window (rejects bad fits) */}
          <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-gray-400">
            Resonance Peak Validation
          </p>
          <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <NumberField
              label="Peak Center Reference (Hz)"
              value={peakCenterReference}
              onChange={setPeakCenterReference}
              step="0.001"
            />
            <NumberField
              label="Peak Center Tolerance (Hz)"
              value={peakCenterTolerance}
              onChange={setPeakCenterTolerance}
              step="0.1"
            />
            <NumberField
              label="Peak Width Reference"
              value={peakWidthReference}
              onChange={setPeakWidthReference}
              step="0.001"
            />
            <NumberField
              label="Peak Width Tolerance"
              value={peakWidthTolerance}
              onChange={setPeakWidthTolerance}
              step="0.1"
            />
          </div>
        </div>
      </div>

      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">
          Load Chemical Composition
        </h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="flex items-center gap-6 flex-wrap sm:col-span-3">
            <div className="flex items-center gap-4 sm:col-span-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Number of Chemicals:
              </p>
              <div className="grid grid-cols-1">
                <select
                  id="country"
                  name="country"
                  autoComplete="country-name"
                  className="col-start-1 row-start-1 w-56 appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                >
                  <option>1</option>
                  <option>2</option>
                  <option>3</option>
                </select>
                <ChevronDownIcon
                  aria-hidden="true"
                  className="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4"
                />
              </div>
            </div>

            <div className="flex gap-3 items-center">
              <div className="flex h-6 shrink-0 items-center">
                <div className="group grid size-4 grid-cols-1">
                  <input
                    id="clean-first"
                    name="clean-first"
                    type="checkbox"
                    className={checkboxCls}
                  />
                  <svg
                    fill="none"
                    viewBox="0 0 14 14"
                    className="pointer-events-none col-start-1 row-start-1 size-3.5 self-center justify-self-center stroke-white group-has-disabled:stroke-gray-950/25"
                  >
                    <path
                      d="M3 8L6 11L11 3.5"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="opacity-0 group-has-checked:opacity-100"
                    />
                  </svg>
                </div>
              </div>
              <label htmlFor="clean-first" className="text-sm/6 font-medium text-gray-900">
                Clean First
              </label>
            </div>

            <div className="flex gap-3 items-center">
              <div className="flex h-6 shrink-0 items-center">
                <div className="group grid size-4 grid-cols-1">
                  <input
                    id="load-composition"
                    name="load-composition"
                    type="checkbox"
                    className={checkboxCls}
                  />
                  <svg
                    fill="none"
                    viewBox="0 0 14 14"
                    className="pointer-events-none col-start-1 row-start-1 size-3.5 self-center justify-self-center stroke-white group-has-disabled:stroke-gray-950/25"
                  >
                    <path
                      d="M3 8L6 11L11 3.5"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="opacity-0 group-has-checked:opacity-100"
                    />
                  </svg>
                </div>
              </div>
              <label htmlFor="load-composition" className="text-sm/6 font-medium text-gray-900">
                Load Composition
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
            <div className="sm:col-span-3">
              <div className="mt-2">
                <div className="flex items-center gap-4 sm:col-span-3">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    Starting Sheet:
                  </p>
                  <input
                    id="starting-sheet"
                    name="starting-sheet"
                    type="text"
                    className={inputCls}
                  />
                </div>
              </div>
            </div>

            <div className="sm:col-span-3">
              <div className="mt-2">
                <div className="flex items-center gap-4 sm:col-span-3">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    Ending Sheet:
                  </p>
                  <input
                    id="ending-sheet"
                    name="ending-sheet"
                    type="text"
                    className={inputCls}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8 mt-4">
            <div className="flex items-center gap-4 sm:col-span-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Compositions File:
              </p>
              <input
                id="compositions-file"
                name="compositions-file"
                type="text"
                autoComplete="off"
                className={inputCls}
              />
              <button
                type="button"
                className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Browse
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Measurement Parameters ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">
          Measurement Parameters
        </h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <NumberField label="Initial Samples" value={measurements} onChange={setMeasurements} />
            <NumberField label="Statistical Batch Size" value={batchSize} onChange={setBatchSize} />
            <NumberField
              label="Viscosity Std Dev"
              value={viscosityStd}
              onChange={setViscosityStd}
              step="0.01"
            />
            <NumberField
              label="Density Std Dev"
              value={densityStd}
              onChange={setDensityStd}
              step="0.01"
            />
            <NumberField label="Warm-up (s)" value={warmup} onChange={setWarmup} step="1" />
            <NumberField label="Max Samples" value={maxSamples} onChange={setMaxSamples} step="1" />
          </div>
        </div>
      </div>

      <div className="ml-auto mt-8 flex justify-end">
        <button
          type="button"
          onClick={runMeasurement}
          disabled={running}
          className={submitBtnCls}
        >
          {running ? 'Measuring…' : 'Run Measurement'}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <ResultPanel result={result} />
    </div>
  );
}
