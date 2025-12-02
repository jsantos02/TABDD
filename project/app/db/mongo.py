# app/db/mongo.py

from pymongo import MongoClient
from app.config import settings

mongo_client = MongoClient(settings.MONGO_URI)
mongo_db = mongo_client[settings.MONGO_DB]

def get_mongo_db():
    return mongo_db