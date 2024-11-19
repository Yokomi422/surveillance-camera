import logging
import cv2
import time

from utils.background import Background
from utils.face import Face
from db.client import get_client
from utils.http import send_detection_data_to_server, DetectionData

logging.basicConfig(
    format='%(levelname)s: %(message)s'
)

similarity_threshold = 0.85 

def main():
    logging.info("surveillance system started")

    background_client = get_client("background")
    face_client = get_client("face")

    background = Background(background_client)
    face = Face(face_client)

    logging.info("background image saving started")
    background.save_background()

    logging.info("background image loading started")
    background.load_background()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    try:
        while True:
            ret, current_frame = cap.read()
            if not ret:
                print("Failed to read frame.")
                continue

            similarity = background.compute_similarity_with_frame(current_frame)
            if similarity is None:
                print("Failed to compute similarity.")
                continue

            if similarity < similarity_threshold:
                logging.info("difference detected")
                blue_boxed_frame = face.detect_person(current_frame)
                if blue_boxed_frame is not None:
                    logging.info("person detected")
                    feature_vector = face.feature_vector(current_frame)

                    on_db = face.compare_with_all_faces(feature_vector)
                    data = None
                    if on_db:
                        logging.info("person detected on db")
                        data = DetectionData(status="known person detected", detail="person detected on db")
                    else:
                        logging.info("person not on db is detected")
                        data = DetectionData(status="unknown person detected", detail="person not on db is detected")
                    send_detection_data_to_server(blue_boxed_frame, data)
                else:
                    logging.info("no person detected")
                    data = DetectionData(status="something detected", detail="no person detected")
                    send_detection_data_to_server(current_frame, data)

            else:
                # 差分がない場合でもフレームを送信する場合は以下を有効にする
                data = DetectionData(status="no difference detected", detail="background unchanged")
                send_detection_data_to_server(current_frame, data)
                pass

            time.sleep(0.01)

    except KeyboardInterrupt:
        logging.info("surveillance system stopped")
    finally:
        cap.release()

if __name__ == '__main__':
    main()
