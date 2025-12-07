# project/app/scripts/check_alerts.py
import sys
import os
from pprint import pprint

# Boilerplate to find 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.append(project_root)

from app.db.mongo import mongo_db

line = mongo_db.lines.find_one({"_id": "LINE_M_A"})
print("--- Alerts for LINE_M_A ---")
pprint(line.get("alerts"))