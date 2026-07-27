import numpy as np
import serial
import string
import serial.tools.list_ports
import time
import argparse
import threading
import nidaqmx
import re
import os
import signal
import sys
from sklearn.linear_model import LinearRegression
import xtalx.z_sensor
from xtalx.tools.z_sensor import z_common
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import cv2
from flask import Flask, Response

import threading
import argparse
from SelectorValvesV9 import Valve_Setup, injectionmode, airmode, solventmode, Valve1_Setup, Valve2_Setup, Valve3_Setup, open_valve1, open_valve2, open_valve3

#Hamilton Pumps for Samples
#Serial Connection for Sample1
SERIALPORT_pumpSample1 = "COM10"
BAUDRATE = 9600
serSample1 = serial.Serial(SERIALPORT_pumpSample1, BAUDRATE)
serSample1.bytesize = serial.EIGHTBITS
serSample1.parity = serial.PARITY_NONE
serSample1.stopbits = serial.STOPBITS_ONE
serSample1.timeout = 1        
serSample1.xonxoff = False    
serSample1.rtscts = False    
serSample1.dsrdtr = False      
serSample1.writeTimeout = 1
connected = False
serSample1.isOpen()
#print ("Starting Up Serial Monitor")
# Functions for pump1
def START_pumpSample1(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        serSample1.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_pumpSample1()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = serSample1.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                serSample1.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pumpSample1 ():
       # Set the pump at zero position
       INITIALIZE ='Y30z'
       START_pumpSample1('1',INITIALIZE)
       ZeroPosition ='OV100A0'
       START_pumpSample1('1',ZeroPosition)
       FillIn = 'OV100P6000'
       START_pumpSample1('1',FillIn)

def PumpReady_pumpSample1():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        serSample1.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = serSample1.readline()

        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pumpSample1(x1,y1):
    #print("injection started")
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Inject1 = f'EV{int(x1*20)}d{int(y1)}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample1('1',Inject1)
   

def PumpWithdrawSample1(x):
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Refill1 = f'OV{x}A6000'
    START_pumpSample1('1',Refill1)

def PumpWithdrawSample1_Volume1(x,y):
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Refill1 = f'OV{x}A{y}'
    START_pumpSample1('1',Refill1)

def Debubble_pumpSample1(x1,y1):
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Inject1 = f'IV{int(x1*20)}d{y1}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample1('1',Inject1)

def PumpCleaning_pumpSample1():
    PumpEmpty_PumpSample1(10)
    for _ in range(1):
        PumpWithdrawSample1(300)
        injectionmode()
        PumpFullInjection_pumpSample1(25,0)

def PumpCleaning_JarSwitch1(x, y):
    PumpEmpty_PumpSample1(10)
    for _ in range(1):
        PumpWithdrawSample1_Volume1(x,y)
        PumpEmpty_PumpSample1(10)
        

def PumpCleaning_pumpSample1_aut():
    PumpEmpty_PumpSample1(10)
    for _ in range(1):
        PumpWithdrawSample1(300)
        PumpEmpty_PumpSample1(10)

def PumpFullInjection_pumpSample1(x1,d):
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Inject1 = f'EV{int(x1*20)}A{d}'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample1('1',Inject1)
   
def PumpEmpty_PumpSample1(x1):
    Stop1 = f'T'
    START_pumpSample1('1',Stop1)
    Inject1 = f'IV{int(x1*20)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample1('1',Inject1)

#Serial Connection for Sample2
SERIALPORT_pumpSample2 = "COM17"
BAUDRATE = 9600
serSample2 = serial.Serial(SERIALPORT_pumpSample2, BAUDRATE)
serSample2.bytesize = serial.EIGHTBITS
serSample2.parity = serial.PARITY_NONE
serSample2.stopbits = serial.STOPBITS_ONE
serSample2.timeout = 1        
serSample2.xonxoff = False    
serSample2.rtscts = False    
serSample2.dsrdtr = False      
serSample2.writeTimeout = 1
connected = False
serSample2.isOpen()
#print ("Starting Up Serial Monitor")
# Functions for pump1
def START_pumpSample2(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        serSample2.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_pumpSample2()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = serSample2.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                serSample2.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pumpSample2 ():
       # Set the pump at zero position
       INITIALIZE ='Y30z'
       START_pumpSample2('1',INITIALIZE)
       ZeroPosition ='V100A0'
       START_pumpSample2('1',ZeroPosition)
       FillIn = 'OV100P6000'
       START_pumpSample2('1',FillIn)

def PumpReady_pumpSample2():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        serSample2.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = serSample2.readline()
        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pumpSample2(x1,y1):
    Stop1 = f'T'
    START_pumpSample2('1',Stop1)
    Inject1 = f'EV{int(x1*20)}d{int(y1)}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample2('1',Inject1)
   

def PumpWithdrawSample2(x):
    Stop1 = f'T'
    START_pumpSample2('1',Stop1)
    Refill1 = f'OV{x}A6000'
    START_pumpSample2('1',Refill1)

def PumpWithdrawSample2_Volume2(x,y):
    Stop2 = f'T'
    START_pumpSample2('1',Stop2)
    Refill2 = f'OV{x}A{y}'
    START_pumpSample2('1',Refill2)
    time.sleep(1)

def Debubble_pumpSample2(x1,y1):
    Stop1 = f'T'
    START_pumpSample2('1',Stop1)
    Inject1 = f'IV{int(x1*20)}d{y1}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample2('1',Inject1)

def PumpCleaning_pumpSample2():
    PumpEmpty_PumpSample2(10)
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    #for _ in range(3):
        #PumpWithdrawSample2()
        #PumpEmpty_PumpSample2(25)
    for _ in range(1):
        PumpWithdrawSample2(300)
        injectionmode()
        PumpFullInjection_pumpSample2(25,0)

def PumpCleaning_JarSwitch2(x,y):
    PumpEmpty_PumpSample2(10)
    for _ in range(1):
        PumpWithdrawSample2_Volume2(x, y)
        PumpEmpty_PumpSample2(10)

def PumpCleaning_pumpSample2_aut():
    PumpEmpty_PumpSample2(10)
    for _ in range(1):
        PumpWithdrawSample2(300)
        PumpEmpty_PumpSample2(10)

def PumpFullInjection_pumpSample2(x1,d):
    Stop1 = f'T'
    START_pumpSample2('1',Stop1)
    Inject1 = f'EV{int(x1*20)}A{d}'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample2('1',Inject1)
   
def PumpEmpty_PumpSample2(x1):
    Stop1 = f'T'
    START_pumpSample2('1',Stop1)
    Inject1 = f'IV{int(x1*20)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample2('1',Inject1)

#Serial Connection for Sample3
SERIALPORT_pumpSample3 = "COM16"
BAUDRATE = 9600
serSample3 = serial.Serial(SERIALPORT_pumpSample3, BAUDRATE)
serSample3.bytesize = serial.EIGHTBITS
serSample3.parity = serial.PARITY_NONE
serSample3.stopbits = serial.STOPBITS_ONE
serSample3.timeout = 1        
serSample3.xonxoff = False    
serSample3.rtscts = False    
serSample3.dsrdtr = False      
serSample3.writeTimeout = 1
connected = False
serSample3.isOpen()
#print ("Starting Up Serial Monitor")

# Functions for pump3
def START_pumpSample3(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        serSample3.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_pumpSample3()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = serSample3.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                serSample3.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pumpSample3 ():
       # Set the pump at zero position
       INITIALIZE ='Y30z'
       START_pumpSample3('1',INITIALIZE)
       ZeroPosition ='OV100A0'
       START_pumpSample3('1',ZeroPosition)
       FillIn = 'OV100P6000'
       START_pumpSample3('1',FillIn)

def PumpReady_pumpSample3():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        serSample3.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = serSample3.readline()
        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pumpSample3(x1,y1):
    #print("injection started")
    Stop1 = f'T'
    START_pumpSample3('1',Stop1)
    Inject1 = f'EV{int(x1*20)}d{int(y1)}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample3('1',Inject1)
   

def PumpWithdrawSample3(x):
    Stop1 = f'T'
    START_pumpSample3('1',Stop1)
    Refill1 = f'OV{x}A6000'
    START_pumpSample3('1',Refill1)

def PumpWithdrawSample3_Volume3(x,y):
    Stop3 = f'T'
    START_pumpSample3('1',Stop3)
    Refill3 = f'OV{int(x)}A{y}'
    START_pumpSample3('1',Refill3)
    time.sleep(1)

def Debubble_pumpSample3(x1,y1):
    Stop1 = f'T'
    START_pumpSample3('1',Stop1)
    Inject1 = f'IV{int(x1*20)}d{y1}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSample3('1',Inject1)

def PumpEmpty_PumpSample3(x1):
    Stop1 = f'T'
    START_pumpSample3('1',Stop1)
    Inject1 = f'IV{int(x1*20)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample3('1',Inject1)

def PumpFullInjection_pumpSample3(x1,d):
    Stop1 = f'T'
    START_pumpSample3('1',Stop1)
    Inject1 = f'EV{int(x1*20)}A{d}'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSample3('1',Inject1)

def PumpCleaning_pumpSample3():
    PumpEmpty_PumpSample3(10)
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    #for _ in range(3):
        #PumpWithdrawSample3()
        #PumpEmpty_PumpSample3(25)
    for _ in range(1):
        PumpWithdrawSample3(300)
        injectionmode()
        PumpFullInjection_pumpSample3(25,0)

def PumpCleaning_JarSwitch3(x,y):
    PumpEmpty_PumpSample3(10)
    for _ in range(1):
        PumpWithdrawSample3_Volume3(x, y)
        PumpEmpty_PumpSample3(10)

def PumpCleaning_pumpSample3_aut():
    PumpEmpty_PumpSample3(10)
    for _ in range(1):
        PumpWithdrawSample3(300)
        PumpEmpty_PumpSample3(10)



#Hamilton Pump for Solvent
#Serial Connection for Solvent
SERIALPORT_pumpSolvent = "COM6"
BAUDRATE = 9600
serSolvent = serial.Serial(SERIALPORT_pumpSolvent, BAUDRATE)
serSolvent.bytesize = serial.EIGHTBITS
serSolvent.parity = serial.PARITY_NONE
serSolvent.stopbits = serial.STOPBITS_ONE
serSolvent.timeout = 1        
serSolvent.xonxoff = False    
serSolvent.rtscts = False    
serSolvent.dsrdtr = False      
serSolvent.writeTimeout = 1
connected = False
serSolvent.isOpen()
#print ("Starting Up Serial Monitor")
# Functions for pump1
def START_pumpSolvent(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        serSolvent.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_pumpSolvent()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = serSolvent.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                serSolvent.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pumpSolvent ():
       # Set the pump at zero position
       INITIALIZE ='Zz'
       START_pumpSolvent('1',INITIALIZE)
       Valve= 'h21006'
       START_pumpSolvent('1',Valve)
       ZeroPosition ='I6V500A0'
       #START_pumpSolvent('1',ZeroPosition)
       FillIn = 'I1V500A13714'
       START_pumpSolvent('1',FillIn)

def PumpReady_pumpSolvent ():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        serSolvent.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = serSolvent.readline()
        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    solventmode()
    time.sleep(3)
    print('Solvent Started')
    #Inject1 = f'EV{int(x1*8)}A0'
    Inject1 = f'I5V{int(x1*18.3)}d2200' # was 2200
    START_pumpSolvent('1',Inject1)

def OneInjection_pumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    solventmode()
    time.sleep(3)
    print('Solvent Started')
    #Inject1 = f'EV{int(x1*8)}A0'
    Inject1 = f'I5V{int(x1*18.3)}A3000'
    START_pumpSolvent('1',Inject1)

def PumpFullInjection_pumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I5V{int(x1*18.3)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)

def PumpInjection_pumpSolvent_Volume(x1,y1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I5V{int(x1*18.3)}d{int(y1)}'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)
   
def PumpEmpty_PumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I6V{int(x1*18.3)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)

def PumpWithdrawSolvent():
    print('Solvent Refill Started')
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    serSolvent.write(bytes(c, 'utf-8'))
    POS=serSolvent.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
        #print(CurrentPosition)
        #print(type(CurrentPosition)) # Output: 5000
   
    RefillPosition = 13714 - CurrentPosition
    Refill1 = f'I1v75p{int(RefillPosition)}'
    START_pumpSolvent('1',Refill1)
    #FillIn = 'Ov20A6000'
    #START_pump1('1',FillIn)

def Debubble_pumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I6V{int(x1*18.3)}v{int(x1*18.3)}c{int(x1*18.3)}d200'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)

def PumpCleaning_pumpSolvent():
    PumpEmpty_PumpSolvent(20)
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    for _ in range(3):
        PumpWithdrawSolvent()
        PumpEmpty_PumpSolvent(25)
    for _ in range(3):
        PumpWithdrawSolvent()
        PumpFullInjection_pumpSolvent(25)

def PumpFullInjection_pumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I5V{int(x1*18.3)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)
   
def PumpEmpty_PumpSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    Inject1 = f'I6V{int(x1*18.3)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)

def  RefillSolvent ():
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    x1 = 25
    Inject1 = f'I1V{int(x1*18.3)}A13714'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pumpSolvent('1',Inject1)

def SolventPumpforTC ():
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    x1 = 2
    Inject1 = f'I2V{int(x1*18.3)}A5500'
    time.sleep(300)
    START_pumpSolvent('1',Inject1)
    PumpInjection_pumpSolvent_Volume (10, 5500)

def SolventPumpCleanedbyAir ():
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    x1 = 50
    Inject1 = f'I3V{int(x1*18.3)}A13714'
    START_pumpSolvent('1',Inject1)
    PumpEmpty_PumpSolvent(50)

#Hamilton Pumps for HC
#Serial Connection for pump1
SERIALPORT_pump1 = "COM14"
BAUDRATE = 9600
ser1 = serial.Serial(SERIALPORT_pump1, BAUDRATE)
ser1.bytesize = serial.EIGHTBITS
ser1.parity = serial.PARITY_NONE
ser1.stopbits = serial.STOPBITS_ONE
ser1.timeout = 1        
ser1.xonxoff = False    
ser1.rtscts = False    
ser1.dsrdtr = False      
ser1.writeTimeout = 1
connected = False
ser1.isOpen()
#print ("Starting Up Serial Monitor")

#Serial Connection for pump2
SERIALPORT_pump1 = "COM5"
BAUDRATE = 9600
ser2 = serial.Serial(SERIALPORT_pump1, BAUDRATE)
ser2.bytesize = serial.EIGHTBITS
ser2.parity = serial.PARITY_NONE
ser2.stopbits = serial.STOPBITS_ONE
ser2.timeout = 1        
ser2.xonxoff = False    
ser2.rtscts = False    
ser2.dsrdtr = False      
ser2.writeTimeout = 1
connected = False
ser2.isOpen()
#print ("Starting Up Serial Monitor")


# Functions for pump1
def START_pump1(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        ser1.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_pump1()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = ser1.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                ser1.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pump1 ():
       # Set the pump at zero position
       INITIALIZE ='Yz'
       START_pump1('1',INITIALIZE)
       ZeroPosition ='OV500A0'
       START_pump1('1',ZeroPosition)
       FillIn = 'OV500P6000'
       START_pump1('1',FillIn)

def PumpReady_pump1():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        ser1.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = ser1.readline()
        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pump1(x1):
    Inject1 = f'IV{int(x1*20)}A0'
    START_pump1('1',Inject1)
   

def PumpRefill_pump1(x1):
    print('start refilling')
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    ser1.write(bytes(c, 'utf-8'))
    POS=ser1.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
        #print(CurrentPosition)
        #print(type(CurrentPosition)) # Output: 5000
   
    RefillPosition = 6000 - CurrentPosition
    Refill1 = f'OV{int(x1)}A6000'
    START_pump1('1',Refill1)
    #FillIn = 'OV20A6000'
    #START_pump1('1',FillIn)

def PumpWithdraw():
    print('Pump Withdraw started.')
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    ser1.write(bytes(c, 'utf-8'))
    POS=ser1.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
        #print(CurrentPosition)
        #print(type(CurrentPosition)) # Output: 5000
   
    RefillPosition = 6000 - CurrentPosition
    Refill1 = f'Ov75p{int(RefillPosition)}'
    START_pump1('1',Refill1)
    #FillIn = 'Ov20A6000'
    #START_pump1('1',FillIn)
   
# Functions for pump2
def START_pump2(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        ser2.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(1)
        PumpReady_pump2()
        while True:
            try:
                #print ("Attempt to Read")
                readOut = ser2.readline().decode("utf-8")
                time.sleep(1)
                #print ("Reading: ", readOut)
                d=c
                ser2.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break
def PumpInitialize_pump2 ():
      # Set the pump at zero position
       INITIALIZE ='Yz'
       START_pump2('1',INITIALIZE)
       ZeroPosition ='V500A0'
       START_pump2('1',ZeroPosition)
       FillIn = 'OV500P6000'
       START_pump2('1',FillIn)

def PumpReady_pump2():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        ser2.write(bytes(c, 'utf-8'))
        readOut = ser2.readline()
        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        if readOut != "@" and readOut != "o":  
            break

def PumpInjection_pump2(x1):
    Inject2 = f'EV200D{int(x1*1000)}'
    START_pump2('1',Inject2)

def PumpRefill_pump2():
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    ser2.write(bytes(c, 'utf-8'))
    POS=ser2.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
        #print(CurrentPosition)
        #print(type(CurrentPosition)) # Output: 5000
   
    RefillPosition = 6000 - CurrentPosition
    Refill2 = f'Ov75p{int(RefillPosition)}'
    START_pump2('1',Refill2)
    #FillIn = 'Ov500a6000'
    #START_pump2('1',FillIn)

def Debubble(x1):
    print('Debubble started')
    Inject1 = f'IV200D{int(x1*1000)}'
    START_pump1('1',Inject1)

def EmptyHcSyringe(x1):
    print('HC syringe is getting emptied')
    Inject1 = f'IV{int(x1)}A0'
    time.sleep(1)
    START_pump1('1',Inject1)

def cleanup(signum, frame):
    print("\nTermination signal received. Stopping pumps...")
    Stop_pump1_HC()
    Stop_pump2_HC()
    print("Pumps stopped. Exiting...")
    sys.exit(0)
 
# Functions for pump1
def START_pump1_HC(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        ser1.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.1)
        #PumpReady_pump1_HC()
        while True:
            try:
                #print ("Attempt to Read")
                readOut = ser1.readline().decode("utf-8")
                time.sleep(0.1)
                #print ("Reading: ", readOut) 
                d=c 
                ser1.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break

def PumpInjection_pump1_HC(x1):
    Stop1 = f'T'
    START_pump1_HC('1',Stop1)
    Inject1 = f'EV{int(x1*20)}A0'
    START_pump1_HC('1',Inject1)

def Stop_pump1_HC():
    Stop1 = f'T'
    START_pump1_HC('1',Stop1)

# Functions for pump2
def START_pump2_HC(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        ser2.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.1)
        #PumpReady_pump1_HC()
        while True:
            try:
                #print ("Attempt to Read")
                readOut = ser2.readline().decode("utf-8")
                time.sleep(0.1)
                #print ("Reading: ", readOut) 
                d=c 
                ser2.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break

def PumpInjection_pump2_HC(x2):
    Stop2 = f'T'
    START_pump2_HC('1',Stop2)
    Inject2 = f'EV{int(x2*20)}A0'
    START_pump2_HC('1',Inject2)

def Stop_pump2_HC():
    Stop2 = f'T'
    START_pump2_HC('1',Stop2)

def InitialInjection_Pump1_HC():
    print('Initial injection started.')
    Stop1 = f'T'
    START_pump1_HC('1',Stop1)
    Inject1 = f'EV{int(20)}A2000'
    START_pump1('1',Inject1)

def InitialInjection_Pump2_HC():
    Stop2 = f'T'
    START_pump2_HC('1',Stop2)
    Inject2 = f'EV{int(40)}A4800'    # 4800
    START_pump2('1',Inject2)

# for swithing solvents
def injectSolvent(x1):
    Stop1 = f'T'
    START_pumpSolvent('1',Stop1)
    solventmode()
    time.sleep(3)
    print('Solvent Started')
    #Inject1 = f'EV{int(x1*8)}A0'
    Inject1 = f'EV{int(x1*8)}A0'
    START_pumpSolvent('1',Inject1)

def RefillSample():
    threads = []
    
    # Create threads for each pump withdraw function
    t1 = threading.Thread(target=PumpWithdrawSample1, args=(200,))
    t2 = threading.Thread(target=PumpWithdrawSample2, args=(200,))
    t3 = threading.Thread(target=PumpWithdrawSample3, args=(200,))

    # Add threads to the list
    threads.extend([t1, t2, t3])

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()



def pump_flow_rate(flow_rate_mm_sample1, flow_rate_mm_sample2, flow_rate_mm_sample3):
    """
    Function to control the flow rate and operation of three pumps via serial communication.
    The function sets the flow rate for each pump, starts the pumps, runs them for a specified time, and then stops them.
    """
    injectionmode()
    time.sleep(5)
    print('Pumping started.')
    #Syringe Volume in mL
    Syringe_Volume = 10 
    #Injection time in min
    Injection_time = 1 
    # Calculate duration in milliseconds
    if flow_rate_mm_sample1!=0:
        duration1 = round(6000 * Injection_time / (Syringe_Volume / flow_rate_mm_sample1))
        dis1=0
    else:
        duration1=0
        dis1=0
    if flow_rate_mm_sample2!=0:
        duration2 = round(6000 * Injection_time / (Syringe_Volume / flow_rate_mm_sample2))
        dis2=0
    else:
        duration2=0
        dis2=0
    if flow_rate_mm_sample3!=0:
        duration3 = round(6000 * Injection_time / (Syringe_Volume / flow_rate_mm_sample3))
        dis3=0
    else:
        duration3=0
        dis3=0
    # Debubble Threads
    thread1d = threading.Thread(target=Debubble_pumpSample1, args=(5,dis1))
    thread2d = threading.Thread(target=Debubble_pumpSample2, args=(5,dis2))
    thread3d = threading.Thread(target=Debubble_pumpSample3, args=(5,dis3))

    # Start all threads at the same time
    thread1d.start()
    thread2d.start()
    thread3d.start()
    
    # Wait for all threads to finish
    thread1d.join()
    thread2d.join()
    thread3d.join()

    time.sleep(0.1)

    # Create threads for each pump
    thread1 = threading.Thread(target=PumpInjection_pumpSample1, args=(flow_rate_mm_sample1, duration1))
    thread2 = threading.Thread(target=PumpInjection_pumpSample2, args=(flow_rate_mm_sample2, duration2))
    thread3 = threading.Thread(target=PumpInjection_pumpSample3, args=(flow_rate_mm_sample3, duration3))
    
    # Start all threads at the same time
    thread1.start()
    thread2.start()
    thread3.start()
    
    # Wait for all threads to finish
    thread1.join()
    thread2.join()
    thread3.join()


    print('Pumping stopped.')


#Serial Connection for TC
SERIALPORT_TC_Reference = "COM13"
BAUDRATE = 9600
serTCRef = serial.Serial(SERIALPORT_TC_Reference, BAUDRATE)
serTCRef.bytesize = serial.EIGHTBITS
serTCRef.parity = serial.PARITY_NONE
serTCRef.stopbits = serial.STOPBITS_ONE
serTCRef.timeout = 1        
serTCRef.xonxoff = False    
serTCRef.rtscts = False    
serTCRef.dsrdtr = False      
serTCRef.writeTimeout = 1
connected = False
serTCRef.isOpen()

def PumpReady_TC_Ref():
    while True:
        PumpNum = '1'
        COMMAND = 'F'
        command = '/' + PumpNum + COMMAND
        closemessage = 'R\r\n'
        c = command + closemessage
        serTCRef.write(bytes(c, 'utf-8'))
        time.sleep(0.1)
        readOut = serTCRef.readline()

        time.sleep(0.1)
        readOut = readOut[2:3].decode("utf-8")
        time.sleep(1)
        if readOut != "@" and readOut != "o":  
            break


def START_pump_TC_Ref(PumpNum, COMMAND):
        #print ("Writing:")
        command = '/'+PumpNum+ COMMAND
        closemessage='R\r\n'
        c=command + closemessage    
        serTCRef.write(bytes(c, 'utf-8'))
        #print(c)
        time.sleep(0.5)
        PumpReady_TC_Ref()
        time.sleep(0.51)
        while True:
            try:
                #print ("Attempt to Read")
                time.sleep(0.5)
                readOut = serTCRef.readline().decode("utf-8")
                time.sleep(0.5)
                #print ("Reading: ", readOut)
                d=c
                serTCRef.write(d)
                break
            except:
                if readOut == "0@":
                    break
                    ser.flush() #flush the buffer
                elif readOut !="0@":
                    pass
                    #print("Restart")
            break
            break

def PumpInitialize_TC_Ref ():
       # Set the pump at zero position
       INITIALIZE ='Y30z'
       START_pump_TC_Ref('1',INITIALIZE)
       ZeroPosition ='OV40A0'
       START_pump_TC_Ref('1',ZeroPosition)
       FillIn = 'OV40P6000'
       START_pump_TC_Ref('1',FillIn)

def PumpInjection_TC_Ref(x1,y1):
    #print("injection started")
    Stop1 = f'T'
    START_pump_TC_Ref('1',Stop1)
    Inject1 = f'EV{int(x1*8)}d{int(y1)}'
    #Inject1 = f'EV{int(x1*8)}v{int(x1*8)}c{int(x1*8)}d960'
    START_pump_TC_Ref('1',Inject1)
   

def PumpWithdraw_TC_Ref(x):
    Stop1 = f'T'
    START_pump_TC_Ref('1',Stop1)
    Refill1 = f'OV{int(x*8)}A6000'
    START_pump_TC_Ref('1',Refill1)

def PumpWithdraw_TC_Ref_Volume(x,y):
    Stop1 = f'T'
    START_pump_TC_Ref('1',Stop1)
    Refill1 = f'OV{x}A{y}'
    START_pump_TC_Ref('1',Refill1)

def PumpEmpty_TC_Ref(x1):
    Stop1 = f'T'
    START_pump_TC_Ref('1',Stop1)
    Inject1 = f'IV{int(x1*8)}A0'
    #Inject1 = f'EV{int(x1*8)}d960'
    START_pump_TC_Ref('1',Inject1)


def TC_Pumping_Calibration ():
    print('Filling TC Ref Channels with Ref Liquid.')
    PumpWithdraw_TC_Ref(5)
    PumpInjection_TC_Ref(8,6000)
    print('Cleaning solvent pump by air, getting it ready for ref liquid injection.')
    PumpEmpty_PumpSolvent(20)
    SolventPumpCleanedbyAir ()
    SolventPumpCleanedbyAir ()
    solventmode()
    print('Filling TC Sample Channel with Ref Liquid.')

    SolventPumpforTC()
    
#PumpInjection_TC_Ref(8,3000)



def Position_SamplePump1 ():
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    serSample1.write(bytes(c, 'utf-8'))
    POS=serSample1.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
    return CurrentPosition

def Position_SamplePump2 ():
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    serSample2.write(bytes(c, 'utf-8'))
    POS=serSample2.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
    return CurrentPosition

def Position_SamplePump3 ():
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    serSample3.write(bytes(c, 'utf-8'))
    POS=serSample3.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
    return CurrentPosition

def Position_HC_Pump1 ():
    PumpNum = '1'
    COMMAND = '?'
    command = '/'+PumpNum+ COMMAND
    closemessage='R\r\n'
    c=command + closemessage    
    ser1.write(bytes(c, 'utf-8'))
    POS=ser1.readline()
    print (POS)
    match = re.search(r"`(\d+)", POS.decode("utf-8"))

    if match:
    # Extract the matched number
        CurrentPosition = int(match.group(1))
    return CurrentPosition


#PumpInitialize_pump1()
#Stop_pump1_HC()
#EmptyHcSyringe(200)
#PumpInitialize_pumpSolvent()
#PumpInitialize_pump2()
#PumpInitialize_TC_Ref ()
#PumpWithdrawSolvent()

# for i in range(10):
#     if i==0 or i==2 or i==4 or i == 6 or i == 8:
#         PumpInitialize_pumpSolvent()
#     PumpInjection_pumpSolvent_Volume(8, 5000)

#InitialInjection_Pump1_HC()
#InitialInjection_Pump2_HC()

PumpInitialize_pump1()
PumpRefill_pump1(200)
PumpInjection_pump1_HC(10)