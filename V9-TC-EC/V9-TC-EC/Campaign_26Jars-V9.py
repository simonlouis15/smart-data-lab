import numpy as np
import serial
import string
import serial.tools.list_ports
import time
import argparse
import threading
import nidaqmx
import re
import os
import signal
import sys
from sklearn.linear_model import LinearRegression
import xtalx.z_sensor
from xtalx.tools.z_sensor import z_common
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import cv2
from flask import Flask, Response
import atexit
import threading
import argparse
from SelectorValvesV9 import (Valve_Setup, injectionmode, airmode, solventmode, 
                            Valve1_Setup, Valve2_Setup, Valve3_Setup, open_valve1, open_valve2, open_valve3,
                            
                            Solvent_Valve1, Air_Valve1, Solvent_Valve2, Air_Valve2, Solvent_Valve3, Air_Valve3)
from SyringePumpsHTPumpTCV9 import (
    START_pumpSample1, PumpInitialize_pumpSample1, PumpReady_pumpSample1,
    PumpInjection_pumpSample1, PumpWithdrawSample1, PumpWithdrawSample1_Volume1,
    Debubble_pumpSample1, PumpCleaning_pumpSample1, PumpCleaning_pumpSample1_aut,
    PumpFullInjection_pumpSample1, PumpEmpty_PumpSample1,

    START_pumpSample2, PumpInitialize_pumpSample2, PumpReady_pumpSample2,
    PumpInjection_pumpSample2, PumpWithdrawSample2, PumpWithdrawSample2_Volume2,
    Debubble_pumpSample2, PumpCleaning_pumpSample2, PumpCleaning_pumpSample2_aut,
    PumpFullInjection_pumpSample2, PumpEmpty_PumpSample2,

    START_pumpSample3, PumpInitialize_pumpSample3, PumpReady_pumpSample3,
    PumpInjection_pumpSample3, PumpWithdrawSample3, PumpWithdrawSample3_Volume3,
    Debubble_pumpSample3, PumpEmpty_PumpSample3, PumpFullInjection_pumpSample3,
    PumpCleaning_pumpSample3, PumpCleaning_pumpSample3_aut,

    START_pumpSolvent, PumpInitialize_pumpSolvent, PumpReady_pumpSolvent,
    PumpInjection_pumpSolvent, OneInjection_pumpSolvent, PumpFullInjection_pumpSolvent,
    PumpEmpty_PumpSolvent, PumpWithdrawSolvent, Debubble_pumpSolvent,
    PumpCleaning_pumpSolvent, RefillSolvent, injectSolvent,

    START_pump1, PumpInitialize_pump1, PumpReady_pump1, PumpInjection_pump1,
    PumpRefill_pump1, PumpWithdraw,

    START_pump2, PumpInitialize_pump2, PumpReady_pump2, PumpInjection_pump2,
    PumpRefill_pump2, Debubble, EmptyHcSyringe, cleanup,

    START_pump1_HC, PumpInjection_pump1_HC, Stop_pump1_HC,
    START_pump2_HC, PumpInjection_pump2_HC, Stop_pump2_HC,
    InitialInjection_Pump1_HC, InitialInjection_Pump2_HC,

    PumpReady_TC_Ref, START_pump_TC_Ref, PumpInitialize_TC_Ref, 
    PumpInjection_TC_Ref, PumpWithdraw_TC_Ref, PumpWithdraw_TC_Ref_Volume,
    PumpEmpty_TC_Ref,

    RefillSample, pump_flow_rate,

    Position_SamplePump1, Position_SamplePump2, Position_SamplePump3,  Position_HC_Pump1
)
from CleaningV9 import (cleaning_part1, Cleaning_part2, Cleaning_part2_switch, Cleaning_Pump1_HC, cleanCp, airpurge)
from SampleSwitchV9 import (switch_sample1, switch_sample2, switch_sample3, switch_solvent)
from HCV9 import (run_experiment, run_experiment2)
from ChemicalAssignmentV9 import (generate_valve_maps, pump1_assign_chemical, pump2_assign_chemical, pump3_assign_chemical, assign_chemicals, get_chemicals_from_top_row, 
                                get_chemicals_and_compositions)
