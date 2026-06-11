//import { Command } from '@tauri-apps/plugin-shell';
import config from '../../config 2.json';

// Access all pumps
interface Pump {
  Port: string;
  'Pump Number': number;
  'Flow Rate': number;
  Baudrate: number;
  // ... other fields
}

{
  /* Devices function. Harware devices such as pumps, valves and data acquisition are controlled here.*/
}
export default function Devices() {
  /*const command = Command.sidecar('binaries/my-sidecar', [
        'arg1',
        '-a',
        '--arg2',
        'any-string-that-matches-the-validator',
    ]);
    const output = await command.execute();*/

  const pumps = config.Devices.Pumps as Record<string, Pump>;

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
          </p>
          <div className="grid grid-cols-1 gap-x-6 gap-y-8">
            <div className="flex items-center gap-4 sm:col-span-3">
              <input
                id="serial-number"
                name="serial-number"
                type="text"
                autoComplete="off"
                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
              />
              <button
                type="button"
                className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 whitespace-nowrap"
              >
                Auto-Detect
              </button>
            </div>
          </div>

          <h2 className="text-base/7 font-semibold text-gray-900 mt-12">
            Pump Configuration
          </h2>
          <p className="mt-1 text-sm/6 text-gray-600">
            Configure sample, solvent and HC pumps. Click on a pump to edit its
            properties.
          </p>
          <div className="mt-2 rounded-md bg-blue-50 border border-gray-300 p-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(pumps).map(([name, pump]: [string, Pump]) => (
                <button
                  key={name}
                  type="button"
                  className="flex flex-col items-start gap-1 rounded-md bg-white px-4 py-3 text-left border border-gray-300 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
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

            <div className="flex justify-center mt-4">
              <button
                type="button"
                className="flex flex-col items-center justify-center gap-1 rounded-md bg-blue-600 px-4 py-3 text-center border border-gray-300 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
              >
                <span className="text-sm font-semibold text-white">
                  Add Config +
                </span>
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
