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

    RefillSample, pump_flow_rate
)
from CleaningV9 import (cleaning_part1, Cleaning_part2, Cleaning_part2_switch, Cleaning_Pump1_HC, cleanCp, airpurge)
from SampleSwitchV9 import (switch_sample1, switch_sample2, switch_sample3, switch_sample1_aut, switch_sample2_aut, switch_sample3_aut, switch_solvent, clean_pump1_line1, clean_pump2_line2, clean_pump3_line3)
from HCV9 import (run_experiment, run_experiment2)


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



# Globals to track previous chemicals
prev_chem_pump1 = None
prev_chem_pump2 = None
prev_chem_pump3 = None

def pump1_assign_chemical(chemical, valve_map, prev_chem_pump1):
    #global prev_chem_pump1
    changed = (chemical != prev_chem_pump1)
    prev_chem_pump1 = chemical
    clean_pump1_line1(changed)
    time.sleep(1)
    open_valve1(chemical, valve_map)
    '''
    if changed==True:
        print("Refill with sample")
        PumpWithdrawSample1(100)
        '''
    return changed

def pump2_assign_chemical(chemical, valve_map, prev_chem_pump2):
    #global prev_chem_pump2
    changed = (chemical != prev_chem_pump2)
    prev_chem_pump2 = chemical
    clean_pump2_line2(changed)
    time.sleep(1)
    open_valve2(chemical, valve_map)
    '''
    if changed==True:
        print("Refill with sample")
        PumpWithdrawSample2(100)
        '''
    return changed

def pump3_assign_chemical(chemical, valve_map, prev_chem_pump3):
    #global prev_chem_pump3
    changed = (chemical != prev_chem_pump3)
    prev_chem_pump3 = chemical
    clean_pump3_line3(changed)
    time.sleep(1)
    open_valve3(chemical, valve_map)
    '''
    if changed==True:
        print("Refill with sample")
        PumpWithdrawSample3(100)
        '''
    return changed

def assign_chemicals(chems, v1_map, v2_map, v3_map, prev_chem_pump1, prev_chem_pump2, prev_chem_pump3):
    injectionmode()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(pump1_assign_chemical, chems[0], v1_map, prev_chem_pump1) if chems[0] else None,
            executor.submit(pump2_assign_chemical, chems[1], v2_map, prev_chem_pump2) if chems[1] else None,
            executor.submit(pump3_assign_chemical, chems[2], v3_map, prev_chem_pump3) if chems[2] else None,
        ]

        # Wait for results, defaulting to False if the future was None
        changed1 = futures[0].result() if futures[0] else False
        changed2 = futures[1].result() if futures[1] else False
        changed3 = futures[2].result() if futures[2] else False

    return changed1, changed2, changed3

def get_chemicals_from_top_row(file_path):
    xls = pd.ExcelFile(file_path)
    sheet_chemicals = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, nrows=0)
        chemicals = list(df.columns)
        chemicals = [str(c).strip() for c in chemicals if str(c).strip().isalpha()]
        sheet_chemicals[sheet_name] = chemicals
    return sheet_chemicals
def get_chemicals_and_compositions(file_path):
    xls = pd.ExcelFile(file_path)
    sheet_data = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        chemicals = list(df.columns)
        chemicals = [str(c).strip() for c in chemicals if str(c).strip().isalpha()]
       
        # Assuming the compositions are in rows below the headers
        compositions = df.iloc[0:].values.tolist()  # Skipping the header row
       
        # Collecting both the chemical list and their compositions
        sheet_data[sheet_name] = {'chemicals': chemicals, 'compositions': compositions}
   
    return sheet_data

