import logging
import cv2
import numpy as np
import time
from skimage.metrics import structural_similarity as ssim
from db.client import MongoDBClient
logging.basicConfig(
    format='%(levelname)s: %(message)s'
)


class Background:
    def __init__(self, db_client: MongoDBClient):
        self.background = None
        self.db = db_client.connect()
        self.collection = self.db["background"]

    def save_background(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("cannot open camera")
            return

        print("Please move away from the camera to save the background image.")
        time.sleep(1)

        ret, frame = cap.read()
        cap.release()
        if ret:
            resized_frame = cv2.resize(frame, (320, 240))
            gray_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)

            bg_vector = gray_frame.flatten().tolist()
            bg_data = {
                "background_vector": bg_vector,
                "shape": gray_frame.shape
            }
            self.collection.delete_many({})
            self.collection.insert_one(bg_data)
            print("saved background image to MongoDB.")
        else:
            print("Failed to capture background image.")

    def load_background(self):
        bg_data = self.collection.find_one()
        if bg_data:
            bg_vector = np.array(bg_data["background_vector"], dtype=np.uint8)
            self.background = bg_vector.reshape(bg_data["shape"])
            print("loaded background image from MongoDB.")
        else:
            print("no background image found in MongoDB.")

    def compute_similarity(self, cap):
        if self.background is None:
            print("no background image loaded.")
            raise ValueError("no background image loaded.")

        ret, frame = cap.read()
        if not ret:
            print("cannot capture frame.")
            return None, None 

        resized_frame = cv2.resize(frame, (320, 240))
        frame_gray = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)

        similarity, _ = ssim(self.background, frame_gray, full=True)
        print(f"SSIM: {similarity:.4f}")

        return similarity, frame 

    def capture_frame(self, cap, num_frames=5):
        frames = []
        for _ in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                print("cannot capture frame.")
                return None
            frames.append(frame)
            time.sleep(0.1)

        avg_frame = np.mean(frames, axis=0).astype(np.uint8)
        return avg_frame
    def compute_similarity_with_frame(self, frame):
        if self.background is None:
            print("no background image loaded.")
            raise ValueError("no background image loaded.")

        resized_frame = cv2.resize(frame, (320, 240))
        frame_gray = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)

        similarity, _ = ssim(self.background, frame_gray, full=True)
        logging.info(f"SSIM: {similarity:.4f}")

        return similarity