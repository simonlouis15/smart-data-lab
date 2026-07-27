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
    PumpFullInjection_pumpSample2, PumpEmpty_PumpSample2, PumpCleaning_JarSwitch1, 
    PumpCleaning_JarSwitch2, PumpCleaning_JarSwitch3,

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

    RefillSample, pump_flow_rate
)

from CleaningV9 import (cleaning_part1, Cleaning_part2, Cleaning_part2_switch, Cleaning_Pump1_HC, cleanCp, airpurge)

def generate_valve_maps(n):
    letters = list(string.ascii_uppercase)
    if n > len(letters):
        raise ValueError(f"Input too large, max is {len(letters)}")

    valve1_chems = letters[0:n]            # A ... nth letter
    valve2_chems = letters[0:n]            # B ... nth letter (shifted 1)
    valve3_chems = letters[0:n]            # C ... nth letter (shifted 2)

    def make_map(chem_list):
        return {chem: idx+1 for idx, chem in enumerate(chem_list)}

    valve1_map = make_map(valve1_chems)
    valve2_map = make_map(valve2_chems)
    valve3_map = make_map(valve3_chems)

    return valve1_map, valve2_map, valve3_map


def Switch_Jar_Pump1(chemical, NumChem):
    v1_map, v2_map, v3_map = generate_valve_maps(NumChem)
    print("Syringe1 getting emptied")
    PumpEmpty_PumpSample1(10)
    time.sleep(1)
    open_valve1(chemical, v1_map)
    time.sleep(1)
    #input("OK, now put the solvent and press Enter to continue...")
    print("Syringe1 filled by solvent")
    PumpCleaning_JarSwitch1()
    #input("OK, now put it in air and press Enter to continue...")
    print("Syringe1 cleaning using Air")
    PumpCleaning_JarSwitch1()
    print("")
    PumpCleaning_JarSwitch1()



def Switch_Jar_Pump2(chemical, NumChem):
    time.sleep(1)
    v1_map, v2_map, v3_map = generate_valve_maps(NumChem)
    print("Syringe2 getting emptied")
    PumpEmpty_PumpSample2(10)
    time.sleep(1)
    open_valve2(chemical, v2_map)
    time.sleep(1)
    #input("OK, now put the solvent and press Enter to continue...")
    print("Syringe2 filled by solvent")
    PumpCleaning_JarSwitch2()
    #input("OK, now put it in air and press Enter to continue...")
    print("Syringe2 cleaning using Air")
    PumpCleaning_JarSwitch2()

def Switch_Jar_Pump3(chemical, NumChem):
    time.sleep(3)
    v1_map, v2_map, v3_map = generate_valve_maps(NumChem)
    print("Syringe3 getting emptied")
    PumpEmpty_PumpSample3(10)
    time.sleep(1)
    open_valve3(chemical, v3_map)
    time.sleep(1)
    #input("OK, now put the solvent and press Enter to continue...")
    print("Syringe3 filled by solvent")
    PumpCleaning_JarSwitch3()
    #input("OK, now put it in air and press Enter to continue...")
    print("Syringe3 cleaning using Air")
    PumpCleaning_JarSwitch3()


def JarSwitchCombined (chemical, NumChem):
    v1_map, v2_map, v3_map = generate_valve_maps(NumChem)

    print ('Syringes Getting Emptied.')
    # Create threads
    t1 = threading.Thread(target=PumpEmpty_PumpSample1, args=(10,))
    t2 = threading.Thread(target=PumpEmpty_PumpSample2, args=(10,))
    t3 = threading.Thread(target=PumpEmpty_PumpSample3, args=(10,))

    # Start threads
    t1.start()
    t2.start()
    t3.start()

    # Wait for all threads to complete
    t1.join()
    t2.join()
    t3.join()

    open_valve1(chemical, v1_map)
    time.sleep(1)
    open_valve2(chemical, v2_map)
    time.sleep(1)
    open_valve3(chemical, v3_map)
    time.sleep(1)
    input("OK, now put the solvent and press Enter to continue...")

    print ('Solvent cleaning.')
    # Create threads
    t1 = threading.Thread(target=PumpCleaning_JarSwitch1, args=(300, 3000))
    t2 = threading.Thread(target=PumpCleaning_JarSwitch2, args=(300, 3000))
    t3 = threading.Thread(target=PumpCleaning_JarSwitch3, args=(300, 3000))

    # Start threads
    t1.start()
    t2.start()
    t3.start()

    # Wait for all threads to complete
    t1.join()
    t2.join()
    t3.join()

    input("OK, now put it in air and press Enter to continue...")
    '''
    print ('Air cleaning.')
    # Create threads
    t1 = threading.Thread(target=PumpCleaning_JarSwitch1)
    t2 = threading.Thread(target=PumpCleaning_JarSwitch2)
    t3 = threading.Thread(target=PumpCleaning_JarSwitch3)

    # Start threads
    t1.start()
    t2.start()
    t3.start()

    # Wait for all threads to complete
    t1.join()
    t2.join()
    t3.join()
    '''
    print ('Air cleaning.')
    # Create threads
    t1 = threading.Thread(target=PumpCleaning_JarSwitch1, args=(300, 3000))
    t2 = threading.Thread(target=PumpCleaning_JarSwitch2, args=(300, 3000))
    t3 = threading.Thread(target=PumpCleaning_JarSwitch3, args=(300, 3000))

    # Start threads
    t1.start()
    t2.start()
    t3.start()

    # Wait for all threads to complete
    t1.join()
    t2.join()
    t3.join()

    input("OK, now put it in new sample and press Enter to continue...")
    # Create threads
    print ('Refilling the line with sample.')
    t1 = threading.Thread(target=PumpCleaning_JarSwitch1, args=(300, 2000))
    t2 = threading.Thread(target=PumpCleaning_JarSwitch2, args=(300, 2000))
    t3 = threading.Thread(target=PumpCleaning_JarSwitch3, args=(300, 2000))

    # Start thread
    t1.start()
    t2.start()
    t3.start()

    # Wait for all threads to complete
    t1.join()
    t2.join()
    t3.join()
    

#JarSwitchCombined ('A', 26)
#JarSwitchCombined ('B', 26)
#JarSwitchCombined ('C', 26)
#JarSwitchCombined ('D', 26)

