import { Command } from '@tauri-apps/plugin-shell';

{/* Devices function. Harware devices such as pumps, valves and data acquisition are controlled here.*/}
export default async function Devices() {

    const command = Command.sidecar('binaries/my-sidecar', [
        'arg1',
        '-a',
        '--arg2',
        'any-string-that-matches-the-validator',
    ]);
    const output = await command.execute();

    const configurations = [
        { id: 1, label: "Config Alpha", description: "Primary setup" },
        { id: 2, label: "Config Beta", description: "Secondary setup" },
        { id: 3, label: "Config Gamma", description: "Tertiary setup" },
        { id: 4, label: "Config Delta", description: "Quaternary setup" },
        { id: 5, label: "Config Epsilon", description: "Fifth setup" },
        { id: 6, label: "Config Zeta", description: "Sixth setup" },
        { id: 7, label: "Config Eta", description: "Seventh setup" },
    ];

    return (
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
                <div className="border-b border-gray-900/10 pb-12">
                    <h3 className="text-3xl font-bold tracking-tight text-gray-900">Devices</h3>
                    <h3 className="text-l tracking-tight text-gray-900">Configure all hardware devices including pumps, valves and data acquisition.</h3>
                </div>
            </header>

            <form>
                <div className="pt-12">
                    <h2 className="text-base/7 font-semibold text-gray-900">Import Configuration</h2>
                    <p className="mt-1 text-sm/6 text-gray-600">
                        Load a saved JSON configuration file to import device settings.
                    </p>

                    <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6 mb-12">
                        <div className="sm:col-span-4">
                            <div className="mt-2">
                                <div className="flex gap-x-2">
                                    <div className="flex items-center rounded-md bg-white pl-3 outline-1 -outline-offset-1 outline-gray-300 focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-blue-600">
                                        <div className="shrink-0 text-base text-gray-500 select-none sm:text-sm/6"></div>
                                        <input
                                            id="configuration"
                                            name="configuration"
                                            type="text"
                                            className="block min-w-0 grow bg-white py-1.5 pr-3 pl-1 text-base text-gray-900 placeholder:text-gray-400 focus:outline-none sm:text-sm/6"
                                        />
                                    </div>
                                    <button
                                        type="button"
                                        className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                                    >
                                        Load Configuration
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <h2 className="text-base/7 font-semibold text-gray-900 mt-12">Pump Configuration</h2>
                    <p className="mt-1 text-sm/6 text-gray-600">
                        Configure sample, solvent and HC pumps. Click on a pump to edit its properties.
                    </p>

                    <div className="mt-2 rounded-md border border-gray-300 p-3">
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            {configurations.map((config) => (
                                <button
                                    key={config.id}
                                    type="button"
                                    className="flex flex-col items-start gap-1 rounded-md bg-white px-4 py-3 text-left border border-gray-300 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                                >
                                    <span className="text-sm font-semibold text-gray-900">{config.label}</span>
                                    <span className="text-xs text-gray-500">{config.description}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </form>
        </div>
    )
}