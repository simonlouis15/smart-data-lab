import UpdateDevice from './UpdateDevice';

import { DocumentArrowUpIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { invoke } from '@tauri-apps/api/core';
import { useEffect, useRef, useState } from 'react';

interface Pump {
  Port: string;
  'Pump Number': number;
  'Flow Rate': number;
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

const EMPTY_PUMP: Pump = {
  Port: 'COM1',
  'Pump Number': 1,
  'Flow Rate': 0.0,
  Baudrate: 9600,
  Bytesize: 8,
  Parity: 'none',
  Stopbits: 1,
  Timeout: 1,
  Xonxoff: false,
  Rtscts: false,
  Dsrdtr: false,
  WriteTimeout: 1,
};

// ── Pump JSON schema validation ────────────────────────────────────────────

const PUMP_FIELD_VALIDATORS: Record<keyof Pump, (v: unknown) => boolean> = {
  Port: (v) => typeof v === 'string' && v.trim().length > 0,
  'Pump Number': (v) => typeof v === 'number' && Number.isInteger(v) && v >= 1,
  'Flow Rate': (v) => typeof v === 'number' && Number.isFinite(v),
  Baudrate: (v) => typeof v === 'number' && Number.isInteger(v) && v > 0,
  Bytesize: (v) => typeof v === 'number' && Number.isInteger(v),
  Parity: (v) => typeof v === 'string' && v.trim().length > 0,
  Stopbits: (v) => typeof v === 'number',
  Timeout: (v) => typeof v === 'number' && Number.isFinite(v),
  Xonxoff: (v) => typeof v === 'boolean',
  Rtscts: (v) => typeof v === 'boolean',
  Dsrdtr: (v) => typeof v === 'boolean',
  WriteTimeout: (v) => typeof v === 'number' && Number.isFinite(v),
};

/** Returns a list of human-readable problems; empty array means it's valid. */
function validatePumpShape(obj: unknown): string[] {
  if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
    return ['not an object'];
  }
  const errors: string[] = [];
  for (const key of Object.keys(PUMP_FIELD_VALIDATORS) as (keyof Pump)[]) {
    const val = (obj as Record<string, unknown>)[key];
    if (val === undefined) {
      errors.push(`missing "${key}"`);
    } else if (!PUMP_FIELD_VALIDATORS[key](val)) {
      errors.push(`invalid "${key}"`);
    }
  }
  return errors;
}

/** A single pump object has "Port" at the top level; a map of pumps does not. */
function looksLikeSinglePump(obj: unknown): boolean {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    !Array.isArray(obj) &&
    'Port' in obj
  );
}

type ImportState = 'idle' | 'reading' | 'importing' | 'success' | 'error';

interface ImportResult {
  added: string[];
  skipped: string[];
  pumps: Record<string, Pump>;
}

