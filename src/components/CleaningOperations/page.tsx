import { useState } from 'react';

const selectCls = "w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500";
const inputCls  = "w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500";

// ---------- Types ----------
interface CleanAllParams {
  refillVolume: number;
  injectVolume: number;
  injectDuration: number;
  iterations: number;
}

interface HCCleaningParams {
  emptyVolume: number;
  refillVolume: number;
  injectVolume: number;
  cleaningType: 'standard' | 'intensive' | 'quick';
}

interface RefillSolventParams {
  solventVolume: number;
}

interface RefillSampleParams {
  sampleVolume: number;
}

interface ValveParams {
  airPosition: number;
  injectionPosition: number;
  solventPosition: number;
}

// ---------- Shared field component ----------
function Field({
  label,
  value,
  onChange,
  type = 'number',
  min,
  step,
}: {
  label: string;
  value: number | string;
  onChange: (v: string) => void;
  type?: string;
  min?: number;
  step?: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-gray-700 whitespace-nowrap w-48 shrink-0">
        {label}
      </label>
      <input
        type={type}
        value={value}
        min={min}
        step={step}
        onChange={(e) => onChange(e.target.value)}
        className={`${inputCls} bg-white`}
      />
    </div>
  );
}

// ---------- Section wrapper — matches Devices.tsx h2 + p pattern ----------
function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="pt-12">
      <h2 className="text-base/7 font-semibold text-gray-900">{title}</h2>
      {description && (
        <p className="mt-1 text-sm/6 text-gray-600">{description}</p>
      )}
      <div className="mt-2 flex flex-col gap-3">{children}</div>
    </div>
  );
}

// ---------- Sub-section label (e.g. "Refill Solvent") ----------
function SubSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="pt-4">
      <h2 className="text-base/7 font-semibold text-gray-900">{title}</h2>
      <div className="mt-2 flex flex-col gap-3">{children}</div>
    </div>
  );
}

// ---------- RunButton ----------
function RunButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-1 self-start rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
    >
      {label}
    </button>
  );
}

