import { useState, useEffect } from 'react';
import { ChevronDownIcon } from '@heroicons/react/16/solid';
import { Command } from '@tauri-apps/plugin-shell';
import { invoke } from '@tauri-apps/api/core';

interface Device {
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

type PumpCommand = 'Initialize' | 'Withdraw' | 'Inject' | 'Flush';

const EMPTY_PUMP_CONTROLS: PumpControls = {
  command: 'Initialize',
  syringe_volume: 0,
};

// Maps the UI-facing command labels to the --option values __main__.py expects
const COMMAND_TO_OPTION: Record<PumpCommand, string> = {
  Initialize: 'initialize',
  Withdraw: 'withdraw_sample',
  Inject: 'inject_sample',
  Flush: 'flush_to_waste',
};

interface PumpControls {
  command: PumpCommand;
  syringe_volume: number;
}

type ValveMode = "sample" | "air" | "solvent";

// Placeholder UI to control specific devices
export default function Controls() {
  const [valveMode, setValveMode] = useState<ValveMode>("sample");
  const [valves, setValves] = useState<Record<string, Device>>({});
  const [selectedValve, setSelectedValve] = useState<string>('');

  const [pumpControls, setPumpControls] = useState<PumpControls>(EMPTY_PUMP_CONTROLS);
  const [pumps, setPumps] = useState<Record<string, Device>>({});
  const [selectedPump, setSelectedPump] = useState<string>('');

  const fetchPumps = async () => {
    try {
      const data = await invoke<Record<string, Device>>('get_pump_configs');
      setPumps(data);
      const names = Object.keys(data);
      if (names.length > 0) {
        setSelectedPump(names[0]);
      }
    } catch {
      throw new Error('Failed to fetch pumps');
    }
  };

  useEffect(() => {
    fetchPumps();
  }, []);

  // Call pump sidecar to initialize/control the selected pump using its stored config
  async function controlPump() {
    const pumpConfig = pumps[selectedPump];

    if (!pumpConfig) {
      throw new Error('No pump selected');
    }

    console.log(pumpConfig)

    if (pumpControls.syringe_volume <= 0) {
      throw new Error('Failed to provide suitable commands for pump controls');
    }

    const command = Command.sidecar('main-pump', [
      'pump',
      '--port',
      pumpConfig.Port,
      '--pump_num',
      pumpConfig['Pump Number'].toString(),
      '--name',
      selectedPump,
      '--option',
      COMMAND_TO_OPTION[pumpControls.command],
      '--flow_rate',
      pumpConfig['Flow Rate'].toString(),
      '--syringe_volume',
      pumpControls.syringe_volume.toString(),
      '--baudrate',
      pumpConfig.Baudrate.toString(),
      '--bytesize',
      pumpConfig.Bytesize.toString(),
      '--parity',
      pumpConfig.Parity,
      '--stopbits',
      pumpConfig.Stopbits.toString(),
      '--timeout',
      pumpConfig.Timeout.toString(),
      '--xonxoff',
      pumpConfig.Xonxoff.toString(),
      '--rtscts',
      pumpConfig.Rtscts.toString(),
      '--dsrdtr',
      pumpConfig.Dsrdtr.toString(),
      '--write_timeout',
      pumpConfig.WriteTimeout.toString(),
    ]);

    const output = await command.execute();

    console.log('Sidecar Status:', output.code);
    console.log('Sidecar Output:', output.stdout);
  }

  const fetchValves = async () => {
    try {
      const data = await invoke<Record<string, Device>>('get_valve_configs');
      setValves(data);
      const names = Object.keys(data);
      if (names.length > 0) {
        setSelectedValve(names[0]);
      }
    } catch {
      throw new Error('Failed to fetch pumps');
    }
  };

  useEffect(() => {
    fetchValves();
  }, []);

  // Call valve sidecar to initialize/control the selected valve using its stored config
  async function controlValve() {
    const valveConfig = valves[selectedValve];

    console.log(valveConfig)

    if (!valveConfig) {
      throw new Error('No valve selected');
    }

    const command = Command.sidecar('main-valve', [
      'valve',
      '--port',
      valveConfig.Port,
      '--name',
      selectedValve,
      '--mode',
      valveMode,
      '--baudrate',
      valveConfig.Baudrate.toString(),
      '--bytesize',
      valveConfig.Bytesize.toString(),
      '--parity',
      valveConfig.Parity,
      '--stopbits',
      valveConfig.Stopbits.toString(),
      '--timeout',
      valveConfig.Timeout.toString(),
      '--xonxoff',
      valveConfig.Xonxoff.toString(),
      '--rtscts',
      valveConfig.Rtscts.toString(),
      '--dsrdtr',
      valveConfig.Dsrdtr.toString(),
      '--write_timeout',
      valveConfig.WriteTimeout.toString(),
    ]);

    const output = await command.execute();

    console.log('Sidecar Status:', output.code);
    console.log('Sidecar Output:', output.stdout);
  }


  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">
            Controls
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Placeholder UI to control specific devices
          </h3>
        </div>
      </header>

      {/* Selector Valve */}

      <form>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">
            Selector Valve
          </h2>

          <fieldset>
            <div className="mt-6 space-y-6">
              <div className="flex items-center gap-x-3">
                <input
                  defaultChecked
                  id="push-everything"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  checked={valveMode === "sample"}
                  onChange={() => setValveMode("sample")}
                />
                <label
                  htmlFor="push-everything"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Sample Injection
                </label>
              </div>
              <div className="flex items-center gap-x-3">
                <input
                  id="push-email"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onChange={() => setValveMode("solvent")}
                />
                <label
                  htmlFor="push-email"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Solvent Injection
                </label>
              </div>
              <div className="flex items-center gap-x-3">
                <input
                  id="push-nothing"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onChange={() => setValveMode("air")}
                />
                <label
                  htmlFor="push-nothing"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Air Injection
                </label>
              </div>
            </div>
          </fieldset>
        </div>

        <div className="ml-auto mt-6">
          <button
            type="button"
            onClick={() => controlValve()}
            className="inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Submit
          </button>
        </div>
      </form>

      {/* Pump Controls*/}
      <form>
        <div className="pt-12">
          <h2 className="text-base/7 font-semibold text-gray-900">
            Pump Controls
          </h2>

          <div className="sm:col-span-3">
            <div className="flex items-center gap-4">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Pump:
              </p>
              <div className="grid grid-cols-1">
                <select
                  id="initial-samples"
                  name="initial-samples"
                  className="col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                  value={selectedPump}
                  onChange={(e) => setSelectedPump(e.target.value)}
                >
                  {Object.keys(pumps).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                <ChevronDownIcon
                  aria-hidden="true"
                  className="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
            <div className="sm:col-span-3">
              <div className="mt-2">
                <div className="flex items-center gap-4 sm:col-span-3">
                  <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                    Syringe Volume (mL):
                  </p>
                  <input
                    id="first-name"
                    name="first-name"
                    type="number"
                    autoComplete="given-name"
                    className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                    onChange={(e) =>
                      setPumpControls((prev) => ({
                        ...prev,
                        syringe_volume: Number(e.target.value),
                      }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          <fieldset>
            <div className="mt-6 space-y-6">
              <div className="flex items-center gap-x-3">
                <input
                  defaultChecked
                  id="push-everything"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onClick={() =>
                    setPumpControls((prev) => ({
                      ...prev,
                      command: 'Initialize',
                    }))
                  }
                />
                <label
                  htmlFor="push-everything"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Initialize
                </label>
              </div>
              <div className="flex items-center gap-x-3">
                <input
                  id="push-email"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onClick={() =>
                    setPumpControls((prev) => ({
                      ...prev,
                      command: 'Withdraw',
                    }))
                  }
                />
                <label
                  htmlFor="push-email"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Withdraw Sample
                </label>
              </div>
              <div className="flex items-center gap-x-3">
                <input
                  id="push-nothing"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onClick={() =>
                    setPumpControls((prev) => ({ ...prev, command: 'Inject' }))
                  }
                />
                <label
                  htmlFor="push-nothing"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Inject Sample
                </label>
              </div>
              <div className="flex items-center gap-x-3">
                <input
                  id="push-email"
                  name="push-notifications"
                  type="radio"
                  className="relative size-4 appearance-none rounded-full border border-gray-300 bg-white before:absolute before:inset-1 before:rounded-full before:bg-white not-checked:before:hidden checked:border-blue-600 checked:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:before:bg-gray-400 forced-colors:appearance-auto forced-colors:before:hidden"
                  onClick={() =>
                    setPumpControls((prev) => ({ ...prev, command: 'Flush' }))
                  }
                />
                <label
                  htmlFor="push-email"
                  className="block text-sm/6 font-medium text-gray-900"
                >
                  Flush to Waste
                </label>
              </div>
            </div>
          </fieldset>
        </div>

        <div className="ml-auto mt-6">
          <button
            type="button"
            onClick={() => controlPump()}
            className="inline-flex justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          >
            Submit
          </button>
        </div>
      </form>
    </div>
  );
}
