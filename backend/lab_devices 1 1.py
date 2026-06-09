import numpy as np
import serial
import serial.tools.list_ports
import time
import argparse
import threading
import nidaqmx
import re
import signal
import sys
from sklearn.linear_model import LinearRegression
import xtalx.z_sensor
from xtalx.tools.z_sensor import z_common
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from datetime import datetime

import cv2
from flask import Flask, Response

import threading
import argparse

# UI module
import tkinter

# robust logging packages
import logging

# SHOULD BE DEINFED IN mAIN: 
logging.basicConfig(level=logging.INFO) # Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)


'''
Let's start by creating classes to create syrial objects

Serial Device will be the main class that's defined to be used as a superclass. 
That is, all other device definitions will be defined off of this one class, and we can override the innit
properties if need be.

PARAMS:
port = communication port of the device that it is defined to
baudrate = speed of data transmissions in the system
    - set to 9600 by default

ATTRIBUTES:
.....

'''


class SerialDevice:
    def __init__(self, port, baudrate=9600, name=''):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        self.label = name

    def write(self, command):
        self.ser.write(bytes(command, 'utf-8'))
        time.sleep(0.1)
        # NOTE: TEMP CODE:
        print(f"Command sent: {command}")
        # ===============

    def read(self):
        return self.ser.readline().decode("utf-8").strip()


'''
Selector Valve Code and Functions
Also includes setup for access to cleaning functions like air and solvent cleaning

Now lets define a child class for SerialDevice, which is specifically for the selector valve.

'''
# needs: port, baudrate, name, list of connections 
# in this case, experiment uses I think 3-4 connections which houses the 3 pumps, air, and an output valve

class SelectorValve(SerialDevice):
    """
    Controls a Hamilton selector valve via serial communication.

    Attributes:
        port (str): Serial port the valve is connected to.
        baudrate (int): Baud rate for communication (default 9600).
        valve_positions (int): Total number of positions (default 10).
        current_position (int): Last known valve position.
    """

    def __init__(self, port: str, baudrate: int = 9600, valve_positions: list = None):
        super().__init__(port, baudrate)
        self.valve_positions = valve_positions
        self.current_position = None
        self.setup_complete = False     # is this an important value?

    def setup(self):
        """
        Initializes the selector valve and ensures its ready to receive commands:
        - Acknowledges connection.
        - Sets manual mode (AM3).
        - Sets the number of positions (e.g., NP10).
        """
        # NOTE: Check if Valve needs to be setup every single time before use
        # Acknowledge command
        self.write("AK\r")     
        response = self.read()
        logging.debug(f"Valve Setup Acknolwedge Command Response: {response}")
        # NOTE: TEMP CODE: 
        print(f"Valve Setup Acknolwedge Command Response: {response}")
        # ===============

        # Set to Multiposition mode and configure valve positions
        self.write("AM3\r")   
        response = self.read()
        logging.debug(f"Valve Setup Multiposition Command Response: {response}")
        # NOTE: TEMP CODE:
        print(f"Valve Setup Multiposition Command Response: {response}")
        # ===============
        self.write(f"NP{len(self.valve_positions)}\r") 
        self.setup_complete = True

    def move_to(self, position: int):
        """
        Moves the valve to the specified position. Position must be accessible to the valve.

        Args:
            position (int): Position to move to (1-based index).
        """
        # if valve setup not complete or there are no valve positions configured
        # if not (self.setup_complete):
        #     # TODO: Set up proper error logging and try-except chains to catch issues early on.
        #     logging.error("Selector valve must be set up before use.")
        #     raise RuntimeError("Selector valve must be set up before use.")
        # if  not ( (position in self.valve_positions) or (self.valve_positions) ):
        #     logging.error(f"Position {position} is out of range for valve with {self.valve_positions} positions.")
        #     raise ValueError(f"Position {position} is out of range for valve with {self.valve_positions} positions.")
        
        # NOTE: check if sleeps are needed between each read/write/command for the valve
        # Format must be zero-padded if < 10
        position_str = f"{position:02d}"
        self.write(f"GO{position_str}\r")
        self.current_position = position
        time.sleep(0.1)
        logging.info(f" Selector Valve Position Change: {self.confirm_position()}")
        # NOTE: TEMP CODE:
        print(f" Selector Valve Position Change: {self.confirm_position()}")
        # ===============

    def confirm_position(self) :
        """
        Issues a 'CP' (confirm position) command and reads the response.
        """
        self.write("CP\r")
        time.sleep(0.1)
        response = self.read()
        return response

    def get_status(self):
        """
        Sends a status query and returns the valve status string.
        """
        self.write("RS\r")
        return self.read()

    def reset(self):
        """
        Resets the valve controller (if supported).
        """
        self.write("AR\r")
        return self.read()
    
    def set_mode(self, position):
        self.setup()
        self.move_to(self, position)
    
