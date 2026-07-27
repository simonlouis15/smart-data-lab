import { useState, useEffect } from 'react';
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

interface ValveConfig extends SerialConfig {
  Positions: number;
  Connections: Record<string, number>;
}

// ---- Result returned by the run_pump / move_valve tauri commands ----
interface SidecarResult {
  success: boolean;
  code: number | null;
  stdout: string;
  stderr: string;
}

// ---- Pump options, matching the v9-sidecar CLI --option values ----
type PumpOption =
  | 'initialize'
  | 'withdraw'
  | 'inject'
  | 'full-injection'
  | 'empty'
  | 'debubble'
  | 'clean'
  | 'stop'
  | 'query-position';

type PumpField =
  | 'rate'
  | 'speed'
  | 'position'
  | 'duration'
  | 'injectionTime'
  | 'syringeVolume'
  | 'syringeSize';

interface PumpFieldSpec {
  name: PumpField;
  required?: boolean;
}

const PUMP_OPTIONS: { value: PumpOption; label: string }[] = [
  { value: 'initialize', label: 'Initialize' },
  { value: 'withdraw', label: 'Withdraw' },
  { value: 'inject', label: 'Inject' },
  { value: 'full-injection', label: 'Full Injection' },
  { value: 'empty', label: 'Empty' },
  { value: 'debubble', label: 'Debubble' },
  { value: 'clean', label: 'Clean' },
  { value: 'stop', label: 'Stop' },
  { value: 'query-position', label: 'Query Position' },
];

// Which parameter inputs each option needs (and which are required).
const OPTION_FIELDS: Record<PumpOption, PumpFieldSpec[]> = {
  initialize: [{ name: 'syringeSize' }],
  withdraw: [{ name: 'speed', required: true }, { name: 'position' }],
  inject: [{ name: 'rate', required: true }, { name: 'injectionTime' }, { name: 'syringeVolume' }],
  'full-injection': [{ name: 'rate', required: true }, { name: 'position' }],
  empty: [{ name: 'rate', required: true }],
  debubble: [{ name: 'rate', required: true }, { name: 'duration', required: true }],
  clean: [{ name: 'rate' }, { name: 'speed' }],
  stop: [],
  'query-position': [],
};

const FIELD_META: Record<PumpField, { label: string; step: string; placeholder?: string }> = {
  rate: { label: 'Flow Rate (mL/min)', step: '0.01' },
  speed: { label: 'Speed', step: '1' },
  position: { label: 'Position (steps)', step: '1' },
  duration: { label: 'Duration (steps)', step: '1' },
  injectionTime: { label: 'Injection Time (min)', step: '0.1', placeholder: '1 (default)' },
  syringeVolume: { label: 'Syringe Volume (mL)', step: '0.1', placeholder: '10 (default)' },
  syringeSize: { label: 'Syringe Size (mL)', step: '1', placeholder: '30 (default)' },
};

// ---- Routines, matching the v9-sidecar `routine --routine` values ----
type RoutineName = 'switch-sample' | 'jar-switch' | 'flow-rate';

const ROUTINES: { value: RoutineName; label: string; description: string }[] = [
  {
    value: 'switch-sample',
    label: 'Switch Sample (Line Clean)',
    description:
      'Empty the syringe, clean against solvent + air, then prime the line. Uses one pump and its 28-port valve.',
  },
  {
    value: 'jar-switch',
    label: 'Jar Switch',
    description:
      'Route the pump’s 28-port valve to a chemical and prime the line. Uses one pump and its 28-port valve.',
  },
  {
    value: 'flow-rate',
    label: 'Flow Rate (Concurrent Dose)',
    description:
      'Switch the main valve to injection, then debubble and inject the selected pumps simultaneously at their mL/min rates.',
  },
];

// ---- Shared style tokens (kept consistent with the rest of the app) ----
const inputCls =
  'block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6';
const selectCls =
  'col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6';
const radioCls =
  'relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden';
const submitBtnCls =
  'inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600';

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

