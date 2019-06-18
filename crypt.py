import os
import time
import config
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.kbkdf import \
(CounterLocation, KBKDFHMAC, Mode)
from cryptography.hazmat.backends import default_backend
import base64

class Disenchant(object):
  def __getSerialNum(self,file_location):
    found = False 
    with open(file_location,'r') as fileobj:
      for line in fileobj:
        if line.__contains__('Serial'):
          found = True
          break
      if found:
        return line[len(line)-17:len(line)-1]
      else:
        return ''
      
  def __genKey(self):
    label = "!There is the sun label"
    context = "!There is the sun context"
    kdf = KBKDFHMAC(algorithm=hashes.SHA256(),\
    mode=Mode.CounterMode,length=32,\
    rlen=4,\
    llen=4,\
    location=CounterLocation.BeforeFixed,\
    label=label,\
    context=context,\
    fixed=None,\
    backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(self.__getSerialNum(config.SER_N_FILE_LOC)))
  
  def getDBdata(self):
    fileobj = open('passes/pi'+str(config.RPI_ID())+'_pass.bin','rb')
    raw_data_list = list()
    text_data_list = list()
    db_item = ''
    
    while True:
      chip = fileobj.read(1)
      if chip == '':
        break
      if chip == chr(0):
        raw_data_list.append(db_item)
        db_item = ''
      else:
        db_item = db_item.__add__(chip)

    fileobj.close()
    key = self.__genKey()
    enigma = Fernet(key)
    for item in raw_data_list:
      word = enigma.decrypt(item)
      text_data_list.append(word)
    return text_data_list
