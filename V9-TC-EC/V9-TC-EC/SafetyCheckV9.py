
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
from matplotlib.ticker import MaxNLocator
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

    RefillSample, pump_flow_rate,

    Position_SamplePump1, Position_SamplePump2, Position_SamplePump3, Position_HC_Pump1
)
from CleaningV9 import (cleaning_part1, Cleaning_part2, Cleaning_part2_switch, Cleaning_Pump1_HC, cleanCp, airpurge)
from SampleSwitchV9 import (switch_sample1, switch_sample2, switch_sample3, switch_solvent)
from EmailV9 import send_email
from ChemicalAssignmentV9 import (generate_valve_maps, pump1_assign_chemical, pump2_assign_chemical, pump3_assign_chemical, assign_chemicals, get_chemicals_from_top_row, 
                                get_chemicals_and_compositions)
from SampleSwitchV9 import (switch_sample1, switch_sample2, switch_sample3, switch_sample1_aut, switch_sample2_aut, switch_sample3_aut, switch_solvent, clean_pump1_line1, clean_pump2_line2, clean_pump3_line3)

def SafetyCheck ():
    #for sample pump 1
    Position_Pump1 = Position_SamplePump1 ()
    print(Position_Pump1)
    if Position_Pump1!=6000:
        print('Pump 1 is not working!')
        send_email("Alert!", f"❗ Pump 1 is not working.", "m93.ebrahimiazar@gmail.com")
        Solvent_Valve1 ()
        PumpInitialize_pumpSample1 ()
        PumpEmpty_PumpSample1(10)
        clean_pump1_line1(True)
        cleaning_part1()
        Cleaning_part2 ()
    else:
        print('Safety check passed for pump 1.')
    #for sample pump 2
    Position_Pump2 = Position_SamplePump2 ()
    print(Position_Pump2)
    if Position_Pump2!=6000:
        print('Pump 2 is not working!')
        send_email("Alert!", f"❗ Pump 2 is not working.", "m93.ebrahimiazar@gmail.com")
        Solvent_Valve2 ()
        PumpInitialize_pumpSample2 ()
        PumpEmpty_PumpSample2(10)
        clean_pump2_line2(True)
        cleaning_part1()
        Cleaning_part2 ()
    else:
        print('Safety check passed for pump 2.')
       
    #for sample pump 3
    Position_Pump3 = Position_SamplePump3 ()
    print(Position_Pump3)
    if Position_Pump3!=6000:
        print('Pump 3 is not working!')
        send_email("Alert!", f"❗ Pump 3 is not working.", "m93.ebrahimiazar@gmail.com")
        Solvent_Valve3 ()
        PumpInitialize_pumpSample3 ()
        PumpEmpty_PumpSample3(10)
        clean_pump3_line3(True)
        cleaning_part1()
        Cleaning_part2 ()
    else:
        print('Safety check passed for pump 3.')

    #for HC Pump
    Position_HC = Position_HC_Pump1 ()
    print(Position_HC)
    if Position_HC!=0:
        print('HC pump is not working!')
        send_email("Alert!", f"❗ Pump HC is not working.", "m93.ebrahimiazar@gmail.com")
        PumpInitialize_pump1 ()
        EmptyHcSyringe(200)
        cleaning_part1()
        Cleaning_part2 ()
        Cleaning_part2 ()
    else:
        print('Safety check passed for pump HC.')