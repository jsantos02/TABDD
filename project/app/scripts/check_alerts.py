# project/app/scripts/check_alerts.py
import sys
import os
from pprint import pprint
from app.db.mongo import mongo_db

line = mongo_db.lines.find_one({"_id": "LINE_M_A"})
print("--- Alerts for LINE_M_A ---")
pprint(line.get("alerts"))