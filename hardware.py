import time
import threading
import logging
import cv2
from gpiozero import LED, Buzzer, DigitalInputDevice, Servo
from picamera2 import Picamera2
from fingerprint1 import FingerprintManager

class OV5647Controller:
    def __init__(self):
        
        self.servo = Servo(
            pin=18,
            initial_value=0.0,
            min_pulse_width=0.5/1000,
            max_pulse_width=2.5/1000)
        
        self.ir_sensor = DigitalInputDevice(4, pull_up=False)
        self.led = LED(17)        
        self.buzzer = Buzzer(27)          
        self.picam2 = Picamera2(camera_num=0)   
        self._setup_camera()
        self.fingerprint = FingerprintManager()
        
        self.auth_attempts = {'face': 0, 'fingerprint': 0, 'password': 0}
        self.lock = threading.Lock()
        self.system_locked = False
        self.lock_time = 0
        
        
        logging.basicConfig(
            #level=logging.INFO
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("yingjian chishihua wac")
    
    def _set_servo_angle(self, angle):
        try:
            value = (angle / 90) - 1
            self.servo.value = value
            time.sleep(0.5)
        except Exception as e:
            logging.info(f"duoji shibai:{str(e)}")
    
    def reset_lock_status(self):
        with self.lock:
            self.system_locked = False
            self.lock_time = 0
            self.auth_attempts = {'face':0, 'fingerprint':0, 'password':0}
    
    def _setup_camera(self):
        
        config = self.picam2.create_still_configuration(
            #main={"size": (2592, 1944)},1296x972
            #main={"size": (1311, 1860)},
            main={"size": (1296, 972)},
            #main={"size": (640, 480)},
            buffer_count=4
        )
        self.picam2.configure(config)
        self.picam2.set_controls({
            "AwbMode": 0,
            "AeEnable": True,
            "AeExposureMode": 1, 
            #"FrameDurationLimits": (33333,33333),
            "AnalogueGain": 5.5
        })
        self.picam2.start()
        time.sleep(2)  

    def capture_frame(self):
        try:
            frame = self.picam2.capture_array("main")
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
#             return frame

        except Exception as e:
            logging.error(f"puhu yichang: {str(e)}")
            return None

    def led_success(self):
        self.led.blink(on_time=0.3, off_time=0.3, n=3)
        self._set_servo_angle(90)
        time.sleep(1)
        self._set_servo_angle(0)
        
        
    def buzzer_alert(self):
        self.buzzer.beep(on_time=0.5, off_time=0.2, n=2)

    def cleanup(self):
        self.servo.detach()
        self.picam2.stop()
        self.led.off()
        self.buzzer.off()
        self.fingerprint.close()
        logging.info("yingian shifang")