export default function Devices() {
  const [selectedPump, setSelectedPump] = useState<string | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [pumps, setPumps] = useState<Record<string, Pump>>({});
  const [loadingPumps, setLoadingPumps] = useState(true);
  const [pumpsError, setPumpsError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [importedFile, setImportedFile] = useState<string | null>(null);
  const [importState, setImportState] = useState<ImportState>('idle');
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [importIssues, setImportIssues] = useState<string[]>([]);

  const fetchPumps = async () => {
    setLoadingPumps(true);
    setPumpsError(null);
    try {
      const data = await invoke<Record<string, Pump>>('get_pump_configs');
      setPumps(data);
    } catch (err) {
      setPumpsError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingPumps(false);
    }
  };

  useEffect(() => {
    fetchPumps();
  }, []);

  const importBusy = importState === 'reading' || importState === 'importing';

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.json')) {
      setImportedFile(file.name);
      setImportState('error');
      setImportMessage('Please upload a .json file.');
      setImportIssues([]);
      return;
    }

    setImportedFile(file.name);
    setImportState('reading');
    setImportMessage(null);
    setImportIssues([]);

    // Parse the file
    let parsed: unknown;
    try {
      const text = await file.text();
      parsed = JSON.parse(text);
    } catch {
      setImportState('error');
      setImportMessage('That file is not valid JSON.');
      return;
    }

    // Normalize into a name -> candidate pump map
    const candidates: Record<string, unknown> = {};
    if (looksLikeSinglePump(parsed)) {
      const inferredName =
        file.name.replace(/\.json$/i, '').trim() || 'Imported Pump';
      candidates[inferredName] = parsed;
    } else if (
      typeof parsed === 'object' &&
      parsed !== null &&
      !Array.isArray(parsed)
    ) {
      Object.assign(candidates, parsed as Record<string, unknown>);
    } else {
      setImportState('error');
      setImportMessage(
        'JSON must be either a single pump object or a map of pump name to pump object.'
      );
      return;
    }

    if (Object.keys(candidates).length === 0) {
      setImportState('error');
      setImportMessage('No pump entries found in that file.');
      return;
    }

    // Validate each candidate against the Pump schema
    const validPumps: Record<string, Pump> = {};
    const issues: string[] = [];
    for (const [name, val] of Object.entries(candidates)) {
      const errors = validatePumpShape(val);
      if (errors.length > 0) {
        issues.push(`"${name}": ${errors.join(', ')}`);
      } else {
        validPumps[name] = val as Pump;
      }
    }

    if (Object.keys(validPumps).length === 0) {
      setImportState('error');
      setImportMessage('No entries matched the pump configuration schema.');
      setImportIssues(issues);
      return;
    }

    // Hand off validated pumps to Rust to merge into config.json
    setImportState('importing');
    try {
      const result = await invoke<ImportResult>('import_pump_configs', {
        pumps: validPumps,
      });
      setPumps(result.pumps);
      setImportState('success');
      setImportIssues(issues);

      const parts: string[] = [];
      if (result.added.length > 0) {
        parts.push(`Added ${result.added.length}: ${result.added.join(', ')}`);
      }
      if (result.skipped.length > 0) {
        parts.push(
          `Skipped ${result.skipped.length} (already exist): ${result.skipped.join(', ')}`
        );
      }
      setImportMessage(parts.join(' — ') || 'Nothing new to import.');
    } catch (err) {
      setImportState('error');
      setImportMessage(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">
            Devices
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Configure all hardware devices including pumps, valves and data
            acquisition.
          </h3>
        </div>
      </header>

      <form>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">
            Import Configuration
          </h2>
          <p className="mt-1 text-sm/6 text-gray-600">
            Load a saved JSON configuration file to import device settings.
            Accepts a single pump object or a map of pump name to pump object.
          </p>

          <div
            onClick={() => !importBusy && fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              if (!importBusy) setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (importBusy) return;
              const file = e.dataTransfer.files[0];
              if (file) handleFile(file);
            }}
            className={`mt-2 flex justify-center rounded-xl border border-dashed px-6 py-10 transition-colors
    ${importBusy ? 'cursor-wait opacity-70' : 'cursor-pointer'}
    ${
      dragOver
        ? 'border-blue-400 bg-blue-50'
        : 'border-gray-300 bg-white hover:bg-gray-50'
    }`}
          >
            <div className="text-center">
              {importBusy ? (
                <span className="mx-auto flex h-12 w-12 items-center justify-center">
                  <span className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                </span>
              ) : (
                <DocumentArrowUpIcon
                  aria-hidden="true"
                  className={`mx-auto size-12 transition-colors ${dragOver ? 'text-blue-400' : 'text-gray-400'}`}
                />
              )}
              <div className="mt-4 flex items-center justify-center text-sm/6 text-gray-600">
                <span className="relative cursor-pointer rounded-xxl font-semibold text-blue-600 hover:text-blue-500">
                  Upload a file
                </span>
                <p className="pl-1">or drag and drop</p>
              </div>
              <p className="mt-1 text-xs/5 text-gray-500">
                {importState === 'reading' && 'Validating file…'}
                {importState === 'importing' &&
                  'Importing pump configurations…'}
                {importState === 'idle' &&
                  (importedFile ?? 'JSON configuration files only')}
                {(importState === 'success' || importState === 'error') &&
                  (importedFile ?? 'JSON configuration files only')}
              </p>
              <input
                ref={fileInputRef}
                id="file-upload"
                name="file-upload"
                type="file"
                accept=".json"
                className="sr-only"
                disabled={importBusy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                  // allow re-selecting the same file name in a row
                  e.target.value = '';
                }}
              />
            </div>
          </div>

          {/* Import result / error feedback */}
          {importMessage &&
            (importState === 'success' || importState === 'error') && (
              <div
                className={`mt-2 rounded-md border p-3 text-sm ${
                  importState === 'success'
                    ? 'border-green-200 bg-green-50 text-green-700'
                    : 'border-red-200 bg-red-50 text-red-600'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <p>{importMessage}</p>
                  <button type="button" onClick={() => setImportState('idle')}>
                    <XMarkIcon className="mx-auto size-6 hover:text-red-400" />
                  </button>
                </div>
                {importIssues.length > 0 && (
                  <ul className="mt-1 list-disc pl-5 text-xs text-gray-500">
                    {importIssues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

          <h2 className="text-base/7 font-semibold text-gray-900 mt-12">
            Pump Configuration
          </h2>
          <p className="mt-1 text-sm/6 text-gray-600">
            Configure sample, solvent and HC pumps. Click on a pump to edit its
            properties.
          </p>
          <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
            {loadingPumps ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                Loading pump configurations…
              </div>
            ) : pumpsError ? (
              <div className="py-8 text-center text-sm text-red-500">
                {pumpsError}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(pumps).map(([name, pump]) => (
                  <button
                    key={name}
                    type="button"
                    className="flex flex-col items-start gap-1 rounded-md bg-white px-4 py-3 text-left border border-gray-300 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                    onClick={() => setSelectedPump(name)}
                  >
                    <span className="text-sm font-semibold text-gray-900">
                      {name}
                    </span>
                    <span className="text-xs text-gray-500">
                      {pump.Port} | {pump.Baudrate} baud
                    </span>
                  </button>
                ))}
              </div>
            )}

            <div className="flex justify-center mt-4">
              <button
                type="button"
                onClick={() => setAddingNew(true)}
                disabled={loadingPumps}
                className="flex flex-col items-center justify-center gap-1 rounded-md bg-blue-600 text-white px-4 py-3 text-center border border-gray-300 hover:bg-blue-500 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                <span className="text-sm font-semibold">Add Config +</span>
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Edit existing pump */}
      {selectedPump && (
        <UpdateDevice
          name={selectedPump}
          pump={pumps[selectedPump]}
          open={true}
          setOpen={() => setSelectedPump(null)}
          onSubmit={(updatedPumps) => {
            setPumps(updatedPumps);
            setSelectedPump(null);
          }}
          onDelete={(updatedPumps) => {
            setPumps(updatedPumps);
            setSelectedPump(null);
          }}
        />
      )}

      {/* Add new pump */}
      {addingNew && (
        <UpdateDevice
          name=""
          pump={EMPTY_PUMP}
          isNew={true}
          open={true}
          setOpen={() => setAddingNew(false)}
          onSubmit={(updatedPumps) => {
            setPumps(updatedPumps);
            setAddingNew(false);
          }}
        />
      )}
    </div>
  );
}
