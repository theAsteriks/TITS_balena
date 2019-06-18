import requests
import json
import config
import time
import logging
import os

id = config.RPI_ID()
#id = 1
polling_url = config.POLLING_URL

logger = logging.getLogger(__name__)
logger.setLevel(config.HTTP_LOG_LEVEL)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(asctime)s:%(message)s')
file_handler = logging.FileHandler('log_files/httpReq.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def poll_server_params():
    i = 0
    for i in range(0,5):
        try:
            response = requests.get(polling_url, timeout = 5)
            break
        except Exception as e:
            logger.debug("%i timeouts as of now"%i)
            if i == 4:
                i += 1
    if i > 4:
        error_dict = dict()
        error_dict['ERROR'] = 'YES'
        error_dict['TYPE'] = 'HTTPREQ'
        error_dict['INFO'] = '5 TIMEOUTS'
        return error_dict
    logger.debug("status code of the response %d"%response.status_code)
    if response.status_code != requests.codes.ok:
        error_dict = dict()
        error_dict['ERROR'] = 'YES'
        error_dict['TYPE'] = 'HTTPREQ'
        error_dict['INFO'] = 'BAD_REQUEST'
        logger.warn("HTTP status code was %i"%response.status_code)
        return error_dict

    if response.text == '0 results':
        logger.warn("Zero results reponse")
        response = dict()
        response['availability'] = 'NO'
        response['ERROR'] = None
        return response
    else:
        json_array = json.loads(response.text)
        response = dict()
        logger.debug("NR of results->%i"%len(json_array))
        for each in json_array:
            try:
                if int(each['mirror_ID']) == id:
                    if int(each['time']) == (time.localtime(time.time())[3]):# to remove the '+2' as the time will be set in the main
                        dict_v = "V{}".format(id)
                        dict_h = "H{}".format(id)
                        if each.has_key(dict_h) and each.has_key(dict_h):
                            response['target_position_H'] = str(each[dict_h])
                            response['target_position_V'] = str(each[dict_v])
                            response['mirror_ID'] = str(each['mirror_ID'])
                            response['time'] = str(each['time'])
                            response['availability'] = str(each['availability'])
                            response['admin_slot_on'] = str(each['admin_slot_on'])
                            response['ERROR'] = None
                            return response
                        else:
                            logger.error("No target position for mirror ID "+str(id))
                            response['ERROR'] = 'YES'
                            response['TYPE'] = 'HTTPREQ'
                            response['INFO'] = 'TARGET_HV_MISMATCH'
                            return response
                    else:
                        logger.error("Mismatch of server time and local time")
                        response['ERROR'] = 'YES'
                        response['TYPE'] = 'HTTPREQ'
                        response['INFO'] = 'SERVER_TIME_MISMATCH'
                        return response
            except Exception as e:
                logger.warning("Unable to convert server response to JSON->%s"%str(json_array))
        logger.error("No coordinates for mirror_ID %d"%id)
        response['ERROR'] = 'YES'
        response['INFO'] = 'LACK_LOCAL_ID'
        response['TYPE'] = 'HTTPREQ'
        return response