from EC_codeV9 import ECmeas
from TC_MeasureV9 import measureTC
from TC_Temp_ControlV9 import Temp_Control
#from JarSwitchV5 import Switch_Jar_Pump1, Switch_Jar_Pump2, Switch_Jar_Pump3, JarSwitchCombined
from SafetyCheckV9 import SafetyCheck
from TCV9 import (CalibrationTC, TC_Temperature_Control, TC_Measure,Tempupdate)
from TC_MeasureV9 import measureTC


#initialize viscosity and density array:
Viscosity = []
Density = []
Trial = []
data = []

#start sensor 
def start_dv_sensor_and_get_queue(args):
    """
    Function to initialize and start a VD sensor, configure its tracking system, 
    and set up a queue to process sensor data asynchronously.
    """
    dev    = xtalx.z_sensor.find_one(serial_number=args.sensor)
    tc     = xtalx.z_sensor.make(dev, verbose=args.verbose,
                                 yield_Y=not args.track_impedance)
    za, zl = z_common.parse_args(tc, args)

    pq = xtalx.z_sensor.PredicateQueue(delegate=z_common.ZDelegate(zl))
    pt = xtalx.z_sensor.PeakTracker(tc, za.amplitude,
                                    za.nfreqs, za.search_time_secs,
                                    za.sweep_time_secs, settle_ms=za.settle_ms,
                                    delegate=pq)
    pt.start_threaded()
    
    return tc, pq, pt

parser = argparse.ArgumentParser()
z_common.add_arguments(parser)
args = parser.parse_args()
tc, pq, pt = start_dv_sensor_and_get_queue(args)
print ('Found D/V sensor %s.' % tc.serial_num)

#get measurement function
def get_dv_measurement(pq):
    time.sleep(1)
    while True:
        m = pq.get_measurement()
        pq.clear()
        if m is not None and m.fw_fit is not None:
            print('   Density: %s' % m.density_g_per_ml)
            print(' Viscosity: %s' % m.viscosity_cp)
            print('   Peak Hz: %s' % m.peak_hz)
            print('Peak Width: %s' % m.peak_fwhm)
            print('  Temp (C): %s' % m.fw_fit.temp_c)
            return m
        
        time.sleep(0.1)


def main(args, x1, x2, x3):

    measurements = []
    BatchV = []
    BatchD = []
    Viscosity = []
    Density = []
    Trial =[]
    Temperature=[]
    #change the number of measurements here
    
    time.sleep(25)

    for _ in range(5):
        measurements.append(get_dv_measurement(pq))
    pq.clear()
    
    for i, m in enumerate(measurements):
        print('Measurement %u: %s %s %s %s' % (i+1, m.peak_hz, m.peak_fwhm, m.density_g_per_ml, m.viscosity_cp))
        #adding the measured data to the array
        Viscosity.append(m.viscosity_cp)
        Density.append(m.density_g_per_ml)
        Temperature.append(m.fw_fit.temp_c)
        Trial.append(i+1)
    
    #check if the STD is within the correct range
    start = 0
    end = 5
    STD_Threshold = 0.1
    while True:
        BatchV = Viscosity[start:end] #adding the measurement to an array with size 5 to check STD
        BatchD = Density[start:end]
        BatchT =Temperature[start:end]
        V_STD = np.std(BatchV) #calculate viscosity STD
        D_STD = np.std(BatchD) #calculate density STD
        if V_STD<=STD_Threshold and D_STD<=STD_Threshold: #check STD, if within the thereshold, break the loop, output result
            print("Current viscosity array to calculate STD", BatchV)
            print("Viscosity STD is:",V_STD)
            print("Current density array to calculate STD", BatchD)
            print("Density STD is:", D_STD)
            pq.clear()
            break
        
        #if the STD is not within the desired range, run another test
        mn=get_dv_measurement(pq)
        measurements.append(mn)
        Viscosity.append(mn.viscosity_cp)
        print(Viscosity)
        print("Viscosity Batch:", BatchV)
        print("V_STD:", V_STD)
        Density.append(mn.density_g_per_ml)
        print("Density Batch:", BatchD)
        print("D_STD:", D_STD)
        Trial.append(end + 1)
        print("Trials", Trial)
        Temperature.append(mn.fw_fit.temp_c)

        start += 1
        end += 1
    
    # Summarize - maybe write to file.
    #v = sum(m.density_g_per_ml for m in measurements) / len(measurements)
    #d = sum(m.viscosity_cp for m in measurements) / len(measurements)
    Mean_V = sum(BatchV)/len(BatchV)
    Mean_D = sum(BatchD)/len(BatchD)
    Mean_T = sum(BatchT)/len(BatchT)
    print('Mean viscosity: %s cP' % Mean_V)
    print('  Mean density: %s g/mL' % Mean_D)

    return Mean_V, Mean_D, Mean_T, V_STD, D_STD
    
    

