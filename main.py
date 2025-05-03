import threading
import logging
import cv2
import time
import concurrent.futures
from hardware import OV5647Controller
from face_detector import FaceDetector
from face_recognitiona import FaceRecognizer
from concurrent.futures import ThreadPoolExecutor

class FaceAccessSystem:
    def __init__(self):
        self.hardware = OV5647Controller()
        self.detector = FaceDetector()
        self.recognizer = FaceRecognizer()
        self.running = True
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        #self.executor = ThreadPoolExecutor()
        self.frame_buffer = []
        
        self.buffer_size = 10
        
        self.processing = False
        self.last_update = 0
        
        self.log_callback = None
        
        self.disable_native_window = False
        
        self.hardware_lock = threading.Lock()
        
        self.fingerprint_attempts = 0
        self.failed_attempts = 0
        self.max_attempts = 3
        self.on_auth_failed_callback = None
        
#         self.sensor_thread = threading.Thread(target=self._monitor_sensor, daemon=True)
#         self.sensor_thread.start()
        
        self.auth_mode = "multi"
        self.current_auth_threads = []
        self.auth_success = threading.Event()
        
        self.auth_timeout = 10
        self.cancel_auth = threading.Event()
        self.auth_lock = threading.Lock()
        
        
        self.recognition_paused = False
        self.pause_lock = threading.Lock()
        
        
        self.sensor_thread = threading.Thread(target=self._monitor_sensor, daemon=True)
        self.sensor_thread.start()
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler('access.log'),
                logging.StreamHandler()
            ]
        )
    
    def _monitor_sensor(self):
        debounce_time = 2.0
        last_trigger = 0.0
        while self.running:
            with self.pause_lock:
                if self.recognition_paused:
                    time.sleep(0.1)
                    continue
            
            current_state = self.hardware.ir_sensor.is_active
            current_time = time.time()
            
            if current_state and (current_time - last_trigger) > debounce_time:
#                 logging.info("jiance daoren,kaishi shibie.")
                last_trigger = current_time
                if not self.processing:
                    self._trigger_recognition()
            time.sleep(0.1)
    
    def _trigger_recognition(self):
        #logging.info("dioayong")
        self.processing = True
        self.executor.submit(self._async_recognize)
    
    def set_auth_failed_callback(self, callback):
        self.on_auth_failed_callback = callback
    
    def capture_frame_safely(self):
        with self.hardware_lock:
            return self.hardware.capture_frame()
    
    def run_without_window(self):
        try:
            logging.info("xitong qidong...")
            while self.running:
#                 frame = self.hardware.capture_frame()
                frame = self.capture_frame_safely() 
                if frame is not None:
                    self.frame_buffer.append(frame.copy())
                    if len(self.frame_buffer) > self.buffer_size:
                        self.frame_buffer = self.frame_buffer[-self.buffer_size:]
                        #self.frame_buffer.pop(0)
                if not self.running:
                    break
                #
                key = cv2.waitKey(1)
                if key == ord('q'):
                    self.shutdown()
                    break
   
                
        except Exception as e:
            logging.error(f"yunxing yichang: {str(e)}")
        finally:
            self.shutdown()
    
    def _async_recognize(self):
        try:
            self.cancel_auth.clear()
            timeout_timer = None
            
            with self.pause_lock:
                if self.recognition_paused:
                    logging.info("renzheng zhanting")
                    return
                
            with self.hardware.lock:
                self.auth_success.clear()
                self.current_auth_threads = []
                def face_auth():
                    try:
                        if not self.frame_buffer:
                            logging.warning("zhenhuan chong weikong")
                            return False
                        
