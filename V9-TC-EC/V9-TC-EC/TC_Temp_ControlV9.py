import time
import sys

import numpy as np
import matplotlib.pyplot as plt

import pandas as pd

from LoggerNI import LoggerNI
from PID import PID

class Temp_Control:

    MAX_V = 12  # Maximum allowed voltage of the heater.

    KP = 8      # Proportional gain for PID controller.
    KD = 0      # Differential gain for PID controller.
    KI = 0.03  # Integral gain for PID controller.

    daq = None  # Variable for DAQ class.
    ps = None   # Variable for power supply class.

    pidA = None # Variable for PID for heater on block A.
    pidB = None # Variable for PID for heater of block B.

    t0 = None   # The starting time of the program.
    then = 0    # The time of the previous iteration.

    tracking = []   # Variable for tracking of block temperature.
    temps = []      # Variable for storing current block temperatures.


    '''
    Initialization function for Temperature control. Sets all appropriate values that are passed in and initializes all helper classes used.

    self:           The class itself, no pass in required.
    daqName:        Name of the thermo couple DAQ card.
    daqFreq:        DAQ frequency of the thermo couple DAQ card.
    temperature:    Setpoint temperature of the TC block.
    powerSupply:    Power supply object.
    '''
    def __init__(self, daqName, daqFreq, temperature, powerSupply):
        self.ps = powerSupply # Sets power supply object
        self.pidA = PID(self.KP, self.KD, self.KI, temperature, 0, self.MAX_V) # Initializes PID controller for block A
        
        self.t=[0,0]
        self.status = True
        self.Sp=temperature
        self.control=0
        self.t0 = time.time() # Initializes starting time
        self.then = self.t0 # Initializes starting time for first iteration
        #self.controllist=[]
        #self.timelist=[]
        self.daq = LoggerNI(daqName, daqFreq, "Thermal") # Initializes thermocouple DAQ
    
    '''
    Rolls the array, keeping the new data point and discarding the oldest one.

    self:       The class itself, no pass in required.
    array:      The array to be rolled.
    data:       The new data point to be rolled into the array.
    '''
    def arrayRoll(self, array, data):
        array.append(data)
        array = array[1:]
        return array


    '''
    Controls the heaters on the TC.

    self:       The class itself, no pass in required.
    '''
    def heatControl(self):

        # Reads the temperatures from the DAQ
        temperatures = self.daq.read_data()
        self.t=temperatures
        now = time.time()
        dt = now - self.then
        self.temps = temperatures

        print(dt)

        #### Old temps calculation
        # tempA = (temperatures[4] + temperatures[5] + temperatures[6] + temperatures[7])/4   # Calculates the average temperature for block A
        # tempB = (temperatures[1] + temperatures[2] + temperatures[3])/3   # Calculates the average temperature for block B
        # tempt = (tempA+tempB)/2
        
        # new tempt readings
        tempt=(temperatures[0]+temperatures[1])/2 # only used 2
        temp1=temperatures[0]
        temp2=temperatures[1]

        if self.status == True:
            control1,control2,controlt = self.pidA.control(tempt, temp1, temp2, dt) # Calculates control for the two blocks

            self.ps.setVoltage(1, control2) # Sets Heater 1 voltage

            self.ps.setVoltage(2, control1) # Sets Heater 2 voltage
            
            # VD update
            
            # SUPER IMPORTANT COMMENT ON HEATERS!!! Didn't actually need new thermocouples :(
            # Black tape on port 1
            # Green heater 1, yellow heater 2
            # Green bottom block, yellow top block
            # Thus
            # Heater 1, bottom block & heater 2, top block
            # Second temp probe (5) to bottom block
            # First temp probe (1) to top block
        
            self.control=controlt
        #     self.controllist.append(controlt)
        # if self.status == False:
        #     self.controllist.append(10000)
        #print(f'heater input is {self.control}')
        #self.timelist.append(now-self.t0)
        self.then = now

        # If the tracking array is too long it rolls it, change to much longer here
        if len(self.tracking) > 20:
            self.tracking = self.arrayRoll(self.tracking, tempt)
        else:
            self.tracking.append(tempt)
        self.T_TC=tempt



    '''
    Checks the stability of the temperature.

    self:       The class itself, no pass in required.
    '''
    def isStable(self):
        # Returns false if there is not enough data to check.
        if len(self.tracking) < 6:
            return False

        track=self.tracking[-6:] # create a list with the latest 6 for fair calculations
        late_avg = sum(track)/len(track) # Finding running average of latest 6
        maxCV = 0

        # Checks that the average of all thermocouple readings is within 0.4% of the setpoint.
        if abs((late_avg - self.pidA.SP)/self.pidA.SP) > 0.004:
            print("SETPOINT TOLERANE NOT REACHED")
            print(f"RUNNING AVERAGE: {late_avg}")
            print(f"ERROR %: {100 * abs(late_avg - self.pidA.SP)/self.pidA.SP}%")
            print(f"CURRENT TEMPERATURE: {self.tracking[-1]}\n")
            return False

        # For all data points in the latest 8 of tracking.
        for i in track:
            cv = abs((i-late_avg)/late_avg) # Calculates coefficient of variation.

            # Takes the maximum coefficient of variation.
            if cv > maxCV:
                maxCV = cv

        # Checks that the maximum coefficient of variation is less than 0.7%.
        if maxCV > 0.007:
            print("CONVERGENCE NOT ACHIEVED")
            print(f"MAXIMUM CV: {maxCV}")
            print(f"CURRENT TEMPERATURE: {self.tracking[-1]}\n")
            return False
        
        # Checks that the standard deviation of the thermocouple readings across both block is less than 0.3
        stdev = np.std(self.temps)
        if stdev > 0.3:
            print("Waiting zone for uniform spread")
            print(f"STDANDARD DEVIATION ACROSS THE BLOCKS: {stdev}")
            print(f"CURRENT TEMPERATURE: {self.tracking[-1]}\n")
            return False

        if self.control<1:
            print('wait for overshoot')
            return False

        return True # If all conditions are met, returns true.

    def stabilizationcheck(self):
        # Sleep for control stabilization
        print('get ready for internal heater')

        # Close controller for now to open internal heater
        time.sleep(30)
        self.status = False
        time.sleep(3.4)


    '''
    Canges the temperature setpoint

    self:       The class itself, no pass in required.
    newTemp:    New temperature to change the setpoint to.
    '''
    def changeTemperature(self, newTemp):
        self.pidA.changeSetpoint(newTemp)

        self.heatControl()


    """
    Turns off all heaters and closes the thermocouple DAQ
    
    self:       The class itself, no pass in required.
    """
    def end(self):
        self.ps.setVoltage(1, 0)
        self.ps.setVoltage(2, 0)
        self.ps.channelOff(0)
        self.daq.close()