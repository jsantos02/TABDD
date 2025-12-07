from typing import List, Dict, Any
from app.db.mongo import mongo_db

def get_lines_by_ids(line_ids: List[str]) -> List[Dict]:
    if not line_ids:
        return []
    return list(mongo_db.lines.find({"_id": {"$in": line_ids}}))

def get_lines_with_active_alerts(line_ids: List[str]) -> List[Dict]:
    return list(mongo_db.lines.find({
        "_id": {"$in": line_ids},
        "alerts": {"$not": {"$size": 0}}
    }))