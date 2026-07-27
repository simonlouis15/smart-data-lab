import serial
import time
import sys

class PowerRS:

    SLEEP_TIME = 0.1    # Sleep time after commmand is sent for power supply to ensure power supply receives command correctly
    hmp4040 = None      # Variable for the power supply serial object

    '''
    Initialization function for power supply. Creates serial connection for power supply and performs a self-test to ensure proper conection.

    self:       The class itself, no pass in required.
    comPort:    The COM port used for the power supply, eg 'COM3'.
    baudRate:   The baud rate for the power supply connection, usually 9600 for RS-232 connections.
    '''
    def __init__(self, comPort, baudRate):
        
        # Initialize the RS-232 connection
        self.hmp4040 = serial.Serial(comPort, baudRate, timeout=1)

        try:
            print('POWER SUPPLY TEST')

            self.deselectChannel(3)

            self.setVoltage(1, 1)       # Set channel 1 voltage to 1V
            self.setCurrent(1, 1.7)     # Set channel 1 current to 1.7A
            self.selectChannel(1)

            self.setVoltage(2, 1)       # Set channel 2 voltage to 1V
            self.setCurrent(2, 1.7)     # Set channel 2 current to 1.7A
            self.selectChannel(2)

            self.channelOn(0)           # Turns all channels on

            time.sleep(1)               # Wait for 1 second

            volt = self.readVoltage(1)  # Reads current voltage of power supply

            # If power supply voltage is not the expected value, throws and exception
            #if not volt == 1:
                #raise ValueError('Voltage reading does not match set voltage. Check power supply connections and try again')

            self.channelOff(0)          # Turn all channels off

        # Catches any exceptions and turns off power supply and ends program to prevent damage or poor results, etc.
        except Exception as error:
            print('POWER SUPPLY ISSUE, CHECK CONNECTIONS AND TRY AGAIN')
            print('EXCEPTION CAUGHT: ' + repr(error))

            self.channelOff(0)
            self.close()

            sys.exit()

        # If all is well, sets all voltages to 0 and continues normal operation
        finally:
            print('POWER SUPPLY GOOD')

            self.setVoltage(1, 0)        # Set Voltage to 0V
            self.setVoltage(2, 0)        # Set Voltage to 0V
            self.setVoltage(3, 0)
            self.setCurrent(3,0)

            self.channelOn(1)
            self.channelOn(2)


    """
    Send a command to the HMP4040 over RS-232.

    self:       The class itself, no pass in required.
    command:    Comand to be sent to power supply.
    """
    def sendCommand(self, command):
        self.hmp4040.write((command + '\n').encode('ascii'))
        time.sleep(self.SLEEP_TIME)  # Brief pause to ensure command is processed


    """
    Send a command to the HMP4040 over RS-232 and read the response.
    
    self:       The class itself, no pass in required.
    command:    Comand to be sent to power supply.
    """
    def readCommand(self, command):
        self.hmp4040.write((command + '\n').encode('ascii'))
        time.sleep(self.SLEEP_TIME)  # Brief pause to ensure command is processed
        response = self.hmp4040.readline().decode('ascii').strip()
        return response


    """
    Sets the desired output channel on the power supply, mostly used for setting correct channel for changing voltage/current.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be chosen.
    """
    def setChannel(self, channel):
        self.sendCommand(f"INST OUT{channel}")


    """
    Sets desired voltage on the specified channel.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be set.
    voltage:    Desired voltage.
    """
    def setVoltage(self, channel, voltage):
        self.setChannel(channel)
        self.sendCommand(f"VOLT {voltage}")


    """
    Sets desired current on the specified channel.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be set.
    current:    Desired current.
    """
    def setCurrent(self, channel, current):
        self.setChannel(channel)
        self.sendCommand(f"CURR {current}")


    """
    Selects desired channel, adding it to list of channels to be simultaneously controlled.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be selected.
    """
    def selectChannel(self, channel):
        self.setChannel(channel)
        self.sendCommand(f"OUTP:SEL 1")


    """
    Deselects desired channel, removing it from list of channels to be simultaneously controlled.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be deselected.
    """
    def deselectChannel(self, channel):
        self.setChannel(channel)
        self.sendCommand(f"OUTP:SEL 0")
    

    """
    Turns on desired channel. In case 0 is paseed as the channel, all selected channels are turned on.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be tuned on. 0 In case all selected channels are to be turned on.
    """
    def channelOn(self, channel):
        if channel == 0:
            self.sendCommand("OUTP:GEN 1")
        else:
            self.selectChannel(channel)
            self.sendCommand("OUTP 1")


    """
    Turns off desired channel. In case 0 is paseed as the channel, all selected channels are turned off.
    
    self:       The class itself, no pass in required.
    channel:    Channel to be tuned off. 0 In case all selected channels are to be turned off.
    """
    def channelOff(self, channel):
        if channel == 0:
            self.sendCommand("OUTP:GEN 0")
        else:
            self.selectChannel(channel)
            self.sendCommand("OUTP 0")


    """
    Reads the voltage from the power supply

    self:       The class itself, no pass in required.
    channel:    Channel to read the voltage of.
    """
    def readVoltage(self, channel):
        self.setChannel(channel)
        voltage = self.readCommand("MEAS:VOLT?")
        return voltage


    """
    Reads the current from the power supply

    self:       The class itself, no pass in required.
    channel:    Channel to read the current of.
    """
    def readCurrent(self, channel):
        self.setChannel(channel)
        current = self.readCommand("MEAS:CURR?")
        return current


    """
    Closes hmp4040 serial port
    
    self:       The class itself, no pass in required.
    """
    def close(self):
        self.hmp4040.close()