def run_refill_functions_concurrently(flowrate1, flowrate2, flowrate3):
    # Parse arguments
    parser = argparse.ArgumentParser()
    z_common.add_arguments(parser)
    args = parser.parse_args()

    def HC_Ready ():
        PumpRefill_pump1(100)
        PumpRefill_pump2()
        time.sleep(60)
        time.sleep(1)
        Debubble(2.5)
        time.sleep(1)
        print('HC getting initialized.')
        # t1 = threading.Thread(target=InitialInjection_Pump1_HC)
        # time.sleep(1)
        # t2= threading.Thread (target = InitialInjection_Pump2_HC)
        # time.sleep(1)
        # t1.start ()
        # t2.start ()
        # t1.join()
        # t2.join()
        # print('initialized.')
        # time.sleep(120)
    
    # Create threads for RefillSolvent, RefillSample, and main
    thread_solvent = threading.Thread(target=RefillSolvent)
    thread_sample = threading.Thread(target=RefillSample)
    thread_HeatCapacity = threading.Thread(target=HC_Ready)
    #thread_Water = threading.Thread(target=PumpRefill_pump2)
    # Start all threads
    thread_solvent.start()
    thread_sample.start()
    thread_HeatCapacity.start()
    #thread_Water.start()
    print('Refill Started.')
    print('VD Measurement Started')
    # main thread
    Mean_D, Mean_V, Mean_T, V_STD, D_STD = main(args, flowrate1, flowrate2, flowrate3)

    # Wait for all threads to complete
    thread_solvent.join()
    thread_sample.join()
    thread_HeatCapacity.join()
    #thread_Water.join()
    return Mean_D, Mean_V, Mean_T, V_STD, D_STD


def TC_run():
    PumpInjection_TC_Ref(10,1500)
    while not TC_Control.control.isStable():
            time.sleep(2)
    Thermal_Conductivity,voltages = TC_Measure(TC_Control, 3, 0.132)
    print("Thermal conductivity is:", Thermal_Conductivity)
    T_TC=TC_Control.control.T_TC
    print(f"At temp:{T_TC}")
    PumpWithdraw_TC_Ref(5)
    return Thermal_Conductivity,T_TC,voltages

def VD_TC_Measurement_HCPreparation (flowrate1, flowrate2, flowrate3):
    # Parse arguments
    parser = argparse.ArgumentParser()
    z_common.add_arguments(parser)
    args = parser.parse_args()

    def HC_Ready ():
        PumpRefill_pump1(100)
        time.sleep(60)
        time.sleep(1)
        Debubble(2.6)
        time.sleep(1)
        # print('HC getting initialized.')
        # InitialInjection_Pump1_HC()
        # time.sleep(1)
        # InitialInjection_Pump2_HC()
        # time.sleep(1)
        # print('initialized.')
        # time.sleep(120)

    def wrapper_TC(result, idx):
        result[idx]=TC_run()
    result={}
    # Create threads for RefillSolvent, RefillSample, and main
    thread_solvent = threading.Thread(target=RefillSolvent)
    thread_sample = threading.Thread(target=RefillSample)
    # Create threads for RefillSolvent, RefillSample, and main
    thread_HeatCapacity = threading.Thread(target=HC_Ready)
    # Create threads
    thread_TC=threading.Thread(target=wrapper_TC, args=(result,0))
    # Start threads
    thread_TC.start()
    #thread_Water = threading.Thread(target=PumpRefill_pump2)
    # Start all threads
    thread_solvent.start()
    thread_sample.start()
    thread_HeatCapacity.start()
    #thread_Water.start()
    print('Refill Started.')
    print('VD Measurement Started')
    # main thread
    Mean_D, Mean_V, Mean_T, V_STD, D_STD = main(args, flowrate1, flowrate2, flowrate3)

    # Wait for all threads to complete
    thread_solvent.join()
    thread_sample.join()
    thread_HeatCapacity.join()
    # Start threads
    thread_TC.join()
    #thread_Water.join()
    return Mean_D, Mean_V, Mean_T, V_STD, D_STD, result[0][0], result[0][1], result[0][2]




