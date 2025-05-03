import binascii
import serial
import time
import logging

logging.basicConfig(
    #level=logging.INFO
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
    )

class FingerprintManager:
    def __init__(self, port='/dev/ttyUSB0', baudrate=57600):
        try:
            self.ser = serial.Serial(port, baudrate)
            logging.info("chuankou dakai chenggong")
        except serial.SerialException as e:
            logging.error(f"chuankou dakai shibai :{str(e)}")
            
        self._init_commands()
        self.head = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00'
        self.link = b'\x07\x13\x00\x00\x00\x00\x00\x1B'
        self.readflash = b'\x03\x16\x00\x1A'
        self.readmould = b'\x03\x1D\x00\x21'
        self.readindex = b'\x04\x1F\x00\x00\x24'
        self.readindex1 = b'\x04\x1F\x01\x00\x25'
        self.cmd_search = b'\x03\x01\x00\x05'
        self.cmd_upload = b'\x03\x0A\x00\x0E'
        self.cmd_gen1 = b'\x04\x02\x01\x00\x08'
        self.cmd_gen2 = b'\x04\x02\x02\x00\x09'
        self.cmd_reg = b'\x03\x05\x00\x09'
        self.cmd_save = b'\x06\x06\x01\x00'
        self.cmd_dis = b'\x08\x04\x01\x00\x00\x01\x2C\x00\x3B'
        self.cmd_deletchar = b'\x07\x0c\x00'

    def _init_commands(self):
        pass  

    def sendcmd(self, cmd):
        self.ser.write(self.head)
        self.ser.write(cmd)
        time.sleep(0.35)

    def init(self):
        logging.info("csh kaishi...")
        try:
            self.sendcmd(self.link)
            self.sendcmd(self.readflash)
            self.sendcmd(self.readmould)
            self.sendcmd(self.readindex)
            self.ser.flushInput()
            self.sendcmd(self.readindex1)
            count = self.ser.inWaiting()
            recv = self.ser.read(count)
            self.ser.flushInput()
            logging.info("csh wanchengong ")
        except Exception as e:
            logging.error(f"csh shiabi: {str(e)}...")

    def searchfig(self):
        logging.info("kaishi zhaozhiwen...")
        try:
            start_time = time.time()
            timeout = 3
            while True:
                self.sendcmd(self.cmd_search)
                time.sleep(0.1)
                count = self.ser.inWaiting()
                hc = self.ser.read(count)
                hex_str = str(binascii.b2a_hex(hc))
                hc = hex_str[21:22] if len(hex_str) >= 22 else ''
                if hc == '0':
                    #logging.info("zhaodao zhiwen")
                    return True
#                 else:
#                     logging.info("zhaobu dao zhiwen")
#                     return False
                if time.time() - start_time > timeout:
                    logging.warning("zhaozhiwen chaoshi")
                    return False
                self.ser.flushInput()
                time.sleep(0.5)
#             time.sleep(0.1)
#             self.sendcmd(self.cmd_search)
#             time.sleep(0.1)
#             count = self.ser.inWaiting()
#             hc = self.ser.read(count)
#             hc = str(binascii.b2a_hex(hc))[21:22]
#             while hc != '0':
#                 time.sleep(0.1)
#                 self.sendcmd(self.cmd_search)
#                 time.sleep(0.1)
#                 count = self.ser.inWaiting()
#                 hc = self.ser.read(count)
#                 hc = str(binascii.b2a_hex(hc))[21:22]
#                 self.ser.flushInput()
        except Exception as e:
            logging.error(f"zhao zhiwen shiabi: {str(e)}...")

    def verify_fingerprint(self):
        logging.info("kaishi yanzheng zhiwen")
        try:  
            print('Please press your finger')
            self.searchfig()
            print('In recognition')
            time.sleep(0.02)
            self.sendcmd(self.cmd_gen1)
            time.sleep(0.01)
            self.ser.flushInput()
            time.sleep(0.01)
            self.sendcmd(self.cmd_dis)
            time.sleep(0.01)
            count = self.ser.inWaiting()
            hc = self.ser.read(count)
            disno = str(binascii.b2a_hex(hc))[21:22]
            disid = str(binascii.b2a_hex(hc))[25:26]
            print("Recognition results:  ")
             #return "No matching fingerprint found" if disno == '9' else disid 
            if disno == '0':
                logging.info(f"zhiwen pipei,yonghu {disid}")
                return int(disid)
            else:
                logging.warning("zhiwen pipei,shibai")
                return None
        except Exception as e:
            logging.error(f"zhiwen pipei,shibai {str(e)}")
            return None

    def waitfig(self):
        time.sleep(0.1)
        self.sendcmd(self.cmd_search)
        time.sleep(0.1)
        count = self.ser.inWaiting()
        hc = self.ser.read(count)
        hc = str(binascii.b2a_hex(hc))[21:22]
        print('Release your fingers')
        while hc == '0':
            time.sleep(0.1)
            self.sendcmd(self.cmd_search)
            time.sleep(0.1)
            count = self.ser.inWaiting()
            hc = self.ser.read(count)
            hc = str(binascii.b2a_hex(hc))[21:22]
            self.ser.flushInput()

    def enroll_fingerprint(self, user_id):
        print('Please press your finger')
        self.searchfig()
        self.sendcmd(self.cmd_gen1)
        print('Please press your finger again')
        time.sleep(3)
        self.searchfig()
        self.sendcmd(self.cmd_gen2)
        time.sleep(0.1)
        self.ser.flushInput()
        self.sendcmd(self.cmd_reg)
        time.sleep(0.1)
        count = self.ser.inWaiting()
        reg = self.ser.read(count)
        reg = str(binascii.b2a_hex(reg))[18:19]
        if reg == '0':
            add = self.cmd_save + bytearray([user_id, 0, user_id + 0xe])
            self.sendcmd(add)
            print(f"Successful deposit  id: {user_id}")
            return True
        else:
            print('Failed to deposit')
            return False
        #self.ser.flushInput()

    def deletfig(self, addr):
        logging.info(f"changshi sanchu zhiwen id: {addr}...")
        try:
            deletchar = self.cmd_deletchar + bytearray([addr, 0, 1, 0, addr + 0x15])
            self.sendcmd(deletchar)
            time.sleep(0.5)
            count = self.ser.inWaiting()
            self.ser.read(count)
            self.ser.flushInput()
            print(f"Deletion complete  id: {addr}")
        except Exception as e:
            logging.error(f"zhiwen sanchu: {str(e)}...")

    def close(self):
        self.ser.close()

