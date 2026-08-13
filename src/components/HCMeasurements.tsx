import { useEffect, useMemo, useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/16/solid';
import { invoke } from '@tauri-apps/api/core';

// ---- Config shapes (mirror backend/config/config.json) ----
interface SerialConfig {
  Port: string;
  Baudrate: number;
  Bytesize: number;
  Parity: string;
  Stopbits: number;
  Timeout: number;
  Xonxoff: boolean;
  Rtscts: boolean;
  Dsrdtr: boolean;
  WriteTimeout: number;
}

interface PumpConfig extends SerialConfig {
  'Pump Number': number;
  'Flow Rate': number;
}

interface DaqConfig {
  Port: string;
  Frequency: number;
  VolumeMin: number;
  VolumeMax: number;
}

// ---- Result returned by the run_hc tauri command ----
interface SidecarResult {
  success: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
}

// ---- Parsed JSON emitted by the sidecar `hc` subcommand on stdout ----
interface HcStep {
  index: number;
  flow_rate: number;
  ref_rate: number;
  stable: boolean;
  voltage: number | null;
  status: string;
  time_s: number;
  num_segments: number;
  time_offset: number;
}

interface HcTrace {
  index: number;
  flow_rate: number;
  times: number[];
  voltages: number[];
}

interface HcResult {
  success: boolean;
  converged: boolean;
  heat_capacity: number | null;
  error_pct: number | null;
  baseline_voltage: number | null;
  slope: number | null;
  intercept: number | null;
  message: string;
  steps: HcStep[];
  trace: HcTrace[];
}

// ---- Shared style tokens (kept consistent with the rest of the app) ----
const inputCls =
  'block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6';
const selectCls =
  'col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6';
const checkboxCls =
  'col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto';
const submitBtnCls =
  'inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';
const browseBtnCls =
  'rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';

// Defaults, mirroring the V9 HCV9.py run_experiment() hyperparameters.
const DEFAULTS = {
  batchName: 'Unk',
  sampleFlowRates: ['0', '0.2', '0.3', '0.4'],
  refDensity: '988.8',
  refFlowRate: '0.15',
  refHeatCapacity: '4176.5',
  sampleDensity: '0',
  sampleRefHc: '1968.9',
  segmentDuration: '14',
  requiredStableSegments: '10',
  voltageThreshold: '4e-7',
  maxSegments: '15',
  xLabel: 'Time',
  yLabel: 'Voltage',
  xLimit: '500',
  yMin: '-1e-05',
  yMax: '1e-05',
  title: 'Live Data Visualization',
};

function Dropdown({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1">
      <select className={selectCls} value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
      <ChevronDownIcon
        aria-hidden="true"
        className="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4"
      />
    </div>
  );
}

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
    <div className="flex gap-3 items-center">
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
      <label htmlFor={id} className="text-sm/6 font-medium text-gray-900">
        {label}
      </label>
    </div>
  );
}

// A labelled field with the label to the left of the control (used throughout).
function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex items-center gap-4">
      <p className="text-sm/6 text-gray-900 whitespace-nowrap">{label}</p>
      {children}
      {hint && <span className="text-xs italic text-gray-400 whitespace-nowrap">{hint}</span>}
    </div>
  );
}