function ResultPanel({ result }: { result: SidecarResult | null }) {
  if (!result) return null;
  return (
    <div className="mt-6 rounded-md border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block size-2 rounded-full ${result.success ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <p className="text-sm font-medium text-gray-900">
          {result.success ? 'Command succeeded' : 'Command failed'}
          {result.code !== null ? ` (exit ${result.code})` : ''}
        </p>
      </div>
      {result.stdout.trim() && (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-gray-700">
          {result.stdout}
        </pre>
      )}
      {result.stderr.trim() && (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-red-600">
          {result.stderr}
        </pre>
      )}
    </div>
  );
}

export default function Controls() {
  // ---- Valve state ----
  const [valves, setValves] = useState<Record<string, ValveConfig>>({});
  const [selectedValve, setSelectedValve] = useState<string>('');
  const [valvePosition, setValvePosition] = useState<number>(1);
  const [valveRunning, setValveRunning] = useState(false);
  const [valveError, setValveError] = useState<string | null>(null);
  const [valveResult, setValveResult] = useState<SidecarResult | null>(null);

  // ---- Pump state ----
  const [pumps, setPumps] = useState<Record<string, PumpConfig>>({});
  const [selectedPump, setSelectedPump] = useState<string>('');
  const [pumpOption, setPumpOption] = useState<PumpOption>('initialize');
  const [params, setParams] = useState<Record<string, string>>({});
  const [pumpRunning, setPumpRunning] = useState(false);
  const [pumpError, setPumpError] = useState<string | null>(null);
  const [pumpResult, setPumpResult] = useState<SidecarResult | null>(null);

  // ---- Routine state ----
  const [routineName, setRoutineName] = useState<RoutineName>('switch-sample');
  const [routinePump, setRoutinePump] = useState<string>('');
  const [routineValve, setRoutineValve] = useState<string>('');
  const [chemical, setChemical] = useState<string>('');
  const [numChemicals, setNumChemicals] = useState<string>('');
  const [flowValve, setFlowValve] = useState<string>('');
  const [flowRates, setFlowRates] = useState<Record<string, string>>({});
  const [injectionTime, setInjectionTime] = useState<string>('');
  const [syringeVolume, setSyringeVolume] = useState<string>('');
  const [routineRunning, setRoutineRunning] = useState(false);
  const [routineError, setRoutineError] = useState<string | null>(null);
  const [routineResult, setRoutineResult] = useState<SidecarResult | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await invoke<Record<string, ValveConfig>>('get_valve_configs');
        setValves(data);
        const names = Object.keys(data);
        if (names.length > 0) {
          selectValve(names[0], data);
          setRoutineValve(names[0]);
          setFlowValve(names[0]);
        }
      } catch (err) {
        setValveError(err instanceof Error ? err.message : String(err));
      }
    })();

    (async () => {
      try {
        const data = await invoke<Record<string, PumpConfig>>('get_pump_configs');
        setPumps(data);
        const names = Object.keys(data);
        if (names.length > 0) {
          setSelectedPump(names[0]);
          setRoutinePump(names[0]);
        }
      } catch (err) {
        setPumpError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  // When the valve changes, default the target to its first named connection
  // (e.g. Injection/Air/Solvent), otherwise position 1.
  function selectValve(name: string, source: Record<string, ValveConfig> = valves) {
    setSelectedValve(name);
    setValveResult(null);
    setValveError(null);
    const cfg = source[name];
    const firstConn = cfg ? Object.values(cfg.Connections)[0] : undefined;
    setValvePosition(firstConn ?? 1);
  }

  async function controlValve() {
    const valve = valves[selectedValve];
    if (!valve) {
      setValveError('No valve selected');
      return;
    }
    if (!Number.isInteger(valvePosition) || valvePosition < 1 || valvePosition > valve.Positions) {
      setValveError(`Position must be between 1 and ${valve.Positions}`);
      return;
    }

    setValveRunning(true);
    setValveError(null);
    setValveResult(null);
    try {
      const result = await invoke<SidecarResult>('move_valve', {
        name: selectedValve,
        valve,
        position: valvePosition,
      });
      setValveResult(result);
    } catch (err) {
      setValveError(err instanceof Error ? err.message : String(err));
    } finally {
      setValveRunning(false);
    }
  }

  async function controlPump() {
    const pump = pumps[selectedPump];
    if (!pump) {
      setPumpError('No pump selected');
      return;
    }

    const action: Record<string, number | string> = { option: pumpOption };
    for (const spec of OPTION_FIELDS[pumpOption]) {
      const raw = params[spec.name];
      const hasValue = raw !== undefined && raw.trim() !== '';
      if (spec.required && !hasValue) {
        setPumpError(`${FIELD_META[spec.name].label} is required for "${pumpOption}"`);
        return;
      }
      if (hasValue) {
        const n = Number(raw);
        if (Number.isNaN(n)) {
          setPumpError(`${FIELD_META[spec.name].label} must be a number`);
          return;
        }
        action[spec.name] = n;
      }
    }

    setPumpRunning(true);
    setPumpError(null);
    setPumpResult(null);
    try {
      const result = await invoke<SidecarResult>('run_pump', {
        name: selectedPump,
        pump,
        action,
      });
      setPumpResult(result);
    } catch (err) {
      setPumpError(err instanceof Error ? err.message : String(err));
    } finally {
      setPumpRunning(false);
    }
  }

  async function runRoutine() {
    let payload: Record<string, unknown>;

    if (routineName === 'switch-sample' || routineName === 'jar-switch') {
      const pump = pumps[routinePump];
      const valve = valves[routineValve];
      if (!pump || !valve) {
        setRoutineError('Select both a pump and a valve');
        return;
      }
      payload = { pump, valve };

      if (routineName === 'jar-switch') {
        if (!chemical.trim()) {
          setRoutineError('Chemical is required for Jar Switch');
          return;
        }
        const nc = Number(numChemicals);
        if (!Number.isInteger(nc) || nc < 1) {
          setRoutineError('Number of chemicals must be a positive integer');
          return;
        }
        payload.chemical = chemical.trim();
        payload.num_chemicals = nc;
      }
    } else {
      // flow-rate
      const valve = valves[flowValve];
      if (!valve) {
        setRoutineError('Select the main valve');
        return;
      }

      const pumpList: { config: PumpConfig; rate: number }[] = [];
      for (const [name, raw] of Object.entries(flowRates)) {
        if (!raw || raw.trim() === '') continue;
        const rate = Number(raw);
        if (Number.isNaN(rate)) {
          setRoutineError(`Rate for "${name}" must be a number`);
          return;
        }
        if (rate > 0) pumpList.push({ config: pumps[name], rate });
      }
      if (pumpList.length === 0) {
        setRoutineError('Enter a flow rate (> 0) for at least one pump');
        return;
      }

      payload = {
        main_valve: valve,
        pumps: pumpList,
        injection_time: injectionTime.trim() === '' ? 1 : Number(injectionTime),
        syringe_volume: syringeVolume.trim() === '' ? 10 : Number(syringeVolume),
      };
    }

    setRoutineRunning(true);
    setRoutineError(null);
    setRoutineResult(null);
    try {
      const result = await invoke<SidecarResult>('run_routine', {
        routine: routineName,
        payload,
      });
      setRoutineResult(result);
    } catch (err) {
      setRoutineError(err instanceof Error ? err.message : String(err));
    } finally {
      setRoutineRunning(false);
    }
  }

  const activeValve = valves[selectedValve];
  const valveConnections = activeValve ? Object.entries(activeValve.Connections) : [];
  const activeRoutine = ROUTINES.find((r) => r.value === routineName);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">Controls</h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Send single pump and selector-valve commands using your saved device configs
          </h3>
        </div>
      </header>

      {/* Selector Valve */}
      <form onSubmit={(e) => e.preventDefault()}>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">Selector Valve</h2>

          {/* Valve picker */}
          <div className="mt-6 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Valve:</p>
            <Dropdown value={selectedValve} onChange={(v) => selectValve(v)}>
              {Object.keys(valves).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Dropdown>
          </div>

          {activeValve && (
            <>
              <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
                {activeValve.Positions}-position valve on {activeValve.Port}
              </p>

              {/* Named connections from config (e.g. Injection / Air / Solvent) */}
              {valveConnections.length > 0 ? (
                <fieldset>
                  <div className="mt-6 space-y-6">
                    {valveConnections.map(([name, pos]) => (
                      <div key={name} className="flex items-center gap-x-3">
                        <input
                          id={`valve-conn-${name}`}
                          name="valve-connection"
                          type="radio"
                          className={radioCls}
                          checked={valvePosition === pos}
                          onChange={() => setValvePosition(pos)}
                        />
                        <label
                          htmlFor={`valve-conn-${name}`}
                          className="block text-sm/6 font-medium text-gray-900"
                        >
                          {name}{' '}
                          <span className="text-gray-400">(position {pos})</span>
                        </label>
                      </div>
                    ))}
                  </div>
                </fieldset>
              ) : (
                <p className="mt-4 text-sm/6 text-gray-500">
                  No named connections configured for this valve. Enter a position below.
                </p>
              )}

              {/* Manual position entry (works for any valve, incl. 28-port) */}
              <div className="mt-6 flex items-center gap-4 sm:max-w-sm">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">Position:</p>
                <input
                  type="number"
                  min={1}
                  max={activeValve.Positions}
                  step={1}
                  value={valvePosition}
                  className={inputCls}
                  onChange={(e) => setValvePosition(Math.floor(Number(e.target.value)))}
                />
              </div>
            </>
          )}
        </div>

        <div className="ml-auto mt-6">
          <button
            type="button"
            onClick={controlValve}
            disabled={valveRunning || !activeValve}
            className={submitBtnCls}
          >
            {valveRunning ? 'Running…' : 'Move Valve'}
          </button>
        </div>

        {valveError && <p className="mt-3 text-sm text-red-600">{valveError}</p>}
        <ResultPanel result={valveResult} />
      </form>

      {/* Pump Controls */}
      <form onSubmit={(e) => e.preventDefault()}>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">Pump Controls</h2>

          {/* Pump picker */}
          <div className="mt-6 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Pump:</p>
            <Dropdown
              value={selectedPump}
              onChange={(v) => {
                setSelectedPump(v);
                setPumpResult(null);
                setPumpError(null);
              }}
            >
              {Object.keys(pumps).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Dropdown>
          </div>

          {pumps[selectedPump] && (
            <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-gray-400">
              Pump #{pumps[selectedPump]['Pump Number']} on {pumps[selectedPump].Port}
            </p>
          )}

          {/* Operation picker */}
          <div className="mt-6 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Operation:</p>
            <Dropdown
              value={pumpOption}
              onChange={(v) => {
                setPumpOption(v as PumpOption);
                setPumpResult(null);
                setPumpError(null);
              }}
            >
              {PUMP_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Dropdown>
          </div>

          {/* Parameter inputs for the selected operation */}
          {OPTION_FIELDS[pumpOption].length > 0 ? (
            <div className="mt-6 grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2">
              {OPTION_FIELDS[pumpOption].map(({ name, required }) => (
                <div key={name} className="flex items-center gap-4">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    {FIELD_META[name].label}
                    {required && <span className="text-red-500">*</span>}:
                  </p>
                  <input
                    type="number"
                    step={FIELD_META[name].step}
                    placeholder={FIELD_META[name].placeholder}
                    value={params[name] ?? ''}
                    className={inputCls}
                    onChange={(e) =>
                      setParams((prev) => ({ ...prev, [name]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-6 text-sm/6 text-gray-500">
              This operation takes no parameters.
            </p>
          )}
        </div>

        <div className="ml-auto mt-6">
          <button
            type="button"
            onClick={controlPump}
            disabled={pumpRunning || !pumps[selectedPump]}
            className={submitBtnCls}
          >
            {pumpRunning ? 'Running…' : 'Run Pump'}
          </button>
        </div>

        {pumpError && <p className="mt-3 text-sm text-red-600">{pumpError}</p>}
        <ResultPanel result={pumpResult} />
      </form>

      {/* Routines */}
      <form onSubmit={(e) => e.preventDefault()}>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">Routines</h2>
          <p className="mt-1 text-sm/6 text-gray-500">
            Multi-step pump/valve sequences that run inside the sidecar over a single
            connection, preserving the original V9 ordering and timing.
          </p>

          {/* Routine picker */}
          <div className="mt-6 flex items-center gap-4">
            <p className="text-sm/6 text-gray-900 whitespace-nowrap">Routine:</p>
            <Dropdown
              value={routineName}
              onChange={(v) => {
                setRoutineName(v as RoutineName);
                setRoutineResult(null);
                setRoutineError(null);
              }}
            >
              {ROUTINES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Dropdown>
          </div>
          {activeRoutine && (
            <p className="mt-3 text-sm/6 text-gray-500">{activeRoutine.description}</p>
          )}

          {/* Per-pump routines: pump + valve (+ chemical for jar-switch) */}
          {(routineName === 'switch-sample' || routineName === 'jar-switch') && (
            <div className="mt-6 grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2">
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">Pump:</p>
                <Dropdown value={routinePump} onChange={setRoutinePump}>
                  {Object.keys(pumps).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </Dropdown>
              </div>
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">Valve:</p>
                <Dropdown value={routineValve} onChange={setRoutineValve}>
                  {Object.keys(valves).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </Dropdown>
              </div>

              {routineName === 'jar-switch' && (
                <>
                  <div className="flex items-center gap-4">
                    <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                      Chemical<span className="text-red-500">*</span>:
                    </p>
                    <input
                      type="text"
                      placeholder="e.g. C"
                      value={chemical}
                      className={inputCls}
                      onChange={(e) => setChemical(e.target.value)}
                    />
                  </div>
                  <div className="flex items-center gap-4">
                    <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                      # Chemicals<span className="text-red-500">*</span>:
                    </p>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      placeholder="e.g. 26"
                      value={numChemicals}
                      className={inputCls}
                      onChange={(e) => setNumChemicals(e.target.value)}
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Flow-rate: main valve + per-pump rates + timing */}
          {routineName === 'flow-rate' && (
            <>
              <div className="mt-6 flex items-center gap-4 sm:max-w-sm">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">Main Valve:</p>
                <Dropdown value={flowValve} onChange={setFlowValve}>
                  {Object.keys(valves).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </Dropdown>
              </div>

              <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-gray-400">
                Pump flow rates (mL/min) — leave blank or 0 to skip a pump
              </p>
              <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2">
                {Object.keys(pumps).map((name) => (
                  <div key={name} className="flex items-center gap-4">
                    <p className="text-sm/6 text-gray-900 whitespace-nowrap">{name}:</p>
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      placeholder="0"
                      value={flowRates[name] ?? ''}
                      className={inputCls}
                      onChange={(e) =>
                        setFlowRates((prev) => ({ ...prev, [name]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>

              <div className="mt-6 grid grid-cols-1 gap-x-6 gap-y-6 sm:grid-cols-2">
                <div className="flex items-center gap-4">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    Injection Time (min):
                  </p>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="1 (default)"
                    value={injectionTime}
                    className={inputCls}
                    onChange={(e) => setInjectionTime(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-4">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    Syringe Volume (mL):
                  </p>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="10 (default)"
                    value={syringeVolume}
                    className={inputCls}
                    onChange={(e) => setSyringeVolume(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="ml-auto mt-6">
          <button
            type="button"
            onClick={runRoutine}
            disabled={routineRunning}
            className={submitBtnCls}
          >
            {routineRunning ? 'Running…' : 'Run Routine'}
          </button>
        </div>

        {routineError && <p className="mt-3 text-sm text-red-600">{routineError}</p>}
        <ResultPanel result={routineResult} />
      </form>
    </div>
  );
}