'''
Pump Device setup (subclass of serial device)
'''
# pumps need: port, pump num, name/label/description (pump 1, pump 2)
# optional:  baudrate (optional), flow rate (optional) 
# NOTE: the things the pump does and the fluids the pumps controle are adjustable in 
# the routines or smthn; shouldn't be in pumps definition 
# pump data for mass initialization and overall device definition can be passed in as a csv or defined manually in the app.
# scan
# NOTE: pumps should start with 3 defined pumps following the definitions in the code
# NOTE: need to fix the bg of the container of the pumps to be lighter gray, add typing to the input fields + ensure that ppl can't define an empty pump object
# General styling should be added in figma cuz gpt is stupid.

class Pump(SerialDevice):
    def __init__(self, port, pump_num:int, name:str, flow_rate= 0, baudrate:int= 9600):
        # use super class' device initialization
        super().__init__(port, baudrate, name)
        self.pump_num = pump_num
        self.flow_rate = flow_rate

    def send_command(self, command):
        """
        Based off of START_pumpSample functions
        """
        # NOTE: What if I stop all commands before sending another here instead?
        # I.e., send command "T" to stop all actions before sending a new command
        if not (self.pump_num):
            return

        full_cmd = f"/{self.pump_num}{command}R\r\n"
        self.write(full_cmd)
        # NOTE: TEMP CODE:
        print(f"Pump {self.pump_num} command sent: {full_cmd}")
        # ===============
        time.sleep(0.5)
        self.wait_until_ready() # pings pump until no actions remain
        time.sleep(0.51)
        try: 
            #TODO: (logging related) print ("Attempt to Read")
            time.sleep(0.5)
            readOut = self.read()
            time.sleep(0.5)
            #TODO: (logging related) print ("Reading: ", readOut) 
            self.write(full_cmd)
        except:
            logging.error("Error reading from pump")
        
        # Untouched (old) code below:
        # while True:
        #     try:
        #         #TODO: (logging related) print ("Attempt to Read")
        #         time.sleep(0.5)
        #         readOut = serSample1.readline().decode("utf-8")
        #         time.sleep(0.5)
        #         #TODO: (logging related) print ("Reading: ", readOut) 
        #         serSample1.write(full_cmd)
        #         break
        #     except:
        #         if readOut == "0@":
        #             break
        #             ser.flush() #flush the buffer
        #         elif readOut !="0@":
        #             pass
        #             #print("Restart")
        #     break

    def initialize(self,
                   syringe_size: int = 30,
                   zero_units: int = 100,
                   zero_accel: int = 0,
                   fill_units: int = 100,
                   fill_speed: int = 6000):
        
        # Syringe size + zero plunger
        self.send_command(f"Y{syringe_size}z")

        # Set zero position by aspirating specified units at 0 accel
        self.send_command(f"OV{zero_units}A{zero_accel}")

        # Fill syringe to desired amount with speed
        self.send_command(f"OV{fill_units}P{fill_speed}")

    def wait_until_ready(self):
        # NOTE: not sure why its stuck sending 90 million commands when it should already be ready
        """
        Blocks until the pump is ready to receive the next command.

        It sends the 'F' (status) command and checks the response. Loop continues until
        the pump returns a status that is NOT '@' (busy) or 'o' (moving).
        """
        response = ""
        while(not ("@" in response or "0" in response)):
            command = f"/{self.pump_num}F\r\n"
            self.write(command)
            # time.sleep(0.1)
            response = self.read()
            # NOTE: TEMP CODE:
            print(f"Pump {self.pump_num} ready status: {response}")
        # ===============

    def inject(self, volume, duration=0, accel=None):
        if accel is not None:
            cmd = f"EV{int(volume * 20)}A{accel}"
        else:
            cmd = f"EV{int(volume * 20)}d{duration}"
        
        self.send_command("T")
        self.send_command(cmd)

    # TODO: look into if we need these fast or slow injections or if we can just define these
    # functions inside of the routines when we get there.
    def full_injection(self, volume_ml: float, accel: int):
        """
        Controlled injection with specified acceleration.
        """
        self.send_command("T")
        volume_units = int(volume_ml * 20)
        self.send_command(f"EV{volume_units}A{accel}")

    def fast_empty(self, volume_ml: float):
        """
        Fast emptying using IV command at A0.
        """
        self.send_command("T")
        volume_units = int(volume_ml * 20)
        self.send_command(f"IV{volume_units}A0")

    def withdraw(self, volume):
        self.send_command("T")
        self.send_command(f"OV{volume}A6000")

    def debubble(self, volume, duration):
        self.send_command("T")
        self.send_command(f"IV{int(volume * 20)}d{duration}")

    def set_flow_rate(given_flow_rate):
        # line 1037 for pump_flow_rate
        """Assumes that valve has been set to pos 3 (is that rlly safe idk)
        Based off of the function pump_flow_rate
        """
        pass
    def clean_pump(self, flush_volume=10, withdraw_volume=300):
        """
        Based off of PumpCleaning_pumpSample1
        """
        # NOTE: Why are we even withdrawing to begin with? whats this for and what are we withdrawing
        self.fast_empty(flush_volume)
        self.withdraw(withdraw_volume)
        self.fast_empty(flush_volume)