#                         liveness_result = self.recognizer.check_liveness(self.frame_buffer[-3:])
#                         if not liveness_result:
#                             logging.warning("bushi huo ti")
#                             self.hardware.buzzer_alert()
#                             return
                        if len(self.frame_buffer) < 3:
                            logging.warning("huotijianc yao3zhen")
                            return
            
                        current_frame = self.frame_buffer[-1]
                        faces_coords = self.detector.detect_faces(current_frame, return_coords=True)
                        if not faces_coords:
                            logging.warning("wei jiance dao renlian")
                            self.hardware.buzzer_alert()
                            return

                        x1, y1, x2, y2 = faces_coords[0]
                        face_roi = current_frame[y1:y2, x1:x2]
                        #user_id = self.recognizer.recognize(user_id)
                        user_id = self.recognizer.recognize(face_roi)

                        if user_id:
                            logging.info(f"shibei chenggong :yonghu {user_id}")
                            self.hardware.led_success()
                            self.failed_attempts = 0 
                        else:
                            logging.warning("weizhi yonghu")
                            self.failed_attempts += 1
                            if self.failed_attempts >= self.max_attempts:
                                if self.on_auth_failed_callback:
                                    self.on_auth_failed_callback()
                                self.failed_attempts = 0
                                
                            self.hardware.buzzer_alert()

                        if user_id:
                            self.auth_success.set()
                            return True
                        return False
                    except:
                        return False
                    
                def fingerprint_auth():
                    try:
                        user_id = self.hardware.fingerprint.verify_fingerprint()
                        if user_id is not None:
                            #self.auth_success.set()
                            self.hardware.led_success()
                            #self.fingerprint_attempts = 0
                            logging.info(f"zhiwen renzheng chenggong id : {user_id}")
                            self.fingerprint_attempts = 0
                            #return True
                        else:
                            self.fingerprint_attempts += 1
                            if self.fingerprint_attempts >= self.max_attempts:
                                if self.on_auth_failed_callback:
                                    self.on_auth_failed_callback()
                                self.fingerprint_attempts = 0
#                         if user_id:
#                             if user_id:
#                                 self.auth_success.set()
#                                 return True

