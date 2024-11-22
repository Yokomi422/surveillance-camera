import cv2
import logging
from utils.face import FaceRecognition
from db.client import get_client

"""
デバッグ用に顔認証のデータを登録するコード
"""
logging.basicConfig(level=logging.INFO)

# カメラを初期化
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()


client = get_client("face")
face_recognition = FaceRecognition(client)

logging.info("ユーザー登録を開始します。カメラを見てください。")

# ユーザーの名前を入力
name = "admin"

# サンプルを保存するリスト
samples = []

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame.")
        break

    # フレームを表示
    cv2.imshow('Register User - Press "s" to save sample, "q" to finish', frame)

    # キー入力を待つ
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        # 's'キーが押されたら画像を保存して登録
        samples.append(frame.copy())
        logging.info(f"サンプルを追加しました。現在のサンプル数: {len(samples)}")
    elif key == ord('q'):
        # 'q'キーが押されたら終了
        logging.info("サンプル収集を終了しました。")
        break

cap.release()
cv2.destroyAllWindows()

if len(samples) > 0:
    # サンプルを使用してユーザーを登録
    face_recognition.register_user(name, samples)
    logging.info("登録が完了しました。")
else:
    logging.info("サンプルが収集されていません。登録を中止します。")