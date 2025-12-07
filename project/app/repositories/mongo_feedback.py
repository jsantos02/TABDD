from typing import Dict, Any
from app.db.mongo import mongo_db

def create_feedback(feedback_data: Dict[str, Any]):
    mongo_db.feedback.insert_one(feedback_data)