# TODO: Add some functions for changing the pumps flow rate for the samples held.  (I think?? Function is called pump_flow_rate.)
# TODO: REVIEW ALL OF THE EXISTING FUNCTIONS AND CLASSES I DEFINED AND MAKE SURE THEY ARE NOT ONLY TRUE TO THE CODE BUT ALSO CORRECT AND NECESSAIRY!!
# TODO: Consider cleaning routines and whether or not every object needs to have a cleaning routine
# TODO: Store flow rate as a value specific to each pump that can be changed w/ methods?
"""
DAQ  Device Setup
"""
class DAQDevice:
    """
    DAQ (Data Acquisition) device class for heat capacity computation.
    This class handles NI DAQ initialization, data acquisition, and 
    heat capacity calculations.
    """

    def __init__(self, port_name="NI9210/ai0", daq_frequency=3):
        """
        Initialize the DAQ device.
        
        Args:
            port_name (str): The DAQ channel name/port (default: "NI9210/ai0")
            daq_frequency (int): Sampling frequency in Hz (default: 3 Hz)
        """
        self.port_name = port_name
        self.daq_frequency = daq_frequency
        self.task = None
        self.initialize_task()

    def initialize_task(self):
        """Initialize the NI DAQ task with voltage channel configuration."""
        try:
            self.task = nidaqmx.Task()
            self.task.ai_channels.add_ai_voltage_chan(
                self.port_name,
                min_val=-0.08,
                max_val=0.08
            )
            self.task.timing.cfg_samp_clk_timing(
                rate=self.daq_frequency,
                sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS
            )
            print(f"DAQ initialized on {self.port_name} at {self.daq_frequency} Hz")
        except Exception as e:
            print(f"Failed to initialize DAQ: {e}")
            raise

    def read_voltage(self):
        """
        Read a single voltage value from the DAQ.
        
        Returns:
            float: Voltage reading from the DAQ
        """
        if self.task is None:
            raise RuntimeError("DAQ task not initialized")
        return self.task.read()

    def read_voltage_batch(self, num_samples):
        """
        Read multiple voltage samples from the DAQ.
        
        Args:
            num_samples (int): Number of samples to read
            
        Returns:
            list: List of voltage readings
        """
        samples = []
        for _ in range(num_samples):
            samples.append(self.read_voltage())
            time.sleep(1.0 / self.daq_frequency)
        return samples

    def close(self):
        """Close the DAQ task and release resources."""
        if self.task is not None:
            self.task.close()
            self.task = None
            print("DAQ task closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure task is closed."""
        self.close()

    @staticmethod
    def check_stabilization(segment_means, abs_threshold, num_consecutive_seg=5):
        """
        Check if the system has stabilized based on segment mean variations.
        
        Args:
            segment_means (list): List of segment mean values
            abs_threshold (float): Absolute threshold for variation
            num_consecutive_seg (int): Number of consecutive segments to check
            
        Returns:
            bool: True if stabilized, False otherwise
        """
        if len(segment_means) < num_consecutive_seg:
            return False

        recent_means = segment_means[-num_consecutive_seg:]
        overall_mean = np.mean(recent_means)
        count_within_threshold = 0

        for seg_mean in recent_means:
            abs_diff = abs(seg_mean - overall_mean)
            if abs_diff <= abs_threshold:
                count_within_threshold += 1

        return count_within_threshold >= 4

    def collect_stabilized_data(self, duration_seconds, stabilization_threshold=0.4e-6, 
                               segment_duration=10, max_segments=15):
        """
        Collect data until stabilization is achieved or max segments reached.
        
        Args:
            duration_seconds (int): Duration for data collection
            stabilization_threshold (float): Threshold for stabilization check
            segment_duration (int): Duration of each segment in seconds
            max_segments (int): Maximum number of segments to try
            
        Returns:
            tuple: (stabilized_mean, all_data, is_stabilized)
        """
        all_data = []
        segment_means = []
        segment_counter = 0
        is_stabilized = False
        stabilized_mean = None

        samples_per_segment = segment_duration * self.daq_frequency

        while segment_counter < max_segments and not is_stabilized:
            segment_data = []

            # Collect data for one segment
            for _ in range(samples_per_segment):
                voltage = self.read_voltage()
                segment_data.append(voltage)
                all_data.append(voltage)
                time.sleep(1.0 / self.daq_frequency)

            # Calculate segment statistics
            seg_mean = np.mean(segment_data)
            segment_means.append(seg_mean)
            segment_counter += 1

            # Check for stabilization after minimum segments
            if segment_counter >= 5:
                if self.check_stabilization(segment_means, stabilization_threshold):
                    is_stabilized = True
                    stabilized_mean = np.mean(segment_means[-5:])
                    print(f"Stabilization achieved after {segment_counter} segments")

        if not is_stabilized:
            print(f"Failed to stabilize after {segment_counter} segments")

        return stabilized_mean, all_data, is_stabilized

    def calculate_heat_capacity(self, signal_data, sample_flow_rates, ref_flow_rate,
                               density_sample, density_ref=988.8, hc_ref=4176.5):
        """
        Calculate heat capacity using linear regression on signal vs flow rate data.
        
        Args:
            signal_data (array): Signal values (voltage differences from baseline)
            sample_flow_rates (array): Sample pump flow rates
            ref_flow_rate (float): Reference pump flow rate
            density_sample (float): Sample density in kg/m³
            density_ref (float): Reference density in kg/m³ (default: water)
            hc_ref (float): Reference heat capacity in J/(kg·K) (default: water)
            
        Returns:
            dict: Dictionary containing heat capacity and regression parameters
        """
        if len(signal_data) < 2:
            print("Not enough data points for regression")
            return None

        # Reshape for sklearn
        signal_data = np.array(signal_data).reshape(-1, 1)
        sample_flow_rates = np.array(sample_flow_rates).reshape(-1, 1)

        # Perform linear regression
        model = LinearRegression()
        model.fit(signal_data, sample_flow_rates)

        slope = model.coef_[0][0]
        intercept = model.intercept_[0]

        # Calculate heat capacity
        if intercept != 0:
            heat_capacity = (ref_flow_rate * hc_ref * density_ref) / (density_sample * intercept)
        else:
            print("Warning: Intercept is zero, cannot calculate heat capacity")
            heat_capacity = None

        return {
            'heat_capacity': heat_capacity,
            'slope': slope,
            'intercept': intercept,
            'r_squared': model.score(signal_data, sample_flow_rates)
        }

    def run_heat_capacity_experiment(self, exp_protocol, density_sample, 
                                     visualization=True, save_path=None):
        """
        Run a complete heat capacity measurement experiment.
        
        Args:
            exp_protocol (list): List of [sample_rate, ref_rate, duration] for each step
            density_sample (float): Sample density in kg/m³
            visualization (bool): Whether to show live visualization
            save_path (str): Path to save data (optional)
            
        Returns:
            dict: Experiment results including heat capacity
        """
        print("Starting heat capacity experiment...")

        all_data = []
        step_averages = []

        if visualization:
            plt.ion()
            fig, ax = plt.subplots()
            x_data, y_data = [], []
            line, = ax.plot([], [])
            plt.xlabel('Time [s]')
            plt.ylabel('Voltage [V]')
            plt.title('Heat Capacity Measurement - Live Data')
            ax.set_xlim([0, 500])
            ax.set_ylim([-1e-5, 1e-5])

        time_counter = 0

        for step_idx, (sample_rate, ref_rate, duration) in enumerate(exp_protocol):
            print(f"Step {step_idx + 1}: Sample={sample_rate} mL/min, Ref={ref_rate} mL/min")

            # Collect stabilized data for this step
            stabilized_mean, step_data, is_stabilized = self.collect_stabilized_data(
                duration,
                stabilization_threshold=0.4e-6,
                segment_duration=10,
                max_segments=15
            )

            if is_stabilized and stabilized_mean is not None:
                step_averages.append({
                    'step': step_idx,
                    'sample_rate': sample_rate,
                    'ref_rate': ref_rate,
                    'average_voltage': stabilized_mean,
                    'stabilized': True
                })
            else:
                # Use overall mean if not stabilized
                step_averages.append({
                    'step': step_idx,
                    'sample_rate': sample_rate,
                    'ref_rate': ref_rate,
                    'average_voltage': np.mean(step_data) if step_data else None,
                    'stabilized': False
                })

            # Update visualization if enabled
            if visualization:
                for voltage in step_data:
                    x_data.append(time_counter / self.daq_frequency)
                    y_data.append(voltage)
                    time_counter += 1

                    if time_counter % (self.daq_frequency * 5) == 0:  # Update every 5 seconds
                        line.set_data(x_data, y_data)
                        ax.relim()
                        ax.autoscale_view()
                        plt.pause(0.01)

            all_data.extend(step_data)

        if visualization:
            plt.ioff()
            plt.close()

        # Calculate heat capacity from stabilized data
        baseline_steps = [s for s in step_averages if s['sample_rate'] == 0 and s['stabilized']]
        sample_steps = [s for s in step_averages if s['sample_rate'] > 0 and s['stabilized']]

        results = {'step_averages': step_averages}

        if baseline_steps and sample_steps:
            baseline = np.mean([s['average_voltage'] for s in baseline_steps])

            # Calculate signals
            signals = [s['average_voltage'] - baseline for s in sample_steps]
            flow_rates = [s['sample_rate'] for s in sample_steps]

            # Get reference flow rate (assuming constant)
            ref_rate = sample_steps[0]['ref_rate'] if sample_steps else 0.15

            # Calculate heat capacity
            hc_results = self.calculate_heat_capacity(
                signals, flow_rates, ref_rate, density_sample
            )

            if hc_results:
                results.update(hc_results)
                print(f"Heat Capacity: {hc_results['heat_capacity']:.2f} J/(kg·K)")
        else:
            print("Insufficient stabilized data for heat capacity calculation")

        # Save data if path provided
        if save_path:
            self.save_experiment_data(all_data, step_averages, results, save_path)

        return results

    def save_experiment_data(self, raw_data, step_averages, results, save_path):
        """
        Save experiment data to Excel file.
        
        Args:
            raw_data (list): Raw voltage data
            step_averages (list): Step average data
            results (dict): Experiment results
            save_path (str): Path to save the Excel file
        """
        # Create timestamps for raw data
        timestamps = np.arange(len(raw_data)) / self.daq_frequency

        # Create DataFrame for raw data
        df_raw = pd.DataFrame({
            'Time [s]': timestamps,
            'Voltage [V]': raw_data
        })

        # Create DataFrame for step averages
        df_steps = pd.DataFrame(step_averages)

        # Create summary DataFrame
        summary_data = {
            'Parameter': ['Heat Capacity', 'Slope', 'Intercept', 'R-squared'],
            'Value': [
                results.get('heat_capacity', 'N/A'),
                results.get('slope', 'N/A'),
                results.get('intercept', 'N/A'),
                results.get('r_squared', 'N/A')
            ]
        }
        df_summary = pd.DataFrame(summary_data)

        # Save to Excel with multiple sheets
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            df_raw.to_excel(writer, sheet_name='Raw Data', index=False)
            df_steps.to_excel(writer, sheet_name='Step Averages', index=False)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

        print(f"Data saved to {save_path}")

