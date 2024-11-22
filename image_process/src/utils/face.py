import cv2
import numpy as np
import logging
from deepface import DeepFace
from facenet_pytorch import MTCNN
import os
from datetime import datetime
from typing import List, Optional, Tuple
from db.client import MongoDBClient  # MongoDBクライアントを正しくインポート
from PIL import Image

class FaceRecognition:
    def __init__(self, db_client: MongoDBClient) -> None:
        self.model_name = 'ArcFace'
        self.db_client = db_client
        self.db = self.db_client.connect()
        self.collection = self.db["faces"]
        self.registered_users = []

        # MTCNNの初期化
        self.mtcnn = MTCNN()

        # データベースから登録済みの顔データを読み込みます
        self.load_registered_embeddings()

    def register_user(self, name: str, images: List[np.ndarray]) -> None:
        """
        ユーザーを登録します。

        Args:
            name (str): ユーザーの名前
            images (List[np.ndarray]): ユーザーの顔画像のリスト
        """
        try:
            embeddings = []
            for idx, image in enumerate(images):
                # 特徴ベクトルの取得
                embedding_objs = DeepFace.represent(img_path=image, model_name=self.model_name,
                                                    detector_backend='mtcnn', enforce_detection=True)
                if len(embedding_objs) == 0:
                    logging.error(f"サンプル {idx + 1} で顔が検出されませんでした。")
                    continue
                embedding = embedding_objs[0]["embedding"]
                embeddings.append(embedding)

            if len(embeddings) == 0:
                logging.error("有効な顔が検出されませんでした。登録を中止します。")
                return

            # MongoDBに保存
            user_id = self.collection.count_documents({}) + 1
            face_data = {
                "user_id": user_id,
                "name": name,
                "embeddings": embeddings,
                "created_at": datetime.utcnow().isoformat()
            }
            self.collection.insert_one(face_data)
            logging.info(f"ユーザー {name} の顔データが保存されました。")

            # 登録ユーザーのリストを更新
            self.registered_users.append(face_data)
        except Exception as e:
            logging.error(f"ユーザーの登録中にエラーが発生しました: {e}")

    def load_registered_embeddings(self) -> None:
        """
        登録されたユーザーの特徴ベクトルをデータベースから読み込みます。
        """
        try:
            self.registered_users = list(self.collection.find())
            logging.info(f"{len(self.registered_users)} 人のユーザーをデータベースから読み込みました。")
        except Exception as e:
            logging.error(f"データベースからの読み込み中にエラーが発生しました: {e}")
            self.registered_users = []

    def verify_user(self, image: np.ndarray) -> Tuple[str, float]:
        """
        入力画像の人物が登録されたadminユーザーかどうかを確認します。

        Args:
            image (np.ndarray): 検証する顔画像

        Returns:
            Tuple[str, float]: (一致したユーザーの名前または "unknown", 類似度スコア)
        """
        try:
            # MTCNNで顔検出
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)
            boxes, _ = self.mtcnn.detect(pil_image)

            if boxes is None or len(boxes) == 0:
                logging.error("顔が検出されませんでした。")
                return "unknown", 0.0

            # 検出された顔領域をクロップ
            x1, y1, x2, y2 = map(int, boxes[0])
            face_crop = image[y1:y2, x1:x2]

            # DeepFaceで特徴ベクトルを取得
            embedding_objs = DeepFace.represent(img_path=face_crop, model_name=self.model_name,
                                                detector_backend='skip', enforce_detection=False)
            if len(embedding_objs) == 0:
                logging.error("特徴ベクトルの取得に失敗しました。")
                return "unknown", 0.0
            embedding = embedding_objs[0]["embedding"]

            # 登録されたadminユーザーとの比較
            admin_user = None
            for user in self.registered_users:
                if user["name"] == "admin":
                    admin_user = user
                    break

            if admin_user is None:
                logging.error("adminユーザーが登録されていません。")
                return "unknown", 0.0

            highest_similarity = -1  # 初期値

            user_embeddings = admin_user["embeddings"]
            for registered_embedding in user_embeddings:
                registered_embedding = np.array(registered_embedding)
                # コサイン類似度の計算
                similarity = np.dot(registered_embedding, embedding) / (np.linalg.norm(registered_embedding) * np.linalg.norm(embedding))
                if similarity > highest_similarity:
                    highest_similarity = similarity

            # 閾値を設定（0.7）
            threshold = 0.7
            if highest_similarity >= threshold:
                return "admin", highest_similarity
            else:
                return "unknown", highest_similarity
        except Exception as e:
            logging.error(f"ユーザーの検証中にエラーが発生しました: {e}")
            return "unknown", 0.0

    def annotate_frame(self, frame: np.ndarray, boxes: np.ndarray, names: List[str]) -> np.ndarray:
        """
        フレームに検出された顔の位置と名前を描画します。

        Args:
            frame (np.ndarray): 元のフレーム
            boxes (np.ndarray): 顔のバウンディングボックスの配列
            names (List[str]): 各顔に対応する名前のリスト

        Returns:
            np.ndarray: アノテーションが追加されたフレーム
        """
        for box, name in zip(boxes, names):
            x1, y1, x2, y2 = map(int, box)
            if name == "admin":
                label = "admin"
                color = (0, 255, 0)  # 緑
            else:
                label = "unknown"
                color = (0, 0, 255)  # 赤

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, color, 2)

        return frame