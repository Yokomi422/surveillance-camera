import cv2
import logging
import numpy as np
from PIL import Image
from typing import Optional, Tuple
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

        self.face_recognizer_model = "face_recognition_sface_2021dec.onnx"

        self.face_recognizer = cv2.FaceRecognizerSF_create(
            self.face_recognizer_model, ""
        )

        # 類似度の閾値
        # 厳しくする
        self.COSINE_THRESHOLD = 0.90 # 値を上げると厳しくなる
        self.NORM_L2_THRESHOLD = 0.62 # 値を下げると厳しくなる

    def feature_vector(self, frame: np.ndarray, boxes: np.ndarray) -> Optional[np.ndarray]:
        """
        フレームと検出された顔のバウンディングボックスから顔の特徴ベクトルを抽出します。

        Args:
            frame (np.ndarray): RGB 色空間のフレーム
            boxes (np.ndarray): 検出された顔のバウンディングボックス

        Returns:
            Optional[np.ndarray]: 顔の特徴ベクトル。顔が検出されない場合は None。
        """
        if boxes is None or len(boxes) == 0:
            logging.info("顔が検出されませんでした。")
            return None

        # 最初の顔のみを使用（複数の顔に対応する場合はループを追加）
        box = boxes[0]

        # MTCNN の出力は [x1, y1, x2, y2]
        x1, y1, x2, y2 = box  # 座標は float 型のまま使用

        # 幅と高さを計算
        w = x2 - x1
        h = y2 - y1

        # NumPy 配列に変換し、データ型を指定
        face_box = np.array([[x1, y1, w, h]], dtype=np.float32)  # 形状を (1, 4) にする

        # フレームを BGR に変換
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # 顔をアラインメント
        aligned_face = self.face_recognizer.alignCrop(frame_bgr, face_box)

        # 特徴量を抽出
        feature = self.face_recognizer.feature(aligned_face)

        return feature

    def compare_with_all_faces(self, feature_vector: np.ndarray) -> Tuple[str, float]:
        """
        入力された特徴ベクトルをデータベース内の全ての特徴ベクトルと比較します。

        Args:
            feature_vector (np.ndarray): 入力された顔の特徴ベクトル

        Returns:
            Tuple[str, float]: マッチした人の名前とスコア。マッチしない場合は ("unknown", 0.0)。
        """
        if feature_vector is None:
            logging.info("入力の特徴ベクトルが None です。")
            return "unknown", 0.0

        max_score = 0.0
        best_match_name = "unknown"

        for face_data in self.collection.find():
            stored_vector = np.array(face_data.get("feature_vector"), dtype=np.float32)
            if stored_vector is None:
                print(f"ユーザーID: {face_data['user_id']}, 名前: {face_data['name']} の特徴ベクトルが存在しません。")
                continue

            # コサイン類似度を計算
            score = self.face_recognizer.match(feature_vector, stored_vector, cv2.FaceRecognizerSF_FR_COSINE)

            if score > self.COSINE_THRESHOLD and score > max_score:
                max_score = score
                best_match_name = face_data["name"]

        return best_match_name, max_score

    def detect_person(self, frame: np.ndarray, name: str = "unknown") -> Optional[np.ndarray]:
        """
        検出した人物の有無を確認し、顔が認識された場合は青枠と名前を付けた画像を返す。

        Args:
            frame (np.ndarray): RGB 色空間のフレーム
            name (str): 認識された人物の名前（デフォルトは "unknown"）

        Returns:
            Optional[np.ndarray]: 青枠と名前を付けた画像。顔が検出されない場合は None。
        """
        pil_image = Image.fromarray(frame)
        boxes, _ = self.mtcnn.detect(pil_image)

        if boxes is not None:
            logging.info(f"人物が検出されました: {name}")

            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame_bgr, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            4, (255, 0, 0), 4)

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            return frame_rgb
        else:
            logging.info("人物が検出されませんでした")
            return None

    def extract_face_encoding(self, image_path: str) -> Optional[np.ndarray]:
        """
        画像ファイルから顔の特徴ベクトルを抽出します。

        Args:
            image_path (str): 画像ファイルのパス

        Returns:
            Optional[np.ndarray]: 顔の特徴ベクトル。顔が検出されない場合は None。
        """
        image = cv2.imread(image_path)
        if image is None:
            logging.error(f"画像を読み込めませんでした: {image_path}")
            return None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        boxes, _ = self.mtcnn.detect(pil_image)

        feature_vector = self.feature_vector(image_rgb, boxes)

        if feature_vector is not None:
            return feature_vector
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