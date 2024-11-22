import logging
import cv2
import time
import numpy as np
from utils.background import Background
from utils.face import Face
from db.client import get_client
from utils.http import send_detection_data_to_server, DetectionData
from PIL import Image

logging.basicConfig(
    format='%(levelname)s: %(message)s'
)

similarity_threshold = 0.85

def main():
    logging.info("surveillance system started")

    background_client = get_client("background")
    face_client = get_client("face")

    background = Background(background_client)
    face_recognition_module = Face(face_client)

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

                # フレームを RGB に変換
                image_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                boxes, _ = face_recognition_module.mtcnn.detect(pil_image)

                if boxes is not None:
                    # 特徴量抽出
                    feature_vector = face_recognition_module.feature_vector(image_rgb, boxes)

                    # 顔認識
                    name, score = face_recognition_module.compare_with_all_faces(feature_vector)
                    logging.info(f"Detected person: {name} (score: {score:.3f})")

                    # 顔にアノテーション
                    annotated_frame_rgb = face_recognition_module.detect_person(image_rgb, name)
                    # フレームを BGR に戻す
                    annotated_frame = cv2.cvtColor(annotated_frame_rgb, cv2.COLOR_RGB2BGR)

                    data = DetectionData(status="person detected", detail=f"Detected person: {name}")
                    send_detection_data_to_server(annotated_frame, data)
                else:
                    logging.info("No faces detected.")
                    data = DetectionData(status="face not detected", detail="No faces detected")
                    send_detection_data_to_server(current_frame, data)
            else:
                # 差分がない場合
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