import numpy as np
import serial
import time
import argparse
import threading
import nidaqmx
from functools import partial
from sklearn.linear_model import LinearRegression
import xtalx.z_sensor
from xtalx.tools.z_sensor import z_common
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from datetime import datetime
from nidaqmx.constants import AcquisitionType
from parse_routines import load_daq_config, load_pump_config, load_valves_config, load_VD_config

import threading
import argparse
import os

# robust logging packages
import logging

# SHOULD BE DEINFED IN mAIN: 
logging.basicConfig(level=logging.INFO) # Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)
"""
READ ME:
============================================
Main backend file for the heat capacity measurement project. Classes need to be instantiated correctly for the devices to be used in the routines, and the routines need to be added to the RoutineManager for execution.
The RoutineManager should call all items and do the proper setup necessairly, all thats required are the device numbers and parameters. Since the code is a bit old, I suggest looking through the routine manager
to ensure that the devices and routiens are being called properly. To do so, check out the "10ml ones - copy.py" file for how the old code was running prior to this refactor; specifically the device setup and routine runs.
The "main.py" file was an old test file used to test the device connections. It should serve as an example for how to instantiate the devices and run the routines, but it is not fully updated to reflect the new code structure.
============================================
"""


"""
============================================
Global Thread Management Functions
============================================
Helper functions for starting and joining multiple threads. Used for running device operations in parallel.
"""


def start_threads(threads: list):
    """
    Start all threads in the provided list.
    
    Args:
        threads: List of threading.Thread objects to start
    """
    for thread in threads:
        thread.start()

def join_threads(threads: list):
    """
    Wait for all threads in the provided list to complete.
    
    Args:
        threads: List of threading.Thread objects to join
    """
    for thread in threads:
        thread.join()

def run_functions_parallel(functions: list, with_args: bool = False):
    """
    Run a list of functions in parallel using threads.
    
    Args:
        functions: List of functions to run, or list of (function, args) tuples if with_args=True
        with_args: If True, functions list contains (function, args) tuples
    
    Returns:
        List of thread objects
    """
    threads = []
    
    if with_args:
        for func, args in functions:
            thread = threading.Thread(target=func, args=args)
            threads.append(thread)
    else:
        for func in functions:
            thread = threading.Thread(target=func)
            threads.append(thread)
    
    start_threads(threads)
    join_threads(threads)
    
    return threads


'''
============================================
Serial Devices Base Class
============================================
Base classes defining devices used in the project. Each device must be instantiated using the below classes.
'''
class SerialDevice:
    '''
    Initializes serial device connection with configurable parameters. This is the base device class for all serially connected devices (e.g., selector valve, pumps). 
    It provides basic read/write functionality and can be extended with device-specific commands in child classes.
    '''
    def __init__(self, port, timeout, xonxoff, rtscts, dsrdtr, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, baudrate=9600, name='', ):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr
        )
        # TODO: RM -> self.ser.writeTimeout = 1

    def write(self, command):
        self.ser.write(bytes(command, 'utf-8'))
        time.sleep(0.1)

    def read(self):
        return self.ser.readline().decode("utf-8").strip()


'''
============================================
Selector Valve Class
============================================
Also includes setup for access to cleaning functions like air and solvent cleaning.
in this case, experiment uses I think 3-4 connections which houses the 3 pumps, air, and an output valve
'''

