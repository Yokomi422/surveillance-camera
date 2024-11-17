from pymongo import MongoClient

class MongoDBClient:
    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "my_database") -> None:
        self.host = host
        self.port = port
        self.db_name = db_name
        self.client = None

    def connect(self) -> MongoClient:
        if self.client is None:
            self.client = MongoClient(self.host, self.port)
        return self.client[self.db_name]

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

def get_client(db_name: str) -> MongoDBClient:
    if db_name == "face":
        return MongoDBClient(db_name="face")
    elif db_name == "background":
        return MongoDBClient(db_name="background")
    else:
        raise ValueError("db_name must be 'face' or 'background'")