def datagather(composition, batch, mix1, mix2, mix3):
    # Iterate through the compositions
    folder_name = f"C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/"
    # Create the folder
    os.makedirs(folder_name, exist_ok=True)
    data = []
    for comp in composition:
        x1, x2, x3 = comp  # Unpack each composition into x1, x2, x3
        print(f"x1: {x1}, x2: {x2}, x3: {x3}")
        # You can add further processing logic or calculations for x1, x2, x3
        # Example: perform any additional data processing or logging here
        flow_rate_mm_sample1 = round(x1, 3) * 10
        flow_rate_mm_sample2 = round(x2, 3) * 10
        flow_rate_mm_sample3 = round(x3, 3) * 10

        # PUMP INJECTION
        pump_flow_rate(flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3)
        EC = ECmeas ()
        # REFILL & VD MEASUREMENT
        Mean_V, Mean_D, Mean_T, V_STD, D_STD, Thermal_Conductivity,T_TC,voltages = VD_TC_Measurement_HCPreparation(flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3)
        print(Mean_D)


        # Prepare arguments for the experiment
        args_experiment = (
            Mean_D * 1000, mix1, mix2, mix3, 
            flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3,
            Mean_V, Mean_D, Mean_T, V_STD, D_STD, batch
        )
        

        # Create threads for concurrent execution
        cleaning_thread = threading.Thread(target=cleaning_part1)

        # Start the first two threads (run_experiment & cleaning_part1)
        cleaning_thread.start()

        #Cp1,e=run_experiment(Mean_D * 1000, mix1, mix2, mix3, flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3, Mean_V, Mean_D, Mean_T, V_STD, D_STD, batch, Thermal_Conductivity)

        # Wait for all threads to finish
        cleaning_thread.join()
        Cp1=1000
        run_experiment2(Mean_D * 1000, mix1, mix2, mix3, flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3, Mean_V, Mean_D, Mean_T, V_STD, D_STD, Cp1, batch, data, Thermal_Conductivity, T_TC, EC)


        # CLEANING PROCESS
        EmptyHcSyringe(200)
        time.sleep(1)

        thread_Water = threading.Thread(target=PumpRefill_pump2)

        thread_Water.start()
        Cleaning_part2()
        time.sleep(1)
        thread_Water.join()
        time.sleep(1)
        injectionmode()
        SafetyCheck()

