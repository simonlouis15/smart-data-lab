from loguru import logger
import argparse

import serial
import serial.tools.list_ports
import nidaqmx

from src import Pump, SelectorValve
from src.constants import (
  INJECTION_MODE,
  AIR_MODE,
  SOLVENT_MODE,
  QUERY_CURRENT_POS,
  CONFIRM_POS,
  STOP_PUMP
)

logger.add("app.log", level="DEBUG")

def str2bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


"""
Basic pump controls

Arguments:
    port: (string) serial port the pump is connected to, e.g. 'COM10'
    pump_num: (int) pump identifier used in the Hamilton protocol string
    name: (string) human readable pump name (from config.json), used for logging
    option: (string) one of 'initialize', 'withdraw_sample', 'inject_sample', 'flush_to_waste'
    flow_rate: (float) ml/min
    syringe_volume: (float) ml
    baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, dsrdtr, write_timeout:
        serial connection parameters, sourced from the pump's entry in config.json
"""
def pump_controls(args):
    logger.info("Selecting controls for pumps...")
    logger.info(f"Port: {args.port}")
    logger.info(f"Pump Num: {args.pump_num}")
    logger.info(f"Name: {args.name}")
    logger.info(f"Option: {args.option}")
    logger.info(f"Flow Rate: {args.flow_rate}")
    logger.info(f"Syringe Volume: {args.syringe_volume}")

    pump = Pump(
        port=args.port,
        pump_num=int(args.pump_num),
        name=args.name,
        flow_rate=float(args.flow_rate),
        baudrate=int(args.baudrate),
        bytesize=int(args.bytesize),
        parity=args.parity,
        stopbits=float(args.stopbits),
        timeout=float(args.timeout),
        xonxoff=str2bool(args.xonxoff),
        rtscts=str2bool(args.rtscts),
        dsrdtr=str2bool(args.dsrdtr),
        write_timeout=float(args.write_timeout) if args.write_timeout is not None else None,
    )

    syringe_volume = float(args.syringe_volume) if args.syringe_volume is not None else None

    match args.option:
        case 'initialize':
            logger.info("Initializing pump")
            pump.wait_until_ready()
            pump.initialize(syringe_volume)
        case 'withdraw_sample':
            logger.info("Withdrawing sample")
            pump.wait_until_ready()
            pump.withdraw(syringe_volume)
        case 'inject_sample':
            logger.info("Injecting sample")
            pump.wait_until_ready()
            pump.inject(syringe_volume)
        case 'flush_to_waste':
            logger.info("Cleaning pump")
            pump.wait_until_ready()
            pump.clean_pump()

    pump.ser.close()

def valve_controls(args):
    logger.info("Selecting controls for selector valve...")

    valve = SelectorValve(
        port=args.port,
        baudrate=int(args.baudrate),
        valve_positions=[INJECTION_MODE, AIR_MODE, SOLVENT_MODE],
    )

    mode_map = {
        "sample": INJECTION_MODE,
        "air": AIR_MODE,
        "solvent": SOLVENT_MODE,
    }

    position = mode_map[args.mode]

    logger.info(f"Setting valve mode '{args.mode}' -> position {position}")

    valve.setup()
    valve.move_to(position)

    response = valve.confirm_position()

    logger.info(f"Valve confirmation response: {response}")

    valve.ser.close()

def main():
    parser = argparse.ArgumentParser(description="SDL control cli tool")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Initialize Pump
    pump = subparsers.add_parser("pump", help="Pump controls")
    pump.add_argument("--name", required=True)

    pump.add_argument("--port", required=True)
    pump.add_argument("--pump_num", required=True)
    pump.add_argument("--flow_rate", required=True)
    pump.add_argument("--baudrate", required=False, default=9600)
    pump.add_argument("--bytesize", required=False, default=8)
    pump.add_argument("--parity", required=False, default="none")
    pump.add_argument("--stopbits", required=False, default=1)
    pump.add_argument("--timeout", required=False, default=1)
    pump.add_argument("--xonxoff", required=False, default="false")
    pump.add_argument("--rtscts", required=False, default="false")
    pump.add_argument("--dsrdtr", required=False, default="false")
    pump.add_argument("--write_timeout", required=False, default=1)

    # Pump command
    pump.add_argument("--option", required=True,
                     choices=["initialize", "withdraw_sample", "inject_sample", "flush_to_waste"])
    pump.add_argument("--syringe_volume", required=False)

    pump.set_defaults(func=pump_controls)

    # Initialize valve
    valve = subparsers.add_parser("valve", help="Selector valve controls")
    valve.add_argument("--name", required=True)

    valve.add_argument("--port", required=True)
    valve.add_argument("--baudrate", required=False, default=9600)
    valve.add_argument("--bytesize", required=False, default=8)
    valve.add_argument("--parity", required=False, default="none")
    valve.add_argument("--stopbits", required=False, default=1)
    valve.add_argument("--timeout", required=False, default=1)
    valve.add_argument("--xonxoff", required=False, default="false")
    valve.add_argument("--rtscts", required=False, default="false")
    valve.add_argument("--dsrdtr", required=False, default="false")
    valve.add_argument("--write_timeout", required=False, default=1)

    # Valve command
    valve.add_argument("--mode", required=True,
                    choices=["sample", "air", "solvent"])

    valve.set_defaults(func=valve_controls)

    args = parser.parse_args()
    args.func(args)
    

"""
def main():
    logger.info("=== DEVICE DISCOVERY ===")

    # List all serial ports
    logger.info("\nSerial Ports:")
    for port in serial.tools.list_ports.comports():
        logger.info(f"  {port.device}: {port.description}")

    # List DAQ devices
    logger.info("\nDAQ Devices:")
    try:
        system = nidaqmx.system.System.local()
        for device in system.devices:
            logger.info(f"  {device.name}: {device.product_type}")
            logger.info(f"    AI Channels: {list(device.ai_physical_chans)}")
    except:
        logger.error("  No DAQ devices found or NI-DAQmx not installed")

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
            logger.info(f"DAQ voltage reading: {voltage:.6f} V")

            # Read multiple samples
            task.timing.cfg_samp_clk_timing(rate=10)
            voltages = task.read(number_of_samples_per_channel=10)
            logger.info(
                f"DAQ 10 samples: min={min(voltages):.6f}V, max={max(voltages):.6f}V"
            )

        logger.info("✓ DAQ test successful")

    except Exception as e:
        logger.error(f"✗ DAQ test failed: {e}")
"""

if __name__ == "__main__":
    main()