#                             with self.hardware.lock:
#                                 logging.info("jinru zhiwen shibai")
#                                 logging.info(f"renlain shibai: {self.hardware.auth_attempts['face']}, zhiwen: {self.hardware.auth_attempts['fingerprint']}")
#                                 self.hardware.auth_attempts['fingerprint'] += 1
#                                 if self.hardware.auth_attempts['fingerprint'] >= 3:
#                                     logging.info("zhiwen cuo 3ci")
#                                     if self.on_auth_failed_callback:
#                                         self.on_auth_failed_callback()
                                        
                            #time.sleep(0.5)
                        return False
                    except Exception as e:
                        logging.error(f"zhiwen renzhengyichang :{str(e)}")
                        return False
                

                def on_auth_completed(success):
                    with self.auth_lock:
                        if success and not self.cancel_auth.is_set():
                            self.cancel_auth.set()
                            if timeout_timer:
                                timeout_timer.cancel()
                            self._handle_success()
                            
                def face_auth_task():
                    for _ in range(3):
                        if face_auth():
                            return True
                        time.sleep(1.5)
                    return False
                    try: 
                        while not self.cancel_auth.is_set():
                            result = face_auth()
                            if result:
                                on_auth_completed(True)
                                return True
                            else:
                                with self.hardware.lock:
                                    self.hardware.auth_attempts['face'] += 1
                                    if self.hardware.auth_attempts['face'] >= self.max_attempts:
                                        if self.on_auth_failed_callback:
                                            self.on_auth_failed_callback()
                                time.sleep(0.5)
                            return False
                    except Exception as e:
                        logging.error(f"renlian,renzheng yichang{str(e)}")
                        return False
                
                def fingerprint_auth_task():
                    for _ in range(3):
                        if fingerprint_auth():
                            return True
                        time.sleep(1.5)
                    return False
                    try:
                        max_retries = 3
                        attempt = 0
                        start_time = time.time()
                        while (attempt < max_retries and 
                           time.time() - start_time < self.auth_timeout and 
                            not self.cancel_auth.is_set()):
                            result = self.hardware.fingerprint.verify_fingerprint()
                            if result:
                                logging.info(f"zhiwen cg")
                                return True
                            
                            else:
                                with self.hardware.lock:
                                    self.hardware.auth_attempts['fingerprint'] += 1
                                    if self.hardware.auth_attempts['fingerprint'] >= self.max_attempts:
                                        if self.on_auth_failed_callback:
                                            self.on_auth_failed_callback()
                                time.sleep(0.5) 
                            attempt += 1
                            time.sleep(1)
                        return False
                    except Exception as e:
                        logging.error(f"zhiwen yichang {str(e)}")
                        return False
                    
                def timeout_handler():
                    with self.auth_lock:
                        if not self.cancel_auth.is_set():
                            logging.warning("renzheng chaoshi")
                            self.cancel_auth.set()
                            self._handle_failure()

                timeout_timer = threading.Timer(self.auth_timeout, timeout_handler)
                timeout_timer.start()
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = []
                    if self.auth_mode in ["multi", "face"]:
                        face_future = executor.submit(face_auth_task)
                        futures.append(face_future)
                    if self.auth_mode in ["multi", "fingerprint"]:
                        fingerprint_future = executor.submit(fingerprint_auth_task)
                        futures.append(fingerprint_future)
                    
                
                done, not_done = concurrent.futures.wait(
                    futures,
                    timeout=self.auth_timeout,
                    return_when=concurrent.futures.FIRST_COMPLETED)
                success = any(future.result() for future in done if future.exception() is None)
                if success:
                    for future in not_done:
                        future.cancel()
                    self._handle_success()
                else:
                    pass
                    #self._handle_failure()
                    

        except Exception as e:
            logging.error(f"renzheng guocheng yichang: {str(e)}")
        finally:
            timeout_timer.cancel()
            self.processing = False
            
    def _handle_success(self):
        self.hardware.led_success()
        self.hardware.auth_attempts = {'face':0, 'fingerprint':0, 'password':0}
        logging.info("renzheng chenggong")
        for t in self.current_auth_threads:
            if not t.done():
                t.cancel()
    
    def _handle_failure(self):
        with self.hardware.lock:
            if self.auth_mode == "face":
                self.hardware.auth_attempts['face'] += 1
            elif self.auth_mode == "fingerprint":
                self.hardware.auth_attempts['fingerprint'] += 1
            elif self.auth_mode == "multi":
                self.hardware.auth_attempts['face'] += 1
                self.hardware.auth_attempts['fingerprint'] += 1
            if (self.hardware.auth_attempts['face'] >=3 or 
                self.hardware.auth_attempts['fingerprint'] >=3):
                self.hardware.buzzer_alert()
                if self.on_auth_failed_callback:
                    self.on_auth_failed_callback()
                
   
    def run(self):
        try:
            logging.info("""
                -----------------------------------
                renlianshibiexitong qidong...
                anhuiche kaishi shibie...
                ---------------------------------------""")
            cv2.namedWindow('Camera Preview', cv2.WINDOW_NORMAL)
            while self.running:
                frame = self.hardware.capture_frame()
                if frame is not None:
                    display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    cv2.imshow('Camera Preview', frame)
                    #cv2.imshow('Camera Preview', display_frame)
                    
                    self.frame_buffer.append(frame.copy())
                    if len(self.frame_buffer) > 5:
                        self.frame_buffer.pop(0)
                        
                key = cv2.waitKey(1)
                if key == ord('q'):
                    self.shutdown()
                    break
                elif key == 13 and not self.processing:
                    self.processing = True
                    logging.info("kaishishibei...")
                    self.executor.submit(self._async_recognize)
    
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        self.running = False
        self.hardware.cleanup()
        cv2.destroyAllWindows()
        logging.info("xitong guanbi")
        
if __name__ == "__main__":
    system = FaceAccessSystem()
    system.run()
