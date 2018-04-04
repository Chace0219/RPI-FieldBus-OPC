
import sys

import serial
import random
from threading import Thread
import time
import json
from Inverter import INVERTER

DEFINE_MAX_ADDR = 125

OffLineCycle = 5 # Second unit
AP_ADDR = 0xB0
ACK = 0x06
NAK = 0x15

'''

'''
class CommQue(object):
    DestAddr = 0x7F
    ControlCode = 0x00
    FuncCode = 0x00
    DataLength = 0x00
    CommData = []
    InverterIndex = 0x7F

    def __init__(self, InverterIndex, Addr, Control, Func, Length, Ptr):
        self.InverterIndex = InverterIndex
        self.DestAddr = Addr
        self.ControlCode = Control
        self.FuncCode = Func
        self.DataLength = Length
        for index in range(0, Length):
            self.CommData.append(Ptr[index])

class InverterMonitor():
    # Global Variables
    Comm_Queue = []
    threadStop = False
    Inverters = []
    leftAddrs = []
    RS485Port = None
    CommThread = None
    RS485Buff = []

    def __init__(self):
        for index in range(0, DEFINE_MAX_ADDR):
            self.leftAddrs.append(index)
        for index in range(0, DEFINE_MAX_ADDR):
            self.RS485Buff.append('0')

        self.Off_Query_Cycle = time.time()
        # Serial port Open and Configuration
        try:
            # Check serial port availability
            self.RS485Port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1.0)
            self.RS485Port.close()
        except serial.SerialException, e:
            print "Serial port open error!" + str(e)
            sys.exit()

        return

    '''
    ************ Get random address function *********
    Parameter:

    Return value:
        8bit Random Address

    Function:
        When an inverter response to offline query, RPI program allocate one random address of unused addresses.
        And then program the address number pop from allocable address table.
    **************************************************
    '''
    def RandomAddrAlloc(self):
        nRes = -1
        nLeftCnt = len(self.leftAddrs)
        if(nLeftCnt > 0):
            nPtr = random.randint(0, nLeftCnt)
            nRes = self.leftAddrs.pop(nPtr)
        return nRes

    '''
    ************ Get random address function *********
    Parameter:
        8bit Inverter address
    Return value:
        None
    Function:
        When an inverter timeout detects by program, it pops inverter the address from Inverters Array.
        And then this function release the address to allocable address table, so others program can allocate it to other address.
    **************************************************
    '''
    def IncreaseAddr(self, RelAddr):
        nRes = -1
        nLeftCnt = len(self.leftAddrs)
        if(nLeftCnt < 126):
            nRes = self.leftAddrs.append(RelAddr)
        return

    '''
    ************Checksum calculation function*********
    Parameter:
        CheckData : Data buffer array
        nLength : nlength of frame to be calculated

    Return value:
        16bit Checksum
    **************************************************
    '''
    def calcChecksum(self, CheckData, nLength):
        # checksum
        CheckSum = 0x7FFF
        CheckSum = 0
        for index in range(0, nLength):
            CheckSum += CheckData[index]
        return CheckSum

    '''
    ************ Communication thread proc *********
    In this proc, program check periodically communication queue.
    And then if there is a
    **************************************************
    '''
    # Main Communication Thread Proc
    def CommThreadProc(self):
        '''
        self.RS485Port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=0.5)
        '''
        while(self.threadStop == False):
            try:
                if(len(self.Comm_Queue) > 0):
                    # pop up first queue
                    CurrQueue = self.Comm_Queue.pop(0)
                    print(len(self.Comm_Queue))

                    # Generate Query
                    self.RS485Buff[0] = 0xAA
                    self.RS485Buff[1] = 0x55
                    self.RS485Buff[2] = AP_ADDR
                    self.RS485Buff[3] = CurrQueue.DestAddr
                    self.RS485Buff[4] = CurrQueue.ControlCode
                    self.RS485Buff[5] = CurrQueue.FuncCode
                    self.RS485Buff[6] = CurrQueue.DataLength
                    for index in range(0, CurrQueue.DataLength):
                        self.RS485Buff[7 + index] = CurrQueue.CommData[index]
                    CheckSum = self.calcChecksum(self.RS485Buff, CurrQueue.DataLength + 7)
                    self.RS485Buff[CurrQueue.DataLength + 8] = CheckSum % 256
                    self.RS485Buff[CurrQueue.DataLength + 7] = CheckSum / 256
                    RequestLen = CurrQueue.DataLength + 9

                    # Flash buffer

                    self.RS485Port.flushInput()


                    # offline query request
                    if(CurrQueue.ControlCode == 0x00 and CurrQueue.FuncCode == 0x00):
                        print("RPI sent offline query!")

                        # send Request: Count - 8 Byte
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)
                        # Read Wait
                        RS485Buff = self.RS485Port.Read(25)

                        PacketLen = len(self.RS485Buff)
                        if(PacketLen != 25):
                            print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x00 and self.RS485Buff[5] == 0x80):
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                nCtrlCode = 0x00
                                nFuncCode = 0x01
                                CommData = []
                                for index in range(0, CurrQueue.DataLength):
                                    CommData.append(self.RS485Buff[7 + index])
                                nAddr = self.RandomAddrAlloc()
                                CommData.append(nAddr)
                                # Append Allocate Address Request queue
                                self.Comm_Queue.append(CommQue(0x7F, 0x7F, nCtrlCode, nFuncCode, 0x11, CommData))

                    # Address Allocate Request
                    elif(CurrQueue.ControlCode == 0x00 and CurrQueue.FuncCode == 0x01):
                        AllocAddr = 0

                        # Packet Write and read Response
                        self.RS485Port.write(self.RS485Buff)
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        AllocAddr = self.RS485Buff[23]
                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(25)

                        PacketLen = len(self.RS485Buff)
                        if(PacketLen != 26):
                            self.IncreaseAddr(AllocAddr)
                            print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x00 and self.RS485Buff[5] == 0x81):
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                self.Inverters.append(INVERTER())
                                self.Inverters[len(self.Inverters) - 1].Addr = AllocAddr

                                #
                                nCtrlCode = 0x01
                                nFuncCode = 0x02
                                CommData = []
                                CommData.append(0)
                                # Append Response ID Info Request queue
                                self.Comm_Queue.append(CommQue(len(self.Inverters) - 1, AllocAddr, nCtrlCode, nFuncCode, 0x00, CommData))

                    # Remove Register Packet
                    elif(CurrQueue.ControlCode == 0x00 and CurrQueue.FuncCode == 0x02):
                        #AllocAddr = 0

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(25)

                        PacketLen = len(self.RS485Buff)
                        if(PacketLen != 9):
                            print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x00 and self.RS485Buff[5] == 0x82):
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                self.IncreaseAddr(CurrQueue.DestAddr)
                                self.Inverters.remove(CurrQueue.InverterIndex)
                                print("Remove Inverter Address - %d" % CurrQueue.DestAddr)

                    # Control Code Read
                    # Query Running Info List
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x01):
                        PacketLen = len(self.RS485Buff)


                        #  Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(11)

                        if(PacketLen != 11):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure(Addr:%d), I will unregister this inverter!" % CommQue.DestAddr)
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                # Query Running Info List
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x81):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                DataIndex = CurrQueue.Data[0]
                                DataValue = self.RS485Buff[7] * 256 + self.RS485Buff[8]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Reading_Lists'][DataIndex]['Value'] = DataValue

                    # Query ID Info List
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x02):

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(73)

                        PacketLen = len(self.RS485Buff)
                        if(PacketLen != 73):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                # Query Running Info List
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x82):
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                self.Inverters[CurrQueue.InverterIndex].FirmwareVer = self.RS485Buff[7:12]
                                self.Inverters[CurrQueue.InverterIndex].ModelName = self.RS485Buff[12:22]
                                self.Inverters[CurrQueue.InverterIndex].Manufacture = self.RS485Buff[22:38]
                                self.Inverters[CurrQueue.InverterIndex].SerialNumber = self.RS485Buff[38:54]
                                self.Inverters[CurrQueue.InverterIndex].Nom_Vpv = self.RS485Buff[54:58]
                                self.Inverters[CurrQueue.InverterIndex].InternalVersion = self.RS485Buff[58:70]
                                self.Inverters[CurrQueue.InverterIndex].SafetyConutryCode = self.RS485Buff[70:72]

                    # Query Setting Info
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x03):

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(21)

                        PacketLen = len(self.RS485Buff)
                        if PacketLen != 21:
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                # Query Running Info List
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x83):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # calc checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['Vpv-Start']['Value'] = \
                                    self.RS485Buff[7] * 256 + self.RS485Buff[8]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['T_Start']['Value'] = \
                                    self.RS485Buff[10] * 256 + self.RS485Buff[11]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['Vac_Min']['Value'] = \
                                    self.RS485Buff[12] * 256 + self.RS485Buff[13]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['Vac_Max']['Value'] = \
                                    self.RS485Buff[14] * 256 + self.RS485Buff[15]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['Fac_Min']['Value'] = \
                                    self.RS485Buff[16] * 256 + self.RS485Buff[17]
                                self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Setting_Lists']['Fac_Max']['Value'] = \
                                    self.RS485Buff[18] * 256 + self.RS485Buff[19]

                    # Query Error Message
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x04):

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(13)

                        PacketLen = len(self.RS485Buff)
                        if PacketLen != 13:
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x84):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # Calc Checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                ErrorStatus = self.RS485Buff[7]
                                ErrorStatus = (ErrorStatus >> 8) + self.RS485Buff[8]
                                ErrorStatus = (ErrorStatus >> 8) + self.RS485Buff[9]
                                ErrorStatus = (ErrorStatus >> 8) + self.RS485Buff[10]

                    # Read Storage Running Info
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x06):
                        DataIndex = self.RS485Buff[7]

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(DataLen + 9)


                        DataLen = self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Storage_Info'][DataIndex]['Length']

                        PacketLen = len(self.RS485Buff)
                        if PacketLen != (DataLen + 9):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x86):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # Calc Checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                if(DataLen == 1):
                                    self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Storage_Info'][DataIndex]['Value'] = self.RS485Buff[7]
                                else:
                                    self.Inverters[CurrQueue.InverterIndex].RunningInfoList['Storage_Info'][DataIndex]['Value'] = \
                                        self.RS485Buff[7] * 256 + self.RS485Buff[8]

                    # Read RTC Time Value
                    elif(CurrQueue.ControlCode == 0x01 and CurrQueue.FuncCode == 0x07):

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(15)


                        PacketLen = len(self.RS485Buff)
                        if PacketLen != 15:
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x01 and self.RS485Buff[5] == 0x87):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # Calc Checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                self.Inverters[CurrQueue.InverterIndex].Year = self.RS485Buff[7];
                                self.Inverters[CurrQueue.InverterIndex].Month = self.RS485Buff[8];
                                self.Inverters[CurrQueue.InverterIndex].Date = self.RS485Buff[9];
                                self.Inverters[CurrQueue.InverterIndex].Hour = self.RS485Buff[10];
                                self.Inverters[CurrQueue.InverterIndex].Minute = self.RS485Buff[11];
                                self.Inverters[CurrQueue.InverterIndex].Second = self.RS485Buff[12];

                    # Control Code 0x03
                    elif(CurrQueue.ControlCode == 0x03): # and CurrQueue.FuncCode == 0x01):

                        # Packet Write and read Response
                        for index in range(0, RequestLen):
                            self.RS485Port.write(self.RS485Buff[index])
                        time.sleep(0.05)

                        # Read Wait
                        self.RS485Buff = self.RS485Port.Read(10)

                        PacketLen = len(self.RS485Buff)
                        if PacketLen != 10:
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt += 1
                            if(self.Inverters[CurrQueue.InverterIndex].ErrorCnt == 3):
                                print("Inverter Communication failure, I will unregister this inverter!")
                                self.IncreaseAddr(self.Inverters[CurrQueue.InverterIndex].Addr)
                                self.Inverters.pop(CurrQueue.InverterIndex)
                            else:
                                self.Comm_Queue.append(CurrQueue)
                                print("Timeout or Communication  Error!")
                        elif(self.RS485Buff[4] == 0x03 and self.RS485Buff[5] == (0x80 + CurrQueue.FuncCode)):
                            self.Inverters[CurrQueue.InverterIndex].ErrorCnt = 0
                            # Calc Checksum
                            CheckSum = self.calcChecksum(self.RS485Buff, PacketLen - 2)
                            # Checking
                            if(CheckSum != (self.RS485Buff[PacketLen - 2] * 256 + self.RS485Buff[PacketLen - 1])):
                                if(self.RS485Buff[7] == ACK):
                                    print("Excute Command Successful, Func Code: %d" % CurrQueue.FuncCode)
                                else:
                                    print("Excute Command Fail, Func Code: %d" % CurrQueue.FuncCode)

            except serial.SerialException, e:
                print "Serial port error" + str(e)
        print("Program done!")

    # Get Running Info list with Dataindex and Inverter index
    def GetRunningInfo(self, InverterIndex, DataIndex):
        CommData = []
        CommData.append(DataIndex)
        # Example of adding read Running Info to queue
        # Control Code: 0x01, Func Code: 0x01, DataLen, 0x00, CommData: DataIndex of Running Info
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x01, 0x01, 0x00, CommData))

    def perform(self):
        mytime = time.time()
        CommThread = Thread(target=self.CommThreadProc, args=())
        print("Communication threading started!!!")

        ################ Usage Example Code
        '''
        self.Inverters.append(INVERTER())
        self.Inverters[len(self.Inverters) - 1].Addr = 0x03

        # Control Code 0x03 Example: Set RTC Time Command
        # 0 - inverter index, 16: Year, 10: Month, 2:Date, 12: Hour, 15: Minute, 17: Second
        self.SetRTCTime(0, 16, 10, 2, 12, 15, 17)

        # Control Code 0x01 Example: Read PV1 Voltage value
        # 0: Invertert index, 0x00: Running Info Index
        Self.GetRunningInfo(0, 0x00)

        time.sleep(1)
        print("PV1 voltage is %d" % self.Inverters[0].RunningInfoList['Reading_Lists'][0]['Value'])
        '''

        # Communication Thread Start
        CommThread.start()

        while self.threadStop == False:
            if(time.time() > (mytime + OffLineCycle)):
                mytime = time.time()
                OL_QueryThread = Thread(target=self.OffLineQuery, args=())
                OL_QueryThread.start()

            # Offline query Interval it would be changed
            time.sleep(5)

    def OffLineQuery(self):
        CommData = []
        CommData.append(0)
        self.Comm_Queue.append(CommQue(0x7F, 0x7F, 0x00, 0x00, 0x00, CommData))

    def SetSafetyCountry(self, InverterIndex, CountryCode):
        CommData = []
        CommData.append(CountryCode)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x01, 0x01, CommData))

    # Set RTC Time Value
    def SetRTCTime(self, InverterIndex, YY, MM, DD, Hr, Min, Sec):
        CommData = []
        CommData.append(YY)
        CommData.append(MM)
        CommData.append(DD)
        CommData.append(Hr)
        CommData.append(Min)
        CommData.append(Sec)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x02, 0x06, CommData))

    ########## Control Code 0x03
    # Z21 Reset Inverter
    def ResetInverter(self, InverterIndex):
        CommData = []
        CommData.append(0)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x1D, 0x00, CommData))

    # Z20 Start Inverter
    def StartInverter(self, InverterIndex):
        CommData = []
        CommData.append(0)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x1B, 0x00, CommData))

    # Z20 Stop Inverter
    def StopInverter(self, InverterIndex):
        CommData = []
        CommData.append(0)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x1C, 0x00, CommData))

    # Z20 Adjust Real Power
    def StopInverter(self, InverterIndex, Percent):
        CommData = []
        CommData.append(Percent)
        self.Comm_Queue.append(CommQue(InverterIndex, self.Inverters[InverterIndex].Addr, 0x03, 0x1E, 0x01, CommData))

if __name__ == "__main__":
    MyManager = InverterMonitor()
    ## Method
    MyManager.perform()
