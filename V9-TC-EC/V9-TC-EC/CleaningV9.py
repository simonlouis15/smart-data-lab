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
from SelectorValvesV9 import Valve_Setup, injectionmode, airmode, solventmode, Valve1_Setup, Valve2_Setup, Valve3_Setup, open_valve1, open_valve2, open_valve3
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
    PumpCleaning_pumpSolvent, RefillSolvent,

    START_pump1, PumpInitialize_pump1, PumpReady_pump1, PumpInjection_pump1,
    PumpRefill_pump1, PumpWithdraw,

    START_pump2, PumpInitialize_pump2, PumpReady_pump2, PumpInjection_pump2,
    PumpRefill_pump2, Debubble, EmptyHcSyringe, cleanup,

    START_pump1_HC, PumpInjection_pump1_HC, Stop_pump1_HC,
    START_pump2_HC, PumpInjection_pump2_HC, Stop_pump2_HC, SolventPumpCleanedbyAir
)


def cleaning_part1():
    print('Cleaning started')
    PumpWithdrawSolvent()
    #Debubble_pumpSolvent(25)
    for _ in range(3):
        airmode()
        print('Air started')
        time.sleep(10)
        # Initialize serial connection for pump 1
        #print("Solvent started")
        PumpInjection_pumpSolvent(20)
    print('Air purge started.')
    airmode()
    time.sleep(140)
    injectionmode()

def cleaning_part1long():
    print('Cleaning started')
    RefillSolvent()
    #Debubble_pumpSolvent(25)
    for _ in range(3):
        airmode()
        print('Air started')
        time.sleep(15)
        # Initialize serial connection for pump 1
        #print("Solvent started")
        solventmode()
        PumpInjection_pumpSolvent(20)
    print('clear line')
    solventmode()
    SolventPumpCleanedbyAir ()
    SolventPumpCleanedbyAir ()
    print('Air purge started.')
    airmode()
    time.sleep(90)
    injectionmode()
    PumpEmpty_PumpSolvent(20)

def Cleaning_part2():
    print('HC Cleaning Started')
    EmptyHcSyringe(200)
    for _ in range(1):  # Repeat the cleaning steps twice
        PumpRefill_pump1(400)
        time.sleep(1)
        Cleaning_Pump1_HC(100)
        time.sleep(0.5)
    for _ in range(1):
        PumpRefill_pump1(400)
        time.sleep(1)
        #EmptyHcSyringe(200)
        Cleaning_Pump1_HC(150)
        time.sleep(1)
    for _ in range(1):
        PumpRefill_pump1(400)
        time.sleep(1)
        #EmptyHcSyringe(200)
        Cleaning_Pump1_HC(150)
        time.sleep(1)

def Cleaning_part2_switch():
    print('HC Cleaning Started')
    EmptyHcSyringe(200)
    for _ in range(5):  # Repeat the cleaning steps twice
        PumpRefill_pump1(400)
        time.sleep(1)
        EmptyHcSyringe(200)
        time.sleep(1)
    

def Cleaning_Pump1_HC(val):
    print('start cleaning HC sensor')
    Inject1 = f'EV{val}A0'
    time.sleep(1)
    START_pump1('1',Inject1)


def cleanCp ():
    print('HC Cleaning Started')
    PumpRefill_pump1(400)
    time.sleep(5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(20)
    time.sleep(30)
    PumpRefill_pump1(400)
    time.sleep(5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(20)
    #airmode()
    time.sleep(30)
    PumpRefill_pump1(400)
    time.sleep(0.5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(20)
    time.sleep(0.5)
    PumpRefill_pump1(400)
    time.sleep(0.5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(20)
    time.sleep(0.5)
    injectionmode()
    print('HC Cleaning Completed')

def airpurge ():
    print('Air loop Started')
    PumpRefill_pump1(400)
    time.sleep(5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(200)
    #time.sleep(30)
    PumpRefill_pump1(400)
    time.sleep(5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(200)
    airmode()
    #time.sleep(30)
    PumpRefill_pump1(400)
    time.sleep(0.5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(200)
    time.sleep(0.5)
    PumpRefill_pump1(400)
    time.sleep(0.5)
    #EmptyHcSyringe(200)
    Cleaning_Pump1_HC(200)
    time.sleep(0.5)
    injectionmode()
    print('HC Cleaning Completed')



# RefillSolvent()
# #Debubble_pumpSolvent(25)
# for _ in range(5):
#     PumpInjection_pumpSolvent(20)
#     print('Air started')
#     airmode()
#     time.sleep(12)
#     input('s')


