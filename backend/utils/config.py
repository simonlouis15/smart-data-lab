import json
from pathlib import Path

from loguru import logging

"""
Helper functions to return the parameters for the requested device from config.json
"""

config_path = Path(__file__).parent.parent / "config" / "config.json"

def load_pump_config():
    pumps = {}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        pumps_data = config.get("Devices", {}).get("Pumps", {})

        for label, pump in pumps_data.items():
            pumps[label] = pump

        return pumps

    except Exception as e:
        logging.ERROR(f"Could not load config.json: {e}")

def load_valves_config():
    valves = {}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        valves_data = config.get("Devices", {}).get("Selector Valves", {})

        for label, valve in valves_data.items():
            valves[label] = valve

        return valves

    except Exception as e:
        logging.ERROR(f"Could not load config.json: {e}")

def load_daq_config():
    daqs = {}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        daqs_data = config.get("Devices", {}).get("DAQs", {})

        for label, daq in daqs_data.items():
            daqs[label] = daq

        return daqs

    except Exception as e:
        logging.ERROR(f"Could not load config.json: {e}")


def load_VD_config():
    vd_config = {}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        vd_routine = config.get("VD Routine", {}).get("Base Routine")
        
        vd_config["Sensor"] = vd_routine.get("Sensor", {})
        vd_config["Routine"] = vd_routine.get("Routine", {})

        return vd_config

    except Exception as e:
        logging.ERROR(f"Could not load VD config from config.json: {e}")
        return None