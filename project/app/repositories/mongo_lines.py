from typing import List, Dict, Any, Optional
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

def get_line_by_id(line_id: str) -> Optional[Dict]:
    return mongo_db.lines.find_one({"_id": line_id})

def add_alert(line_id: str, alert: Dict[str, Any]) -> int:
    
    result = mongo_db.lines.update_one(
        {"_id": line_id},
        {"$push": {"alerts": alert}}
    )
    
    # Fallback, tries updating by field 'line_id' if _id didn't match
    if result.matched_count == 0:
        result = mongo_db.lines.update_one(
            {"line_id": line_id},
            {"$push": {"alerts": alert}}
        )
        
    return result.modified_count