import logging
import cv2
import time
import numpy as np
from utils.background import Background
from utils.face import FaceRecognition
from db.client import get_client
from utils.http import send_detection_data_to_server, DetectionData
from PIL import Image

logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.INFO  # ログレベルを INFO に設定
)

similarity_threshold = 0.85

def main():
    logging.info("Surveillance system started")

    background_client = get_client("background")
    face_client = get_client("face")

    background = Background(background_client)
    face_recognition_module = FaceRecognition(face_client)

    logging.info("Background image saving started")
    background.save_background()

    logging.info("Background image loading started")
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
                logging.info("Difference detected")

                # フレームを RGB に変換
                image_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)

                # MTCNN を使用して顔検出
                boxes, _ = face_recognition_module.mtcnn.detect(pil_image)

                if boxes is not None:
                    names = []
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box)
                        face_crop = current_frame[y1:y2, x1:x2]

                        # ユーザーの確認
                        name, score = face_recognition_module.verify_user(face_crop)
                        logging.info(f"Detected person: {name} (score: {score:.3f})")
                        names.append(name)

                    # フレームにアノテーションを追加
                    annotated_frame = face_recognition_module.annotate_frame(current_frame, boxes, names)

                    data = DetectionData(status="person detected", detail=f"Detected persons: {names}")
                    send_detection_data_to_server(annotated_frame, data)
                else:
                    logging.info("No faces detected.")
                    data = DetectionData(status="face not detected", detail="No faces detected")
                    send_detection_data_to_server(current_frame, data)
            else:
                # 差分がない場合
                data = DetectionData(status="no difference detected", detail="background unchanged")
                send_detection_data_to_server(current_frame, data)

            time.sleep(0.01)

    except KeyboardInterrupt:
        logging.info("Surveillance system stopped")
    finally:
        cap.release()
        cv2.destroyAllWindows()  # OpenCV のウィンドウを閉じる

if __name__ == '__main__':
    main()