import { ChevronDownIcon } from '@heroicons/react/16/solid';

export default function VD_Measurements() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="relative after:pointer-events-none after:absolute after:inset-x-0 after:inset-y-0 after:border-y after:border-white/10">
        <div className="border-b border-gray-900/10 pb-12">
          <h3 className="text-3xl font-bold tracking-tight text-gray-900">
            Viscosity / Density Measurement
          </h3>
          <h3 className="text-l tracking-tight text-gray-900">
            Configure and run viscosity and density measurements using the XtaiX
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
              <div className="flex gap-3">
                <div className="flex h-6 shrink-0 items-center">
                  <div className="group grid size-4 grid-cols-1">
                    <input
                      id="candidates"
                      name="candidates"
                      type="checkbox"
                      aria-describedby="candidates-description"
                      className="col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto"
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
                      <path
                        d="M3 7H11"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="opacity-0 group-has-indeterminate:opacity-100"
                      />
                    </svg>
                  </div>
                </div>
                <div className="text-sm/6">
                  <label
                    htmlFor="candidates"
                    className="font-medium text-gray-900"
                  >
                    Verbose Mode
                  </label>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="flex h-6 shrink-0 items-center">
                  <div className="group grid size-4 grid-cols-1">
                    <input
                      id="offers"
                      name="offers"
                      type="checkbox"
                      aria-describedby="offers-description"
                      className="col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto"
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
                      <path
                        d="M3 7H11"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="opacity-0 group-has-indeterminate:opacity-100"
                      />
                    </svg>
                  </div>
                </div>
                <div className="text-sm/6">
                  <label htmlFor="offers" className="font-medium text-gray-900">
                    Track Impedance
                  </label>
                </div>
              </div>
            </div>
          </fieldset>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8  mt-4">
            <div className="flex items-center gap-4 sm:col-span-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Serial Number:
              </p>
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
                    id="candidates"
                    name="candidates"
                    type="checkbox"
                    aria-describedby="candidates-description"
                    className="col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto"
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
                    <path
                      d="M3 7H11"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="opacity-0 group-has-indeterminate:opacity-100"
                    />
                  </svg>
                </div>
              </div>
              <label
                htmlFor="candidates"
                className="text-sm/6 font-medium text-gray-900"
              >
                Clean First
              </label>
            </div>

            <div className="flex gap-3 items-center">
              <div className="flex h-6 shrink-0 items-center">
                <div className="group grid size-4 grid-cols-1">
                  <input
                    id="offers"
                    name="offers"
                    type="checkbox"
                    aria-describedby="offers-description"
                    className="col-start-1 row-start-1 appearance-none rounded-sm border border-gray-300 bg-white checked:border-blue-600 checked:bg-blue-600 indeterminate:border-blue-600 indeterminate:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:border-gray-300 disabled:bg-gray-100 disabled:checked:bg-gray-100 forced-colors:appearance-auto"
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
                    <path
                      d="M3 7H11"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="opacity-0 group-has-indeterminate:opacity-100"
                    />
                  </svg>
                </div>
              </div>
              <label
                htmlFor="offers"
                className="text-sm/6 font-medium text-gray-900"
              >
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
                    id="first-name"
                    name="first-name"
                    type="text"
                    autoComplete="given-name"
                    className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
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
                    id="last-name"
                    name="last-name"
                    type="text"
                    autoComplete="family-name"
                    className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8  mt-4">
            <div className="flex items-center gap-4 sm:col-span-3">
              <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                Compositions File:
              </p>
              <input
                id="serial-number"
                name="serial-number"
                type="text"
                autoComplete="off"
                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
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
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-6">

            {/* Row 1: Initial Samples + Statistical Batch Size */}
            <div className="sm:col-span-3">
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                  Initial Samples:
                </p>
                <div className="grid grid-cols-1">
                  <select
                    id="initial-samples"
                    name="initial-samples"
                    className="col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                    defaultValue="5"
                  >
                    {[1,2,3,4,5,6,7,8,9,10].map(n => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                  <ChevronDownIcon
                    aria-hidden="true"
                    className="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4"
                  />
                </div>
              </div>
            </div>

            <div className="sm:col-span-3">
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                  Statistical Batch Size:
                </p>
                <div className="grid grid-cols-1">
                  <select
                    id="batch-size"
                    name="batch-size"
                    className="col-start-1 row-start-1 w-full appearance-none rounded-md bg-white py-1.5 pr-8 pl-3 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                    defaultValue="5"
                  >
                    {[1,2,3,4,5,6,7,8,9,10].map(n => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                  <ChevronDownIcon
                    aria-hidden="true"
                    className="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end text-gray-500 sm:size-4"
                  />
                </div>
              </div>
            </div>

            {/* Row 2: Viscosity Std Dev + Density Std Dev */}
            <div className="sm:col-span-3">
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                  Viscosity Std Dev:
                </p>
                <input
                  id="viscosity-std-dev"
                  name="viscosity-std-dev"
                  type="number"
                  step="0.01"
                  defaultValue="0.1"
                  className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                />
              </div>
            </div>

            <div className="sm:col-span-3">
              <div className="flex items-center gap-4">
                <p className="text-sm/6 text-gray-900 whitespace-nowrap">
                  Density Std Dev:
                </p>
                <input
                  id="density-std-dev"
                  name="density-std-dev"
                  type="number"
                  step="0.01"
                  defaultValue="0.1"
                  className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-600 sm:text-sm/6"
                />
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  );
}