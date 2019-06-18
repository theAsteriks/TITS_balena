import os

if not os.path.exists('log_files'):
    os.makedirs('log_files')
    
os.system('find / -name \'platform.pyc\' -delete')

import time
import httpReq
import UART
import config
import constr_params
import supDB
import logging

logger = logging.getLogger(__name__)
logger.setLevel(config.MAIN_LOG_LEVEL)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(asctime)s:%(message)s')
file_handler = logging.FileHandler('log_files/main.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


##########################################################################
#################### GLOBAL VARIABLES ####################################
id = config.RPI_ID()
sub_boss = constr_params.GlobalVarMGR()
logger.debug("Initiated global variable holder")
wind_tracer = config.IS_WIND_TRACER(id)
io_counter = config.POLLING_INTERVAL
current_state = "ADMIN_IDLE"
max_wind_poll_counter = config.MAX_NO_WIND_DETECTION
wind_poll_counter = max_wind_poll_counter
ok_status = True

#########################################################################

#changing the local timezone to CET because the resin.io's default timezone is UTC

def set_local_time():
    os.environ['TZ'] = 'Europe/Brussels'
    time.tzset()
    logger.debug("Set the timezone to Brussels' timezone")

##############################################################################

def failureCheck():
    voltage = int(tracker_params[39])
    failure_byte = int(tracker_params[136])
    failure_set['overcurrentMotorA'] = failure_byte & 0x1
    failure_set['hallErrorA'] = (failure_byte & 0x2) >> 1
    failure_set['tooLogReferenceA'] = (failure_byte & 0x4) >> 2
    failure_set['cableErrorA'] = (failure_byte & 0x8) >> 3
    failure_set['overCurrentMotorB'] = (failure_byte & 0x10) >> 4
    failure_set['hallErrorB'] = (failure_byte & 0x20) >> 5
    failure_set['tooLogReferenceB'] = (failure_byte & 0x40) >> 6
    failure_set['cableErrorB'] = (failure_byte & 0x80) >> 7
    failure_set['powerFailure'] = (failure_byte & 0x100) >> 8
    failure_set['syncedMoveErr'] = (failure_byte & 0x400) >> 10
    failure_set['someButtonStuck'] = (failure_byte & 0x4000) >> 14
    failure_set['motorALosingHall'] = (failure_byte & 0x400000) >> 22
    failure_set['motorBLosingHall'] = (failure_byte & 0x800000) >> 23

def update_wind_counter_limit():
    global sub_boss
    global max_wind_poll_counter

    if sub_boss.tracer == True:
        wind_speed = sub_boss.tracker_params['avg_wind_speed']
    else:
        wind_speed = sub_boss.polled_wind_speed
    try:
        wind_speed = float(wind_speed)
        if wind_speed >= config.MAX_AVG_WIND_SPEED:
            max_wind_poll_counter = config.MAX_NO_WIND_DETECTION/9
            return
        for i in range(3,0,-1):
            if wind_speed >= (3-i)*config.MAX_AVG_WIND_SPEED/3 and \
            wind_speed < (4-i)*config.MAX_AVG_WIND_SPEED/3:
                max_wind_poll_counter = config.MAX_NO_WIND_DETECTION/3**(3-i)
                break
    except Exception as e:
        logger.exception(e)



def MAIN_FSM():
    global current_state
    global sub_boss


    if current_state == "NIGHT_IDLE":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking disabled':
            sub_boss.send_to_idle()
        time.sleep(config.NIGHT_SLEEP_TIME)
        return
    elif current_state == "WIND_IDLE":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking disabled':
            sub_boss.send_to_idle()
    elif current_state == "ADMIN_IDLE":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking disabled':
            sub_boss.send_to_idle()
        return
    elif current_state == "USER_IDLE":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking disabled':
            sub_boss.send_to_idle()
        return
    elif current_state == "EMERGENCY":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking disabled':
            sub_boss.send_to_idle()
        return

    elif current_state == "TRACKING":
        if sub_boss.tracker_params[config.d['Mode']] != 'tracking enabled':
            sub_boss.tracker_activate()
        sub_boss.tracker_update_motors()
        return
    else:
        current_state = "ADMIN_IDLE"
        return

def IO_MGR():
    global io_counter
    global current_state
    global id
    global sub_boss
    global max_wind_poll_counter
    global wind_poll_counter
    global ok_status

    if sub_boss.tracer == True:
        sub_boss.poll_tracker(max_wind_poll_counter)
        sub_boss.update_wind_ok(max_wind_poll_counter)
    else:
        if io_counter % 5 == 0:
            sub_boss.poll_tracker(max_wind_poll_counter)

    if io_counter == config.POLLING_INTERVAL:
        sub_boss.poll_server()
        sub_boss.update_cpu_temp()
        if sub_boss.tracer == False:
            sub_boss.db_update(current_state,max_wind_poll_counter)
        inst_status = True
        for each in sub_boss.bools.itervalues():
            inst_status = inst_status and each
            if inst_status == False:
                break
        ok_status = inst_status
        if ok_status == True:
            supDB.update_rpi_status(current_state)

    if wind_poll_counter >= max_wind_poll_counter:
        if sub_boss.tracer == True:
            sub_boss.db_update(current_state,max_wind_poll_counter)
        else:
            sub_boss.update_wind_ok(max_wind_poll_counter)

    if io_counter >= config.POLLING_INTERVAL:
        io_counter = 0
        sub_boss.reset_wifi()
    else:
        io_counter += 1

    update_wind_counter_limit()

    if wind_poll_counter >= max_wind_poll_counter:
        wind_poll_counter = 0
    else:
        if sub_boss.tracer == True:
            wind_poll_counter += 5
        else:
            wind_poll_counter += 2

def STATE_MGR():
    global current_state
    global sub_boss
    global ok_status

    if time.localtime()[3] not in range(8,20):
        if current_state != "NIGHT_IDLE":
            logger.info("Changing state from %s to NIGHT_IDLE"%current_state)
        current_state = "NIGHT_IDLE"
        return
    elif sub_boss.tracker_params[config.d['Mode']].__contains__('too far'):
        current_state = "NIGHT_IDLE"
        return
    elif sub_boss.tracker_params['wind_ok'] == 'NO':
        if current_state != "WIND_IDLE":
            logger.info("Changing state from %s to WIND_IDLE"%current_state)
        current_state = "WIND_IDLE"
        return
    elif sub_boss.server_params['admin_slot_on'] == 'NO':
        if current_state != "ADMIN_IDLE":
            logger.info("Changing state from %s to ADMIN_IDLE"%current_state)
        current_state = "ADMIN_IDLE"
        return
    elif sub_boss.server_params['availability'] == 'NO':
        if current_state != "USER_IDLE":
            logger.info("Changing state from %s to USER_IDLE"%current_state)
        current_state = "USER_IDLE"
        return
    elif ok_status == False:
        if current_state != "EMERGENCY":
            logger.info("Changing state from %s to EMERGENCY"%current_state)
        current_state = "EMERGENCY"
        return
    else:
        if current_state != "TRACKING":
            logger.info("Changing state from %s to TRACKING"%current_state)
        current_state = "TRACKING"

constr_params.set_PCB_time()
set_local_time()

if sub_boss.tracer == True:
    sub_boss.set_wind_factor()
sub_boss.clear_tracker_errors()


while True:

    IO_MGR()
    STATE_MGR()
    MAIN_FSM()

    time.sleep(1)
