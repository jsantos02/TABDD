from datetime import datetime, timezone, timedelta
from app.db.mongo import mongo_db

line_id = "LINE_M_A"

new_alert = {
    "msg": "Delays due to track maintenance at Dragao.",
    "from": datetime.now(timezone.utc),
    # Change seconds=10 to minutes=30
    "to": datetime.now(timezone.utc) + timedelta(seconds=10) 
}

result = mongo_db.lines.update_one(
    {"_id": line_id},
    {"$push": {"alerts": new_alert}}
)

print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")