import config
import supDB
import httpReq
import UART

import time
import logging
import ctypes
import csv

id = config.RPI_ID()
#id = 1

logger = logging.getLogger(__name__)
logger.setLevel(config.CONSTR_PARAMS_LOG_LEVEL)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(asctime)s:%(message)s')
file_handler = logging.FileHandler('log_files/constr_params.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def update_existing_keys(dictionary, new_dictionary):
    for key in new_dictionary.iterkeys():
        if dictionary.has_key(key):
            dictionary[key] = new_dictionary[key]

class GlobalVarMGR(object):
    def __init__(self):
        self.tracker_params = dict()
        for key in config.d.itervalues():
            self.tracker_params[key] = ''
        self.tracker_params['cpu_temp'] = ''
        self.tracker_params['wind_ok'] = 'YES'
        self.server_params = dict()
        for key in config.SERVER_PARAMS:
            self.server_params[key] = ''
        self.tracer = config.IS_WIND_TRACER(id)
        self.timings = {
            'last_http_req':time.time(),
            'last_db_update':time.time(),
            'last_tracker_poll':time.time(),
            'last_wind_poll':time.time(),
            'last_tracker_update':time.time(),
            'last_wifi_reset':time.time()
        }
        self.bools = {
            'db_updated':True,
            'http_polled':True,
            'tracker_polled':True,
            'wind_polled':True,
            'tracker_updated':True
        }
        if self.tracer == True:
            self.tracker_params['avg_wind_speed'] = 0.0
            self.tracker_params['avg_wind_speed2'] = 0.0
            self.wind_speed_array = []
            self.wind_speed_array2 = []
            self.wind_data = 'log_files/wind_measurements.csv'
            self.wind_data_first_write = None
#            try:
#                tablefile = open(self.wind_data,'w')
#                fieldnames = ['inst_wind_speed','avg_wind_speed','avg_wind_speed2','time']
#                writer = csv.DictWriter(tablefile,fieldnames = fieldnames)
#                writer.writeheader()
#            except Exception as err:
#                logger.exception(err)
#            finally:
#                tablefile.close()
        else:
            self.polled_wind_speed = 0.0

    def make_db_params(self,state):
        values = dict()
        if state != "TRACKING":
            values['current_position_H'] = self.tracker_params[config.d['Angle_A']]
            values['current_position_V'] = self.tracker_params[config.d['Angle_B']]
        else:
            values['current_position_H'] = self.tracker_params[61]
            values['current_position_V'] = self.tracker_params[62]
        values['target_position_H'] = self.server_params['target_position_H']
        values['target_position_V'] = self.server_params['target_position_V']
        values['cpu_temp'] = self.tracker_params['cpu_temp']
        values['wind_ok'] = self.tracker_params['wind_ok']
        if self.tracer == True:
            values['wind_speed'] = self.tracker_params['avg_wind_speed']
        else:
            values['wind_speed'] = self.polled_wind_speed
        return values

    def update_wind_ok(self,time_limit):
        if self.tracer == False:
            interm = supDB.db_wind_poll()
            if interm['ERROR'] == None and \
            time.time() - time.mktime(time.strptime(interm['last_modified'])) \
            < 2*time_limit:
                self.tracker_params['wind_ok'] = interm['wind_ok']
                self.polled_wind_speed = interm['wind_speed']
                self.timings['last_wind_poll'] = time.time()
                self.bools['wind_polled'] = True
            else:
                if interm['ERROR'] == None:
                    if self.bools['wind_polled'] == True:
                        supDB.update_rpi_status('Tracer DB_inactivity')
                        logger.warn("The tracer hasn't updated the db "
                        "for more than %d seconds"%(2*time_limit))
                    self.bools['wind_polled'] = False
                    self.tracker_params['wind_ok'] = 'NO'
                else:
                    if self.bools['wind_polled'] == True:
                        logger.warn("DB down for more than %d sec"%(2*time_limit))
                    self.bools['wind_polled'] = False
                    ##action on no wind detection
        else:
            speed_now = config.MAX_INST_WIND_SPEED/2
            speed_avg = config.MAX_AVG_WIND_SPEED/2
            try:
                speed_now = float(self.tracker_params[config.d['WindSpeed']])
                speed_avg = float(self.tracker_params['avg_wind_speed'])
            except Exception as err:
                logger.exception(err)

            if speed_now > config.MAX_INST_WIND_SPEED or speed_avg > \
            config.MAX_AVG_WIND_SPEED or self.bools['tracker_polled'] == False:
                self.tracker_params['wind_ok'] = 'NO'
            else:
                self.tracker_params['wind_ok'] = 'YES'
            if self.bools['tracker_polled'] == True:
                self.timings['last_wind_poll'] = time.time()
                self.bools['wind_polled'] = True
            else:
                if time.time() - self.timings['last_wind_poll'] > \
                2*time_limit:
                    if self.bools['wind_polled'] == True:
                        logger.warn("No wind detection for more than %d sec"%(2*time_limit))
                    self.bools['wind_polled'] = False
                    #action on no wind detection

    def update_cpu_temp(self):
        try:
            tempfile = open(config.CPU_TEMP_PATH,'r')
            temp = float(tempfile.readline())/1000
            self.tracker_params['cpu_temp'] = str(temp)
            if time.localtime()[4] % 10 == 0:
                logger.info("%2.1fC core temp"%temp)
            if temp > config.CPU_MAX_TEMP:
                logger.critical("Exceeding max cpu temperature, currently %fC"%temp)
                time.sleep(config.OVERTEMP_SLEEP_TIME)
        except Exception as err:
            logger.exception(err)
        finally:
            tempfile.close()

    def poll_server(self):
        interm = httpReq.poll_server_params()
        if interm['ERROR'] == None:
            self.timings['last_http_req'] = time.time()
            self.bools['http_polled'] = True
            update_existing_keys(self.server_params,interm)
        else:
            if time.time() - self.timings['last_http_req'] > config.MAX_SERVERDOWN_TIME:
                if self.bools['http_polled'] == True:
                    logger.warn("Server is inactive for more than %d seconds"%config.MAX_SERVERDOWN_TIME)
                    supDB.update_rpi_status("server_down")
                self.bools['http_polled'] = False
                ###actions on server/internet failure

    def poll_tracker(self,time_limit):
        interm = UART.poll_tracker_params()
        if interm['ERROR'] == None:
            self.timings['last_tracker_poll'] = time.time()
            self.bools['tracker_polled'] = True
            update_existing_keys(self.tracker_params,interm)
            if self.tracer == True:
                self.calc_avg_wind_speed()
        else:
            if self.tracer == True:
                if time.time() - self.timings['last_tracker_poll'] > time_limit:
                    if self.bools['tracker_polled'] == True:
                        supDB.update_rpi_status('tracer RS458 read failure')
                        logger.warn("tracer failed to poll the tracker for more than %d sec"%time_limit)
                    self.bools['tracker_polled'] = False
            else:
                if time.time() - self.timings['last_tracker_poll'] > config.MAX_UART_DOWN_TIME:
                    if self.bools['tracker_polled'] == True:
                        supDB.update_rpi_status('RS458 read failure')
                        logger.critical("RS485 read failure for more than %d seconds"\
                        %config.MAX_UART_DOWN_TIME)
                    self.bools['tracker_polled'] = False
                ## actions on RS458 read failure

    def tracker_update_motors(self):
        currentH = self.tracker_params[config.d['Target_Default_H']]
        currentV = self.tracker_params[config.d['Target_Default_V']]
        targetH = self.server_params['target_position_H']
        targetV = self.server_params['target_position_V']
        if currentH != targetH:
            successH = UART.send_write_command(config.d['Target_Default_H'],targetH)
        if currentV != targetV:
            successV = UART.send_write_command(config.d['Target_Default_V'],targetV)
        if successH['ERROR'] == None and successV['ERROR'] == None:
            self.timings['last_tracker_update'] = time.time()
            self.bools['tracker_updated'] = True
        else:
            if time.time() - self.timings['last_tracker_update'] > \
            config.MAX_UART_DOWN_TIME:
                if self.bools['tracker_updated'] == True:
                    supDB.update_rpi_status('RS458 write failure')
                    logger.warn("RS485 write failure for more than %d seconds"\
                    %config.MAX_UART_DOWN_TIME)
                self.bools['tracker_updated'] = 'False'
            ##action on failing to update the tracking target

    def tracker_activate(self):
        success = UART.send_write_command(config.d['Mode'],'y')
        if success['ERROR'] == None:
            self.timings['last_tracker_update'] = time.time()
            self.bools['tracker_updated'] = True
        else:
            if time.time() - self.timings['last_tracker_update'] > \
            config.MAX_UART_DOWN_TIME:
                if self.bools['tracker_updated'] == True:
                    supDB.update_rpi_status('RS458 write failure')
                    logger.warn("RS485 write failure for more than %d seconds"\
                    %config.MAX_UART_DOWN_TIME)
                self.bools['tracker_updated'] = 'False'

    def send_to_idle(self):
        success1 = UART.send_write_command(config.d['Mode'],'n')
        time.sleep(0.5)
        success2 = UART.send_write_command(config.d['Angle_A'],config.IDLEA)
        time.sleep(0.5)
        success3 = UART.send_write_command(config.d['Angle_B'], config.IDLEB)
        if success1['ERROR'] == None and success2['ERROR'] == None \
        and success3['ERROR'] == None:
            self.timings['last_tracker_update'] = time.time()
            self.bools['tracker_updated'] = True
        else:
            if time.time() - self.timings['last_tracker_update'] > config.MAX_UART_DOWN_TIME:
                if self.bools['tracker_updated'] == True:
                    logger.warn("RS485 write failure for more than %d seconds"\
                    %config.MAX_UART_DOWN_TIME)
                    supDB.update_rpi_status('RS458 write failure')
                self.bools['tracker_updated'] = 'False'
    def clear_tracker_errors(self):
        success = UART.send_write_command(136,'clear')
        if success['ERROR'] == None:
            self.timings['last_tracker_update'] = time.time()
            self.bools['tracker_updated'] = True
        else:
            if time.time() - self.timings['last_tracker_update'] > config.MAX_UART_DOWN_TIME:
                if self.bools['tracker_updated'] == True:
                    logger.warn("RS485 write failure for more than %d seconds"\
                    %config.MAX_UART_DOWN_TIME)
                    supDB.update_rpi_status('RS458 write failure')
                self.bools['tracker_updated'] = 'False'


    def set_wind_factor(self):
        success = UART.send_write_command(config.d['WindFactor'],config.WIND_MULTIPLIER)
        if success['ERROR'] == None:
            self.timings['last_tracker_update'] = time.time()
            self.bools['tracker_updated'] == True
        else:
            if time.time() - self.timings['last_tracker_update'] > config.MAX_UART_DOWN_TIME:
                if self.bools['tracker_updated'] == True:
                    logger.warn("RS485 write failure for more than %d seconds"\
                    %config.MAX_UART_DOWN_TIME)
                    supDB.update_rpi_status('RS458 write failure')
                self.bools['tracker_updated'] = 'False'


    def db_update(self,state,time_limit):
        new_db_values = self.make_db_params(state)
        success = supDB.db_update(new_db_values)
        if success['ERROR'] == None:
            self.timings['last_db_update'] = time.time()
            self.bools['db_updated'] = True
        else:
            if self.tracer == False:
                if time.time() - self.timings['last_db_update'] > \
                config.MAX_DB_DOWN_TIME:
                    if self.bools['db_updated'] == True:
                        logger.warn("DB update failure for more than %d seconds"\
                        %config.MAX_DB_DOWN_TIME)
                        self.bools['db_updated'] = False
            else:
                if time.time() - self.timings['last_db_update'] > (2*time_limit):
                    if self.bools['db_updated'] == True:
                        logger.critical("tracer DB_FAILURE for more than %d secs"\
                        %(2*time_limit))
                        self.bools['db_updated'] = False
    def reset_wifi(self):
    	if time.time() - self.timings['last_wifi_reset'] > config.WIFI_RESET_TIMER:
            librf = ctypes.cdll.LoadLibrary("./librf/rf_state32.so")
            librf.wifi_state(ctypes.c_int(1))
            time.sleep(10)
            librf.wifi_state(ctypes.c_int(0))
            self.timings['last_wifi_reset'] = time.time()

    def calc_avg_wind_speed(self):
        inst_wind_speed = 0.0
        try:
            inst_wind_speed += float(self.tracker_params[config.d['WindSpeed']])
        except Exception as e:
            logger.exception(e)
        if len(self.wind_speed_array) >= config.MAX_WIND_ARRAY_LENGTH:
            self.wind_speed_array.pop()
        if len(self.wind_speed_array2) >= 2*config.MAX_WIND_ARRAY_LENGTH:
            self.wind_speed_array2.pop()
        self.wind_speed_array.insert(0,inst_wind_speed)
        self.wind_speed_array2.insert(0,inst_wind_speed)
        sum = 0.0
        for velocity in self.wind_speed_array:
            sum += velocity
        self.tracker_params['avg_wind_speed'] = round(sum/len(self.wind_speed_array),2)
        sum = 0.0
        for velocity in self.wind_speed_array2:
            sum += velocity
        self.tracker_params['avg_wind_speed2'] = round(sum/len(self.wind_speed_array2),2)

def set_PCB_time():
    t = time.gmtime()
    UART.send_write_command(config.d["Seconds"],str(t[5]))
    time.sleep(0.5)
    UART.send_write_command(config.d["Minutes"],str(t[4]))
    time.sleep(0.5)
    UART.send_write_command(config.d["Hours"],str(t[3]))
    time.sleep(0.5)
    UART.send_write_command(config.d["Date"],str(t[2]))
    time.sleep(0.5)
    UART.send_write_command(config.d["Month"],str(t[1]))
#           NO WRITING THE WIND VALUES TO A FILE ANYMORE
#        try:
#            datafile = open(self.wind_data,'a')
#            fieldnames = ['inst_wind_speed','avg_wind_speed','avg_wind_speed2','time']
#            writer = csv.DictWriter(datafile,fieldnames = fieldnames)
#            if self.wind_data_first_write == None:
#                self.wind_data_first_write = int(time.time())
#            rowDict = {
#            'inst_wind_speed':inst_wind_speed,
#            'avg_wind_speed':self.tracker_params['avg_wind_speed'],
#            'avg_wind_speed2':self.tracker_params['avg_wind_speed2'],
#            'time':int(time.time())-self.wind_data_first_write
#            }
#            writer.writerow(rowDict)
#        except Exception as err:
#            logger.exception(err)
#        finally:
#            datafile.close()
