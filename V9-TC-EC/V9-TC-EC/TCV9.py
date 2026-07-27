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

    RefillSample, pump_flow_rate, SolventPumpCleanedbyAir,SolventPumpforTC, TC_Pumping_Calibration
)
from CleaningV9 import (cleaning_part1, Cleaning_part2, Cleaning_part2_switch, Cleaning_Pump1_HC, cleanCp, airpurge, cleaning_part1long)
from SampleSwitchV9 import (switch_sample1, switch_sample2, switch_sample3,switch_solvent)
from HCV9 import (run_experiment, run_experiment2)
from ChemicalAssignmentV9 import (generate_valve_maps, pump1_assign_chemical, pump2_assign_chemical, pump3_assign_chemical, assign_chemicals, get_chemicals_from_top_row, 
                                get_chemicals_and_compositions)

from TC_MeasureV9 import measureTC
from TC_Temp_ControlV9 import Temp_Control



#### Functions for TC measurements
def CalibrationTC (TC_Control):
    '''
    Function for calibration with cleaning included
    '''
    
    TC_Pumping_Calibration ()
    while not TC_Control.control.isStable():
        time.sleep(2)
    TC_Control.calibrate()

    t1 = threading.Thread(target=prepareforclean)

    t1.start()

    t1.join()

    print('Cleaning part 1 started.')
    cleaning_part1()
    
def MeasurewithrefTC (TC_Control):
    '''
    Function for measuring 2-butanol to check accuracy with cleaning included
    '''
    PumpEmpty_PumpSolvent(20)
    solventmode()
    PumpInjection_TC_Ref(8,1500)
    SolventPumpforTC()
    while not TC_Control.control.isStable():
        time.sleep(2)
    k = TC_Control.thermalConductivity(TC_Control.takeMeasurement(), 3, 0.132)
    PumpWithdraw_TC_Ref(5)
    print(k)
    
    t1 = threading.Thread(target=prepareforclean)

    t1.start()

    t1.join()
    
    print('Cleaning part 1 started.')
    cleaning_part1long()
    return k

def TC_Measure(TC_Control, sampleChannel, referenceK):
    '''
    Function for taking tc measurement
    '''
    while not TC_Control.control.isStable():
        time.sleep(2)

    voltages = TC_Control.takeMeasurement()
    print(f'check if voltage looks good {voltages}')
    k = TC_Control.thermalConductivity(voltages, sampleChannel, referenceK)

    if k == 0:
        while not TC_Control.control.isStable():
            time.sleep(2)
        voltages = TC_Control.takeMeasurement()
        k = TC_Control.thermalConductivity(voltages, sampleChannel, referenceK)
    return k,voltages


#### Function for temperature control, need to be ran in a thread at all times
def TC_Temperature_Control (TC_Control):
    V1_l=[]
    I1_l=[]
    V2_l=[]
    I2_l=[]
    while not TC_Control.isdone:
        TC_Control.control.heatControl()
        if TC_Control.record==True:
            V1=TC_Control.hmp4040.readVoltage(1)
            V2=TC_Control.hmp4040.readVoltage(2)
            I1=TC_Control.hmp4040.readCurrent(1)
            I2=TC_Control.hmp4040.readCurrent(2)
            V1_l.append(V1)
            I1_l.append(I1)
            V2_l.append(V2)
            I2_l.append(I2)
            print(V1_l)
            print(I1_l)
    print('Closing TC and Control')
    V3=TC_Control.hmp4040.readVoltage(3)
    I3=TC_Control.hmp4040.readCurrent(3)
    df=pd.DataFrame({
        'I1':I1_l,
        'V1':V1_l,
        'I2':I2_l,
        'V2':V2_l
    })
    df.to_excel(r'C:\Users\Indus\OneDrive\Desktop\26 Campaign\DataGatheringCampaign\V9-TC-EC\V9-TC-EC\Powerdata_1.xlsx')
    print(f'V3:{V3}, I3:{I3}')
    TC_Control.end()

def Tempupdate(TC_Control):
    while not TC_Control.isdone:
        time.sleep(10)
        print(f'Temp of block is {TC_Control.control.T_TC}')
        print(TC_Control.control.t)


####
def prepareforclean():
    solventmode()
    print('Solvent pump getting cleaned by solvent.')
    PumpEmpty_PumpSolvent(15)
    RefillSolvent ()
    PumpEmpty_PumpSolvent(15)
    SolventPumpCleanedbyAir ()
    SolventPumpCleanedbyAir ()
    RefillSolvent ()



    