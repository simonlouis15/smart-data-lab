import serial
import time
import statistics

# Setting up EC
EC= serial.Serial(
    port='COM7',  
    baudrate=9600,
    bytesize=8,
    parity='N',   # No parity
    stopbits=1,
    timeout=1,    
    xonxoff=False,  # Disable software handshaking
    rtscts=False    # Disable hardware handshaking
)

def getECreading():
    response=EC.readall().decode().strip()
    #print(response)
    lines=response.split('\r')
    for line in lines:
        if line.strip() and line.strip().upper() != "*OK":
        #if line.strip():
            print(line)
            meas=float(line)
            #print(type(meas))
            return meas

def getECresponse():
    response=EC.readall().decode().strip()
    #print(response)
    lines=response.split('\r')
    for line in lines:
        if line.strip():
            print(line)
    

def ECsetup():
    EC.write(b'Find\r')
    response = EC.readline().decode().strip()
    print(f'check if sensor found: {response}')
    time.sleep(1)
    # Turn off cont. mode
    EC.write(b'C,0\r')
    response = EC.readline().decode().strip()
    print(f'turn off continuos mode: {response}')
    time.sleep(1)
    # enable EC measurement
    EC.write(b'O,EC,1\r')
    time.sleep(1)
    checkmeas=EC.readline().decode().strip()
    print(f'check if EC enabled: {checkmeas}')
    time.sleep(1)
    EC.write(b'O,?\r')
    checkmeas=EC.readline().decode().strip()
    print(f'check if EC enabled: {checkmeas}')
    # Set up K constant
    time.sleep(1)
    EC.write(b'K,0.01\r')
    time.sleep(1)
    EC.write(b'K,?\r')
    getECresponse()
    time.sleep(1)
    EC.write(b'T,?\r')
    getECresponse()

def takereading(x):
    a=0
    while a<x:
        EC.write(b'R\r')
        getECreading()
        time.sleep(0.1)
        #Temp.write(b'R\r')
        #gettempresponse()
        time.sleep(1)
        a+=1


def ECmeas():
    i=0
    EC_std=100
    EC_final=100
    EClist=[]
    while EC_std>0.1*EC_final and len(EClist)<10:
        EC.write(b'R\r')
        EC_meas=getECreading()
        time.sleep(1)
        i+=1
        EClist.append(EC_meas)
        print(len(EClist))
        if len(EClist)>=5:
            EC_final=statistics.mean(EClist[-5:])
            EC_std=statistics.stdev(EClist[-5:])
    print(f'EC reading is {EC_final}')
    return EC_final


def calibrationdry():
    EC.write(b'Cal,clear\r')
    time.sleep(1)
    response = EC.readline().decode().strip()
    print(response)
    takereading(10)
    time.sleep(5)
    EC.write(b'Cal,dry\r')
    response = EC.readline().decode().strip()
    print(response)
    time.sleep(5)
    takereading(5)

def calibrationone(x):
    takereading(10)
    time.sleep(5)
    inp=f'Cal,{x}\r'
    print(inp)
    EC.write(inp.encode('utf-8'))
    response = EC.readline().decode().strip()
    print(response)
    time.sleep(5)
    takereading(5)

def calibwithsolutionlow():
    takereading(30)
    EC.write(b'Cal,low,0.22\r')
    response = EC.readline().decode().strip()
    print(response)

def calibwithsolutionhigh():
    takereading(30)
    EC.write(b'Cal,high,80\r')
    response = EC.readline().decode().strip()
    print(response)
    time.sleep(1)
    EC.write(b'Cal,?\r')
    getECresponse()

def calibrateEC(x):
    calibrationdry()
    input('ready for standard solution')
    calibrationone(x)
    print('calibration done')

# Setting the parameters of EC sensor
#ECsetup()

# Calibration
#calibrateEC(5)

# Taking measurement
#ECmeas ()

