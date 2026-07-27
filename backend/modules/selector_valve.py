'''
============================================
Selector Valve Class (subclass of serial device)
============================================

Controls a Hamilton selector valve via serial communication.

Attributes:
    port (str): Serial port the valve is connected to.
    baudrate (int): Baud rate for communication (default 9600).
    valve_positions (int): Total number of positions (default 10).
    current_position (int): Last known valve position.

Includes setup for access to cleaning functions like air and solvent cleaning.
In this case, experiment uses 3-4 connections which houses the 3 pumps, air, and an output valve
'''

import time
import logging

from modules.serial_device import SerialDevice

logging.basicConfig(level=logging.INFO)

class SelectorValve(SerialDevice):
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