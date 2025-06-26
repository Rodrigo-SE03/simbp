from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.collection import Collection
from pymongo import DESCENDING


MONGO_USER = ""  # Replace with your MongoDB username
MONGO_PASSWORD = ""  # Replace with your MongoDB password
MONGO_CLUSTER = (
    "cluster0.b77cm.mongodb.net"  # Replace with your MongoDB cluster address
)
uri = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0"

local_uri = "mongodb://localhost:27017/"  # Local MongoDB URI

db = None
collection_leituras = None


def init_db() -> Collection:
    global db, collection_leituras

    # Decomment the following lines to use MongoDB Atlas
    # logger.info("Connecting to MongoDB Atlas...")
    # client = MongoClient(uri, server_api=ServerApi('1'))
    # client.admin.command('ping')
    # logger.info("MongoDB Atlas connection successful")

    # Comment the following line if you want to use MongoDB Atlas
    client = MongoClient(local_uri)

    db = client["projeto_integrador"]
    collection_leituras = db["leituras"]
    return collection_leituras


def get_collection() -> Collection:
    return init_db() if collection_leituras is None else collection_leituras


def aggregate(collection, pipeline):
    if db is None:
        init_db()

    result = list(collection.aggregate(pipeline))
    for doc in result:
        doc["_id"] = str(doc["_id"])

    return result
