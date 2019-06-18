import config
import time
import serial
import RPi.GPIO as GPIO
import logging


#############     UART configuration
port = config.SERIAL_PORT
baud = 19200
bytesize = serial.EIGHTBITS
parity = serial.PARITY_EVEN
stopbits = serial.STOPBITS_ONE
read_timeout = 0.5
xonxoff = False
id = config.RPI_ID()
#id = 1

logger = logging.getLogger(__name__)
logger.setLevel(config.UART_LOG_LEVEL)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(asctime)s:%(message)s')
file_handler = logging.FileHandler('log_files/UART.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def init_UART():
    try:
        channel = serial.Serial(port, baud, bytesize, parity, stopbits, read_timeout, xonxoff)
        logger.debug("Successfully created a serial port")
        return channel
    except serial.SerialException as e:
        logger.exception(e)
        error_dict = dict()
        error_dict['ERROR'] = 'YES'
        error_dict['TYPE'] = 'PYSERIAL'
        error_dict['INFO'] = e.errno
        return error_dict


def pins_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT, initial = GPIO.HIGH)

def pins_close():
    GPIO.cleanup()

def RS485_send(command, port):
    to_send = bytearray(command)
    nr = port.write(to_send)
    time.sleep(len(to_send)*0.00057)
    return nr


def RS485_read(port):
    msg = port.read(config.MAX_UART_RECEIVE_LENGTH)
    return bytearray(msg)

def CRC_GEN(stream):
    data = bytearray(stream)
    crc_calc = 0xffff
    for chunk in data:
        crc_calc ^= chunk
        for _ in range(0,8):
            lsb = crc_calc & 0x0001
            if lsb != 0:
                crc_calc >>= 1
                crc_calc ^= 0xa001
            else:
                crc_calc >>= 1
    byte1 = crc_calc
    byte1 &= 0xff00
    byte1 >>= 8
    byte2 = crc_calc & 0x00ff
    return bytearray([byte2, byte1])


def is_valid_msg(msg):
    if len(msg) < 4:
        return False
    if msg[0] != id:
        logger.debug("Invalid machinID %d in a UART response, local ID is %d"%(msg[0],id))
        return False
    header = msg[0:len(msg)-2]
    crc = msg[len(msg)-2:len(msg)]
    #### THE real CRC check:
    if crc != CRC_GEN(header):
        logger.warn("INVALID CRC message")
        return False
    return True


def parse_msg(msg):
    if is_valid_msg(msg) == False:
        return  dict()
    output = dict()
    i = 0
    while i < len(msg):
        if msg[i] == 0x24:
            i += 1
            bin = msg[i]
            value = ''
            i += 1
            while i < len(msg)-2 and msg[i] != 0x24:
                value += chr(msg[i])
                i += 1
            output[bin] = value
        else:
            i += 1
    return output

def send_write_command(bin, value):
    command = bytearray([id,0x20,0x24])
    command.append(bin)
    command += bytearray(value)
    command += CRC_GEN(command)
    tunnel = init_UART()
    if type(tunnel) is dict:
        return tunnel
    pins_setup()
    GPIO.output(18, GPIO.LOW) # driving the READ/#WRITE pin low for transmitting
    try:
        sent = RS485_send(command,tunnel)
        GPIO.output(18, GPIO.HIGH) # driving the READ/#WRITE pin low for receiving
        sent_back = RS485_read(tunnel)
        pins_close()
    except Exception as e:
        logger.exception(e)
        error_dict = dict()
        error_dict['ERROR'] = 'YES'
        error_dict['TYPE'] = 'PYSERIAL'
        error_dict['INFO'] = e
        pins_close()
        return error_dict

    if sent == len(command) and sent_back[0:2] == bytearray([id,0x20]):
        return {'ERROR':None}
    else:
        logger.error("Invalid response of a write command")
        logger.warn("sent %s - received %s"%(command,sent_back))
        return {
        'ERROR':'YES',
        'TYPE':'PYSERIAL',
        'INFO':'INVALID_RESPONSE'
        }

def poll_tracker_params():
    tunnel = init_UART()
    if type(tunnel) is dict:
        return tunnel
    params = dict()
    pins_setup()
    for i in range(0x10,0x17):
        try:
            command = bytearray([id,i])
            command += CRC_GEN(command)
            GPIO.output(18, GPIO.LOW) #Transmition
            RS485_send(command,tunnel)
            GPIO.output(18, GPIO.HIGH) # receiving
            response = RS485_read(tunnel)
            parsed = parse_msg(response)
            params.update(parsed)
        except Exception as e:
            logger.info(e)
            params['ERROR'] = 'YES'
            params['TYPE'] = 'PYSERIAL'
            params['INFO'] = e
            pins_close()
            return params
    if tunnel.is_open:
        tunnel.flushOutput()
        tunnel.close()
    pins_close()
    if len(params) < 50:
        logger.info("Unusually short message of %d characters"%len(params))
        params['ERROR'] = 'YES'
        params['TYPE'] = 'PYSERIAL'
        params['INFO'] = 'TOO_SHORT'
        return params
    params['ERROR'] = None
    return params
