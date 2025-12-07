from datetime import datetime, timezone
from typing import List, Dict, Any
from app.repositories import mongo_profiles, mongo_lines

def get_active_user_alerts(user_id: str) -> List[Dict[str, Any]]:
    alerts = []
    # 1. Get User Preferences & Favorites via Repo
    profile = mongo_profiles.get_or_create_profile(user_id)
    
    if profile.get("prefs", {}).get("notifyDisruptions", True):
        fav_line_ids = profile.get("favorites", {}).get("lines", [])
        
        if fav_line_ids:
            # 2. Get Lines with Alerts via Repo
            lines_with_alerts = mongo_lines.get_lines_with_active_alerts(fav_line_ids)
            now = datetime.now(timezone.utc)

            # 3. Filter Alerts by Date
            for line in lines_with_alerts:
                for alert in line.get("alerts", []):
                    start_dt = alert.get("from")
                    end_dt = alert.get("to")
                    
                    # Ensure timezone awareness
                    if start_dt and start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    if end_dt and end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)

                    if start_dt and start_dt <= now:
                        if not end_dt or end_dt > now:
                            alerts.append({
                                "line_code": line.get("code"),
                                "line_name": line.get("name"),
                                "msg": alert.get("msg"),
                                "level": "warning"
                            })
    return alerts