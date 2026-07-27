"""
============================================
Serial Devices Base Class
============================================

Base classes defining devices used in the project. Initializes serial device connection with configurable parameters.

Attributes:
    port = communication port of the device that it is defined to
    baudrate = speed of data transmissions in the system (set to 9600 by default)

This is the base device class for all serially connected devices (e.g., selector valve, pumps).
It provides basic read/write functionality and can be extended with device-specific commands in child classes.
"""

import serial
import time
import logging

logging.basicConfig(level=logging.INFO)


class SerialDevice:
    def __init__(
        self,
        port,
        baudrate=9600,
        name="",
        bytesize=8,
        parity=serial.PARITY_NONE,
        stopbits=1,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
        write_timeout=None,
    ):

        parity_map = {
            "none" : serial.PARITY_NONE,
            "even" : serial.PARITY_EVEN,
            "odd" : serial.PARITY_ODD,
            "mark" : serial.PARITY_MARK,
            "space" : serial.PARITY_SPACE  
        }

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity_map[parity],
            stopbits=stopbits,
            timeout=timeout,
            xonxoff=xonxoff,
            rtscts=rtscts,
            dsrdtr=dsrdtr
        )
        self.label = name

    def write(self, command):
        self.ser.write(bytes(command, "utf-8"))
        time.sleep(0.1)
        # NOTE: TEMP CODE:
        print(f"Command sent: {command}")
        # ===============

    def read(self):
        return self.ser.readline().decode("utf-8").strip()
