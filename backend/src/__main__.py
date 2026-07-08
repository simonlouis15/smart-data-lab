from loguru import logging

import serial
import serial.tools.list_ports
import nidaqmx

from src import DAQDevice, Pump, SelectorValve
from constants import (
  INJECTION_MODE,
  AIR_MODE,
  SOLVENT_MODE,
  QUERY_CURRENT_POS,
  CONFIRM_POS,
  STOP_PUMP
)

"""
NOTE: more device discovery tests can be run in device_discover.py. 
Look into this file for more details and things to test out. 
NOTE: Rememver to look through the device intialization code in lab_devices.py 
and spot out any comments or notes that might help guide what else to test/look into.
"""


def main():
    logging.INFO("=== DEVICE DISCOVERY ===")

    # List all serial ports
    logging.INFO("\nSerial Ports:")
    for port in serial.tools.list_ports.comports():
        logging.INFO(f"  {port.device}: {port.description}")

    # List DAQ devices
    logging.INFO("\nDAQ Devices:")
    try:
        system = nidaqmx.system.System.local()
        for device in system.devices:
            logging.INFO(f"  {device.name}: {device.product_type}")
            logging.INFO(f"    AI Channels: {list(device.ai_physical_chans)}")
    except:
        logging.ERROR("  No DAQ devices found or NI-DAQmx not installed")

    # Initialize lab devices
    selectorValve = SelectorValve(port="COM9", name="Main Selector Valve")

    pumpSample1 = Pump(port="COM10", pump_num=1, name="Pump 1")
    pumpSample2 = Pump(port="COM7", pump_num=2, name="Pump 2")
    pumpHCSample = Pump(port="COM14", pump_num=3, name="HC Sample Pump")
    pumpHcReference = Pump(port="COM5", pump_num=4, name="HC Reference Pump")
    pumpSolvent = Pump(port="COM6", pump_num=5, name="Solvent Pump")

    # daqSensor = DAQDevice(port="COM8", name="DAQ Device")

    # Test acknowledgment and Multiposition Mode
    selectorValve.setup()
    selectorValve.move_to(INJECTION_MODE)
    selectorValve.confirm_position()
    selectorValve.move_to(AIR_MODE)
    selectorValve.confirm_position()
    selectorValve.move_to(SOLVENT_MODE)
    selectorValve.confirm_position()
    selectorValve.ser.close()

    # Test pump 1 ready status and positin query
    pumpSample1.wait_until_ready()
    pumpSample1.send_command(QUERY_CURRENT_POS)
    pumpSample1.send_command(CONFIRM_POS)
    pumpSample1.send_command(STOP_PUMP)
    pumpSample1.ser.close()

    # Test pump 2 ready status and position query
    pumpSample2.wait_until_ready()
    pumpSample2.send_command(QUERY_CURRENT_POS)
    pumpSample2.send_command(CONFIRM_POS)
    pumpSample2.send_command(STOP_PUMP)
    pumpSample2.ser.close()

    # Test HC pump ready status and position query
    pumpHCSample.wait_until_ready()
    pumpHCSample.send_command(QUERY_CURRENT_POS)
    pumpHCSample.send_command(CONFIRM_POS)
    pumpHCSample.send_command(STOP_PUMP)
    pumpHCSample.ser.close()

    # Test HC reference pump ready status and position query
    pumpHcReference.wait_until_ready()
    pumpHcReference.send_command(QUERY_CURRENT_POS)
    pumpHcReference.send_command(CONFIRM_POS)
    pumpHcReference.send_command(STOP_PUMP)
    pumpHcReference.ser.close()

    # Test solvent pump ready status and position query
    pumpSolvent.wait_until_ready()
    pumpSolvent.send_command(QUERY_CURRENT_POS)
    pumpSolvent.send_command(CONFIRM_POS)
    pumpSolvent.send_command(STOP_PUMP)
    pumpSolvent.ser.close()

    # Test DAQ Device
    try:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                "NI9210/ai0", min_val=-0.08, max_val=0.08
            )

            # Read single voltage value
            voltage = task.read()
            logging.INFO(f"DAQ voltage reading: {voltage:.6f} V")

            # Read multiple samples
            task.timing.cfg_samp_clk_timing(rate=10)
            voltages = task.read(number_of_samples_per_channel=10)
            logging.INFO(
                f"DAQ 10 samples: min={min(voltages):.6f}V, max={max(voltages):.6f}V"
            )

        logging.INFO("✓ DAQ test successful")

    except Exception as e:
        logging.ERROR(f"✗ DAQ test failed: {e}")


if __name__ == "__main__":
    main()
