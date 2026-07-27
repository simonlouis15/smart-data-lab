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
    START_pump2_HC, PumpInjection_pump2_HC, Stop_pump2_HC
)

#initialize viscosity and density array:
Viscosity = []
Density = []
Trial = []
data = []
signal.signal(signal.SIGINT, cleanup)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, cleanup) # Handle termination signal

# Simplified Logger class
class LoggerNI:
    def __init__(self, port_name, daq_frequency):
        self.task = nidaqmx.Task()
        self.task.ai_channels.add_ai_voltage_chan(port_name, min_val=-0.08, max_val=0.08)
        self.task.timing.cfg_samp_clk_timing(rate=daq_frequency, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
        
    def read_voltage(self):
        return self.task.read()
        
    def close(self):
        self.task.close()



# Functions for stabilization check
def within_linient_segment_variation_limit(array, abs_threshold):
    overall_mean = np.mean(array)
    count_within_threshold = 0
    for seg_mean in array:
        abs_diff = abs(seg_mean - overall_mean) 
        if abs_diff <= abs_threshold:
            count_within_threshold +=1
    if count_within_threshold >= 4:
        return True
    else:
        return False

def map_chemicals(chem1, chem2, chem3):
    mapping = {'A': 'Dimethyl Malonate',
               'B': 'Cyclohexyl Methacrylate',
               'C': 'Cyclohexyl Acetate',
               'D': 'Octyl Octanoate',
               'E': 'Propylene Glycol Propyl Ether',
               'F': '1,4-Dichlorobutane',
               'G': '1-Butanol',
               'H': 'Diethyl Malonate',
               'I': 'Ethyl Laurate',
               'J': 'Ethyl 4-Methylbenzoate',
               'K': '2,6-Dimethyl-4-Heptanone',
               'L': 'Ethyl Acetoacetate',
               'M': 'Ethyl Levulinate',
               'N': 'Isoamyl Isovalerate',
               'O': 'Cuminaldehyde',
               'P': 'Cyclohexyl Butyrate',
               'Q': '2-Butanol',
               'R': '2-Pentanol',
               'S': '3-Pentanol',
               'T': 'N,N Diethyl Hydroxyamine',
               'U': '3-Methyl 2-Butanol',
               'V': 'Y-Nonanoic Lactone',
               'W': '2-Nonanone',
               'X': 'Diethylene Glycol Monoethyl Ether Acetate',
               'Y': 'Acetophenone',
               'Z': 'Phenyl Acetate'}
    return mapping[chem1], mapping[chem2], mapping[chem3]


# Main experiment function
def run_experiment(density_sample,chem1,chem2,chem3,f1,f2,f3,Mean_V, Mean_D, Mean_T, V_STD, D_STD,batch,tc):
    m1, m2, m3 = map_chemicals(chem1, chem2, chem3)
    print('HC measurement started.')
    # Equipment initialization
    daq_freq = 3
    daq = LoggerNI("NI9210/ai0", daq_freq)
 

    # Experiment parameters
    exp_step_duration = 120  # Duration for each step in seconds
    ref_pump_rate = 0.15  # Reference pump injection rate in mL/min
    exp_sample_pump_rates = [0, 0.2, 0.3, 0.4]  # Removed last zero flow rate
    exp_Protocol = []
    for rate in exp_sample_pump_rates:
        exp_Protocol.append([rate, ref_pump_rate if rate != 0 else 0, exp_step_duration])

    # Smart Injection Hyperparameters
    seg_step_duration = 10  # Duration of each segment in seconds
    num_consecutive_seg = 5
    max_num_seg = 15
    segment_variation_abs = 0.4e-6 # Threshold for stabilization check in percent

    step_data_4analysis = [False] * len(exp_Protocol)
    failed_flow_rates = []  # To track which flow rates failed stabilization
    passed_flow_rates = []  # To track which flow rates passed stabilization

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
   #plt.show()

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

    # After collecting data, filter the data for regression by excluding failed flow rates
    valid_indices = [i for i in range(len(step_data_4analysis)) if step_data_4analysis[i] is not False]

    if len(valid_indices) >= 2:
        try:
            # Identify baseline steps (zero flow rate) with valid data
            baseline_steps = [i for i in valid_indices if exp_Protocol[i][0] == 0]

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

                    #density_sample = 672.9  # Replace with actual sample density (kg/m^3)
                    density_ref = 988.8     # Replace with actual reference density (kg/m^3)
                    heatCapacity_ref = 4176.5  # Replace with actual reference heat capacity (J/(kg·K))
                    heatCapacity_sample_ErrorCalc = 1968.9

                    heatCapacity_sam = (ref_pump_rate * heatCapacity_ref * density_ref) / (density_sample * intercept)
                    Error=(heatCapacity_sam-heatCapacity_sample_ErrorCalc)/heatCapacity_sample_ErrorCalc*100
                    print(f"Heat Capacity of Sample = {heatCapacity_sam:.8g} J/(kg·K)")
                    print("Error=",Error)

                    #print(f"Slope: {slope}")
                    #print(f"Intercept: {intercept}")

                    # Save regression data
                  
                    regression_data = pd.DataFrame({
                        'Sample Pump Rate [mL/min]': sample_pump_rates.flatten(),
                        'Step Average Voltage [V]': [step_data_4analysis[i] for i in sample_flow_steps],
                        'Signal [V]': signal.flatten()
                    })

                    # Add Heat Capacity and Error to the regression data
                    regression_data['Heat Capacity [J/(kg·K)]'] = heatCapacity_sam
                    regression_data['Error [%]'] = Error

                    # Save the updated DataFrame to the Excel file
                    #regression_data.to_excel('C:/Users/Indus/OneDrive/Desktop/Hanie/Dec12/water-heptane4_regression_data.xlsx', index=False)
                    #print("Regression data, including heat capacity and error, saved successfully.")


                    # Save all step averages
                    all_step_averages = pd.DataFrame({
                        'Experiment Step': valid_indices,
                        'Sample Pump Rate [mL/min]': [exp_Protocol[i][0] for i in valid_indices],
                        'Average Voltage [V]': [step_data_4analysis[i] for i in valid_indices]
                    })

                    all_step_averages.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-water-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}_step_averages.xlsx', index=False)
                    print("Step averages saved successfully.")
                else:
                    heatCapacity_sam = 0
                    Error=0
                    print("Not enough data points for regression.")
            else:
                print("Baseline is missing. Cannot perform regression.")
        except Exception as e:
            print(f"Regression failed: {e}")
    else:
        heatCapacity_sam = 0
        Error=0
        print("Not enough valid data points to perform regression.")
    #time.sleep(200)
    return heatCapacity_sam, Error


