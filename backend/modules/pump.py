'''
============================================
Pump Device Class (subclass of serial device)
============================================

Defines pump-specific commands and functions for controlling the Hamiltonian syringe pumps.

Attributes:
    port (str): Serial port the pump is connected to.
    pump_num (int): Identifier for the pump (e.g., 1, 2, 3).
    name (str): Name of the pump for logger purposes.
    flow_rate (float): Initial flow rate for the pump (default 0). Note: flow rate is typically set via specific commands, so this may just be a stored attribute rather than an active setting on initialization
    others args: Serial communication parameters.

Requires pump number, port, and optional parameters like flow rate and baud rate. Provides functions for initializing the pump, sending commands, waiting for readiness, and performing injections.
'''

import time
from loguru import logger

from modules.serial_device import SerialDevice
from src.constants import STOP_ALL_ACTIONS

# NOTE: the things the pump does and the fluids the pumps controle are adjustable in 
# the routines or smthn; shouldn't be in pumps definition 
# pump data for mass initialization and overall device definition can be passed in as a csv or defined manually in the app.
# scan
# NOTE: pumps should start with 3 defined pumps following the definitions in the code
# NOTE: need to fix the bg of the container of the pumps to be lighter gray, add typing to the input fields + ensure that ppl can't define an empty pump object

class Pump(SerialDevice):
    def __init__(
        self,
        port,
        pump_num: int,
        name: str,
        flow_rate=0,
        baudrate: int = 9600,
        **serial_kwargs,
    ):
        super().__init__(port, baudrate, name, **serial_kwargs)
        self.pump_num = pump_num
        self.flow_rate = flow_rate

    def send_command(self, command):
        # NOTE: What if I stop all commands before sending another here instead?
        # I.e., send command STOP_ALL_ACTIONS to stop all actions before sending a new command
        if not (self.pump_num):
            return

        try: 
            full_cmd = f"/{self.pump_num}{command}R\r\n"
            self.write(full_cmd)
            time.sleep(0.5)
            self.wait_until_ready()
            time.sleep(0.5)
            self.write(full_cmd)
            logger.info("Success reading from pump")
        except:
            logger.error("Error reading from pump")
        
        # Untouched (old) code below:
        # while True:
        #     try:
        #         #TODO: (logger related) print ("Attempt to Read")
        #         time.sleep(0.5)
        #         readOut = serSample1.readline().decode("utf-8")
        #         time.sleep(0.5)
        #         #TODO: (logger related) print ("Reading: ", readOut) 
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
        # NOTE: not sure why its stuck sending 90 million commands when it should already be ready
        """
        Blocks until the pump is ready to receive the next command.

        It sends the 'F' (status) command and checks the response. Loop continues until
        the pump returns a status that is NOT '@' (busy) or 'o' (moving).
        """
        response = "@"
        while("@" in response or "o" in response):
            command = f"/{self.pump_num}FR\r\n"
            self.write(command)
            time.sleep(0.5)
            response = self.read()
            logger.info(f"Pump {self.pump_num} ready status: {response}")
            

    def inject(self, flow_rate, position=0):
        
        cmd = f"EV{int(flow_rate * 20)}A{position}"
        
        self.send_command(STOP_ALL_ACTIONS)
        self.send_command(cmd)

    # TODO: look into if we need these fast or slow injections or if we can just define these
    # functions inside of the routines when we get there.
    def full_injection(self, volume_ml: float, accel: int):
        """
        Controlled injection with specified acceleration.
        """
        self.send_command(STOP_ALL_ACTIONS)
        volume_units = int(volume_ml * 20)
        self.send_command(f"EV{volume_units}A{accel}")

    def fast_empty(self, flush_rate: float):
        """
        Fast emptying using IV command at A0.
        """
        cmd = f"IV{int(flush_rate * 20)}A0"

        self.send_command(STOP_ALL_ACTIONS)
        self.send_command(cmd)

    def withdraw(self, flow_rate):

        cmd = f"OV{int(flow_rate * 20)}A6000"     

        self.send_command(STOP_ALL_ACTIONS)
        self.send_command(cmd)

    def debubble(self, volume, duration):
        self.send_command(STOP_ALL_ACTIONS)
        self.send_command(f"IV{int(volume * 20)}d{duration}")

    def set_flow_rate(given_flow_rate):
        # line 1037 for pump_flow_rate
        """Assumes that valve has been set to pos 3 (is that rlly safe idk)
        Based off of the function pump_flow_rate
        """
        pass
    def clean_pump(self, flush_rate=10, withdraw_rate=30):
        """
        Based off of PumpCleaning_pumpSample1
        """
        # NOTE: Why are we even withdrawing to begin with? whats this for and what are we withdrawing
        self.fast_empty(flush_rate)
        self.wait_until_ready()
        self.withdraw(withdraw_rate)
        self.wait_until_ready()
        self.fast_empty(flush_rate)
