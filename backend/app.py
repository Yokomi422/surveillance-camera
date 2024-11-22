# app.py

# poetry run uvicorn app:app --reload --host 0.0.0.0 --port 8080
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import threading
import logging
import numpy as np
import cv2  # OpenCV のインポートを追加
from PIL import Image

from db.client import MongoDBClient, get_client
from utils.face import FaceRecognition

app = FastAPI()

LATEST_FRAME_PATH = "./latest_frame.jpg"
REGISTERED_FACES_DIR = "./registered_faces"

logging.basicConfig(level=logging.INFO)
latest_frame_lock = threading.RLock()
detection_lock = threading.RLock()
registration_lock = threading.RLock()

latest_detection = None

class DetectionData(BaseModel):
    status: str
    detail: str

    def to_dict(self):
        return {
            "status": self.status,
            "detail": self.detail
        }

# MongoDBクライアントのインスタンス化
mongo_client = get_client("face")
db = mongo_client.connect()

# FaceRecognitionクラスのインスタンス化
face_recognition = FaceRecognition(mongo_client)

@app.post("/upload_frame")
async def upload_frame(image: UploadFile = File(...)):
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        logging.error("Invalid image type")
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    try:
        # 画像を読み込み、OpenCVの形式に変換
        image_data = await image.read()
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            logging.error("Failed to decode image")
            raise HTTPException(status_code=400, detail="Failed to decode image. Ensure the image is valid.")

        # ユーザーの確認
        name, similarity = face_recognition.verify_user(frame)
        logging.info(f"Detected person: {name} (similarity: {similarity:.3f})")

        # フレームにアノテーションを追加
        annotated_frame = face_recognition.annotate_frame(frame, name)

        # アノテーションが追加されたフレームを保存
        with latest_frame_lock:
            cv2.imwrite(LATEST_FRAME_PATH, annotated_frame)
        logging.info("Frame received, processed, and saved with annotations")
        return {"message": "Frame received, processed, and saved with annotations"}
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="Failed to process and save image")

@app.get("/get_frame", response_class=FileResponse)
async def get_frame():
    with latest_frame_lock:
        if not os.path.exists(LATEST_FRAME_PATH):
            logging.error("No frame available")
            raise HTTPException(status_code=404, detail="No frame available")
        return FileResponse(LATEST_FRAME_PATH, media_type="image/jpeg", filename="latest_frame.jpg")

@app.post("/notification")
async def notification(
    status: str = Form(...),
    detail: str = Form(...),
    image: UploadFile = File(...)
):
    global latest_detection

    if image.content_type not in ["image/jpeg", "image/jpg"]:
        logging.error("Invalid image type")
        raise HTTPException(status_code=400, detail="Invalid image type")

    try:
        # 画像を読み込み、OpenCVの形式に変換
        image_data = await image.read()
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            logging.error("Failed to decode image")
            raise HTTPException(status_code=400, detail="Failed to decode image. Ensure the image is valid.")

        # ユーザーの確認
        name, similarity = face_recognition.verify_user(frame)
        logging.info(f"Detected person: {name} (similarity: {similarity:.3f})")

        # フレームにアノテーションを追加
        annotated_frame = face_recognition.annotate_frame(frame, name)

        # アノテーションが追加されたフレームを保存
        with latest_frame_lock:
            cv2.imwrite(LATEST_FRAME_PATH, annotated_frame)
        logging.info("Notification received, image processed, and saved with annotations")
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="Failed to process and save image")

    with detection_lock:
        latest_detection = DetectionData(status=status, detail=detail)
    logging.info("Detection data updated")

    return {"message": "Notification received and saved"}

@app.get("/get_detection")
async def get_detection():
    with detection_lock:
        if latest_detection is None:
            logging.error("No detection data available")
            raise HTTPException(status_code=404, detail="No detection data available")
        return JSONResponse(content=latest_detection.to_dict())

@app.post("/register_face")
async def register_face(
    name: str = Form(...),
    image: UploadFile = File(...)
):
    """
    ユーザーの顔を登録するエンドポイント。
    """
    if image.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        logging.error("Invalid image type for face registration")
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG and PNG are supported.")
    
    try:
        # 画像を読み込み、OpenCVの形式に変換
        image_data = await image.read()
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            logging.error("Failed to decode image")
            raise HTTPException(status_code=400, detail="Failed to decode image. Ensure the image is valid.")

        # 画像をリストにして登録（単一の画像でもリストで渡す必要があります）
        images = [frame]

        face_recognition.register_user(name=name, images=images)

        logging.info(f"Face registered successfully for user: {name}")
        return {"message": f"Face registered successfully for user: {name}"}
    
    except HTTPException as he:
        logging.error(f"HTTPException occurred: {he.detail}")
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in register_face: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register face due to an unexpected error: {str(e)}")