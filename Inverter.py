
'''

'''
import json

# Json format Running Info list string
Running_Info = '''
{
    "Setting_Lists" :
        {
            "Vpv-Start":
            {
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "PV1 start-up voltage",
                "Length" : 2,
                "Value" : 0
            },

            "T_Start":
            {
                "Unit": "Sec",
                "UnitVal" : 1,
                "Description" : "Time to connect grid",
                "Length" : 2,
                "Value" : 0
            },

            "Vac_Min":
            {
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "Minimum operational grid voltage",
                "Length" : 2,
                "Value" : 0
            },

            "Vac_Max":
            {
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "Maximum operational grid voltage",
                "Length" : 2,
                "Value" : 0
            },

            "Fac_Min":
            {
                "Unit": "V",
                "UnitVal" : 0.01,
                "Description" : "Minimum operational grid Frequency",
                "Length" : 2,
                "Value" : 0
            },

            "Fac-Max":
            {
                "Unit": "V",
                "UnitVal" : 0.01,
                "Description" : "Maximum operational grid Frequency",
                "Length" : 2,
                "Value" : 0
            }
        },

    "Storage_Info" :
        [
            {
                "Data_Index": 0,
                "Measuring_chn": "Vpv1",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "PV1 voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 1,
                "Measuring_chn": "Ipv1",
                "Unit": "A",
                "UnitVal" : 0.1,
                "Description" : "PV1 current",
                "Length" : 2,
                "Value" : 0
            }

        ],

    "Reading_Lists" :
        [
            {
                "Data_Index": 0,
                "Measuring_chn": "Vpv1",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "PV1 voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 1,
                "Measuring_chn": "Vpv2",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "PV2 voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 2,
                "Measuring_chn": "Ipv1",
                "Unit": "A",
                "UnitVal" : 0.1,
                "Description" : "PV1 current",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 3,
                "Measuring_chn": "Ipv2",
                "Unit": "A",
                "UnitVal" : 0.1,
                "Description" : "PV2 current",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 4,
                "Measuring_chn": "Vac1",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "Phase L1 Voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 5,
                "Measuring_chn": "Vac2",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "Phase L2 Voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 6,
                "Measuring_chn": "Vac3",
                "Unit": "V",
                "UnitVal" : 0.1,
                "Description" : "Phase L3 Voltage",
                "Length" : 2,
                "Value" : 0
            },

            {
                "Data_Index": 7,
                "Measuring_chn": "Iac1",
                "Unit": "A",
                "UnitVal" : 0.1,
                "Description" : "Phase L1 Current",
                "Length" : 2,
                "Value" : 0
            }
        ]
}
'''
'''
********** Invert Class*****
    It consists various spec info variables and assignments by communication flow.
    ex: Addr: Alloaction communication address
    It could be added as our requirements.
'''
class INVERTER():

    DeviceType = 0x00 #

    FirmwareVer = [] # 5 Byte
    ModelName = [] # 10 Byte
    Manufacture = [] # 16 Byte
    SerialNumber = [] # 16 Byte
    Nom_Vpv = [] # 4 Byte
    InternalVersion = [] # 12 Byte
    SafetyConutryCode = 0 # 1 Byte

    ###
    Vpv_Start = 0 # PV Start-up Voltage
    T_Start = 0 # Time to connect grid
    Vac_Min = 0 # Minimum operational grid voltage
    Vac_Max = 0 # Maximum operational grid voltage
    Fac_Min = 0 # Minimum operational grid Frequency
    Fac_Max = 0 # Maximum operational grid Frequency

    ### RTC Time value
    Year = 0;
    Month = 0;
    Date = 0;
    Hour = 0;
    Minute = 0;
    Second = 0;

    def __init__(self):
        self.ErrorCnt = 0
        self.Addr = 0x7F
        # Json to Array
        self.RunningInfoList = json.loads(Running_Info)
        for index in range(0, 10):
            self.FirmwareVer.append('0')
        for index in range(0, 20):
            self.ModelName.append('A')
        for index in range(0, 20):
            self.Manufacture.append('A')
            self.SerialNumber.append('A')
            self.InternalVersion.append('0')
        for index in range(0, 10):
            self.Nom_Vpv.append('0')