// ---- Live data / results chart (SVG line plot of the voltage trace) ----
function TraceChart({
  trace,
  xLabel,
  yLabel,
  title,
  xLimit,
  yMin,
  yMax,
}: {
  trace: HcTrace[];
  xLabel: string;
  yLabel: string;
  title: string;
  xLimit: number;
  yMin: number;
  yMax: number;
}) {
  const width = 760;
  const height = 320;
  const pad = { top: 36, right: 20, bottom: 44, left: 70 };

  // Flatten the per-step traces into a single continuous series using each
  // step's time offset so the plot reads left-to-right across the run.
  const points = useMemo(() => {
    const pts: { x: number; y: number }[] = [];
    let offset = 0;
    for (const step of trace) {
      for (let i = 0; i < step.times.length; i++) {
        pts.push({ x: offset + step.times[i], y: step.voltages[i] });
      }
      const last = step.times.length ? step.times[step.times.length - 1] : 0;
      offset += last;
    }
    return pts;
  }, [trace]);

  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const xScale = (x: number) => pad.left + (xLimit > 0 ? (x / xLimit) * plotW : 0);
  const yRange = yMax - yMin || 1;
  const yScale = (y: number) => pad.top + plotH - ((y - yMin) / yRange) * plotH;

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.x).toFixed(2)} ${yScale(p.y).toFixed(2)}`)
    .join(' ');

  const yTicks = 5;
  const xTicks = 5;

  return (
    <div className="mt-4 rounded-md border border-gray-300 bg-white p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
        <text
          x={width / 2}
          y={20}
          textAnchor="middle"
          className="fill-gray-900 text-sm font-semibold"
        >
          {title}
        </text>

        {/* Axes */}
        <line
          x1={pad.left}
          y1={pad.top}
          x2={pad.left}
          y2={pad.top + plotH}
          className="stroke-gray-400"
          strokeWidth={1}
        />
        <line
          x1={pad.left}
          y1={pad.top + plotH}
          x2={pad.left + plotW}
          y2={pad.top + plotH}
          className="stroke-gray-400"
          strokeWidth={1}
        />

        {/* Y grid + ticks */}
        {Array.from({ length: yTicks + 1 }).map((_, i) => {
          const v = yMin + (yRange * i) / yTicks;
          const y = yScale(v);
          return (
            <g key={`y${i}`}>
              <line
                x1={pad.left}
                y1={y}
                x2={pad.left + plotW}
                y2={y}
                className="stroke-gray-100"
                strokeWidth={1}
              />
              <text x={pad.left - 8} y={y + 3} textAnchor="end" className="fill-gray-500 text-[10px]">
                {v.toExponential(1)}
              </text>
            </g>
          );
        })}

        {/* X ticks */}
        {Array.from({ length: xTicks + 1 }).map((_, i) => {
          const v = (xLimit * i) / xTicks;
          const x = xScale(v);
          return (
            <text
              key={`x${i}`}
              x={x}
              y={pad.top + plotH + 16}
              textAnchor="middle"
              className="fill-gray-500 text-[10px]"
            >
              {Math.round(v)}
            </text>
          );
        })}

        {/* Axis labels */}
        <text
          x={pad.left + plotW / 2}
          y={height - 6}
          textAnchor="middle"
          className="fill-gray-600 text-xs"
        >
          {xLabel}
        </text>
        <text
          x={16}
          y={pad.top + plotH / 2}
          textAnchor="middle"
          transform={`rotate(-90 16 ${pad.top + plotH / 2})`}
          className="fill-gray-600 text-xs"
        >
          {yLabel}
        </text>

        {points.length > 0 && (
          <path d={path} fill="none" className="stroke-blue-600" strokeWidth={1.5} />
        )}
      </svg>
    </div>
  );
}

function statusColor(status: string) {
  const s = status.toLowerCase();
  if (s === 'stable') return 'text-green-600';
  if (s === 'unstable') return 'text-amber-600';
  return 'text-gray-600';
}

// Parse the loguru progress lines the sidecar writes to stderr into log rows.
function parseLog(stderr: string): { time: string; message: string; tone: string }[] {
  return stderr
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      // loguru default: "2026-08-06 20:16:42.491 | INFO | ... - message"
      const parts = line.split(' | ');
      let time = '';
      let message = line;
      if (parts.length >= 3) {
        const ts = parts[0];
        time = ts.includes(' ') ? ts.split(' ')[1] : ts;
        message = parts.slice(2).join(' | ');
        const dash = message.indexOf(' - ');
        if (dash !== -1) message = message.slice(dash + 3);
      }
      const lower = message.toLowerCase();
      let tone = 'text-gray-700';
      if (lower.includes('stable')) tone = 'text-green-600';
      else if (lower.includes('fail') || lower.includes('error') || lower.includes('stopped'))
        tone = 'text-red-600';
      else if (lower.includes('starting') || lower.includes('heat capacity')) tone = 'text-blue-600';
      return { time, message, tone };
    });
}

export default function HC_Measurements() {
  // ---- Device configs ----
  const [pumps, setPumps] = useState<Record<string, PumpConfig>>({});
  const [daqs, setDaqs] = useState<Record<string, DaqConfig>>({});

  // ---- Experiment configuration ----
  const [refPump, setRefPump] = useState('');
  const [samplePump, setSamplePump] = useState('');
  const [daq, setDaq] = useState('');
  const [batchName, setBatchName] = useState(DEFAULTS.batchName);
  const [saveRegression, setSaveRegression] = useState(true);
  const [saveStepAverages, setSaveStepAverages] = useState(true);
  const [regressionFile, setRegressionFile] = useState('');
  const [stepAverageFile, setStepAverageFile] = useState('');
  const [sampleFlowRates, setSampleFlowRates] = useState<string[]>(DEFAULTS.sampleFlowRates);

  // ---- Load chemical composition ----
  const [numChemicals, setNumChemicals] = useState('11');
  const [cleanFirst, setCleanFirst] = useState(false);
  const [loadComposition, setLoadComposition] = useState(true);
  const [startingSheet, setStartingSheet] = useState('DIK');
  const [endingSheet, setEndingSheet] = useState('');
  const [compositionsFile, setCompositionsFile] = useState('');

  // ---- Fluid properties ----
  const [refDensity, setRefDensity] = useState(DEFAULTS.refDensity);
  const [refFlowRate, setRefFlowRate] = useState(DEFAULTS.refFlowRate);
  const [refHeatCapacity, setRefHeatCapacity] = useState(DEFAULTS.refHeatCapacity);
  const [sampleDensity, setSampleDensity] = useState(DEFAULTS.sampleDensity);
  const [sampleRefHc, setSampleRefHc] = useState(DEFAULTS.sampleRefHc);

  // ---- Stabilization parameters ----
  const [segmentDuration, setSegmentDuration] = useState(DEFAULTS.segmentDuration);
  const [requiredStableSegments, setRequiredStableSegments] = useState(
    DEFAULTS.requiredStableSegments
  );
  const [voltageThreshold, setVoltageThreshold] = useState(DEFAULTS.voltageThreshold);
  const [maxSegments, setMaxSegments] = useState(DEFAULTS.maxSegments);

  // ---- Visualization settings ----
  const [xLabel, setXLabel] = useState(DEFAULTS.xLabel);
  const [yLabel, setYLabel] = useState(DEFAULTS.yLabel);
  const [xLimit, setXLimit] = useState(DEFAULTS.xLimit);
  const [yMin, setYMin] = useState(DEFAULTS.yMin);
  const [yMax, setYMax] = useState(DEFAULTS.yMax);
  const [title, setTitle] = useState(DEFAULTS.title);
  // Applied chart settings (updated via "Update Graph").
  const [chartSettings, setChartSettings] = useState({
    xLabel: DEFAULTS.xLabel,
    yLabel: DEFAULTS.yLabel,
    title: DEFAULTS.title,
    xLimit: Number(DEFAULTS.xLimit),
    yMin: Number(DEFAULTS.yMin),
    yMax: Number(DEFAULTS.yMax),
  });

  // ---- Run state ----
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SidecarResult | null>(null);

  // Seed the pump + DAQ pickers from the saved config on mount.
  useEffect(() => {
    (async () => {
      try {
        const p = await invoke<Record<string, PumpConfig>>('get_pump_configs');
        setPumps(p);
        const names = Object.keys(p);
        // Default to the HC-specific pumps when present.
        setRefPump(names.find((n) => n.toLowerCase().includes('reference')) ?? names[0] ?? '');
        setSamplePump(
          names.find((n) => n.toLowerCase().includes('hc sample')) ??
            names.find((n) => n.toLowerCase().includes('sample')) ??
            names[0] ??
            ''
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();

    (async () => {
      try {
        const d = await invoke<Record<string, DaqConfig>>('get_daq_configs');
        setDaqs(d);
        const names = Object.keys(d);
        if (names.length > 0) setDaq(names[0]);
      } catch (err) {
        // Non-fatal: DAQ section may be absent in older configs.
      }
    })();
  }, []);

  function applyGraphSettings() {
    setChartSettings({
      xLabel,
      yLabel,
      title,
      xLimit: Number(xLimit) || 0,
      yMin: Number(yMin),
      yMax: Number(yMax),
    });
  }

  function updateFlowRate(i: number, v: string) {
    setSampleFlowRates((prev) => prev.map((r, idx) => (idx === i ? v : r)));
  }

  function addFlowRate() {
    setSampleFlowRates((prev) => [...prev, '']);
  }

  function removeFlowRate(i: number) {
    setSampleFlowRates((prev) => (prev.length > 1 ? prev.filter((_, idx) => idx !== i) : prev));
  }

  const parsed: HcResult | null = useMemo(() => {
    if (!result) return null;
    try {
      const line = result.stdout.trim().split('\n').filter(Boolean).pop();
      return line ? (JSON.parse(line) as HcResult) : null;
    } catch {
      return null;
    }
  }, [result]);

  const logRows = useMemo(() => (result ? parseLog(result.stderr) : []), [result]);

  async function runMeasurement() {
    // Validate the numeric fields up front so we fail before hitting hardware.
    const numeric: Record<string, string> = {
      'Reference density': refDensity,
      'Reference flow rate': refFlowRate,
      'Reference heat capacity': refHeatCapacity,
      'Sample density': sampleDensity,
      'Segment duration': segmentDuration,
      'Required stable segments': requiredStableSegments,
      'Voltage variation threshold': voltageThreshold,
      'Max segments': maxSegments,
    };
    for (const [label, raw] of Object.entries(numeric)) {
      if (raw.trim() === '' || Number.isNaN(Number(raw))) {
        setError(`${label} must be a number`);
        return;
      }
    }

    const rates = sampleFlowRates
      .map((r) => r.trim())
      .filter((r) => r !== '')
      .map(Number);
    if (rates.some((r) => Number.isNaN(r))) {
      setError('Sample flow rates must all be numbers');
      return;
    }
    if (!rates.includes(0)) {
      setError('Sample flow rates must include a 0 (baseline) step');
      return;
    }

    const sample = pumps[samplePump];
    const reference = pumps[refPump];
    const daqCfg = daqs[daq];
    if (!sample || !reference) {
      setError('Select both a sample and reference pump');
      return;
    }
    if (!daqCfg) {
      setError('Select a DAQ');
      return;
    }

    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await invoke<SidecarResult>('run_hc', {
        payload: {
          sample_pump: sample,
          ref_pump: reference,
          daq: daqCfg,
          ref_rate: Number(refFlowRate),
          sample_flow_rates: rates,
          segment_duration: Number(segmentDuration),
          required_stable_segments: Math.floor(Number(requiredStableSegments)),
          max_segments: Math.floor(Number(maxSegments)),
          voltage_threshold: Number(voltageThreshold),
          fluid: {
            density_ref: Number(refDensity),
            hc_ref: Number(refHeatCapacity),
            density_sample: Number(sampleDensity),
            ref_hc: sampleRefHc.trim() === '' ? 0 : Number(sampleRefHc),
          },
          save_regression: saveRegression,
          save_step_averages: saveStepAverages,
          regression_file: regressionFile,
          step_average_file: stepAverageFile,
          batch: batchName,
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
            Heat Capacity Measurement
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Configure and run heat capacity measurements using differential flow calorimetry.
          </h3>
        </div>
      </header>

      {/* ── Experiment Configuration ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">Experiment Configuration</h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-3">
            <Field label="Reference Pump:">
              <Dropdown value={refPump} onChange={setRefPump}>
                {Object.keys(pumps).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Dropdown>
            </Field>
            <Field label="Sample Pump:">
              <Dropdown value={samplePump} onChange={setSamplePump}>
                {Object.keys(pumps).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Dropdown>
            </Field>
            <Field label="DAQ:">
              <Dropdown value={daq} onChange={setDaq}>
                {Object.keys(daqs).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Dropdown>
            </Field>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-6">
            <Field label="Batch name:">
              <input
                type="text"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Checkbox
              id="save-regression"
              label="Save regression data"
              checked={saveRegression}
              onChange={setSaveRegression}
            />
            <Checkbox
              id="save-step-averages"
              label="Save step averages data"
              checked={saveStepAverages}
              onChange={setSaveStepAverages}
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-y-4">
            <div className="flex items-center gap-4">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap w-28">Regression file:</p>
              <input
                type="text"
                value={regressionFile}
                onChange={(e) => setRegressionFile(e.target.value)}
                disabled={!saveRegression}
                className={inputCls}
              />
              <button type="button" className={browseBtnCls}>
                Browse
              </button>
            </div>
            <div className="flex items-center gap-4">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap w-28">Step average file:</p>
              <input
                type="text"
                value={stepAverageFile}
                onChange={(e) => setStepAverageFile(e.target.value)}
                disabled={!saveStepAverages}
                className={inputCls}
              />
              <button type="button" className={browseBtnCls}>
                Browse
              </button>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3 flex-wrap">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Sample Flow Rates:</p>
            {sampleFlowRates.map((rate, i) => (
              <input
                key={i}
                type="number"
                step="0.1"
                value={rate}
                onChange={(e) => updateFlowRate(i, e.target.value)}
                onDoubleClick={() => removeFlowRate(i)}
                title="Double-click to remove"
                className="w-20 rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
              />
            ))}
            <span className="text-sm/6 text-gray-500">mL/min</span>
            <button
              type="button"
              onClick={addFlowRate}
              title="Add a flow-rate step"
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              …
            </button>
          </div>
        </div>
      </div>

      {/* ── Load Chemical Composition ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">Load Chemical Composition</h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="flex items-center gap-6 flex-wrap">
            <Field label="Number of Chemicals:">
              <input
                type="number"
                min={1}
                step={1}
                value={numChemicals}
                onChange={(e) => setNumChemicals(e.target.value)}
                className="w-24 rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
              />
            </Field>
            <Checkbox
              id="clean-first"
              label="Clean First"
              checked={cleanFirst}
              onChange={setCleanFirst}
            />
            <Checkbox
              id="load-composition"
              label="Load Composition"
              checked={loadComposition}
              onChange={setLoadComposition}
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <Field label="Starting Sheet:">
              <input
                type="text"
                value={startingSheet}
                onChange={(e) => setStartingSheet(e.target.value)}
                disabled={!loadComposition}
                className={inputCls}
              />
            </Field>
            <Field label="Ending Sheet:">
              <input
                type="text"
                value={endingSheet}
                onChange={(e) => setEndingSheet(e.target.value)}
                disabled={!loadComposition}
                className={inputCls}
              />
            </Field>
          </div>

          <div className="mt-4 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Compositions File:</p>
            <input
              type="text"
              value={compositionsFile}
              onChange={(e) => setCompositionsFile(e.target.value)}
              disabled={!loadComposition}
              className={inputCls}
            />
            <button type="button" className={browseBtnCls}>
              Browse
            </button>
          </div>
        </div>
      </div>

      {/* ── Fluid Properties ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">Fluid Properties</h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">
            Reference Fluid
          </p>
          <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <Field label="Density (kg/m³):">
              <input
                type="number"
                step="0.1"
                value={refDensity}
                onChange={(e) => setRefDensity(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Flow Rate (mL/min):">
              <input
                type="number"
                step="0.01"
                value={refFlowRate}
                onChange={(e) => setRefFlowRate(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Heat Capacity (J/kg·K):">
              <input
                type="number"
                step="0.1"
                value={refHeatCapacity}
                onChange={(e) => setRefHeatCapacity(e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>

          <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-gray-400">
            Sample Fluid
          </p>
          <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <Field label="Density (kg/m³):" hint="from V/D measurement">
              <input
                type="number"
                step="0.1"
                value={sampleDensity}
                onChange={(e) => setSampleDensity(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Reference HC (J/kg·K):" hint="Optional - for validation">
              <input
                type="number"
                step="0.1"
                value={sampleRefHc}
                onChange={(e) => setSampleRefHc(e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>
        </div>
      </div>

      {/* ── Stabilization Parameters ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">Stabilization Parameters</h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <Field label="Segment Duration (s):">
              <input
                type="number"
                step="1"
                value={segmentDuration}
                onChange={(e) => setSegmentDuration(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Required Stable Segments:">
              <input
                type="number"
                step="1"
                value={requiredStableSegments}
                onChange={(e) => setRequiredStableSegments(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Voltage Variation Threshold:">
              <input
                type="text"
                value={voltageThreshold}
                onChange={(e) => setVoltageThreshold(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Max Segments:">
              <input
                type="number"
                step="1"
                value={maxSegments}
                onChange={(e) => setMaxSegments(e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>
        </div>
      </div>

      {/* ── Visualization Settings ── */}
      <div className="mt-12">
        <h2 className="text-base/7 font-semibold text-gray-900">Visualization Settings</h2>

        <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
            <Field label="X Label:">
              <input
                type="text"
                value={xLabel}
                onChange={(e) => setXLabel(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="Y Label:">
              <input
                type="text"
                value={yLabel}
                onChange={(e) => setYLabel(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label="X Limit (s):">
              <input
                type="number"
                step="1"
                value={xLimit}
                onChange={(e) => setXLimit(e.target.value)}
                className={inputCls}
              />
            </Field>
            <div className="flex items-center gap-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">Y Limits:</p>
              <input
                type="text"
                value={yMin}
                onChange={(e) => setYMin(e.target.value)}
                className={inputCls}
              />
              <span className="text-sm/6 text-gray-500">to</span>
              <input
                type="text"
                value={yMax}
                onChange={(e) => setYMax(e.target.value)}
                className={inputCls}
              />
            </div>
          </div>

          <div className="mt-4 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Title:</p>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={inputCls}
            />
            <button type="button" onClick={applyGraphSettings} className={browseBtnCls}>
              Update Graph
            </button>
          </div>

          <TraceChart
            trace={parsed?.trace ?? []}
            xLabel={chartSettings.xLabel}
            yLabel={chartSettings.yLabel}
            title={chartSettings.title}
            xLimit={chartSettings.xLimit}
            yMin={chartSettings.yMin}
            yMax={chartSettings.yMax}
          />
        </div>
      </div>

      <div className="ml-auto mt-8 flex justify-end">
        <button type="button" onClick={runMeasurement} disabled={running} className={submitBtnCls}>
          {running ? 'Measuring…' : 'Run Measurement'}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {/* ── Results: measurement table + log ── */}
      {result && (
        <div className="mt-8">
          {parsed && parsed.heat_capacity !== null && (
            <dl className="mb-6 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <div>
                <dt className="text-xs uppercase tracking-widest text-gray-400">Heat Capacity</dt>
                <dd className="text-lg font-semibold text-gray-900">
                  {parsed.heat_capacity.toFixed(2)} J/kg·K
                </dd>
              </div>
              {parsed.error_pct !== null && (
                <div>
                  <dt className="text-xs uppercase tracking-widest text-gray-400">Error</dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {parsed.error_pct.toFixed(2)} %
                  </dd>
                </div>
              )}
              {parsed.baseline_voltage !== null && (
                <div>
                  <dt className="text-xs uppercase tracking-widest text-gray-400">Baseline</dt>
                  <dd className="text-sm text-gray-700">{parsed.baseline_voltage.toExponential(4)} V</dd>
                </div>
              )}
              <div>
                <dt className="text-xs uppercase tracking-widest text-gray-400">Converged</dt>
                <dd className={`text-sm font-medium ${parsed.converged ? 'text-green-600' : 'text-amber-600'}`}>
                  {parsed.converged ? 'Yes' : 'No'}
                </dd>
              </div>
            </dl>
          )}

          {parsed?.message && !parsed.converged && (
            <p className="mb-4 text-sm text-amber-600">{parsed.message}</p>
          )}

          {/* Measurement table */}
          {parsed && parsed.steps.length > 0 && (
            <div className="overflow-hidden rounded-md border border-gray-300">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Flow Rate</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Voltage</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-600">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {parsed.steps.map((step) => (
                    <tr key={step.index}>
                      <td className="px-4 py-2 text-gray-900">{step.flow_rate} mL/min</td>
                      <td className="px-4 py-2 text-gray-900">
                        {step.voltage !== null ? step.voltage.toExponential(4) : '—'} V
                      </td>
                      <td className={`px-4 py-2 font-medium ${statusColor(step.status)}`}>
                        {step.status}
                      </td>
                      <td className="px-4 py-2 text-gray-900">{step.time_s}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Measurement log */}
          <div className="mt-6">
            <div className="flex items-center gap-2">
              <span
                className={`inline-block size-2 rounded-full ${result.success ? 'bg-green-500' : 'bg-red-500'}`}
              />
              <h2 className="text-base/7 font-semibold text-gray-900">Measurement Log</h2>
            </div>
            <div className="mt-2 max-h-64 overflow-auto rounded-md border border-gray-300 bg-gray-50 p-3 font-mono text-xs">
              {logRows.length === 0 ? (
                <p className="text-gray-500">No log output.</p>
              ) : (
                logRows.map((row, i) => (
                  <div key={i} className={row.tone}>
                    {row.time && <span className="text-gray-400">[{row.time}] </span>}
                    {row.message}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
