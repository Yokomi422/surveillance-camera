# face_module.py

import cv2
import logging
import numpy as np
from PIL import Image
from typing import Optional
import face_recognition
from facenet_pytorch import MTCNN
import os
from datetime import datetime
from fastapi import HTTPException

from db.client import MongoDBClient

class Face:
    def __init__(self, db_client: MongoDBClient) -> None:
        self.db = db_client.connect()
        self.collection = self.db["faces"]
        self.mtcnn = MTCNN()
        os.makedirs("registered_faces", exist_ok=True)

    def feature_vector(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        フレームから顔の特徴ベクトルを抽出します。
        
        Args:
            frame (np.ndarray): カメラからの入力フレーム
        
        Returns:
            Optional[np.ndarray]: 顔の特徴ベクトル。顔が検出されない場合はNone。
        """
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(image)
        if face_encodings:
            return face_encodings[0]
        else:
            return None

    def compare_with_all_faces(self, feature_vector: np.ndarray) -> bool:
        """
        入力された特徴ベクトルをデータベース内の全ての特徴ベクトルと比較します。
        
        Args:
            feature_vector (np.ndarray): 入力された顔の特徴ベクトル
        
        Returns:
            bool: 類似度が閾値を下回る顔が存在する場合はTrue、そうでない場合はFalse。
        """
        if feature_vector is None:
            logging.info("入力の特徴ベクトルが None です。")
            return False

        threshold = 0.45  # 類似度の閾値

        for face_data in self.collection.find():
            stored_vector = face_data.get("feature_vector")
            if stored_vector is None:
                print(f"ユーザーID: {face_data['user_id']}, 名前: {face_data['name']} の特徴ベクトルが存在しません。")
                continue

            stored_vector = np.array(stored_vector)
            distance = face_recognition.face_distance([stored_vector], feature_vector)[0]

            if distance < threshold:
                return True 

        return False

    def detect_person(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        検出した人物の有無を確認し、顔が認識された場合は青枠を付けた画像を返す。
        
        Args:
            frame (np.ndarray): カメラからの入力フレーム
        
        Returns:
            Optional[np.ndarray]: 青枠を付けた画像。顔が検出されない場合は None。
        """
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_cropped = self.mtcnn(image, return_prob=False)  # 顔領域を検出

        if img_cropped is not None:
            logging.info("人物が検出されました")

            boxes, _ = self.mtcnn.detect(image)

            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box) 
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2) 

            return frame 
        else:
            logging.info("人物が検出されませんでした")
            return None

    def extract_face_encoding(self, image_path: str) -> Optional[np.ndarray]:
        """
        画像ファイルから顔の特徴ベクトルを抽出します。
        
        Args:
            image_path (str): 画像ファイルのパス
        
        Returns:
            Optional[np.ndarray]: 顔の特徴ベクトル。顔が検出されない場合はNone。
        """
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) == 1:
            return encodings[0]
        elif len(encodings) > 1:
            logging.error("複数の顔が検出されました。1つの顔のみをアップロードしてください。")
            return None
        else:
            logging.error("顔が検出されませんでした。")
            return None

    def save_face(self, name: str, encoding: np.ndarray) -> None:
        try:
            user_id = self.collection.count_documents({}) + 1
            face_data = {
                "user_id": user_id,
                "name": name,
                "feature_vector": encoding.tolist(),
                "created_at": datetime.utcnow().isoformat()
            }
            self.collection.insert_one(face_data)
            logging.info(f"ユーザー {name} の顔データが保存されました。")
        except Exception as e:
            logging.error(f"データベースへの保存中にエラーが発生しました: {e}")
            raise HTTPException(status_code=500, detail="Failed to save face data.")