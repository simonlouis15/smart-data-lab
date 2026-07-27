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
#Selector Valve
servalve = serial.Serial(
    port='COM9',  # Change to your actual COM port
    baudrate=9600,
    bytesize=8,
    parity='N',   # No parity
    stopbits=1,
    timeout=1,    # Set timeout to 1 second
    xonxoff=False,  # Disable software handshaking
    rtscts=False    # Disable hardware handshaking
)

def Valve_Setup():
    # Check connection and configure the valve properly
    servalve.write(b'AK\r')  # Send "AK" command with carriage return
    response = servalve.readline().decode().strip()  # Read response
    #print(f"Checking for connection, the Response: {response}")

    # Set Actuator to Multiposition Mode
    servalve.write(b'AM3\r')
    #print("Setting actuator to multiposition mode")

    # Step 2: Set the number of positions to 3
    servalve.write(b'NP10\r')
    #print("Configuring actuator for 10 positions")

    # Define the functions for use

def injectionmode():
    Valve_Setup()
    servalve.write(b'GO03\r')
    time.sleep(0.1)
    servalve.write(b'CP\r')
    time.sleep(0.1)
    response = servalve.readline().decode().strip()
    #print(f'Current position is {response}')

def airmode():
    Valve_Setup()
    servalve.write(b'GO09\r')
    time.sleep(0.1)
    servalve.write(b'CP\r')
    time.sleep(0.1)
    response = servalve.readline().decode().strip()
    #print(f'Current position is {response}')

def solventmode():
    Valve_Setup()
    servalve.write(b'GO01\r')
    time.sleep(0.1)
    servalve.write(b'CP\r')
    time.sleep(0.1)
    response = servalve.readline().decode().strip()
    #print(f'Current position is {response}')

#Selector Valves for pumps
servalve1 = serial.Serial(
    port='COM3',  # Change to your actual COM port
    baudrate=9600,
    bytesize=8,
    parity='N',   # No parity
    stopbits=1,
    timeout=1,    # Set timeout to 1 second
    xonxoff=False,  # Disable software handshaking
    rtscts=False    # Disable hardware handshaking
)


#Selector Valves for pumps
servalve2 = serial.Serial(
    port='COM4',  # Change to your actual COM port
    baudrate=9600,
    bytesize=8,
    parity='N',   # No parity
    stopbits=1,
    timeout=1,    # Set timeout to 1 second
    xonxoff=False,  # Disable software handshaking
    rtscts=False    # Disable hardware handshaking
)


#Selector Valves for pumps
servalve3 = serial.Serial(
    port='COM11',  # Change to your actual COM port
    baudrate=9600,
    bytesize=8,
    parity='N',   # No parity
    stopbits=1,
    timeout=1,    # Set timeout to 1 second
    xonxoff=False,  # Disable software handshaking
    rtscts=False    # Disable hardware handshaking
)
def Valve1_Setup():
    # Check connection and configure the valve properly
    servalve1.write(b'AK\r')  # Send "AK" command with carriage return
    response = servalve1.readline().decode().strip()  # Read response
    #print(f"Checking for connection, the Response: {response}")

    # Set Actuator to Multiposition Mode
    servalve1.write(b'AM3\r')
    #print("Setting actuator to multiposition mode")

    # Step 2: Set the number of positions to 3
    servalve1.write(b'NP28\r')
    #print("Configuring actuator for 10 positions")

    # Define the functions for use
def Valve2_Setup():
    # Check connection and configure the valve properly
    servalve2.write(b'AK\r')  # Send "AK" command with carriage return
    response = servalve2.readline().decode().strip()  # Read response
    #print(f"Checking for connection, the Response: {response}")

    # Set Actuator to Multiposition Mode
    servalve2.write(b'AM3\r')
    #print("Setting actuator to multiposition mode")

    # Step 2: Set the number of positions to 3
    servalve2.write(b'NP28\r')
    #print("Configuring actuator for 10 positions")

    # Define the functions for use
def Valve3_Setup():
    # Check connection and configure the valve properly
    servalve3.write(b'AK\r')  # Send "AK" command with carriage return
    response = servalve3.readline().decode().strip()  # Read response
    #print(f"Checking for connection, the Response: {response}")

    # Set Actuator to Multiposition Mode
    servalve3.write(b'AM3\r')
    #print("Setting actuator to multiposition mode")

    # Step 2: Set the number of positions to 3
    servalve3.write(b'NP28\r')
    #print("Configuring actuator for 10 positions")

    # Define the functions for use

def open_valve1(chemical, valve_map):
    chemical = chemical.upper()
    if chemical not in valve_map:
        print(f"Valve1: Chemical '{chemical}' not in mapping")
        return
    port = valve_map[chemical]
    cmd = f'GO{port:02d}\r'
    Valve1_Setup()
    time.sleep(1)
    servalve1.write(cmd.encode())
    time.sleep(1)
    print(f"[Valve 1] Command to send: {cmd}")
    #PumpWithdrawSample1()

def open_valve2(chemical, valve_map):
    chemical = chemical.upper()
    if chemical not in valve_map:
        print(f"Valve2: Chemical '{chemical}' not in mapping")
        return
    port = valve_map[chemical]
    cmd = f'GO{port:02d}\r'
    Valve2_Setup()
    time.sleep(1)
    servalve2.write(cmd.encode())
    time.sleep(1)
    print(f"[Valve 2] Command to send: {cmd}")
    #PumpWithdrawSample2()

def open_valve3(chemical, valve_map):
    chemical = chemical.upper()
    if chemical not in valve_map:
        print(f"Valve3: Chemical '{chemical}' not in mapping")
        return
    port = valve_map[chemical]
    cmd = f'GO{port:02d}\r'
    Valve3_Setup()
    time.sleep(1)
    servalve3.write(cmd.encode())
    time.sleep(1)
    print(f"[Valve 3] Command to send: {cmd}")
    #PumpWithdrawSample3()

def Solvent_Valve1 ():
    servalve1.write(b'GO27\r')

def Air_Valve1 ():
    servalve1.write(b'GO28\r')

def Solvent_Valve2 ():
    servalve2.write(b'GO27\r')

def Air_Valve2 ():
    servalve2.write(b'GO28\r')

def Solvent_Valve3 ():
    servalve3.write(b'GO27\r')

def Air_Valve3 ():
    servalve3.write(b'GO28\r')