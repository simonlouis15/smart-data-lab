'use client';

import {
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from '@headlessui/react';
import { invoke } from '@tauri-apps/api/core';
import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

const COM_PORTS = ['COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9','COM10','COM11','COM12','/dev/ttyUSB0','/dev/ttyUSB1','/dev/ttyS0','/dev/ttyS1'];
const BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200];
const BYTESIZES = [5, 6, 7, 8];
const PARITIES = ['none', 'even', 'odd', 'mark', 'space'];
const STOPBITS = [1, 1.5, 2];

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

interface Props {
  name: string;
  pump: Pump;
  open: boolean;
  isNew?: boolean;
  setOpen: () => void;
  onSubmit?: (updatedPumps: Record<string, Pump>) => void;
  onDelete?: (updatedPumps: Record<string, Pump>) => void;
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-700">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${value ? 'bg-blue-600' : 'bg-gray-300'}`}
      >
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${value ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 items-center gap-4 py-2.5">
      <label className="text-sm text-gray-700">{label}</label>
      <div>{children}</div>
    </div>
  );
}

const selectCls = "w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500";
const inputCls  = "w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500";

export default function UpdateDevice({ name, pump, open, isNew = false, setOpen, onSubmit, onDelete }: Props) {
  const [pumpName, setPumpName] = useState(name);
  const [form, setForm] = useState<Pump>({ ...pump });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const busy = saving || deleting;

  const set = <K extends keyof Pump>(key: K, value: Pump[K]) =>
    setForm(prev => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    const trimmedName = pumpName.trim();
    if (!trimmedName) {
      setError('Pump name is required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        const exists = await invoke<boolean>('pump_config_exists', { name: trimmedName });
        if (exists) {
          setError(`A pump named "${trimmedName}" already exists.`);
          setSaving(false);
          return;
        }
      }
      const updatedPumps = await invoke<Record<string, Pump>>('update_pump_config', {
        name: trimmedName,
        pump: form,
        originalName: isNew ? null : name,
      });
      onSubmit?.(updatedPumps);
      setOpen();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      const updatedPumps = await invoke<Record<string, Pump>>('delete_pump_config', { name });
      onDelete?.(updatedPumps);
      setOpen();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setDeleting(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => !busy && setOpen()} className="relative z-10">
      <DialogBackdrop
        transition
        className="fixed inset-0 bg-blue-50/80 backdrop-blur-sm transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
      />

      <div className="fixed inset-0 z-10 w-screen overflow-y-auto">
        <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <DialogPanel
            transition
            className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-xl ring-1 ring-gray-200 transition-all data-closed:translate-y-4 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-lg data-closed:sm:translate-y-0 data-closed:sm:scale-95"
          >
            {/* Loading overlay - stays up until the config write finishes */}
            {busy && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-white/80 backdrop-blur-sm">
                <span className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
                <p className="text-sm font-medium text-gray-600">
                  {deleting ? 'Removing config…' : 'Saving config…'}
                </p>
              </div>
            )}

            {/* Header */}
            <div className="border-b border-gray-100 px-6 py-4">
              <DialogTitle as="h3" className="text-base font-semibold text-blue-600">
                {isNew ? 'New Pump' : `Configure — ${name}`}
              </DialogTitle>
              <p className="mt-0.5 text-xs text-gray-400">
                {isNew ? 'Fill in the details for your new pump.' : 'Edit serial port settings.'}
              </p>
            </div>

            {/* Body */}
            <div className="max-h-[60vh] overflow-y-auto px-6 py-4">

              {/* ── Attributes ── */}
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-gray-400">Attributes</p>
              <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 px-3">

                {isNew && (
                  <Field label="Pump Name">
                    <input
                      type="text"
                      className={inputCls}
                      placeholder="e.g. Sample Pump"
                      value={pumpName}
                      onChange={e => setPumpName(e.target.value)}
                    />
                  </Field>
                )}

                <Field label="Port">
                  <select className={selectCls} value={form.Port} onChange={e => set('Port', e.target.value)}>
                    {COM_PORTS.map(p => <option key={p}>{p}</option>)}
                  </select>
                </Field>

                <Field label="Pump Number">
                  <input
                    type="number"
                    min={1}
                    step={1}
                    className={inputCls}
                    value={form['Pump Number']}
                    onChange={e => set('Pump Number', Math.max(1, Math.floor(Number(e.target.value))))}
                  />
                </Field>

                <Field label="Flow Rate">
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    className={inputCls}
                    value={form['Flow Rate']}
                    onChange={e => set('Flow Rate', Number(e.target.value))}
                  />
                </Field>

                <Field label="Baudrate">
                  <select className={selectCls} value={form.Baudrate} onChange={e => set('Baudrate', Number(e.target.value))}>
                    {BAUDRATES.map(b => <option key={b} value={b}>{b}</option>)}
                  </select>
                </Field>

              </div>

              {/* ── Advanced Settings ── */}
              <div className="mt-4">
                <button
                  type="button"
                  onClick={() => setAdvancedOpen(prev => !prev)}
                  className="flex w-full items-center justify-between rounded-lg border border-gray-200 px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
                >
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Advanced Settings</p>
                  <ChevronDownIcon
                    className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${advancedOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                {advancedOpen && (
                  <div className="divide-y divide-gray-100 rounded-b-lg border border-t-0 border-gray-200 px-3">

                    <Field label="Bytesize">
                      <select className={selectCls} value={form.Bytesize} onChange={e => set('Bytesize', Number(e.target.value))}>
                        {BYTESIZES.map(b => <option key={b} value={b}>{b}</option>)}
                      </select>
                    </Field>

                    <Field label="Parity">
                      <select className={selectCls} value={form.Parity} onChange={e => set('Parity', e.target.value)}>
                        {PARITIES.map(p => <option key={p}>{p}</option>)}
                      </select>
                    </Field>

                    <Field label="Stopbits">
                      <select className={selectCls} value={form.Stopbits} onChange={e => set('Stopbits', Number(e.target.value))}>
                        {STOPBITS.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </Field>

                    <Field label="Timeout (s)">
                      <input type="number" min={0} step={1} className={inputCls} value={form.Timeout}
                        onChange={e => set('Timeout', Number(e.target.value))} />
                    </Field>

                    <Field label="Write Timeout (s)">
                      <input type="number" min={0} step={1} className={inputCls} value={form.WriteTimeout}
                        onChange={e => set('WriteTimeout', Number(e.target.value))} />
                    </Field>

                    <div className="pt-1 pb-1">
                      <Toggle label="Xon/Xoff" value={form.Xonxoff} onChange={v => set('Xonxoff', v)} />
                      <Toggle label="RTS/CTS"  value={form.Rtscts}  onChange={v => set('Rtscts', v)} />
                      <Toggle label="DSR/DTR"  value={form.Dsrdtr}  onChange={v => set('Dsrdtr', v)} />
                    </div>

                  </div>
                )}
              </div>

            </div>

            {/* Footer */}
            <div className="border-t border-gray-100 bg-gray-50 px-6 py-3 flex items-center gap-2">
              {!isNew && (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={busy}
                  className={`inline-flex justify-center rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50 ${
                    confirmingDelete
                      ? 'bg-red-600 text-white hover:bg-red-500'
                      : 'bg-white text-red-600 ring-1 ring-red-300 hover:bg-red-50'
                  }`}
                >
                  {confirmingDelete ? 'Confirm delete?' : 'Delete'}
                </button>
              )}

              {error && <p className="text-xs text-red-500 mx-2">{error}</p>}

              <div className="ml-auto flex flex-row-reverse gap-2">
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={busy}
                  className="inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                >
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
                <button
                  type="button"
                  onClick={() => (confirmingDelete ? setConfirmingDelete(false) : setOpen())}
                  disabled={busy}
                  className="inline-flex justify-center rounded-md bg-white px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>

          </DialogPanel>
        </div>
      </div>
    </Dialog>
  );
}