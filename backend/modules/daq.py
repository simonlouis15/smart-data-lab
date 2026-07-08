"""
============================================
Data Aqcuisition (DAQ) Device Class (subclass of serial device)
============================================

Defines a class for handling NI DAQ devices used for voltage measurements in the heat capacity experiment.

Attributes:
    port_name (str): The DAQ channel name/port (default: "NI9210/ai0")
    daq_frequency (int): Sampling frequency in Hz (default: 3 Hz)

Includes initialization, voltage reading, stabilization checking, and data collection functions.
"""

import time
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)

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