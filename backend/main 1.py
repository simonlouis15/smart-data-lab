import lab_devices as labDevices
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

print("hello")

if __name__ == "__main__":
    # NOTE: more device discovery tests can be run in device_discover.py. 
    # Look into this file for more details and things to test out. 
    # NOTE: Rememver to look through the device intialization code in lab_devices.py
    # and spot out any comments or notes that might help guide what else to test/look into.
    # DEVICE DISCOVERY
    print("=== DEVICE DISCOVERY ===")

  # List all serial ports
    print("\nSerial Ports:")
    for port in serial.tools.list_ports.comports():
        print(f"  {port.device}: {port.description}")

    # List DAQ devices
    print("\nDAQ Devices:")
    try:
        system = nidaqmx.system.System.local()
        for device in system.devices:
            print(f"  {device.name}: {device.product_type}")
            print(f"    AI Channels: {list(device.ai_physical_chans)}")
    except:
        print("  No DAQ devices found or NI-DAQmx not installed")
    # ===========

    # Initialize lab devices
    selectorValve = labDevices.SelectorValve('COM9', 9600, 'Main Selector Valve')

    pumpSample1 = labDevices.Pump('COM10', 9600, 1, 'Pump 1')
    pumpSample2 = labDevices.Pump('COM7', 9600, 2, 'Pump 2')
    pumpHCSample = labDevices.Pump('COM14', 9600, 3, 'HC Sample Pump')
    pumpHcReference = labDevices.Pump('COM5', 9600, 4, 'HC Reference Pump')
    pumpSolvent = labDevices.Pump('COM6', 9600, 5, 'Solvent Pump')

    daqSensor = labDevices.DAQDevice('COM8', 9600, 'DAQ Device')

    # ==== Test Selector Valve ====
      # Test selector valve connection
    # 1. Test acknowledgment and Multiposition Mode
    selectorValve.setup()
    selectorValve.move_to(3)    # injection mode
    # NOTE: sending another command right after to see if a valve setup is neeeded
    # on each command
    selectorValve.confirm_position()   
    selectorValve.move_to(9)    # air mode
    selectorValve.confirm_position()
    selectorValve.move_to(1)    # solvent mode
    selectorValve.confirm_position()
    selectorValve.ser.close()  # Close the serial connection

    # ==== Test sample pumps ====
    # PUMP 1
      # 1. Test pump ready status
    pumpSample1.wait_until_ready()

      # 2. Test position query
    pumpSample1.send_command('/1?')  # Query current position
    pumpSample1.send_command('/1CP')  # Confirm position
    pumpSample1.send_command('/1T')  # Stop pump (ensure that its working)
    pumpSample1.ser.close()  # Close the serial connection

    # PUMP 2
          # 1. Test pump ready status
    pumpSample2.wait_until_ready()

      # 2. Test position query
    pumpSample2.send_command('/1?')  # Query current position
    pumpSample2.send_command('/1CP')  # Confirm position
    pumpSample2.send_command('/1T')  # Stop pump (ensure that its working)
    pumpSample2.ser.close()  # Close the serial connection

     # HC SAMPLE PUMP
          # 1. Test pump ready status
    pumpHCSample.wait_until_ready()

      # 2. Test position query
    pumpHCSample.send_command('/1?')  # Query current position
    pumpHCSample.send_command('/1CP')  # Confirm position
    pumpHCSample.send_command('/1T')  # Stop pump (ensure that its working)
    pumpHCSample.ser.close()  # Close the serial connection

    # HC REFERENCE PUMP
          # 1. Test pump ready status
    pumpHcReference.wait_until_ready()

      # 2. Test position query
    pumpHcReference.send_command('/1?')  # Query current position
    pumpHcReference.send_command('/1CP')  # Confirm position
    pumpHcReference.send_command('/1T')  # Stop pump (ensure that its working)
    pumpHcReference.ser.close()  # Close the serial connection

    # SOLVENT PUMP
          # 1. Test pump ready status
    pumpSolvent.wait_until_ready()

      # 2. Test position query
    pumpSolvent.send_command('/1?')  # Query current position
    pumpSolvent.send_command('/1CP')  # Confirm position
    pumpSolvent.send_command('/1T')  # Stop pump (ensure that its working)
    pumpSolvent.ser.close()  # Close the serial connection

    # ==== Test DAQ Device ====
    try:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan("NI9210/ai0", min_val=-0.08, max_val=0.08)

            # Read single voltage value
            voltage = task.read()
            print(f"DAQ voltage reading: {voltage:.6f} V")

            # Read multiple samples
            task.timing.cfg_samp_clk_timing(rate=10)
            voltages = task.read(number_of_samples_per_channel=10)
            print(f"DAQ 10 samples: min={min(voltages):.6f}V, max={max(voltages):.6f}V")

        print("✓ DAQ test successful")
    
    except Exception as e:
      print(f"✗ DAQ test failed: {e}")

    # 