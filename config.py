d = dict()

d["PCB_version"] = 37
d["Version"] = 38
d["U_solar"] = 39
d["Hours"] = 40
d["Minutes"] = 41
d["Seconds"] = 42
d["Date"] = 43
d["Angle_A"] = 44
d["Position_A"] = 45
d["Destination_A"] = 46
d["Current_A"] = 47
d["Angle_B"] = 48
d["Position_B"] = 49
d["Destination_B"] = 50
d["Current_B"] = 51
d["Latitude"] = 52
d["Longitude"] = 53
d["Moving_Interval"] = 54
d["Boot"] = 55
d["Mode"] = 56
d["Navigation"] = 57
d["Service"] = 58
d["Month"] = 59
d["Year"] = 60
d["Target_Default_H"] = 61
d["Target_Default_V"] = 62
d["A1_A"] = 70
d["A2_A"] = 71
d["A3_A"] = 72
d["A4_A"] = 73
d["A5_A"] = 74
d["A6_A"] = 75
d["B1_A"] = 76
d["B2_A"] = 77
d["Gear_ratio_A"] = 78
d["Max_range_A"] = 79
d["Coordinate_mode_A"] = 80
d["SyncAB_diff"] = 81
d["Geometry_mode_A"] = 83
d["USolar_factor"] = 84
d["Imotor_factor_A"] = 85
d["Cflags"] = 86
d["ID_number1"] = 87
d["ID_number2"] = 88
d["ID_number3"] = 89
d["Slave_id"] = 90
d["Buyflags"] = 91
d["WidePanelA"] = 94
d["SpacePanelA"] = 95
d["A1_B"] = 96
d["A2_B"] = 97
d["A3_B"] = 98
d["A4_B"] = 99
d["A5_B"] = 100
d["A6_B"] = 101
d["B1_B"] = 102
d["B2_B"] = 103
d["Gear_ratio_B"] = 104
d["Max_range_B"] = 105
d["Coordinate_mode_B"] = 106
d["Geometry_mode_B"] = 107
d["Night_position_A"] = 108
d["Night_position_B"] = 109
d["Min_range_A"] = 110
d["Min_range_B"] = 111
d["Max_Imotor_A"] = 112
d["Max_Imotor_B"] = 113
d["Imotor_factor_B"] = 114
d["Link_ok"] =  115
d["RTC_correction"] = 116
d["Goref_Nday_A"] = 117
d["Goref_Nday_B"] = 118
d["WindSpeed"] = 119
d["WindSpeedThreshold"] = 120
d["WindDestinationA"] = 122
d["WindDestinationB"] = 123
d["WindFactor"] = 124
d["FocusSensorOutputA"] = 128
d["FocusSensorOutputB"] = 129
d["FocusMiddleA"] = 130
d["FocusMiddleB"] = 131
d["WindFallTime"] = 133
d["FocusOffsetA"] = 134
d["FocusOffsetB"] = 135
d["Status"] = 136
d["WidePanelB"] = 137
d["SpacePanelB"] = 138
d["OverTempShift"] = 139
d["OTemp_shift_timeout"] = 140

mac_table = ("b8:27:eb:07:71:18", "b8:27:eb:33:21:a8", "b8:27:eb:e4:6b:d8")
SER_N_FILE_LOC = "/proc/cpuinfo"

CPU_MAX_TEMP = 70.0
SERIAL_PORT = '/dev/ttyAMA0'
MAX_UART_RECEIVE_LENGTH = 150
WIFI_INTERFACE = 'wlan0'
CPU_TEMP_PATH = '/sys/class/thermal/thermal_zone0/temp'
IDLEA = '0.0'
IDLEB = '89.9'
NIGHT_SLEEP_TIME = 1800

POLLING_INTERVAL = 30
POLLING_URL = 'http://www.thereisthesun.be/rpiretrievecurrentapid.php'
WIFI_RESET_TIMER = 7200 # 2 hours

MAX_SERVERDOWN_TIME = 300
MAX_DB_DOWN_TIME = 150
MAX_UART_DOWN_TIME = 120
MAX_AVG_WIND_SPEED = 15.0
MAX_WIND_ARRAY_LENGTH = 50
MAX_INST_WIND_SPEED = 35.0
MAX_NO_WIND_DETECTION = 90
OVERHEAT_SLEEP_TIME = 300


WIND_MULTIPLIER = '2.44'
SERVER_PARAMS = ('target_position_H','target_position_V','mirror_ID','time','availability','admin_slot_on')

DB_STATUS_TABLE_COLUMNS = ('current_position_H','current_position_V',
    'target_position_H','target_position_V','cpu_temp','rpi_status',
    'wind_speed','wind_ok')

MAIN_LOG_LEVEL = 20
CONSTR_PARAMS_LOG_LEVEL = 20
UART_LOG_LEVEL = 30
DB_LOG_LEVEL = 30
HTTP_LOG_LEVEL = 30

def RPI_ID():
    macfile = None
    mac = "00:00:00:00:00:00"
    try:
        macFile = open('/sys/class/net/'+WIFI_INTERFACE+'/address')
    except Exception as e:
        return -1
    else:
        mac = macFile.readline()[0:17]
        macFile.close()
    finally:
        if mac == mac_table[0]:
            return 1
        elif mac == mac_table[1]:
            return 2
        elif mac == mac_table[2]:
            return 3
        else:
            return -1

def IS_WIND_TRACER(rpi_id):
    z = rpi_id
    if z == 1:
        return False
    elif z == 2:
        return False
    elif z == 3:
        return True
    else:
        return False

def WIND_TRACER_ID():
    for i in range(1,4):
        if IS_WIND_TRACER(i) == True:
            return i
    return -1
