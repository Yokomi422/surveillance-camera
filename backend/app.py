# app.py

# poetry run uvicorn app:app --reload --host 0.0.0.0 --port 8080
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import threading
import logging
import json

from db.client import MongoDBClient, get_client
from utils.face import Face

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

# Faceクラスのインスタンス化
face = Face(mongo_client)

@app.post("/upload_frame")
async def upload_frame(image: UploadFile = File(...)):
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        logging.error("Invalid image type")
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    try:
        with latest_frame_lock:
            with open(LATEST_FRAME_PATH, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
        logging.info("Frame received and saved")
        return {"message": "Frame received and saved"}
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image")

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
        with latest_frame_lock:
            with open(LATEST_FRAME_PATH, "wb") as buffer:
                content = await image.read()
                buffer.write(content)
        logging.info("Notification received and image saved")
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image")

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
        temp_image_dir = "temp"
        os.makedirs(temp_image_dir, exist_ok=True)
        temp_image_path = os.path.join(temp_image_dir, f"{name}_temp.jpg")
        with open(temp_image_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        encoding = face.extract_face_encoding(temp_image_path)
        
        if encoding is None:
            logging.error("Failed to extract face encoding: Encoding is None.")
            os.remove(temp_image_path)
            raise HTTPException(status_code=400, detail="No face detected or the image is not clear enough.")
        
        face.save_face(name=name, encoding=encoding)
        
        os.remove(temp_image_path)
        
        logging.info(f"Face registered successfully for user: {name}")
        return {"message": f"Face registered successfully for user: {name}"}
    
    except HTTPException as he:
        logging.error(f"HTTPException occurred: {he.detail}")
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in register_face: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register face due to an unexpected error: {str(e)}")