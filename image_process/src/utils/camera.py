import cv2
import numpy as np

class Camera:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
    
    def read(self):
        ret, frame = self.cap.read()
        return frame
    
    def isOpened(self):
        return self.cap.isOpened()
    
    def take_photo(self) -> np.ndarray:
        ret, frame = self.cap.read()
        return frame 
    
    def take_video(self, filename, duration=10):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
        start_time = cv2.getTickCount()
        while True:
            ret, frame = self.cap.read()
            out.write(frame)
            if (cv2.getTickCount() - start_time) / cv2.getTickFrequency() > duration:
                break
        out.release()
    
    def imshow(self, frame):
        cv2.imshow(str(self), frame)
    
    def imwrite(self, frame, filename):
        cv2.imwrite(filename, frame)
        
    def wait_key(self, delay=1):
        return cv2.waitKey(delay)
    
    def release(self):
        self.cap.release()
    
    def __del__(self):
        self.release()
    
    def __str__(self):
        return f"Camera {self.camera_id}"