# Main experiment function
def run_experiment2(density_sample,chem1,chem2,chem3,f1,f2,f3,Mean_V, Mean_D, Mean_T, V_STD, D_STD,Cp,batch, data, tc, T_TC, EC):
    m1, m2, m3 = map_chemicals(chem1, chem2, chem3)
    if Cp <0 or Cp==0: 
        time.sleep(200)
        print('HC measurement started.')
        # Equipment initialization
        daq_freq = 3
        daq = LoggerNI("NI9210/ai0", daq_freq)
 

        # Experiment parameters
        exp_step_duration = 120  # Duration for each step in seconds
        ref_pump_rate = 0.15  # Reference pump injection rate in mL/min
        exp_sample_pump_rates = [0, 0.2, 0.3, 0.4]  # Removed last zero flow rate
        exp_Protocol = []
        for rate in exp_sample_pump_rates:
            exp_Protocol.append([rate, ref_pump_rate if rate != 0 else 0, exp_step_duration])

        # Smart Injection Hyperparameters
        seg_step_duration = 10  # Duration of each segment in seconds
        num_consecutive_seg = 5
        max_num_seg = 15
        segment_variation_abs = 0.4e-6 # Threshold for stabilization check in percent

        step_data_4analysis = [False] * len(exp_Protocol)
        failed_flow_rates = []  # To track which flow rates failed stabilization
        passed_flow_rates = []  # To track which flow rates passed stabilization

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
        #plt.show()

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
        df.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-water1-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}.xlsx', index=False)

        # After collecting data, filter the data for regression by excluding failed flow rates
        valid_indices = [i for i in range(len(step_data_4analysis)) if step_data_4analysis[i] is not False]

        if len(valid_indices) >= 2:
            try:
                # Identify baseline steps (zero flow rate) with valid data
                baseline_steps = [i for i in valid_indices if exp_Protocol[i][0] == 0]

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

                        #density_sample = 672.9  # Replace with actual sample density (kg/m^3)
                        density_ref = 988.8     # Replace with actual reference density (kg/m^3)
                        heatCapacity_ref = 4176.5  # Replace with actual reference heat capacity (J/(kg·K))
                        heatCapacity_sample_ErrorCalc = 1968.9

                        heatCapacity_sam = (ref_pump_rate * heatCapacity_ref * density_ref) / (density_sample * intercept)
                        Error=(heatCapacity_sam-heatCapacity_sample_ErrorCalc)/heatCapacity_sample_ErrorCalc*100
                        print(f"Heat Capacity of Sample = {heatCapacity_sam:.8g} J/(kg·K)")
                        print("Error=",Error)

                        #print(f"Slope: {slope}")
                        #print(f"Intercept: {intercept}")

                        # Save regression data
                  
                        regression_data = pd.DataFrame({
                            'Sample Pump Rate [mL/min]': sample_pump_rates.flatten(),
                            'Step Average Voltage [V]': [step_data_4analysis[i] for i in sample_flow_steps],
                            'Signal [V]': signal.flatten()
                        })

                        # Add Heat Capacity and Error to the regression data
                        regression_data['Heat Capacity [J/(kg·K)]'] = heatCapacity_sam
                        regression_data['Error [%]'] = Error

                        # Save the updated DataFrame to the Excel file
                        #regression_data.to_excel('C:/Users/Indus/OneDrive/Desktop/Hanie/Dec12/water-heptane4_regression_data.xlsx', index=False)
                        #print("Regression data, including heat capacity and error, saved successfully.")


                        # Save all step averages
                        all_step_averages = pd.DataFrame({
                            'Experiment Step': valid_indices,
                            'Sample Pump Rate [mL/min]': [exp_Protocol[i][0] for i in valid_indices],
                            'Average Voltage [V]': [step_data_4analysis[i] for i in valid_indices]
                        })

                        all_step_averages.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}_step_averages.xlsx', index=False)
                        print("Step averages saved successfully.")
                    else:
                        heatCapacity_sam=0
                        print("Not enough data points for regression.")
                else:
                    print("Baseline is missing. Cannot perform regression.")
            except Exception as e:
                print(f"Regression failed: {e}")
        else:
            heatCapacity_sam=0
            print("Not enough valid data points to perform regression.")

        if heatCapacity_sam!=0 and Cp!=0:
            final_Cp=(heatCapacity_sam+Cp)/2
        elif heatCapacity_sam!=0 and Cp==0:
            final_Cp=heatCapacity_sam
        else:
            final_Cp=Cp

        data.append( {m1: f1,
                m2: f2,
                m3: f3,
                'Mean Viscosity (cp)': Mean_V,
                'Mean Density (g/mL)': Mean_D,
                'Mean T': Mean_T,
                'std_vis':V_STD,
                'std_den':D_STD,
                'Cp_avg':final_Cp,
                'Cp_1':Cp,
                'Cp_2':heatCapacity_sam,
                'difference':((heatCapacity_sam-Cp)/final_Cp),
                'thermal_conductivity':tc,
                'EC':EC})
                
    
        VDCp = pd.DataFrame(data)
        VDCp.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-Test3_VD+HC_{m1}+{m2}+{m3}_{now}.xlsx', index=False)

        return final_Cp, Error
    else:
        now=date.today()
        timenow=datetime.now()
        data.append( {m1: f1,
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
                'difference':'---',
                'thermal_conductivity':tc,
                'T_TC':T_TC,
                'EC':EC
        })
        VDCp = pd.DataFrame(data)
        VDCp.to_excel(f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/{batch}-Test3_VD+HC_{m1}+{m2}+{m3}_{now}.xlsx', index=False)


