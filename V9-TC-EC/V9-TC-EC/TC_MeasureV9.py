import time
from scipy.stats import linregress

from LoggerNI import LoggerNI
from TC_Temp_ControlV9 import Temp_Control
from PowerRS import PowerRS
import pandas as pd

class measureTC:

    hmp4040 = None  # Power supply class.
    ni9205 = None   # Voltage DAQ class.
    control = None  # Temperature control class.

    voltageTrack = []   # Variable for tracking internal heater voltage.

    CORRECTION_FACTORS = [1, 1, 1, 1, 1]    # Voltage correction factors.
    # Top 3 candidates, the last one is adopted
    CORRECTION_FACTORS = [0.9959969222422006, 1.002886903494073, 1.0032461799914043, 1.0012142044064254, 0.9967006473973222]
    CORRECTION_FACTORS = [0.995959035391456, 1.00312170665174, 1.0018774553, 1.0034302665125, 0.995668865662962]
    CORRECTION_FACTORS = [0.996057915896886, 1.00329156507812, 1.00226787725246, 1.00171496989771, 0.996710304210557]
    CORRECTION_FACTORS = [0.9949275128433253, 1.0059458819880351, 1.000199539651762, 1.0025809983805885, 0.9964227028575177] # THIS undershoot
    CORRECTION_FACTORS = [1.0066425039843419, 0.9996583258652267, 0.9880195957595043, 0.9982317045097635, 1.0077073459309818]

    K_MIN = 0.05    # Minimum expected value for thermal conductivity.
    K_MAX = 0.3     # Maximum expected value for thermal conductivity.

    MEASUREMENT_CURRENT = 0.29   # Current used for the internal heater when taking a measurement WAS AT 0.3


    '''
    Initialization function for TC measurement. Initializes all helper classes used.

    self:           The class itself, no pass in required.
    '''
    def __init__(self):
        self.hmp4040 = PowerRS("COM8", 9600)    # Initializes power supply class.
        self.control = Temp_Control("NI9212R/ai3:6", 0.29, 39, self.hmp4040) # Initializes temperature control class.
        self.isdone = False
        self.record=False


    '''
    Checks the stability of the TC measurement heater voltage.

    self:       The class itself, no pass in required.
    '''
    def voltageStabilized(self):
        # Makes sure there is enough data to judge convergence.
        if len(self.voltageTrack) < 5: # was 2
            print("NOT ENOUGH DATA POINTS TO JUDGE CONVERGENCE")
            return False
        
        voltagetrack=self.voltageTrack

        average = sum(voltagetrack) / len(voltagetrack) # Calculates average of all voltage data points
        maxCV = 0

        # Makes sure the voltage reading is high enough. Threshold can be adjusted if needed.
        if self.voltageTrack[-1] < 8:
            print("VOLTAGE TOO LOW")
            print(f"VOLTAGE: {self.voltageTrack[-1]}")
            return False

        # For all data points in the tracking.
        for i in voltagetrack:
            cv = abs((i-average)/average) # Calculates coefficient of variation.

            # Takes the maximum coefficient of variation.
            if cv > maxCV:
                maxCV = cv

        # Checks that the maximum coefficient of variation is lett than 0.3%.
        if maxCV > 0.003:
            print("CONVERGENCE NOT ACHIEVED")
            print(f"MAXIMUM CV: {maxCV}")
            return False

        return True
    

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
    Performs calibration of the TC device.

    self:       The class itself, no pass in required.
    '''
    def calibrate(self):
        print("\nCALIBRAATING DEVICE, ENSURE ALL CHANNELS ARE FILLED WITH REFERENCE FLUID\n")

        voltages = self.takeMeasurement() # Takes voltage measurement.
        depths = [150, 300, 450, 600, 750] # Array of TC channel depths.

        # Calculates inverse voltages for all measured voltages.
        for i in range(len(voltages)):
            voltages[i] = 1/voltages[i]

        fit = linregress(depths, voltages) # Fits inverse voltages to a line.

        coefficients = []

        # Calculates correction factor for each TC channel.
        for i in range(len(voltages)):
            ideal = (fit.slope * depths[i]) + fit.intercept # Calculates "ideal" inverse voltage measurement for each channel based on line fit.
            coefficients.append(ideal/voltages[i]) # Calculates correction factors based on ideal and measured voltages.

        print(f"CORRECTION FACTORS ARE: {coefficients}")

        self.CORRECTION_FACTORS = coefficients # Sets the correction factors in the class.


    '''
    Calculates the thermal conductivity from passed in voltage measurements.

    self:           The class itself, no pass in required.
    voltages:       Measured voltages from the TC.
    sampleChannel:  Channel with the sample fluid.
    referenceK:     Thermal conductivity of the reference fluid.
    '''
    def thermalConductivity(self, voltages, sampleChannel, referenceK, batch=0, chem1=1,chem2=2,chem3=3,f1=4,f2=5,f3=6):
        # m1, m2, m3 = map_chemicals(chem1, chem2, chem3)
        # now=date.today()
        # excel_path = f'C:/Users/Indus/OneDrive/Desktop/26 Campaign/{batch}/ThermalConductivity-{batch}-{m1}{f1}+{m2}{f2}+{m3}{f3}_{now}_step_averages.xlsx'
        # sample = 0
        # sampleDelta = 0

        reference = []
        referenceDelta = []

        # For all channels
        for i in range(len(voltages)):
            # For the reference channel
            if i == sampleChannel - 1:
                sample = (1/voltages[i]) * self.CORRECTION_FACTORS[i] # Calculates corrected inverse voltage for sample channel. CHANGED here
                sampleDelta = (i + 1) * 150 # Calculates sample channel depth.
            else:
                reference.append((1/voltages[i]) * self.CORRECTION_FACTORS[i]) # Calculates corrected inverse voltage for reference channels.
                referenceDelta.append((i + 1) * 150) # Calculates reference channel depths.

        print(f"\nSAMPLE CHANNEL DEPTH: {sampleDelta}")
        print(f"SAMPLE CHANNEL VOLTAGE: {sample}\n")

        print(f"\nREFERENCE CHANNEL DEPTHS: {referenceDelta}")
        print(f"REFERENCE CHANNEL VOLTAGES: {reference}\n")

        fit = linregress(referenceDelta, reference) # Fits the reference channel data to a line.
        rSquare = pow(fit.rvalue, 2) # Calculates the R-squared value of the reference linear fit.

        print(f"REFERENCE FIT: {fit.slope}, {fit.intercept}\n")
        print(f"REFERENCE R SQUARED: {rSquare}\n")


        if rSquare < 0.94:
            print("POOR FIT, CHECK FOR ISSUES WITH DEVICE")
            return 0

        deltaStar = (sample - fit.intercept) / fit.slope # Calculates delta star for sample.
        kFactor = sampleDelta / deltaStar # Calculates k factor for sample.

        k = kFactor * referenceK # Calculates sample thermal conductivity.

        summary_df = pd.DataFrame({
        "Parameter": [
            "SAMPLE CHANNEL DEPTH",
            "SAMPLE CHANNEL VOLTAGE",
            "REFERENCE CHANNEL DEPTHS",
            "REFERENCE CHANNEL VOLTAGES",
            "REFERENCE FIT, SLOPE",
            "REFERENCE FIT, INTERCEPT",
            "Reference R^2",
            "Reference k (input)",
            "Thermal conductivity (W/m·K)",
        ],
        "Value": [
            sampleDelta,
            sample,
            referenceDelta,
            reference,
            fit.slope,
            fit.intercept,
            rSquare,
            referenceK,
            k
        ]
    })

  

        # with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        #     summary_df.to_excel(writer, index=False, sheet_name="Summary")

        # print(f"Saved results to Excel: {excel_path}")
              
        # If the reference fit is poor, returns 0 as a sign to retry measurements.

        # Checks that thermal conductivity is within the expected range, if not returns 0 as a sign to retry measurements.
        if k > self.K_MAX:
            print("THERMAL CONDUCTIVITY HIGHER THAN EXPECTED, TRY MEASUREMENTS AGAIN")
            return 0
        
        if k < self.K_MIN:
            print("THERMAL CONDUCTIVITY LOWER THAN EXPECTED, TRY MEASUREMENTS AGAIN")
            return 0

        return k
    
    '''
    Flips the array, making the first element the last and so on.

    self:       The class itself, no pass in required.
    array:      The array to be flipped.
    '''
    def arrayFlip(self, array):

        length = len(array)

        flipped = [0 for x in range(length)]

        for i in range(length):
            flipped[i] = array[length - 1 - i]

        return flipped

        
    '''
    Takes voltage measurement from NI DAQ.

    self:           The class itself, no pass in required.
    '''
    def takeMeasurement(self):
        # Ensure blocks are uniformally heated, controller is fixed here also
        self.control.stabilizationcheck()

        # Once blocks are uniformally heated, proceeds
        measurements = [[0 for x in range(5)] for y in range(10)] # Initializes measurement array, 2D with 10x5 elements.
        voltages = [0 for x in range(5)] # Initializes voltage array with 5 elements.

        # Turns on the internal heater (remember to stop control in case of conflict)
        self.hmp4040.setVoltage(3, 32)
        self.hmp4040.setCurrent(3, self.MEASUREMENT_CURRENT)
        self.hmp4040.channelOn(3)

        # reopen temp control and wait for temp stabilization
        self.control.status = True

        # Initializes the voltage DAQ.
        self.ni9205 = LoggerNI("NI9205/ai0:4", 2, "Voltage") # Initializes the voltage DAQ.
        # NOTE: The voltage DAQ is initialized again every time the measurement is takes as a result of limited DAQ buffer, which overflows between measurements otherwise.

        # Runs as long as heater voltage is not stable.
        while not self.voltageStabilized():
            # Rolls the tracking array if there are more than 10 elements.
            if len(self.voltageTrack) < 10:
                self.voltageTrack.append(sum(self.ni9205.read_data()))
            else:
                self.voltageTrack = self.arrayRoll(self.voltageTrack, sum(self.ni9205.read_data()))
        # Once voltage is stabilized, takes 10 measurements from the DAQ. 
        for i in range(10):
            measurements[i] = self.ni9205.read_data()

        # Turns off internal heater.
        self.control.status = False
        time.sleep(3.4)
        self.hmp4040.setVoltage(3, 0)
        self.hmp4040.setCurrent(3, 0)
        self.hmp4040.channelOff(3)
        self.hmp4040.deselectChannel(3)
        self.control.status = True

        # Closes voltage DAQ to prevent buffer issues.
        self.ni9205.close()

        # For each channel in the TC, takes the average of the 15 data points taken from DAQ.
        for i in range(5):
            measurementSum = 0

            for j in range(10):
                measurementSum += measurements[j][i] # Sums 10 voltage data points.

            voltages[i] = measurementSum/10 # Calculates average.

        # Resets voltage tracking.
        self.voltageTrack = []

        voltages = self.arrayFlip(voltages)

        print(f'voltage should be going up broski:{voltages}')
        print(f'to check correction bro {self.CORRECTION_FACTORS}')

        return voltages
    

    """
    Closes all supporting classes, DAQ and Power supply connections.
    
    self:       The class itself, no pass in required.
    """
    def end(self):
        self.control.end()
        self.hmp4040.close()