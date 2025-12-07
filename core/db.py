import pymongo
import os
import datetime

# MongoDB URL Environment Variable se lega
MONGO_URI = os.environ.get("MONGO_URI")

client = pymongo.MongoClient(MONGO_URI)
db = client['telegram_bot_db']

users_col = db['users']
logs_col = db['logs']
groups_col = db['groups']

def update_user(user_id, username, first_name):
    """User ko database me save ya update karega"""
    users_col.update_one(
        {"_id": user_id},
        {"$set": {
            "username": username,
            "first_name": first_name,
            "last_active": datetime.datetime.utcnow()
        }},
        upsert=True
    )

def log_event(chat_id, event, details):
    """Logs save karega"""
    logs_col.insert_one({
        "chat_id": chat_id,
        "event": event,
        "details": details,
        "timestamp": datetime.datetime.utcnow()
    })
  
