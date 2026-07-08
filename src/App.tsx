import { useState } from 'react';
import './App.css';
import Devices from './components/Devices/page';
import VD_Measurements from './components/VDMeasurements';
import HC_Measurements from './components/HCMeasurements';
import CleaningOperations from './components/CleaningOperations/page';
import Routine_Manager from './components/RoutineManager';

const navigation = [
  { name: 'Devices', href: '/components/Devices' },
  { name: 'V/D Measurements', href: '/components/VD_Measurements' },
  { name: 'HC Measurements', href: '/components/HC_Measurements' },
  { name: 'Cleaning Operations', href: '/components/CleaningOperations' },
  { name: 'Routine Manager', href: '/components/Routine_Manager' },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

{
  /* Main function. Navbar defined here.*/
}
export default function App() {
  const [current, setCurrent] = useState('Devices');

  return (
    <>
      <div className="min-h-full">
        <div className="bg-white border-b border-blue-200">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex justify-center h-10 items-end">
              <div className="flex items-end">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    className={classNames(
                      current === item.name
                        ? 'bg-blue-50 border border-b border-blue-200 text-blue-700 font-semibold -mb-px'
                        : 'text-gray-500 hover:text-blue-600 hover:bg-blue-50 border border-transparent',
                      'px-4 py-3 text-sm'
                    )}
                    onClick={() => setCurrent(item.name)}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {current == 'Devices' && <Devices />}
        {current == 'V/D Measurements' && <VD_Measurements />}
        {current == 'HC Measurments' && <HC_Measurements />}
        {current == 'Cleaning Operations' && <CleaningOperations />}
        {current == 'Routine Manager' && <Routine_Manager />}
      </div>
    </>
  );
}
