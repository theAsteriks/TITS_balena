import mysql.connector as connector
import config
import logging
import time
import crypt

db_data = crypt.Disenchant().getDBdata()
db_user = db_data[0]
db_pass = db_data[1]
db_host = db_data[2]
db_database = db_data[3]
db_status_table = db_data[4]
id = config.RPI_ID()

tracer_id = config.WIND_TRACER_ID()

logger = logging.getLogger(__name__)
logger.setLevel(config.DB_LOG_LEVEL)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(asctime)s:%(message)s')
file_handler = logging.FileHandler('log_files/supDB.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def db_connect():
    try:
        cnx = connector.connect(user = db_user, password = db_pass,
        host = db_host, database = db_database)
        logger.debug(repr(cnx))
        return cnx
    except connector.Error as e:
        logger.warning("Unable to connect to DB")
        error_response = dict()
        error_response['ERROR'] = 'YES'
        error_response['TYPE'] = 'DB_ERROR'
        error_response['INFO'] = e.msg
        return error_response


def db_update(new_values):
    return_dict = dict()
    cnx = db_connect()
    if type(cnx) is dict:
        return cnx
    current_position_H = new_values['current_position_H']
    current_position_V = new_values['current_position_V']
    target_position_H = new_values['target_position_H']
    target_position_V = new_values['target_position_V']
    cpu_temp = new_values['cpu_temp']
    wind_ok = new_values['wind_ok']
    wind_speed = new_values['wind_speed']
    query = ("UPDATE {} SET current_position_H = %s, current_position_V = %s, "
    "target_position_H = %s, target_position_V = %s, wind_ok = %s, "
    "cpu_temp = %s, wind_speed = %s, last_modified = %s "
    "WHERE mirror_ID = %s;".format(db_status_table))
    values = (current_position_H, current_position_V, target_position_H, \
    target_position_V, wind_ok, cpu_temp, wind_speed, time.asctime(), id)
    cursor = cnx.cursor()
    return_value = dict()
    try:
        cursor.execute(query, values)
        cnx.commit()
        return_value['ERROR'] = None
        return return_value
    except connector.Error as err:
        logger.exception(err)
        return_value['ERROR'] = 'YES'
        return_value['TYPE'] = 'DB_ERROR'
        return_value['INFO'] = err.msg
        return return_value
    finally:
        cursor.close()
        cnx.close()



def db_wind_poll():
    return_dict = dict()
    cnx = db_connect()
    if type(cnx) is dict:
        return cnx
    query = ("SELECT wind_speed, wind_ok, last_modified "
    "FROM {} WHERE mirror_ID = %s;".format(db_status_table))
    cursor = cnx.cursor()
    return_value = dict()
    try:
        cursor.execute(query,(tracer_id,))
        for (wind_speed, wind_ok, last_modified) in cursor:
            return_value['wind_speed'] = float(str(wind_speed))
            return_value['wind_ok'] = str(wind_ok)
            return_value['last_modified'] = str(last_modified)
            return_value['ERROR'] = None
            return return_value
    except connector.Error as err:
        logger.exception(err)
        return_value['ERROR'] = 'YES'
        return_value['TYPE'] = 'DB_ERROR'
        return_value['INFO'] = err.msg
        return return_value
    finally:
        cursor.close()
        cnx.close()

def update_rpi_status(status):
    return_dict = dict()
    cnx = db_connect()
    if type(cnx) is dict:
        return cnx
    query = "UPDATE {} SET rpi_status = %s, last_modified = %s "\
    "WHERE mirror_ID = %s;".format(db_status_table)
    cursor = cnx.cursor()
    try:
        cursor.execute(query,(status,time.asctime(),id))
        cnx.commit()
    except Exception as e:
        logger.exception(e)
    finally:
        cursor.close()
        cnx.close()