class SelectorValve(SerialDevice):
    """
    Controls a Hamilton selector valve via serial communication.

    Attributes:
        port (str): Serial port the valve is connected to.
        baudrate (int): Baud rate for communication (default 9600).
        valve_positions (int): Total number of positions (default 10).
        current_position (int): Last known valve position.
    """

    # TODO: Have valve positions be a dictonairy! a simple mapping table of the com port and the object!
    def __init__(self, port: str, name, bytesize, parity, stopbits, timeout, xonxoff, rtscts, dsrdtr, baudrate: int = 9600, connections={}):
        super().__init__(
            port=port,
            baudrate=baudrate,
            name=name,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr
            )
        
        self.connections = connections
        self.name = name
        
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

        # Set to Multiposition mode and configure valve positions
        self.write("AM3\r")   
        response = self.read()
        logging.debug(f"Valve Setup Multiposition Command Response: {response}")
        self.write(f"NP{len(self.valve_positions)}\r") 

    def move_to(self, position: int):
        """
        Moves the valve to the specified position. Position must be accessible to the valve.

        Args:
            position (int): Position to move to (1-based index).
        """
        # NOTE: check if sleeps are needed between each read/write/command for the valve
        # Format must be zero-padded if < 10
        print(f"passed position: {position}")
        position_str = f"{position:02d}"
        self.write(f"GO{position_str}\r")
        self.current_position = position
        time.sleep(0.1)
        logging.info(f" Selector Valve Position Change: {self.confirm_position()}")
        

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
============================================
Pump Device setup (subclass of serial device)
============================================
Defines pump-specific commands and functions for controlling the Hamiltonian syringe pumps. 
Requires pump number, port, and optional parameters like flow rate and baud rate. Provides functions for initializing the pump, sending commands, waiting for readiness, and performing injections.
'''

class Pump(SerialDevice):
    def __init__(self, port, pump_num, name, bytesize, parity, stopbits, timeout, xonxoff, rtscts, dsrdtr, flow_rate=0, baudrate=9600):
        '''
        Initializes a pump device with specified parameters.

        Args:
            port (str): Serial port the pump is connected to.
            pump_num (int): Identifier for the pump (e.g., 1, 2, 3).
            name (str): Name of the pump for logging purposes.
            flow_rate (float): Initial flow rate for the pump (default 0). Note: flow rate is typically set via specific commands, so this may just be a stored attribute rather than an active setting on initialization
            others args: Serial communication parameters.

        '''
        super().__init__(
            port=port,
            baudrate=baudrate,
            name=name,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr)
        self.pump_num = pump_num
        self.flow_rate = flow_rate
        self.name = name

    def send_command(self, command):
        """
        Sends a command to the pump and waits for it to be ready before proceeding.
        Based off of START_pumpSample functions
        """
        # I.e., send command "T" to stop all actions before sending a new command
        if not (self.pump_num):
            return

        full_cmd = f"/{self.pump_num}{command}R\r\n"
        self.write(full_cmd)

        time.sleep(0.5)
        self.wait_until_ready() # pings pump until no actions remain
        time.sleep(0.51)
        try: 
            time.sleep(0.5)
            readOut = self.read()
            time.sleep(0.5)
            self.write(full_cmd)
            print(f"Pump {self.name} read command response: {readOut}")
        except Exception as e:
            logging.error(f"Error reading from pump: {e}")
        
    def initialize(self,
                   syringe_size: int = 30,
                   zero_units: int = 100,
                   zero_accel: int = 0,
                   fill_units: int = 100,
                   fill_speed: int = 6000):
        '''
        Initializes the pump by setting syringe size, zeroing the plunger, and filling to a specified amount.
        Args:
            syringe_size (int): Size of the syringe in mL (default 30 mL)
            zero_units (int): Units to aspirate for zeroing the plunger (default 100 units, which is 5 mL since 1 unit = 0.05 mL)
            zero_accel (int): Acceleration for zeroing the plunger (default 0, which means no acceleration)
            fill_units (int): Units to aspirate for filling the syringe (default 100 units, which is 5 mL)
            fill_speed (int): Speed for filling the syringe (default 6000, which is the maximum speed for the pump)
        '''
        
        # Syringe size + zero plunger
        self.send_command(f"Y{syringe_size}z")

        # Set zero position by aspirating specified units at 0 accel
        self.send_command(f"OV{zero_units}A{zero_accel}")

        # Fill syringe to desired amount with speed
        self.send_command(f"OV{fill_units}P{fill_speed}")

    def wait_until_ready(self):
        '''
        Blocks until the pump is ready to receive the next command.

        It sends the 'F' (status) command and checks the response. Loop continues until
        the pump returns a status that is NOT '@' (busy) or 'o' (moving).
        '''
        response = ""
        while(not ("@" in response or "0" in response)):
            command = f"/{self.pump_num}F\r\n"
            self.write(command)
            # time.sleep(0.1)
            response = self.read()
            # NOTE: TEMP CODE:
            print(f"Pump {self.pump_num} ready status: {response}")
        # ===============
        print("Pump is ready")

    def inject(self, volume, duration=0, accel=None):
        if accel is not None:
            cmd = f"EV{int(volume * 20)}A{accel}"
        else:
            cmd = f"EV{int(volume * 20)}d{duration}"
        
        self.send_command("T")
        self.send_command(cmd)
        print("Injection Complete")

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
        print("Debubling Complete")


    def set_flow_rate(self, given_flow_rate):
        # line 1037 for pump_flow_rate
        """Assumes that valve has been set to pos 3 (is that rlly safe idk)
        Based off of the function pump_flow_rate
        """
        self.flow_rate = given_flow_rate

    def clean_pump(self, flush_volume=10, withdraw_volume=300):
        """
        Based off of PumpCleaning_pumpSample1
        """
        self.fast_empty(flush_volume)
        self.withdraw(withdraw_volume)
        self.fast_empty(flush_volume)


"""
============================================
Data Aqcuisition (DAQ) Device Class
============================================
Defines a class for handling NI DAQ devices used for voltage measurements in the heat capacity experiment.
Includes initialization, voltage reading, stabilization checking, and data collection functions.
"""

class DAQDevice:
    def __init__(self, port_name="NI9210/ai0", daq_frequency=3, min_vol=-0.08, max_vol=0.08):
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
                sample_mode=AcquisitionType.CONTINUOUS
            )
            print(f"DAQ initialized on {self.port_name} at {self.daq_frequency} Hz")
        except Exception as e:
            print(f"Failed to initialize DAQ: {e}")
            raise
        # NOTE: tasks are essentially DAQ objects with their own functions
        # and properites that allow for reading/writing/running experiments in their own
        # specified channels. 

    def read_voltage(self):
        """
        Read a single voltage value from the DAQ.
        
        Returns:
            float: Voltage reading from the DAQ
        """
        if self.task is None:
            raise RuntimeError("DAQ task not initialized")
        return self.task.read()

    # NOTE: unsure if this function is necessairy
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

    # NOTE: Unsure if this function is necessairy
    def __enter__(self):
        """Context manager entry."""
        return self

    # NOTE: Unsure if this function is necessairy
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



'''
============================================
Routine Management Classes
============================================
Defines classes for managing the overall experimental routine, including orchestrating the VD sensor measurements, DAQ data collection, and device control. 
This includes the VDRoutine class which integrates the VD sensor with the DAQ and provides functions for running full measurement routines.
'''

class VDRoutine:
    """
    Orchestrates a full viscosity/density measurement routine using xtalx.z_sensor.
    """

    def __init__(self, 
                 serial_number=None, 
                 verbose=False, 
                 track_impedance=False, 
                 PEAK_CENTER_TOLERANCE_HZ = 100,
                 PEAK_WIDTH_TOLERANCE_HZ  = 20,
                 PEAK_CENTER_REFERENCE = 32776.181,
                 PEAK_WIDTH_REFERENCE = 2.174,
                 measurements=5, batchsize=5, VSTD_range=0.1, DSTD_range=0.1):
        '''
        Initializes the VDRoutine with specified parameters and sets up the VD sensor. 
        Args:
            serial_number (str): Serial number of the VD sensor to connect to (optional)
            verbose (bool): Whether to enable verbose logging for the VD sensor (default False)
            track_impedance (bool): Whether to track impedance instead of yield (default False)
            PEAK_CENTER_TOLERANCE_HZ (float): Tolerance for peak center frequency in Hz (default 100 Hz)
            PEAK_WIDTH_TOLERANCE_HZ (float): Tolerance for peak width (FWHM) in Hz (default 20 Hz)
            PEAK_CENTER_REFERENCE (float): Reference value for peak center frequency in Hz (default 32776.181 Hz)
            PEAK_WIDTH_REFERENCE (float): Reference value for peak width (FWHM) in Hz (default 2.174 Hz)
            measurements (int): Number of measurements to take in the routine (default 5)
            batchsize (int): Number of measurements to take before calculating batch statistics (default 5)
            VSTD_range (float): Standard deviation threshold for viscosity measurements to consider a batch valid (default 0.1 cP)
        '''

        # Details for the peak values that the VD sensor will detect
        # This is primairly (I think) only used for determining if the sensor is clean or not.

        self.peak_center_reference = PEAK_CENTER_REFERENCE
        self.peak_center_tolerance = PEAK_CENTER_TOLERANCE_HZ
        self.peak_width_reference = PEAK_WIDTH_REFERENCE
        self.peak_width_tolerance = PEAK_WIDTH_TOLERANCE_HZ

        self.tc = None  # tracking controller
        self.pq = None  # predicate queue
        self.pt = None  # peak tracker

        self.viscosity = []
        self.density = []
        self.trial_ids = []
        self.temperature = []
        # self.batchV = []  # batch viscosity
        # self.batchD = []  # batch density
        self.raw_data = []  # NOTE: is this necessiary?

        # Routine-specific definitions
        self.measurements = measurements
        self.batchsize = batchsize
        self.VSTD_range = VSTD_range
        self.DSTD_range = DSTD_range

        # Setup the V/D
        parser = argparse.ArgumentParser()
        z_common.add_arguments(parser)
        args = parser.parse_args()

        self.serial_number = args.sensor
        self.verbose = args.verbose  # more detailed logging of the VD processes
        self.track_impedance = args.track_impedance

        self.initialize_vd(args)


    def initialize_vd(self, args):
        """
        Used to start the V/D Sensor and configure it to a predicate queue
        Based off of the start_dv_sensor_and_get_queue function. Note that args uses default
        arguments for za and zl.
        """

        device = xtalx.z_sensor.find_one(serial_number=self.serial_number)
        self.tc = xtalx.z_sensor.make(device, verbose=self.verbose,
                                      yield_Y=not self.track_impedance)

        # Arqs required here because parse_args expects a tc and CLI style arguments object
        za, zl = z_common.parse_args(self.tc, args)

        self.pq = xtalx.z_sensor.PredicateQueue(delegate=z_common.ZDelegate(zl))
        self.pt = xtalx.z_sensor.PeakTracker(
            self.tc, za.amplitude, za.f0, za.f1, za.df,
            za.nfreqs, za.search_time_secs, za.sweep_time_secs,
            settle_ms=za.settle_ms,
            delegate=self.pq
        )
        # Run the peak tracker in a separate thread
        self.pt.start_threaded()
        print(f"[VD] Sensor {self.tc.serial_num} initialized and tracking.")

    def get_measurement(self, trial_id=None):
        """
        Fetch the most recent measurement data from the VD sensor's predicate queue.
        This function will continue to fetch until a valid measurement is found, or until timeout.
        Based off of get_dv_measurement function.
        """
        if not self.pq:
            raise RuntimeError("VD sensor has not been initialized.")
        
        time.sleep(1)
        while True:
            m = self.pq.get_measurement()
            self.pq.clear()
            if m is not None and m.fw_fit is not None:
                self.raw_data.append(m)
                self.viscosity.append(m.viscosity_cp)
                self.density.append(m.density_g_per_ml)
                self.temperature.append(m.fw_fit.temp_c)
                self.trial_ids.append(trial_id)
                # NOTE: trial_id is not defined in the original code - we should make sure to pass it in when calling get_measurement in the main routine function
                print('   Density: %s' % m.density_g_per_ml)
                print(' Viscosity: %s' % m.viscosity_cp)
                print('   Peak Hz: %s' % m.peak_hz)
                print('Peak Width: %s' % m.peak_fwhm)
                print('  Temp (C): %s' % m.fw_fit.temp_c)
                return m
            
            time.sleep(0.1)
        
        # NOTE: Old code below 
        # result = self.pq.dequeue(timeout=timeout)
        # if result:
        #     visc = getattr(result, 'viscosity', None)
        #     dens = getattr(result, 'density', None)
        #     self.viscosity.append(visc)
        #     self.density.append(dens)
        #     self.trial_ids.append(trial_id)
        #     self.raw_data.append(result)

        #     print(f"[VD] Trial {trial_id or len(self.trial_ids)}: "
        #           f"Viscosity={visc}, Density={dens}")
        #     return visc, dens
        # else:
        #     print("[VD] Warning: No measurement received within timeout.")
        #     return None, None

    def stop_vd(self):
        if self.pt:
            self.pt.stop_threaded()
            print("[VD] Sensor thread stopped.")

    def inject_samples(self, pumps:list[Pump], syringe_volume:float=10, injection_time:float=1):
        """
        Function for injecting a sample from x amount of syringes depending on their given flow rates. 
        Assumes that we are in injection mode. Suppose flow rates have already been set. debubbles and injects
        samples into the vd sensor.
        """
        
        time.sleep(5)
        debubble_threads = []
        injection_threads = []

        for pump in pumps:
            duration = 0
            dist = 0

            if pump.flow_rate != 0:
                duration = round(6000 * injection_time / (syringe_volume / pump.flow_rate))

            thread_debubble = threading.Thread(target=pump.debubble, args=(5,dist))
            thread_injection = threading.Thread(target=pump.inject, args=(pump.flow_rate, duration))

            debubble_threads.append(thread_debubble)
            injection_threads.append(thread_injection)
        
        start_threads(debubble_threads)
        join_threads(debubble_threads)

        time.sleep(0.1)

        start_threads(injection_threads)
        join_threads(injection_threads)

    def validate_STD(self, num_stats_batch=5, VSTD_range=0.1, DSTD_range=0.1):
        """
         Function to validate that the standard deviation of the viscosity and density measurements are within a specified range. 
         If the standard deviation is not within the range, it will continue to take measurements until it is. This function assumes that the first (num_stats_batch) measurements have already been taken and are stored in the viscosity and density lists.
        """
        # check if the STD is within the correct range
        # NOTE: indexing arrays to always view the first (X) measurements in the list 
        start = 0
        end = num_stats_batch

        while True:
            BatchV = self.viscosity[start:end] #adding the measurement to an array with size 5 to check STD
            BatchD = self.density[start:end]
            BatchT = self.temperature[start:end]
            V_STD = np.std(BatchV) #calculate viscosity STD
            D_STD = np.std(BatchD) #calculate density STD
            if V_STD<=VSTD_range and D_STD<=DSTD_range: #check STD, if within the thereshold, break the loop, output result
                print("Current viscosity array to calculate STD", BatchV)
                print("Viscosity STD is:",V_STD)
                print("Current density array to calculate STD", BatchD)
                print("Density STD is:", D_STD)
                self.pq.clear()
                break
            
            #if the STD is not within the desired range, run another test and keep running till STD is ok
            self.get_measurement(end + 1) # send over the trial number

            start += 1
            end += 1
        return BatchV, BatchD, BatchT, V_STD, D_STD

    # These should be changed to self.num_measurements instead.
    def run_vd_routine(self, num_measurements=5, num_stats_batch=5, VSTD_range=0.1, DSTD_range=0.1) :
        """
        based off of the main function for measureming V/D
        This function will run the V/D routine, collecting measurements
        for a specified number of trials.
        """
        # TODO: Add error handling here to ensure that people provide the correct range of measurements and stats batch size
        # i.e., num_stats_batch MUST be <= num_measurements. 

        # Define batch V/D as empty arrays
        print("Experiment in progress....")
        BatchV = []
        BatchD = []
        BatchT = []
        V_STD = 0.0
        D_STD = 0.0

        # fetch first (N) measurements from the predicate queue
        time.sleep(25)
        for i in range(num_measurements):
            self.get_measurement(i + 1) # send over the trial number
        self.pq.clear()
    
        # NOTE: moved measurements for the V/D sensor to the validate_STD function
        BatchV, BatchD, BatchT, V_STD, D_STD = self.validate_STD(num_stats_batch, VSTD_range, DSTD_range)
        #v = sum(m.density_g_per_ml for m in measurements) / len(measurements)
        #d = sum(m.viscosity_cp for m in measurements) / len(measurements)
        Mean_V = sum(BatchV)/len(BatchV)
        Mean_D = sum(BatchD)/len(BatchD)
        Mean_T = sum(BatchT)/len(BatchT)
        print('Mean viscosity: %s cP' % Mean_V)
        print('  Mean density: %s g/mL' % Mean_D)

        return Mean_V, Mean_D, Mean_T, V_STD, D_STD

    def is_clean(pq):
        """
        Uses the defined values of VD's peak width and frequency to determine 
        if the sensor is clean or not.
        Based off of is_sensor_clean_in_air
        """
        pass

class HCRoutine:
    """
    HC Routine should handle all things related to computing cP.
    It should include its own DAQ device responsible for reading the data 
    and computing the heat capacity.
    NOTE: num of ppumps is hardcoded for HC routine, but will have to make this more expandable in future
    """
    def __init__(self, daq:DAQDevice, ref_pump:Pump, sample_pump:Pump):
        self.viscosity = []
        self.density = []
        self.trial = []
        self.data = []

        self.ref_pump = ref_pump
        self.sample_pump = sample_pump

        self.daq = daq  # DAQ device for heat capacity measurement

    def initialize_visualization(self, xLabel='Time [s]', ylabel='Voltage [V]', title='Live Data Visualization', xLim=500, yLim=(-1e-5, 1e-5)):
        """
        Initialize the live data visualization for the HC routine.
        """
        # Variable setup
        fig, ax = plt.subplots()
        line, = ax.plot([], [])
        plt.xlabel(xLabel)
        plt.ylabel(ylabel)
        plt.title(title)
        ax.set_xlim([0, xLim])
        ax.set_ylim(yLim)

        plt.ion()  # Enable interactive mode for live updates
        plt.show(block=False)  # Show the plot without blocking the execution

        return fig, ax, line
    
    def update_visualization(self, idx, ax:plt.Axes, line:plt.Line2D, x_data, y_data, x_counter, y_axis_margin=1e-5):
        """
        frequently called to update the graphical visualization of the HC routine.
        """
        if idx % self.daq.daq_frequency == 0:
            line.set_data(x_data, y_data)
            # Adjust x-axis if necessary
            current_xlim = ax.get_xlim()
            
            if x_counter / self.daq.daq_frequency > current_xlim[1]:
                ax.set_xlim(current_xlim[0], current_xlim[1] + 200)  # Add 200 seconds to x-axis
            # Adjust y-axis if necessary
            current_ylim = ax.get_ylim()
            if max(y_data) > current_ylim[1] or min(y_data) < current_ylim[0]:
                ax.set_ylim(min(y_data) - y_axis_margin, max(y_data) + y_axis_margin)
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.01)

    def validate_segment(self, segment_array, variation_limit=0.1) -> bool:
        """
        Check if the segment within the variation limit.
        Based off of the within_linient_segment_variation_limit
        """
        overall_mean = np.mean(segment_array)
        count_within_threshold = 0  # what does this mean?? amnt in threshold?
        
        for seg_mean in segment_array:
            abs_diff = abs(seg_mean - overall_mean) 
            if abs_diff <= variation_limit:
                count_within_threshold +=1
        # NOTE: means that if at least 4 or more of the segments are within threshold,
        # then the entire segment is considered valid.
        if count_within_threshold >= 4:
            return True
        else:
            return False

    def measure_voltage_segment(self, exp_protocol, m1, m2, m3, f1, f2, f3, batch, step_duration=5, num_consecutive_seg=2, num_max_seg=5, variation_limit=0.4e-6
                                , xLim=500, y_axis_margin=1e-5):
        """
        A chunk of the run_experiment function in HC.py (from the smart injection hyperparameters).
        Responsible for running a segment of the experiment and checking if the segment is valid.
        """
            # Smart Injection Hyperparameters
        step_data_4analysis = [False] * len(exp_protocol)
        failed_flow_rates = []  # To track which flow rates failed stabilization
        passed_flow_rates = []  # To track which flow rates passed stabilization
        x_data, y_data = [], []
        fig, ax, line = self.initialize_visualization('Time [s]', 'Voltage [V]', 'Live Data Visualization', xLim, (-y_axis_margin, y_axis_margin))

        x_counter = 0
        all_data = []

        # for each defined protocol (i.e., configuration w/ flow rates and durations))
        for i_exp, protocol in enumerate(exp_protocol):
            # NOTE: TEMP DISABLED
            sample_rate = 10
            ref_rate = 10
            # sample_rate, ref_rate = protocol
            print(f"Starting experiment step {i_exp + 1}/{len(exp_protocol)} with sample rate {sample_rate} mL/min.")

            self.ref_pump.inject(ref_rate, accel=0)
            self.sample_pump.inject(sample_rate, accel=0)

            is_stabalized = False    
            seg_loop_counter = 0
            seg_mean_mem = []
            data_in_loop = []

            # while the segment is not stabalized
            while not is_stabalized:
                segment_data = []
                for idx in range(step_duration * self.daq.daq_frequency):
                    voltage = self.daq.read_voltage()
                    data_in_loop.append(voltage)
                    segment_data.append(voltage)
                    # Plot data for visualization:
                    x_data.append(x_counter / self.daq.daq_frequency)
                    y_data.append(voltage)
                    x_counter += 1

                    self.update_visualization(idx, ax, line, x_data, y_data, x_counter, y_axis_margin)
                    
                    # Update visualization every second
                    # NOTE: Create a seprate funciton for updating visualization
                    # if idx % self.daq.daq_frequency == 0:
                    #     # Update plot
                    #     line.set_data(x_data, y_data)
                    #     # Adjust x-axis if necessary
                    #     current_xlim = ax.get_xlim()
                    #     if x_counter / self.daq.daq_frequency > current_xlim[1]:
                    #         ax.set_xlim(current_xlim[0], current_xlim[1] + 200)  # Add 200 seconds to x-axis
                    #     # Adjust y-axis if necessary
                    #     current_ylim = ax.get_ylim()
                    #     if max(y_data) > current_ylim[1] or min(y_data) < current_ylim[0]:
                    #         ax.set_ylim(min(y_data) - y_axis_margin, max(y_data) + y_axis_margin)
                    #     ax.relim()
                    #     ax.autoscale_view()
                    #     plt.pause(0.01)

                # Segment Analysis
                seg_mean = np.mean(segment_data)
                seg_std = np.std(segment_data)
                seg_mean_mem.append(seg_mean)

                print(f"Segment Loop Counter: {seg_loop_counter}")
                print(f"num_consecutive_seg: {num_consecutive_seg}")

                if seg_loop_counter < num_consecutive_seg:
                    seg_loop_counter += 1
                elif seg_loop_counter < num_max_seg:
                    if self.validate_segment(seg_mean_mem[-num_consecutive_seg:], variation_limit):
                        is_stabalized = True
                        step_data_4analysis[i_exp] = np.mean(seg_mean_mem[-num_consecutive_seg:])
                        passed_flow_rates.append(i_exp)
                        print(f"Stabilization achieved at step {i_exp + 1}.")
                    else:
                        seg_loop_counter += 1
                else:
                    print(f"Flow rate {sample_rate} mL/min failed to stabilize completely. Removing from regression analysis.")
                    failed_flow_rates.append(i_exp)
                    is_stabalized = True

            # Pumps Stop
            stopCmd = "T"
            self.sample_pump.send_command(stopCmd)
            self.ref_pump.send_command(stopCmd)

            # Data Packaging for Analysis
            exp_data = np.zeros((len(data_in_loop), 4))
            exp_data[:, 1] = np.array(data_in_loop)
            exp_data[:, 0] = np.linspace(0, (len(data_in_loop) - 1) * (1 / self.daq.daq_frequency), len(data_in_loop))
            exp_data[:, 2] = ref_rate  # Reference rate
            exp_data[:, 3] = sample_rate  # Sample rate

            all_data.extend(exp_data)

            print(f"Finished experiment step {i_exp + 1}/{len(exp_protocol)}.")

            # close all connections
            plt.ioff()
            plt.pause(0.001)

            # Save Data 
            now=date.today()
            timenow=datetime.now()

            # NOTE: TEMPORARILY DISABLING IT (turn back on after)
            # df = pd.DataFrame(all_data, columns=['Time [s]', 'Voltage [V]', 'ref_rate', 'sample_rate'])
            # df.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-water-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}.xlsx', index=False)


        # TODO: Read some of the parameters being given to the run_hc_routine function and see what
        # should be an attribute specific to the HCRoutine (like sample_pump_rates, etc..) and what shouldn't
    def run_hc_routine(self, density_sample, m1, m2, m3, f1, f2, f3, batch, Mean_V, Mean_D, Mean_T, V_STD, D_STD, visualization=True, save_path=None, step_duration=120, 
                       sample_pump_rates=[0, 0.2, 0.3, 0.4], ref_pump_rate=0.15, exp_protocol:list=[], num_consecutive_seg=5, num_max_seg=15,
                       variation_limit=0.4e-6, xLim=500, y_axis_margin=1e-5, Cp=None):
        """
        Based off of the run_experiment function in HC.py.
        Goal is to overall run heat capacity experiments and gather data.
        
        """
        print('HC measurement started.')

        # NOTE: Equipment initialization already handled in DAQDevice class
        # daq_freq = 3
        # daq = LoggerNI("NI9210/ai0", daq_freq)
    
        # NOTE: Experiment parameters
        # NOTE: exp protocol refers to the order in which everything should be conducted in,
        # including the parsing and stringing together of all the data needed to conduct the experiment.
        # It makes the experiemnt more flexible and allows for iterating over diff exp in one array.
        # exp_step_duration = 120  # Duration for each step in seconds
        # ref_pump_rate = 0.15  # Reference pump injection rate in mL/min
        # exp_sample_pump_rates = [0, 0.2, 0.3, 0.4]  # Removed last zero flow rate
        # exp_Protocol = []
        #NOTE: look into using this type of exp protocol to add dynamic routines / routine constructions!
        # NOTE: combining the run_experiment2 function into the run_hc_routine function:
        if (Cp and (Cp <= 2500 and Cp != 0)):
            now=date.today()
            timenow=datetime.now()
            self.data.append( {m1: f1,
                    m2: f2,
                    m3: f3,
                    'Mean Viscosity (cp)': Mean_V,
                    'Mean Density (g/mL)': Mean_D,
                    'Mean T': Mean_T,
                    'std_vis':V_STD,
                    'std_den':D_STD,
                    'Cp_avg':Cp,
                    'Cp_1':Cp,
                    'Cp_2':'---',
                    'difference':'---'
            })
            VDCp = pd.DataFrame(self.data)
            VDCp.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-Test3_VD+HC_{m1}+{m2}+{m3}_{now}.xlsx', index=False)
        
        if exp_protocol == []:
            for rate in sample_pump_rates:
                exp_protocol.append([rate, ref_pump_rate if rate != 0 else 0, step_duration])

        # NOTE: maybe condense everything here into a function?
        # Smart Injection Hyperparameters
    #     seg_step_duration = 10  # Duration of each segment in seconds
    #     num_consecutive_seg = 5
    #     max_num_seg = 15
    #     segment_variation_abs = 0.4e-6 # Threshold for stabilization check in percent

        step_data_4analysis = [False] * len(exp_protocol)
        failed_flow_rates = []  # To track which flow rates failed stabilization
        passed_flow_rates = []  # To track which flow rates passed stabilization

        self.measure_voltage_segment(exp_protocol, m1, m2, m3, f1, f2, f3, batch, step_duration, num_consecutive_seg, num_max_seg, variation_limit, xLim, y_axis_margin)



        # Visualization setup
        fig, ax = plt.subplots()
        x_data, y_data = [], []
        line, = ax.plot([], [])
        plt.xlabel('Time [s]')
        plt.ylabel('Voltage [V]')
        plt.title('Live Data Visualization')
        ax.set_xlim([0, 500])  # Initial x-axis limit set to 500 seconds

        y_axis_margin = 1e-5  # y-axis margin of 1e-5
        ax.set_ylim([-y_axis_margin, y_axis_margin])  # Initial y-axis limits

        plt.ion()
        plt.show(block=False)
        x_counter = 0
        

        all_data = []

        for i_exp, protocol in enumerate(exp_Protocol):
            sample_rate, ref_rate, duration = protocol
            print(f"Starting experiment step {i_exp + 1}/{len(exp_Protocol)} with sample rate {sample_rate} mL/min.")

            PumpInjection_pump1_HC(sample_rate)
            PumpInjection_pump2_HC(ref_rate)

            step_master_cond = False
            seg_loop_counter = 0
            seg_mean_mem = []
            data_in_loop = []

            while not step_master_cond:
                segment_data = []
                for idx in range(seg_step_duration * daq_freq):
                    voltage = daq.read_voltage()
                    data_in_loop.append(voltage)
                    segment_data.append(voltage)
                    x_data.append(x_counter / daq_freq)
                    y_data.append(voltage)
                    x_counter += 1

                    # Update visualization every second
                    if idx % daq_freq == 0:
                        # Update plot
                        line.set_data(x_data, y_data)
                        # Adjust x-axis if necessary
                        current_xlim = ax.get_xlim()
                        if x_counter / daq_freq > current_xlim[1]:
                            ax.set_xlim(current_xlim[0], current_xlim[1] + 200)  # Add 200 seconds to x-axis
                        # Adjust y-axis if necessary
                        current_ylim = ax.get_ylim()
                        if max(y_data) > current_ylim[1] or min(y_data) < current_ylim[0]:
                            ax.set_ylim(min(y_data) - y_axis_margin, max(y_data) + y_axis_margin)
                        ax.relim()
                        ax.autoscale_view()
                        plt.pause(0.01)

                # Segment Analysis
                seg_mean = np.mean(segment_data)
                seg_std = np.std(segment_data)
                seg_mean_mem.append(seg_mean)

                if seg_loop_counter < num_consecutive_seg:
                    seg_loop_counter += 1
                elif seg_loop_counter < max_num_seg:
                    if within_linient_segment_variation_limit(seg_mean_mem[-num_consecutive_seg:], segment_variation_abs):
                        step_master_cond = True
                        step_data_4analysis[i_exp] = np.mean(seg_mean_mem[-num_consecutive_seg:])
                        passed_flow_rates.append(i_exp)
                        print(f"Stabilization achieved at step {i_exp + 1}.")
                    else:
                        seg_loop_counter += 1
                else:
                    print(f"Flow rate {sample_rate} mL/min failed to stabilize completely. Removing from regression analysis.")
                    failed_flow_rates.append(i_exp)
                    step_master_cond = True

            # Pumps Stop
            Stop_pump1_HC()
            Stop_pump2_HC()

            # Data Packaging for Analysis
            exp_data = np.zeros((len(data_in_loop), 4))
            exp_data[:, 1] = np.array(data_in_loop)
            exp_data[:, 0] = np.linspace(0, (len(data_in_loop) - 1) * (1 / daq_freq), len(data_in_loop))
            exp_data[:, 2] = ref_rate  # Reference rate
            exp_data[:, 3] = sample_rate  # Sample rate

            all_data.extend(exp_data)

            print(f"Finished experiment step {i_exp + 1}/{len(exp_Protocol)}.")

        plt.ioff()
        plt.show()

        # Close connections
        daq.close()
        # Register signal handlers
        #signal.signal(signal.SIGINT, cleanup)  # Handle Ctrl+C
        #signal.signal(signal.SIGTERM, cleanup) # Handle termination signal
        #sample_pump.close()
        #ref_pump.close()

        plt.close('all')
        plt.pause(0.001)

        now=date.today()
        timenow=datetime.now()
        # Save data
        df = pd.DataFrame(all_data, columns=['Time [s]', 'Voltage [V]', 'ref_rate', 'sample_rate'])
        df.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-water-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}.xlsx', index=False)

        # Perform regression analysis on collected data
        # NOTE: I'm not really all too sure what this all is?
        heatCapacity_sam, Error = self.perform_regression_analysis(
            step_data_4analysis=step_data_4analysis,
            exp_protocol=exp_protocol,
            density_sample=density_sample,
            ref_pump_rate=ref_pump_rate,
            batch=batch,
            m1=m1, f1=f1, m2=m2, f2=f2, m3=m3, f3=f3
        )
        
        return heatCapacity_sam, Error
    
    def perform_regression_analysis(self, step_data_4analysis, exp_protocol,
                                   density_sample, ref_pump_rate, batch, 
                                   m1, f1, m2, f2, m3, f3, now,
                                   density_ref=988.8, heatCapacity_ref=4176.5,
                                   heatCapacity_sample_ErrorCalc=1968.9,
                                   save_step_averages=True, save_regression_data=False,
                                   step_averages_path=None, regression_data_path=None):
        """
        Perform regression analysis on collected heat capacity data.
        
        Parameters:
        -----------
        step_data_4analysis : list
            Average voltage data for each step
        exp_protocol : list
            Protocol with lowercase 'p' containing flow rates
        exp_Protocol : list
            Protocol with uppercase 'P' containing flow rates
        density_sample : float
            Density of the sample (kg/m^3)
        ref_pump_rate : float
            Reference pump flow rate (mL/min)
        batch : str
            Batch identifier for naming output files
        m1, f1, m2, f2, m3, f3 : various
            Material and fraction identifiers for file naming
        now : datetime or str
            Timestamp for file naming
        density_ref : float, optional
            Reference fluid density (kg/m^3), default=988.8
        heatCapacity_ref : float, optional
            Reference fluid heat capacity (J/(kg·K)), default=4176.5
        heatCapacity_sample_ErrorCalc : float, optional
            Expected sample heat capacity for error calculation, default=1968.9
        save_step_averages : bool, optional
            Whether to save step averages to Excel, default=True
        save_regression_data : bool, optional
            Whether to save regression data to Excel, default=False
        step_averages_path : str, optional
            Custom path for step averages file
        regression_data_path : str, optional
            Custom path for regression data file
        
        Returns:
        --------
        tuple : (heatCapacity_sam, Error)
            Calculated heat capacity and error percentage
        """
        # Filter the data for regression by excluding failed flow rates
        valid_indices = [i for i in range(len(step_data_4analysis)) if step_data_4analysis[i] is not False]

        if len(valid_indices) >= 2:
            try:
                # Identify baseline steps (zero flow rate) with valid data
                baseline_steps = [i for i in valid_indices if exp_protocol[i][0] == 0]

                if len(baseline_steps) >= 1:
                    baseline = np.mean([step_data_4analysis[i] for i in baseline_steps])
                else:
                    print("No valid baseline data available. Cannot compute heat capacity.")
                    baseline = None

                # Steps with non-zero sample flow rates
                sample_flow_steps = [i for i in valid_indices if exp_Protocol[i][0] != 0]

                # Prepare data for regression
                if baseline is not None:
                    signal = np.array([step_data_4analysis[i] - baseline for i in sample_flow_steps])
                    sample_pump_rates = np.array([exp_Protocol[i][0] for i in sample_flow_steps])

                    if len(signal) >= 2:
                        signal = signal.reshape(-1, 1)
                        sample_pump_rates = sample_pump_rates.reshape(-1, 1)

                        model = LinearRegression()
                        model.fit(signal, sample_pump_rates)
                        slope = model.coef_[0][0]
                        intercept = model.intercept_[0]

                        # Corrected calculation of intersection_point
                        #intersection_point = - intercept / slope

                        heatCapacity_sam = (ref_pump_rate * heatCapacity_ref * density_ref) / (density_sample * intercept)
                        Error = (heatCapacity_sam - heatCapacity_sample_ErrorCalc) / heatCapacity_sample_ErrorCalc * 100
                        print(f"Heat Capacity of Sample = {heatCapacity_sam:.8g} J/(kg·K)")
                        print("Error=", Error)

                        #print(f"Slope: {slope}")
                        #print(f"Intercept: {intercept}")

                        # NOTE: I don't think saving the regression data should be a conditional query
                        # Save regression data if requested
                        if save_regression_data:
                            regression_data = pd.DataFrame({
                                'Sample Pump Rate [mL/min]': sample_pump_rates.flatten(),
                                'Step Average Voltage [V]': [step_data_4analysis[i] for i in sample_flow_steps],
                                'Signal [V]': signal.flatten()
                            })

                            # Add Heat Capacity and Error to the regression data
                            regression_data['Heat Capacity [J/(kg·K)]'] = heatCapacity_sam
                            regression_data['Error [%]'] = Error

                            # Save the updated DataFrame to the Excel file
                            if regression_data_path:
                                regression_data.to_excel(regression_data_path, index=False)
                                print(f"Regression data saved to {regression_data_path}")
                            #regression_data.to_excel('C:/Users/Indus/OneDrive/Desktop/Hanie/Dec12/water-heptane4_regression_data.xlsx', index=False)
                            #print("Regression data, including heat capacity and error, saved successfully.")

                        # Save all step averages if requested
                        if save_step_averages:
                            all_step_averages = pd.DataFrame({
                                'Experiment Step': valid_indices,
                                'Sample Pump Rate [mL/min]': [exp_Protocol[i][0] for i in valid_indices],
                                'Average Voltage [V]': [step_data_4analysis[i] for i in valid_indices]
                            })

                            if step_averages_path:
                                all_step_averages.to_excel(step_averages_path, index=False)
                            else:
                                all_step_averages.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-water-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}_step_averages.xlsx', index=False)
                            print("Step averages saved successfully.")
                    else:
                        heatCapacity_sam = 0
                        Error = 0
                        print("Not enough data points for regression.")
                else:
                    print("Baseline is missing. Cannot perform regression.")
                    heatCapacity_sam = 0
                    Error = 0
            except Exception as e:
                print(f"Regression failed: {e}")
                heatCapacity_sam = 0
                Error = 0
        else:
            heatCapacity_sam = 0
            Error = 0
            print("Not enough valid data points to perform regression.")
        
        #time.sleep(200)
        return heatCapacity_sam, Error
    
    def ready_hc(self, sample_accel=2000, ref_accel=4800):
        """
        Based off of the HC_Ready() function
        """
        #NOTE : I'm not sure which pump is actually the reference and which is actually the sample
        # Pump 1 refill
        self.sample_pump.withdraw(volume=100)
        time.sleep(60)
        time.sleep(1)
        # Pump 1 debubble
        self.sample_pump.debubble(volume=200, duration=2.5 * 1000)
        time.sleep(1)
        print('HC getting initialized.')
        t1 = threading.Thread(target=self.sample_pump.inject(1, accel=sample_accel))
        time.sleep(1)
        t2= threading.Thread (target =self.ref_pump.inject(1, accel=ref_accel))
        time.sleep(1)
        t1.start ()
        t2.start ()
        t1.join()
        t2.join()
        print('initialized.')
        time.sleep(120)


        
    
# This should be replaced with a cleaning routine instead that runs all cleaning functions
# Which I think it already does but it def needs to be defined a bit better and more accureatley to the code
class SensorCleaningRoutine:
    """
    Handles cleaning routines for sensors (e.g., VD sensors connected to pumps).
    Provides a structured process for cleaning with solvent, air, and sample loading.
    """

    def __init__(self, pump:Pump, sample_volume=100, flush_volume=10, delay_seconds=30):
        """
        :param pump: A pump object with methods like .empty(), .clean(), .withdraw(), .inject()
        :param sample_volume: Volume to withdraw after cleaning
        :param flush_volume: Volume to flush during cleaning
        :param delay_seconds: Delay to allow sample to settle before injection
        """
        # pump cleaning
        self.pump = pump
        self.sample_volume = sample_volume
        self.flush_volume = flush_volume
        self.delay_seconds = delay_seconds

        # HC sensor cleaning


    def sensor_cleaning(self):
        print("Starting sensor cleaning routine...")
        self.pump.empty(self.flush_volume)
        input("Place the pump in solvent for sensor cleaning and press Enter to continue...")
        self.pump.clean()
        input("Place the pump in air for sensor drying and press Enter to continue...")
        self.pump.clean()
        print("Sensor cleaning completed.")

    def hc_cleaning(self):
        print("Starting HC cleaning routine...")
        self.pump.empty(self.flush_volume)
        input("Place the pump in HC solvent and press Enter to continue...")
        self.pump.clean()
        input("Place the pump in air and press Enter to continue...")
        self.pump.clean()
        print("HC cleaning completed.")

    # intended for injection later after cleaning
    def inject_sample(self, volume=None, acceleration=4500):
        print("Injecting sample...")
        self.pump.inject(volume or self.sample_volume, acceleration)
        self.pump.withdraw(self.sample_volume)

    def run_full_routine(self):
        self.sensor_cleaning()
        self.load_sample()
        self.inject_sample()
        print("Cleaning and injection routine comple")

    def someKindOfCleaing(self):
        self.pump.withdraw(25 * 8)


class RoutineManager:
    """
    Manages multiple routines for V/D measurement, sensor cleaning, and other tasks.
    Provides a structured way to run and manage different routines.
    For now this class will simply organize main routine functions that are not necessairly
    dependant of each other routine (like HC, V/D and Cleaniing which should be defined within themselves.)
    """

    def __init__(self, file_path=None, start_sheet=None, end_sheet=None, num_chemicals=None, first_cleaning=None, routine=""):
        
        # TODO: remove this later since this should be created by the process sheets for pumps class.
        # The only actual variable that we need is the ones passed into process pumps for sheets.
        # TODO: instead define the new changed variables above w/ self. notation later.
        """
        Initializes the RoutineManager with pump, valve, and DAQ configurations.
        Sets up the necessary equipment based on provided configurations and prepares routines.
        """

        self.routines = []

        # Pump Setup
        pumps_config = load_pump_config()
        self.pumps = {}        
        for label, pump in pumps_config.items():
            print(f"Pump items: {pump}")
            pump_object = Pump(
                        port=pump["Port"],
                        pump_num=pump["Pump Number"],
                        name=label,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1,
                        xonxoff=False,
                        rtscts=False,
                        dsrdtr=False,
                        flow_rate=pump["Flow Rate"],
                        baudrate=pump["Baudrate"]
                        )
            self.pumps[label] = pump_object
            print(f"Pump added: {pump}")
            print(f"Total pumps: {self.pumps}")

        self.sample_pumps = {"Sample 1": self.pumps.get("Sample 1"), "Sample 2": self.pumps.get("Sample 2"), "Sample 3": self.pumps.get("Sample 3")}
        self.hc_pumps = {"HC Sample": self.pumps.get("HC Sample"), "HC Reference": self.pumps.get("HC Reference")}
        self.solvent_pumps = {"Solvent": self.pumps.get("Solvent")}
        print(f"Pump Setup complete: {self.pumps}")

            
         # Selector Valve Setup
        valve_config = load_valves_config()
        self.valves = {}
        for label, valve in valve_config.items():
            valve_object = SelectorValve(
                port=valve["Port"], 
                baudrate=valve["Baudrate"], 
                name=label, 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                )
            self.valves[label] = valve_object

        self.main_valve = {"Main Selector": self.valves.get("Main Selector")}
        self.pump_valves = {"Pump Selector 1": self.valves.get("Pump Selector 1"), "Pump Selector 2": self.valves.get("Pump Selector 2"), "Pump Selector 3": self.valves.get("Pump Selector 3")}
        print(f"Valve Setup complete: {self.valves}")

        # DAQ Setup 
        daq_config = load_daq_config()
        self.daqs = {}
    
        for label, daq in daq_config.items():
            daq_object = DAQDevice(port_name=daq["Port"], daq_frequency=daq["Frequency"], min_vol=daq["VolumeMin"], max_vol=daq["VolumeMax"])
            self.daqs[label] = daq_object
        print(f"DAQ Setup complete: {self.daqs}")

        #HC Routine Setup
        # NOTE: Does not use a config file for the time being cuz
        # setting one up rn while I'm at the lab is a giant time waster
        self.hc_routine = HCRoutine(
                            daq=self.daqs["HC DAQ"],
                            ref_pump=self.hc_pumps["HC Sample"],
                            sample_pump=self.hc_pumps["HC Reference"]
                            )
        # required values: m1, m2, m3, f1, f2, f3, batch

        # NOTE: Need to add os.makedir in main routine runner before HC Routine is run
        # and general full routine is run since its important to ensure that the directory exists
        # before actually inserting data to it.
        # TODO: Not sure if the data that V/D and other routines use are needed to be saved;
        # maybe ask before end of the day for confirmation on this.

        # VD Routine Setup
        vd_config = load_VD_config()
        vd_sensor = vd_config.get("Sensor")
        vd_exp = vd_config.get("Routine")

        self.vd_routine = VDRoutine(serial_number=vd_sensor["Serial number"], verbose=vd_sensor["Verbose"], track_impedance=vd_sensor["Track impedance"], 
                                    PEAK_CENTER_TOLERANCE_HZ=vd_sensor["Peak center tolerance"], PEAK_WIDTH_TOLERANCE_HZ=vd_sensor["Peak width tolerance"],
                                    PEAK_CENTER_REFERENCE=vd_sensor["Peak center reference"], PEAK_WIDTH_REFERENCE=vd_sensor["Peak width reference"],
                                    )
        print(f"VD Routine Setup complete: {self.vd_routine}")


        # NOTE: VD Config only holds one defined instance of VD for the time being.
        self.flow_rates = []
        # self.test_connections()
        if routine == "VD":
            # Use partial to store functions with their arguments without executing them
            self.add_routine(partial(self.valve_injection_mode, 
                                   self.main_valve["Main Selector"]
                                   ))
            self.add_routine(partial(self.vd_routine.inject_samples, 
                                   list(self.sample_pumps.values()), 
                                   vd_exp["Syringe volume"], 
                                   vd_exp["Injection time"]))
            self.add_routine(partial(self.vd_routine.run_vd_routine, 
                                   vd_exp["Measurements"], 
                                   vd_exp["Batch size"], 
                                   vd_exp["VSTD range"], 
                                   vd_exp["DSTD range"]))
            
        if routine == "HC":
            # NOTE: basically all of the items defined here are MANDATORY values required by the user
            # AKA define it in config.json
            self.add_routine(partial(self.hc_routine.ready_hc))
            self.add_routine(partial(self.hc_routine.run_hc_routine,
                                    density_sample=2000,
                                    m1="A",
                                    m2="B",
                                    m3="C",
                                    f1=self.sample_pumps["Sample 1"].flow_rate,
                                    f2=self.sample_pumps["Sample 2"].flow_rate,
                                    f3=self.sample_pumps["Sample 3"].flow_rate,
                                    batch="TESTING UI",
                                    Mean_V=223,
                                    Mean_D=554,
                                    Mean_T=112,
                                    V_STD=vd_exp["VSTD range"],
                                    D_STD=vd_exp["DSTD range"]
                                     ))

        # finalize the initialization by running the main routine
        # NOTE: Don't run for the time being below so as not to inject any fluids. Temp function to do so
        # self.process_pumps_for_sheets(file_path, start_sheet, end_sheet, num_chemicals, first_cleaning)
        self.safe_run_routines()

        # if routine is empty, then routiens should include just the datagather function.
        # otherwise, configure diff loadouts for the routines that will be hardcoded for now.

    def add_routine(self, routine):
        """
        Adds a routine to the RoutineManager's list of routines to run.
        :param routine: A function or callable that represents a routine to be executed.
        """
        self.routines.append(routine)

    def run_all(self):
        """
        Executes all routines that have been added to the RoutineManager in sequence.
        """
        for routine in self.routines:
            routine.run()


# NOTE: move all of this cleaning to a cleaning routine instead

    def clean_all(self, pump:Pump, pump_valve:SelectorValve, refill_volume=25, inject_volume=20, inject_duration=960, iterations=5, position:int=9):
        # pump num 1 handles solvent so assume pump is passed in
        # first, load in the solvent 
        """
        This function handles the cleaning of the sensors by running the pump through a series of solvent refills, air drying, and sample injections.
        """
        self.refill_solvent(self, pump, refill_volume)

        # put the line into air for x amount of iterations
        for _ in range(iterations):
            self.valve_air_mode(pump_valve, position)
            print('Air started')
            time.sleep(15)
            # call to inject solvent here
            self.inject_solvent(pump, inject_volume, inject_duration)
        self.valve_air_mode(pump_valve, position)
        time.sleep(180)
        self.valve_injection_mode()
        
    def inject_solvent(self, pump:Pump, volume=20, duration=960):
        pump.inject(self, volume, duration=duration)

    # NOTE: these mgiht lowk be useless later but we'll see
    def valve_air_mode(self, valve:SelectorValve, position:int=9):
        valve.move_to(position)
        valve.confirm_position()

    def valve_injection_mode(self, valve:SelectorValve, position:int=3):
        print("Injecting samples...")
        valve.move_to(position)
        valve.confirm_position()

    def valve_solvent_mode(self, valve:SelectorValve, position:int=1):
        valve.move_to(position)
        valve.confirm_position()

    def hc_cleaning(self, hc_pump:Pump, empty_volume, refill_volume, inject_volume):
        """
        This function handles the cleaning of the HC sensors by running the pump through a series of solvent refills, air drying, and sample injections.
        """
        print('HC Cleaning Started')
        hc_pump.fast_empty(empty_volume)
        
        for _ in range(1):
            hc_pump.withdraw(refill_volume)
            time.sleep(1)
            hc_pump.fast_empty(empty_volume)
            time.sleep(0.5)

        for _ in range(1):
            hc_pump.withdraw(refill_volume)
            time.sleep(1)
            hc_pump.inject(inject_volume)
            time.sleep(1)

        for _ in range(1):
            hc_pump.withdraw(refill_volume)
            time.sleep(1)
            hc_pump.inject(inject_volume)
            time.sleep(1)
    
    def hc_cleaning_switch(self, hc_pump:Pump, empty_volume, refill_volume):
        """
        This function handles the cleaning of the HC sensors by running the pump through a series of solvent refills and fast emptying.
        """
        print('HC Cleaning Started')
        hc_pump.fast_empty(empty_volume)

        for _ in range(5):
            hc_pump.withdraw(refill_volume)
            time.sleep(1)
            hc_pump.fast_empty(empty_volume)
            time.sleep(1)

    def refill_solvent(self, pump:Pump, volume=25):
        """
        Given a Pump object which is presumably the dedicated solvent pump, refill
        that pump and its fluids in particular.
        Copies off of the RefillSolvent function in SyringePumps.py
        """
        pump.withdraw(volume * 8)  # Withdraw the specified volume
        print(f"Refilling solvent in pump {pump.pump_num} with {volume} mL.")
    
    def refill_sample(self, volume=200):
        """
        Given a Pump object which is presumably the dedicated sample pump, refill
        that pump and its fluids in particular.
        Copies off of the RefillSample function in SyringePumps.py
        """
        # NOTE: when refilling the sample pump, look into refilling multiple pumps using threading
        sample_pumps = [self.pumps["Sample 1"], self.pumps["Sample 2"], self.pumps["Sample 3"]]
        threads = []

        for pump in sample_pumps:
            thread = threading.Thread(target=pump.withdraw, args=(200))
            threads.append(thread)

        start_threads(threads)
        join_threads(threads)

        # Code below from RefillSample: 
        #   ======
        # threads = []
    
        # # Create threads for each pump withdraw function
        # t1 = threading.Thread(target=PumpWithdrawSample1, args=(200,))
        # t2 = threading.Thread(target=PumpWithdrawSample2, args=(200,))
        # t3 = threading.Thread(target=PumpWithdrawSample3, args=(200,))

        # # Add threads to the list
        # threads.extend([t1, t2, t3])

        # # Start all threads
        # for thread in threads:
        #     thread.start()

        # # Wait for all threads to complete
        # for thread in threads:
        #     thread.join()


    def run_refills_concurrently(self, flowrate1, flowrate2, flowrate3):
        # This class should handle the datagather function which is responsible for
        # sample injections, refills & v/d mesurements, running cP calcuatlions, and cleaning.
        # THAT is my goal. to make it so that all of the other routines can be used here.

        # Parse arguments
        # NOTE: args and the small snippet below are not used in the code

        # NOTE: For now we will hardcode threading, but this will be determined by the routine 
        # manager who will run all of the routines w/ the corresponding tags in parallel.
        """
         This function runs the refilling of solvent and sample concurrently with the V/D measurement routine.
         It ensures that the refilling processes do not block the V/D measurements, allowing for efficient use of time during the experiment.
        """
        routine_threads = []
        routine_threads.append(threading.Thread(target=self.refill_solvent))
        routine_threads.append(threading.Thread(target=self.refill_sample))
        routine_threads.append(threading.Thread(target=self.HC_routine.ready_hc))

        # Start all threads
        start_threads(routine_threads)
        #thread_Water.start()
        print('Refill Started.')
        print('VD Measurement Started')
        # main thread
        # NOTE: Change this to be the VDRoutine
        # NOTE: Add the HCRoutine ready check and initialization here as well  (HC Ready function)
        Mean_D, Mean_V, Mean_T, V_STD, D_STD = self.vd_routine.run_vd_routine(args, flowrate1, flowrate2, flowrate3)

        # Wait for all threads to complete
        join_threads(routine_threads)
        return Mean_D, Mean_V, Mean_T, V_STD, D_STD
    
    def flow_rate_injection(self, pumps: list[Pump] = None, syringe_volume: float = 10, injection_time: float = 1):
        """
        This function handles the debubbling and injection of the samples based on the flow rates set for each pump.
         It calculates the duration of injection based on the flow rate and syringe volume, and runs the debubbling and injection processes concurrently for all pumps provided in the list. If no pumps are provided, it defaults to an empty list and simply runs the injection mode without any pump actions.
         The injection mode is activated at the start of the function, and a message is printed to indicate the start of pumping. After the processes are completed, a message is printed to indicate the stop of pumping. 
        """
        if pumps is None:
            pumps = {}

        injectionmode()
        time.sleep(5)
        print('Pumping started.')
        debubble_threads = []
        injection_threads = []

        for pump in pumps:
            duration = 0
            dist = 0
            
            if pump.flow_rate != 0:
                duration = round(6000 * injection_time / (syringe_volume / pump.flow_rate))
                # NOTE: this is always zero in the pump_flow_rate functions
        
            thread_debubble = threading.Thread(target=pump.debubble, args=(5,dist))
            thread_injection = threading.Thread(target=PumpInjection_pumpSample1, args=(pump.flow_rate, duration))

            debubble_threads.append(thread_debubble)
            injection_threads.append(thread_injection)
        
        start_threads(debubble_threads)
        join_threads(debubble_threads)

        time.sleep(0.1)

        start_threads(injection_threads)
        join_threads(injection_threads)

        print('Pumping stopped.')
    
    def run_base_routines(self):
        """
        This function is for running the preset routines; no adjustments to code needed.
        """
        # TODO: add compositions batches here as well
        folder_name = f"C:/Users/Indus/OneDrive/Desktop/26 Campaign/{self.batch}/"
    # Create the folder
        os.makedirs(folder_name, exist_ok=True)
        data = []
        
        sample_pumps = [self.pumps["Sample 1"], self.pumps["Sample 2"], self.pumps["Sample 3"]]

        for comp in self.composition:
            x1, x2, x3 = comp  # Unpack each composition into x1, x2, x3
            print(f"x1: {x1}, x2: {x2}, x3: {x3}")
            # You can add further processing logic or calculations for x1, x2, x3
            # Example: perform any additional data processing or logging here
            flow_rate_mm_sample1 = round(x1, 3) * 10
            flow_rate_mm_sample2 = round(x2, 3) * 10
            flow_rate_mm_sample3 = round(x3, 3) * 10

            sample_pumps[0].set_flow_rate(flow_rate_mm_sample1)
            sample_pumps[1].set_flow_rate(flow_rate_mm_sample2)
            sample_pumps[2].set_flow_rate(flow_rate_mm_sample3)
            # NOTE: should probably define these pumps better later
            
            # Debubble samples and inject them
            self.flow_rate_injection(pumps=sample_pumps)

            # REFILL & VD MEASUREMENT
            Mean_V, Mean_D, Mean_T, V_STD, D_STD = self.run_refills_concurrently(flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3)
            print(Mean_D)


    def vd_setup(self, flow_rate1, flow_rate2, flow_rate3):
        """
       Initializes the V/D routine and runs it independantly
        """
        sample_pumps = [self.pumps["Sample 1"], self.pumps["Sample 2"], self.pumps["Sample 3"]]
        
        sample_pumps[0].set_flow_rate(flow_rate1)
        sample_pumps[1].set_flow_rate(flow_rate2)
        sample_pumps[2].set_flow_rate(flow_rate3)
            
        # Debubble samples and inject them
        self.flow_rate_injection(pumps=sample_pumps)

        self.refill_sample()
        self.refill_solvent()
        
        self.vd.run_vd_routine()

    # assume vd_setup was passed in to routines which is a collection of functions

    # def process_pumps_for_sheets(self, file_path, sample_pumps:list[Pump], start_sheet=None, end_sheet=None, num_chemicals=11, first_cleaning = True):
    #     prev_chem_pump1 = f'{start_sheet[0]}'
    #     prev_chem_pump2 = f'{start_sheet[1]}'
    #     prev_chem_pump3 = f'{start_sheet[2]}'
    #     # Generate valve maps once
    #     v1_map, v2_map, v3_map = generate_valve_maps(num_chemicals)

    #     sheet_data = get_chemicals_and_compositions(file_path)
    #     sheet_names = list(sheet_data.keys())
    #     print(sheet_names)

    #     if start_sheet is not None:
    #         if start_sheet not in sheet_names:
    #             raise ValueError(f"Sheet '{start_sheet}' not found in Excel file.")
    #         start_index = sheet_names.index(start_sheet)
    #         print(start_index)
    #         if start_index == 0:
    #             start_index_adj =0
    #         else:
    #             start_index_adj =start_index-1

    #         sheet_names = sheet_names[start_index_adj:]  # process from start_sheet onwards
    #     if end_sheet is not None:
    #         if end_sheet not in sheet_names:
    #             raise ValueError(f"Sheet '{end_sheet}' not found in Excel file.")
    #         end_index = sheet_names.index(end_sheet) + 1
    #     else:
    #         end_index = len(sheet_names)

    #     # Slice sheet list from start to end (inclusive of end_sheet)
    #     sheet_names = sheet_names[start_index:end_index]
    #     print(sheet_names)

    #     for sheet in sheet_names:
    #         data = sheet_data[sheet]
    #         chems = data['chemicals']
    #         compositions = data['compositions']

    #         print(f"Processing sheet '{sheet}' with chemicals: {chems}")
    #         print(f"Compositions: {compositions}")
        
    #         chems = (chems + [None]*3)[:3]  # Ensure 3 chemicals
        
    #         #changed1 = pump1_assign_chemical(chems[0], v1_map) if chems[0] else False
    #         #changed2 = pump2_assign_chemical(chems[1], v2_map) if chems[1] else False
    #         #changed3 = pump3_assign_chemical(chems[2], v3_map) if chems[2] else False
    #         if first_cleaning:
    #             changed1, changed2, changed3 = assign_chemicals(chems, v1_map, v2_map, v3_map, prev_chem_pump1, prev_chem_pump2, prev_chem_pump3)

    #             print(f" Pump 1 chemical: {chems[0]}, changed: {changed1}")
    #             print(f" Pump 2 chemical: {chems[1]}, changed: {changed2}")
    #             print(f" Pump 3 chemical: {chems[2]}, changed: {changed3}")
    #             print()
        
    #             # If any of the pumps changed, perform cleaning
    #             # If any of the pumps changed, perform cleaning
    #             if True:
    #                 print('VD Cleaning Started.')
    #                 cleaning_part1()
    #                 print('HC Cleaning Started.')
    #                 t1 = threading.Thread(target=Cleaning_part2_switch)
    #                 t2 = threading.Thread(target=RefillSample)
    #                 t3 = threading.Thread(target=RefillSolvent)
    #                 # Start both threads
    #                 t1.start()
    #                 t2.start()
    #                 t3.start()

    #                 # Wait for both to finish
    #                 t1.join()
    #                 t2.join()
    #                 t3.join()

    #                 print('Sample Debubble Started.')
    #                 t1 = threading.Thread(target=Debubble_pumpSample1, args=(20, 500))
    #                 t2 = threading.Thread(target=Debubble_pumpSample2, args=(20, 500))
    #                 t3 = threading.Thread(target=Debubble_pumpSample3, args=(20, 500))

    #                 t1.start()
    #                 t2.start()
    #                 t3.start()

    #                 t1.join()
    #                 t2.join()
    #                 t3.join()
    #                 print('Sample Refill Started.')
    #                 RefillSample()
    #                 time.sleep(30)
            
    #         self.run_routines(compositions, sheet, chems[0], chems[1], chems[2])
    #         time.sleep(20)
    #         first_cleaning = True

    def run_routines(self, compositions, sheet, chems0, chems1, chems2):
        for comp in compositions:
            x1, x2, x3 = comp  # Unpack each composition into x1, x2, x3
            print(f"x1: {x1}, x2: {x2}, x3: {x3}")
            # You can add further processing logic or calculations for x1, x2, x3
            # Example: perform any additional data processing or logging here
            flow_rate_mm_sample1 = round(x1, 3) * 10
            flow_rate_mm_sample2 = round(x2, 3) * 10
            flow_rate_mm_sample3 = round(x3, 3) * 10
            
            self.sample_pumps[0].set_flow_rate(flow_rate_mm_sample1)
            self.sample_pumps[1].set_flow_rate(flow_rate_mm_sample2)
            self.sample_pumps[2].set_flow_rate(flow_rate_mm_sample3)

            # NOTE: the unfortunate nested loop

            for routine in self.routines:
                # Handle partial functions which have .func attribute
                if hasattr(routine, 'func'):
                    print(f"Running {routine.func.__name__}...")
                    routine()  # Partial functions already have their args bound
                else:
                    # Regular functions that expect the standard arguments
                    print(f"Running {routine.__name__}...")
                    routine(compositions, sheet, chems0, chems1, chems2)

    def safe_run_routines(self):
        """
        This function runs the routines that have been added to the RoutineManager in a safe manner, ensuring that necessary preconditions are met before execution.
        For example, it can set flow rates for sample pumps before running routines that depend on those flow rates, and it can handle any exceptions that may arise during routine execution to prevent crashes and provide informative error messages.
        """
        flow_rate_mm_sample1 = round(10, 3) * 10
        flow_rate_mm_sample2 = round(10, 3) * 10
        flow_rate_mm_sample3 = round(10, 3) * 10
        
        self.sample_pumps["Sample 1"].set_flow_rate(flow_rate_mm_sample1)
        self.sample_pumps["Sample 2"].set_flow_rate(flow_rate_mm_sample2)
        self.sample_pumps["Sample 3"].set_flow_rate(flow_rate_mm_sample3)

        for routine in self.routines:
            # Handle partial functions which have .func attribute
            if hasattr(routine, 'func'):
                print(f"Running {routine.func.__name__}...")
                routine()

    def test_connections(self):
        """
         This function is for testing the connections to the pumps, valves, and DAQ devices. It can be used to ensure that all equipment is properly connected and communicating before running the main routines.
        """
        print("Testing Connections")
        # pump = self.pumps.get("Sample 1")
        # label = "Sample 1"
        for label, pump in self.sample_pumps.items():
            print(f"Parsing {label}")
            # pump.debubble(5, 0)
            # pump.inject(pump.flow_rate, 800)
            # pump.full_injection(25, 0)
            pump.withdraw(100)
        


print("Running main routine:")
main_routine = RoutineManager(routine="HC")