def process_pumps_for_sheets(file_path, start_sheet=None, end_sheet=None, num_chemicals=26, first_cleaning = False):
    prev_chem_pump1 = f'{start_sheet[0]}'
    prev_chem_pump2 = f'{start_sheet[1]}'
    prev_chem_pump3 = f'{start_sheet[2]}'
    # Generate valve maps once
    v1_map, v2_map, v3_map = generate_valve_maps(num_chemicals)

    sheet_data = get_chemicals_and_compositions(file_path)
    sheet_names = list(sheet_data.keys())
    print(sheet_names)

    if start_sheet is not None:
        if start_sheet not in sheet_names:
            raise ValueError(f"Sheet '{start_sheet}' not found in Excel file.")
        start_index = sheet_names.index(start_sheet)
        print(start_index)
        if start_index == 0:
            start_index_adj =0
        else:
            start_index_adj =start_index-1

        sheet_names = sheet_names[start_index_adj:]  # process from start_sheet onwards
    if end_sheet is not None:
        if end_sheet not in sheet_names:
            raise ValueError(f"Sheet '{end_sheet}' not found in Excel file.")
        end_index = sheet_names.index(end_sheet) + 1
    else:
        end_index = len(sheet_names)

    # Slice sheet list from start to end (inclusive of end_sheet)
    sheet_names = sheet_names[start_index:end_index]
    print(sheet_names)

    for sheet in sheet_names:
        data = sheet_data[sheet]
        chems = data['chemicals']
        compositions = data['compositions']

        print(f"Processing sheet '{sheet}' with chemicals: {chems}")
        print(f"Compositions: {compositions}")
       
        chems = (chems + [None]*3)[:3]  # Ensure 3 chemicals
       
        #changed1 = pump1_assign_chemical(chems[0], v1_map) if chems[0] else False
        #changed2 = pump2_assign_chemical(chems[1], v2_map) if chems[1] else False
        #changed3 = pump3_assign_chemical(chems[2], v3_map) if chems[2] else False
        if first_cleaning:
            changed1, changed2, changed3 = assign_chemicals(chems, v1_map, v2_map, v3_map, prev_chem_pump1, prev_chem_pump2, prev_chem_pump3)

            print(f" Pump 1 chemical: {chems[0]}, changed: {changed1}")
            print(f" Pump 2 chemical: {chems[1]}, changed: {changed2}")
            print(f" Pump 3 chemical: {chems[2]}, changed: {changed3}")
            print()
      
            # If any of the pumps changed, perform cleaning
            # If any of the pumps changed, perform cleaning
            if True:
                # Get rid of the excess liquids
                # PumpRefill_pump1(400)
                # time.sleep(25)
                # EmptyHcSyringe(200)
                # PumpRefill_pump1(400)
                # time.sleep(25)
                # EmptyHcSyringe(200)
                # PumpRefill_pump1(400)
                # time.sleep(25)
                # EmptyHcSyringe(200)
                # Start cleaning
                print('VD Cleaning Started.')
                cleaning_part1()
                print('HC Cleaning Started.')
                t1 = threading.Thread(target=Cleaning_part2_switch)
                t2 = threading.Thread(target=RefillSample)
                t3 = threading.Thread(target=RefillSolvent)
                # Start both threads
                t1.start()
                t2.start()
                t3.start()

                # Wait for both to finish
                t1.join()
                t2.join()
                t3.join()

                print('Sample Debubble Started.')
                t1 = threading.Thread(target=Debubble_pumpSample1, args=(20, 500))
                t2 = threading.Thread(target=Debubble_pumpSample2, args=(20, 500))
                t3 = threading.Thread(target=Debubble_pumpSample3, args=(20, 500))

                t1.start()
                t2.start()
                t3.start()

                t1.join()
                t2.join()
                t3.join()
                print('Sample Refill Started.')
                RefillSample()
                time.sleep(30)
                print('Refilling the lines')
                injectionmode()
                t1 = threading.Thread(target=PumpInjection_pumpSample1, args=(1, 500))
                t2 = threading.Thread(target=PumpInjection_pumpSample2, args=(1, 500))
                t3 = threading.Thread(target=PumpInjection_pumpSample3, args=(1, 500))

                t1.start()
                t2.start()
                t3.start()

                t1.join()
                t2.join()
                t3.join()
                print('Sample Refill Started.')
                RefillSample()
                time.sleep(30)


        
        datagather(compositions, sheet, chems[0], chems[1], chems[2])
        time.sleep(20)
        first_cleaning = True
    
    

def datagather_Test(composition, sheet, Mix1, Mix2, Mix3):
    print('Data Gathering Started')
    print(f"Sheet: {sheet}")
   
    # Iterate through the compositions
    for comp in composition:
        x1, x2, x3 = comp  # Unpack each composition into x1, x2, x3
        print(f"x1: {x1}, x2: {x2}, x3: {x3}")
        # You can add further processing logic or calculations for x1, x2, x3
        # Example: perform any additional data processing or logging here





# Start temp control threads
TC_Control = measureTC()

time.sleep(0.1)

thread_TC_Temperature = threading.Thread(target=TC_Temperature_Control, args=(TC_Control,))
threadtempupdate=threading.Thread(target=Tempupdate, args=(TC_Control,))
thread_TC_Temperature.start()
threadtempupdate.start()

def cleanup ():
    print('Closing TC')
    tc=measureTC()
    time.sleep(0.1)
    injectionmode()
    tc.end()

atexit.register(cleanup)




