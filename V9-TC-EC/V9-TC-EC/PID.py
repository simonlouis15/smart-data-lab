import math
class PID:

    KP = 0          # Proportional gain
    KD = 0          # Differential gain
    KI = 0          # Integral gain

    SP = 0          # Setpoint

    MIN = 0         # Minimum control
    MAX = 0         # Maximum control

    integral1 = 0    # Integral tracking
    integral2=0

    oldError1 = 0    # Error in previous iteration
    oldError2 = 0

    '''
    Initialization function for PID. Sets all appropriate values that are passed in.

    self:       The class itself, no pass in required.
    KP:         Proportional gain
    KD:         Differential gain
    KI:         Integral gain
    setPoint:   initial setpoint
    minVal:     The lower bound for the control output
    maxVal:     The upper bound for the control output
    '''
    def __init__(self, KP, KD, KI, setPoint, minVal, maxVal):
        self.KP = KP
        self.KD = KD
        self.KI = KI

        self.SP = setPoint

        self.MIN = minVal
        self.MAX = maxVal


    '''
    Calculates the contol variable given the input and control gains.

    self:       The class itself, no pass in required.
    value:      The current value of the feedback variable.
    dt:         The time difference between the last and current iterations.
    '''
    def control(self, value, t1,t2,dt):
        error1 = self.SP - t1 # Calculates current error.
        error2 = self.SP - t2 # Larger error

        differential1 = (error1 - self.oldError1)/dt # Calculates the differential of the error.
        differential2 = (error2 - self.oldError2)/dt

        self.integral1 += error1 * dt # Calculates the current integral of the error and adds it to the total integral.
        self.integral2 += error2 * dt

        # Compute control output
        power1=self.KP*error1 + self.KD*differential1 + self.KI*self.integral1
        power2=self.KP*error2 + self.KD*differential2 + self.KI*self.integral2
        control1_raw=(power1/2)*7.3
        control2_raw=(power2/2)*7.3

        if control1_raw>=0:
            control_r1=round(math.sqrt(control1_raw), 3)
        elif control1_raw<0:
            control_r1= -round(math.sqrt(abs(control1_raw)), 3)

        if control2_raw>=0:
            control_r2=round(math.sqrt(control2_raw), 3)
        elif control2_raw<0:
            control_r2= -round(math.sqrt(abs(control2_raw)), 3)

        # Sets the range of the control variable to the set minimum and maximum
        if control_r1 > self.MAX:
            control1 = self.MAX
        elif control_r1 < self.MIN:
            control1 = self.MIN
        else:
            control1=control_r1

        if control_r1!=control1:
            self.integral1 -= error1*dt

        # do the same for the second controller
        if control_r2 > self.MAX:
            control2 = self.MAX
        elif control_r2 < self.MIN:
            control2 = self.MIN
        else:
            control2=control_r2
        
        if control_r2!=control2:
            self.integral2 -= error2*dt

        control=(control1+control2)/2

        self.oldError1 = error1 # Sets the current error as the old error for the next iteration
        self.oldError2 = error2
        #print(f'control interval is {dt}s')
        return control1, control2,control
    
    '''
    Changes the setpoint of the controller

    self:       The class itself, no pass in required.
    setPoint:   New setpoint
    '''
    def changeSetpoint(self, setPoint):
        self.SP = setPoint