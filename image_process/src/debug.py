from typing import Literal

from db.client import MongoDBClient
from utils.face import Face

"""MODES"""
MODES = Literal["save_face"]

mode: MODES = "save_face"
def main():
    if mode == "save_face":
        face_client = MongoDBClient(db_name="face")
        face = Face(MongoDBClient(db_name="face"))
        feature_vector = face.feature_vector_from_camera()
        face.save_to_mongodb(user_id="user1", name="face1", feature_vector=feature_vector)

if __name__ == '__main__':
	main()
