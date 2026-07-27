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


def switch_sample1():
    PumpEmpty_PumpSample1(10)
    input("OK, now put the solvent and press Enter to continue...")
    print("Syringe cleaning using solvent")
    PumpCleaning_pumpSample1()

    input("OK, now put it in air and press Enter to continue...")
    print("Syringe cleaning using Air")
    PumpCleaning_pumpSample1()

    input("OK, now put the sample and press Enter to continue...")
    print("Refill with new sample")
    PumpWithdrawSample1(100)
    time.sleep(30)

    print("Starting injection mode...")
    injectionmode()
    
    time.sleep(2)
    print("Performing full injection...")
    PumpFullInjection_pumpSample1(10,4500)
    PumpWithdrawSample1(100)
    '''
    print("Cleaning the line")
    PumpWithdrawSolvent()
    cleaning_part1()
    '''
    print("Process completed!")
    
def switch_sample2():
    
    PumpEmpty_PumpSample2(10)
    input("OK, now put the solvent and press Enter to continue...")
    print("Syringe cleaning using solvent")
    PumpCleaning_pumpSample2()

    input("OK, now put it in air and press Enter to continue...")
    print("Syringe cleaning using Air")
    PumpCleaning_pumpSample2()
    
    input("OK, now put the sample and press Enter to continue...")
    print("Refill with new sample")
    PumpWithdrawSample2(100)
    time.sleep(30)

    print("Starting injection mode...")
    injectionmode()
    
    time.sleep(2)
    print("Performing full injection...")
    PumpFullInjection_pumpSample2(10,4500)
    PumpWithdrawSample2(100)
    '''
    print("Cleaning the line")
    PumpWithdrawSolvent()
    cleaning_part1()
    '''
    print("Process completed!")


def switch_sample3():
    
    PumpEmpty_PumpSample3(10)
    
    input("OK, now put the solvent and press Enter to continue...")
    print("Syringe cleaning using solvent")
    PumpCleaning_pumpSample3()
    
    input("OK, now put it in air and press Enter to continue...")
    print("Syringe cleaning using Air")
    PumpCleaning_pumpSample3()
    
    input("OK, now put the sample and press Enter to continue...")
    print("Refill with new sample")
    PumpWithdrawSample3(100)
    
    print("Starting injection mode...")
    injectionmode()
    
    time.sleep(2)
    print("Performing full injection...")
    PumpFullInjection_pumpSample3(10,4500)
    PumpWithdrawSample3(100)
    
    print("Process completed!")


def switch_sample1_aut():
    print("Syringe1 getting emptied")
    PumpEmpty_PumpSample1(10)
    time.sleep(1)
    Solvent_Valve1 ()
    time.sleep(1)
    print("Syringe1 cleaning using solvent")
    PumpCleaning_pumpSample1_aut()
    time.sleep(1)
    Air_Valve1()
    time.sleep(1)
    print("Syringe1 cleaning using Air")
    PumpCleaning_pumpSample1_aut()
    time.sleep(1)
    PumpCleaning_pumpSample1_aut()
    time.sleep(1)
    print("Starting injection mode...")
    print('Line1 Cleaning Started!')
    Solvent_Valve1 ()
    time.sleep(1)
    PumpWithdrawSample1_Volume1(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample1(20,6000)
    time.sleep(1)
    Air_Valve1 ()
    PumpWithdrawSample1_Volume1(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample1(20,6000)
    time.sleep(1)
    PumpWithdrawSample1_Volume1(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample1(20,6000)
    time.sleep(1)
    print("Syringe1 and Line1 Cleaning completed!")
    
def switch_sample2_aut():
    print("Syringe2 getting emptied")
    PumpEmpty_PumpSample2(10)
    time.sleep(1)
    Solvent_Valve2 ()
    time.sleep(1)
    print("Syringe2 cleaning using solvent")
    PumpCleaning_pumpSample2_aut()
    time.sleep(1)
    Air_Valve2 ()
    time.sleep(1)
    print("Syringe2 cleaning using Air")
    PumpCleaning_pumpSample2_aut()
    time.sleep(1)
    PumpCleaning_pumpSample2_aut()
    time.sleep(1)
    print("Starting injection mode...")
    print('Line2 Cleaning Started!')
    Solvent_Valve2 ()
    time.sleep(1)
    PumpWithdrawSample2_Volume2(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample2(20,6000)
    time.sleep(1)
    Air_Valve2 ()
    PumpWithdrawSample2_Volume2(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample2(20,6000)
    time.sleep(1)
    PumpWithdrawSample2_Volume2(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample2(20,6000)
    time.sleep(1)
    print("Syringe2 and Line Cleaning completed!")
    

def switch_sample3_aut():
    print("Syringe3 getting emptied")
    PumpEmpty_PumpSample3(10)
    time.sleep(1)
    Solvent_Valve3 ()
    print("Syringe3 cleaning using solvent")
    PumpCleaning_pumpSample3_aut()
    Air_Valve3 ()
    time.sleep(1)
    print("Syringe3 cleaning using Air")
    PumpCleaning_pumpSample3_aut()
    time.sleep(1)
    PumpCleaning_pumpSample3_aut()
    time.sleep(1)
    print("Starting injection mode...")
    print('Line3 Cleaning Started!')
    Solvent_Valve3 ()
    time.sleep(1)
    PumpWithdrawSample3_Volume3(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample3(20,6000)
    time.sleep(1)
    Air_Valve3 ()
    PumpWithdrawSample3_Volume3(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample3(20,6000)
    time.sleep(1)
    PumpWithdrawSample3_Volume3(300,6000)
    time.sleep(1)
    PumpInjection_pumpSample3(20,6000)
    time.sleep(1)
    print("Syringe3 and Line3 Cleaning completed!")

def switch_solvent():
    injectSolvent(20)
    input("OK, now put it in air and press Enter to continue...")
    print("Syringe cleaning using Air")
    RefillSolvent()
    injectSolvent(20)
    RefillSolvent()
    injectSolvent(20)
    RefillSolvent()
    injectSolvent(20)
    input("OK, now put it in new solvent and press Enter to continue...")
    print("Filling with solvents")
    RefillSolvent()
    injectSolvent(20)
    RefillSolvent()

def clean_pump1_line1(changed):
    switch_sample1_aut()
    time.sleep(1)
    '''
    if changed:
        print("Pump 1 chemical changed — starting cleaning.")
        switch_sample1_aut()
    else:
        print("Pump 1 chemical unchanged — no cleaning needed.")
    '''

def clean_pump2_line2(changed):
    switch_sample2_aut()
    time.sleep(1)
    '''
    if changed:
        print("Pump 2 chemical changed — starting cleaning.")
        switch_sample2_aut()
    else:
        print("Pump 2 chemical unchanged — no cleaning needed.")
        '''

def clean_pump3_line3(changed):
    switch_sample3_aut()
    time.sleep(1)
    '''
    if changed:
        print("Pump 3 chemical changed — starting cleaning.")
        switch_sample3_aut()
    else:
        print("Pump 3 chemical unchanged — no cleaning needed.")
        '''
    
#PumpInitialize_pumpSample3()
#switch_sample1_aut()
#switch_sample2_aut()
#switch_sample3_aut()
#PumpEmpty_PumpSample3(10)