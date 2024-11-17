import requests
import cv2
import logging

class DetectionData:
    def __init__(self, status: str, detail: str):
        self.status = status
        self.detail = detail

    def to_dict(self):
        return {
            'status': self.status,
            'detail': self.detail
        }

def send_detection_data_to_server(frame, data: DetectionData):
    url = "http://localhost:8080/notification"
    payload = data.to_dict()

    # フレームをJPEGにエンコード
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        logging.error("フレームのエンコードに失敗しました")
        return

    frame_data = buffer.tobytes()

    files = {
        'image': ('frame.jpg', frame_data, 'image/jpeg')
    }

    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"サーバーへの送信中にエラーが発生しました: {e}")
    else:
        logging.info(f"サーバーからのレスポンス: {response.text}")