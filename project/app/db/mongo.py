# app/db/mongo.py

from pymongo import MongoClient
from app.config import settings

# Single MongoClient for the whole app
mongo_client = MongoClient(settings.MONGO_URI)
mongo_db = mongo_client[settings.MONGO_DB]
