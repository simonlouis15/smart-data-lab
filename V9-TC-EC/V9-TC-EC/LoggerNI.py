import nidaqmx
import time
import sys
from PowerRS import PowerRS

class LoggerNI:

    '''
    Initialization function for DAQ. Creates serial connection for DAQ and performs a self-test to ensure proper conection.

    self:           The class itself, no pass in required.
    port_name:      The DAQ name and channels to be used eg. "NI9205/ai0:4".
    daq_frequency:  Reading frequency of the DAQ in Hertz. Important to choose correct value, values too high may cause buffer issues with DAQ, too low may cause code to run slowly.
    daqType:        Type of DAQ, either "Thermal" or "Voltage".
    '''
    def __init__(self, port_name, daq_frequency, daqType):
        
        self.task = nidaqmx.Task() # Variable for ni daq
        
        # Sets task to be a thermal type DAQ. In current configuration uses K-type thermocouples and Celsius as units.
        if daqType == "Thermal":
            #self.task.ai_channels.add_ai_thrmcpl_chan('NI9212R/ai3', thermocouple_type=nidaqmx.constants.ThermocoupleType.K, units=nidaqmx.constants.TemperatureUnits.DEG_C)
            self.task.ai_channels.add_ai_thrmcpl_chan('NI9212R/ai1', thermocouple_type=nidaqmx.constants.ThermocoupleType.K, units=nidaqmx.constants.TemperatureUnits.DEG_C)
            self.task.ai_channels.add_ai_thrmcpl_chan('NI9212R/ai5', thermocouple_type=nidaqmx.constants.ThermocoupleType.K, units=nidaqmx.constants.TemperatureUnits.DEG_C)

        # Sets task to be a voltage type DAQ. In current configuration uses differential measurements, in the -10 to +10 V range, with Volts as units.
        if daqType == "Voltage":
            self.task.ai_channels.add_ai_voltage_chan(port_name, terminal_config = nidaqmx.constants.TerminalConfiguration.DIFF, min_val = -5, max_val = 5, units=nidaqmx.constants.VoltageUnits.VOLTS)
        
        # Sets the DAQ frequency to passed in value, and acquisition type to continuous.
        time.sleep(0.1)
        self.task.timing.cfg_samp_clk_timing(rate=daq_frequency, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)

        # Attempts to read from DAQ as a self test.
        try:
            time.sleep(0.1)
            print(self.task.read())

        # If DAQ can't read it throws an error and stops the program.
        except:
            print("DAQ ISSUE, CHECK CONNECTIONS AND MAKE SURE NO CONFLICTS EXIST, THEN TRY AGAIN")
            sys.exit()

        # If all is well keeps program running.
        finally:
            print("DAQ GOOD")
       
    
    """
    Reads data from the DAQ.
    
    self:       The class itself, no pass in required.
    """
    def read_data(self):
        time.sleep(0.1)
        return self.task.read()


    """
    Closes hmp4040 serial port
    
    self:       The class itself, no pass in required.
    """ 
    def close(self):
        self.task.close()



if __name__=="__main__":
    test=LoggerNI("NI9212R/ai3:6", 0.29, "Thermal") # Initializes temperature control class.
    hmp4040 = PowerRS("COM8", 9600)

    while True:
        a=test.read_data()
        print(a)