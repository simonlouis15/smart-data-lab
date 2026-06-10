import { useState } from 'react'
import './App.css'
import Devices from "./components/Devices"
import VD_Measurements from './components/VD_Measurements'

const navigation = [
  { name: 'Devices', href: '/components/Devices.tsx'},
  { name: 'V/D Measurements', href: '/components/VD_Measurements.tsx' },
  { name: 'HC Measurements', href: '/components/HC_Measurements.tsx' },
  { name: 'Cleaning', href: '/components/Cleaning.tsx' },
  { name: 'Routine Manager', href: '/components/Routine_Manager.tsx' },
]

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

export default function Example() {

  const [current, setCurrent] = useState('Devices')

  return (
    <>
      <div className="min-h-full">
        <div className="bg-gray-100">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-center">
              <div className="flex items-center">
                <div className="hidden md:block">
                  <div className="ml-10 flex items-baseline space-x-4">
                      {navigation.map((item) => (
                        <button
                          key={item.name}
                          className={classNames(
                            current === item.name ? 'bg-gray-300 text-gray-900' : 'text-gray-900 hover:bg-gray-200',
                            'rounded-md px-3 py-2 text-sm font-medium',
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
          </div>
        </div>
        
        {current == "Devices" && <Devices />}
        {current == "V/D Measurements" && <VD_Measurements />}
        
      </div>
    </>
  )
}