// ---------- Main Component ----------
export default function CleaningOperations() {
  const [cleanAll, setCleanAll] = useState<CleanAllParams>({
    refillVolume: 25,
    injectVolume: 2,
    injectDuration: 960,
    iterations: 1,
  });

  const [hcCleaning, setHCCleaning] = useState<HCCleaningParams>({
    emptyVolume: 100,
    refillVolume: 150,
    injectVolume: 50,
    cleaningType: 'standard',
  });

  const [refillSolvent, setRefillSolvent] = useState<RefillSolventParams>({
    solventVolume: 30,
  });

  const [refillSample, setRefillSample] = useState<RefillSampleParams>({
    sampleVolume: 20,
  });

  const [valve, setValve] = useState<ValveParams>({
    airPosition: 9,
    injectionPosition: 3,
    solventPosition: 6,
  });

  const handleRunCleanAll = () => console.log('Running complete cleaning:', cleanAll);
  const handleRunHCCleaning = () => console.log('Running HC cleaning:', hcCleaning);
  const handleRunSolventRefill = () => console.log('Running solvent refill:', refillSolvent);
  const handleRunSampleRefill = () => console.log('Running sample refill:', refillSample);
  const handleSetAirMode = () => console.log('Setting air mode, position:', valve.airPosition);
  const handleSetInjectionMode = () => console.log('Setting injection mode, position:', valve.injectionPosition);
  const handleSetSolventMode = () => console.log('Setting solvent mode, position:', valve.solventPosition);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">

      {/* ── Header — matches Devices.tsx exactly ── */}
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">
            Cleaning Operations
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Configure and execute cleaning functions for system maintenance.
          </h3>
        </div>
      </header>

      <form>

        {/* ── Complete System Cleaning ── */}
        <Section
          title="Complete System Cleaning"
          description="Run a full system flush with configurable volumes, duration and repetitions."
        >
          <div className="rounded-md bg-blue-50 border border-gray-300 p-4 flex flex-col gap-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Refill Volume (mL):"
                value={cleanAll.refillVolume}
                onChange={(v) => setCleanAll((p) => ({ ...p, refillVolume: Number(v) }))}
                min={0}
              />
              <Field
                label="Inject Volume (mL):"
                value={cleanAll.injectVolume}
                onChange={(v) => setCleanAll((p) => ({ ...p, injectVolume: Number(v) }))}
                min={0}
              />
              <Field
                label="Inject Duration (s):"
                value={cleanAll.injectDuration}
                onChange={(v) => setCleanAll((p) => ({ ...p, injectDuration: Number(v) }))}
                min={0}
              />
              <Field
                label="Iterations:"
                value={cleanAll.iterations}
                onChange={(v) => setCleanAll((p) => ({ ...p, iterations: Number(v) }))}
                min={1}
                step={1}
              />
            </div>
            <RunButton label="Run Complete Cleaning" onClick={handleRunCleanAll} />
          </div>
        </Section>

        {/* ── HC Cleaning ── */}
        <Section
          title="Heat Capacity Cleaning"
          description="Configure and run heat capacity cleaning cycles."
        >
          <div className="rounded-md bg-blue-50 border border-gray-300 p-4 flex flex-col gap-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label="Empty Volume (mL):"
                value={hcCleaning.emptyVolume}
                onChange={(v) => setHCCleaning((p) => ({ ...p, emptyVolume: Number(v) }))}
                min={0}
              />
              <Field
                label="Refill Volume (mL):"
                value={hcCleaning.refillVolume}
                onChange={(v) => setHCCleaning((p) => ({ ...p, refillVolume: Number(v) }))}
                min={0}
              />
              <Field
                label="Inject Volume (mL):"
                value={hcCleaning.injectVolume}
                onChange={(v) => setHCCleaning((p) => ({ ...p, injectVolume: Number(v) }))}
                min={0}
              />
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700 whitespace-nowrap w-48 shrink-0">
                  Cleaning Type:
                </label>
                <select
                  value={hcCleaning.cleaningType}
                  onChange={(e) =>
                    setHCCleaning((p) => ({
                      ...p,
                      cleaningType: e.target.value as HCCleaningParams['cleaningType'],
                    }))
                  }
                  className={selectCls}
                >
                  <option value="standard">standard</option>
                  <option value="intensive">intensive</option>
                  <option value="quick">quick</option>
                </select>
              </div>
            </div>
            <RunButton label="Run HC Cleaning" onClick={handleRunHCCleaning} />
          </div>
        </Section>

        {/* ── Refill Operations ── */}
        <Section
          title="Refill Operations"
          description="Refill solvent and sample pump reservoirs."
        >
          <div className="rounded-md bg-blue-50 border border-gray-300 p-4 flex flex-col gap-4">

            <SubSection title="Refill Solvent">
              <div className="flex flex-wrap items-center gap-3">
                <Field
                  label="Solvent Volume (mL):"
                  value={refillSolvent.solventVolume}
                  onChange={(v) => setRefillSolvent({ solventVolume: Number(v) })}
                  min={0}
                />
                <button
                  type="button"
                  onClick={handleRunSolventRefill}
                  className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  Run Solvent Refill
                </button>
              </div>
            </SubSection>

            <SubSection title="Refill Sample Pumps">
              <div className="flex flex-wrap items-center gap-3">
                <Field
                  label="Sample Volume (mL):"
                  value={refillSample.sampleVolume}
                  onChange={(v) => setRefillSample({ sampleVolume: Number(v) })}
                  min={0}
                />
                <button
                  type="button"
                  onClick={handleRunSampleRefill}
                  className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  Run Sample Refill
                </button>
              </div>
            </SubSection>

          </div>
        </Section>

        {/* ── Valve Position Controls ── */}
        <Section
          title="Valve Position Controls"
          description="Set valve positions for air, injection and solvent modes."
        >
          <div className="rounded-md bg-blue-50 border border-gray-300 p-4 flex flex-col gap-3">

            <div className="flex flex-wrap items-center gap-3">
              <Field
                label="Air Position:"
                value={valve.airPosition}
                onChange={(v) => setValve((p) => ({ ...p, airPosition: Number(v) }))}
                min={0}
              />
              <button
                type="button"
                onClick={handleSetAirMode}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Set Air Mode
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Field
                label="Injection Position:"
                value={valve.injectionPosition}
                onChange={(v) => setValve((p) => ({ ...p, injectionPosition: Number(v) }))}
                min={0}
              />
              <button
                type="button"
                onClick={handleSetInjectionMode}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Set Injection Mode
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Field
                label="Solvent Position:"
                value={valve.solventPosition}
                onChange={(v) => setValve((p) => ({ ...p, solventPosition: Number(v) }))}
                min={0}
              />
              <button
                type="button"
                onClick={handleSetSolventMode}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                Set Solvent Mode
              </button>
            </div>

          </div>
        </Section>

      </form>
    </div>
  );
}