# Example usage:
#PumpInitialize_pump2()
#print('Initialized.')
#Cleaning_part2()
#Stop_pump1_HC()
#Stop_pump2_HC()
#PumpRefill_pump2()
#Cp1,e=run_experiment(1 * 1000, 'A', 'B', 'C', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)
#Stop_pump2_HC()
#PumpRefill_pump2()
#RefillSolvent()
#PumpInitialize_pump1 ()
#PumpInitialize_pump2 ()
#cleaning_part1()
#Cleaning_part2 ()
#Cleaning_part2 ()
#PumpWithdrawSample1(100)
#PumpWithdrawSample2(100)
#PumpWithdrawSample3(100)
file_path = r'C:\Users\Indus\OneDrive\Desktop\26 Campaign\DataGatheringCampaign\V9-TC-EC\V9-TC-EC\user_defined_ternary_compositions_in_ternary_sheets.xlsx'
#PumpInitialize_pumpSolvent()
#PumpEmpty_PumpSolvent(10)
#EmptyHcSyringe(400)
#airmode()
#PumpInitialize_pump2()
#Cleaning_part2()
#EmptyHcSyringe(200)
#PumpEmpty_PumpSample2(20)
#process_pumps_for_sheets(file_path, start_sheet='JKL', end_sheet=None, num_chemicals=26, first_cleaning = False)
#Cleaning_part2()
#TC_run()
#PumpInitialize_pump1()
#PumpRefill_pump1(200)
#Debubble(2.5)
#InitialInjection_Pump1_HC()
#Stop_pump1_HC()
#EmptyHcSyringe(400)
#PumpInitialize_pump1()
#PumpWithdraw()
#Cleaning_Pump1_HC(60)
#Stop_pump1_HC()
#Stop_pump2_HC()
#EmptyHcSyringe(400)
#PumpWithdrawSolvent()
#PumpEmpty_PumpSample1(10)
#EmptyHcSyringe(200)
#InitialInjection_Pump1_HC()
#InitialInjection_Pump2_HC()
#airmode()
#PumpInitialize_TC_Ref()
#PumpEmpty_TC_Ref(10)
#PumpInitialize_pumpSolvent()
# injectionmode()
PumpWithdrawSample2(10)
PumpFullInjection_pumpSample2(10,0)

PumpInjection_TC_Ref(8,3000)
PumpWithdraw_TC_Ref(8)
time.sleep(400)

TC_Control.record=True
time.sleep(90)


# Turns on the internal heater (remember to stop control in case of conflict)
# reopen temp control and wait for temp stabilization
TC_Control.control.status = False
time.sleep(4)
TC_Control.hmp4040.setVoltage(3, 32)
TC_Control.hmp4040.setCurrent(3, 0.07)
TC_Control.hmp4040.channelOn(3)
time.sleep(4)
TC_Control.control.status = True


time.sleep(360)



TC_Control.isdone = True

thread_TC_Temperature.join()
threadtempupdate.join()

def cleanup ():
    print('Closing TC')
    tc=measureTC()
    time.sleep(0.1)
    injectionmode()
    tc.end()

atexit.register(cleanup)


'''
tc = measureTC()

tc.calibrate()

tc.control.heatControl() # Run in a separate thread

tc.control.changeTemperature(30)

tc.control.isStable() # Check temperature stability, run before taking measurement

k = tc.thermalConductivity(tc.takeMeasurement(), 3, 0.265)
print(k)

tc.end()
'''
#PumpInjection_pumpSample1(10, 6000)
#PumpWithdraw_TC_Ref(5)
#PumpInitialize_pumpSolvent()
#PumpInjection_pumpSolvent(10)
#cleaning_part1()
#PumpInitialize_pump2()
#PumpInitialize_pumpSample3()
#PumpWithdrawSample1(100)
#JarSwitchCombined ('K', 11)
#PumpWithdrawSample3(100)
#cleaning_part1()
#Cleaning_part2()
#PumpInitialize_pumpSample3()
#num_chemicals=26
#v1_map, v2_map, v3_map = generate_valve_maps(num_chemicals)
#open_valve1('A', v1_map)
#RefillSample()
#PumpInitialize_pumpSolvent ()
#PumpWithdrawSolvent()
#solventmode()
#PumpInjection_pumpSolvent(20)