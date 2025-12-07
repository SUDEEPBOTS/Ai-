import pymongo
import os
import datetime
import random

MONGO_URI = os.environ.get("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client['telegram_bot_db']

users_col = db['users']
groups_col = db['groups']
stickers_col = db['stickers'] # New Collection

# --- Config Functions ---
def set_group_config(chat_id, key, value):
    groups_col.update_one({"_id": chat_id}, {"$set": {key: value}}, upsert=True)

def get_group_config(chat_id, key):
    data = groups_col.find_one({"_id": chat_id})
    return data.get(key) if data else None

# --- Sticker Functions (New) ---
def add_sticker(file_id):
    """Owner ka sticker save karega"""
    # Check if already exists to avoid duplicates
    if not stickers_col.find_one({"file_id": file_id}):
        stickers_col.insert_one({"file_id": file_id})

def get_random_sticker():
    """Baat karte waqt random sticker dega"""
    stickers = list(stickers_col.find())
    if stickers:
        return random.choice(stickers)['file_id']
    return None

# --- Warning System ---
def add_warning(chat_id, user_id):
    """Warning count badhayega. Returns total warnings."""
    key = f"warns_{chat_id}_{user_id}"
    # Simple key-based storage in users or separate logic
    # Here using user document update for simplicity
    user = users_col.find_one({"_id": user_id})
    current_warns = user.get(f"warns_{chat_id}", 0) + 1
    
    users_col.update_one(
        {"_id": user_id},
        {"$set": {f"warns_{chat_id}": current_warns}},
        upsert=True
    )
    return current_warns

def reset_warnings(chat_id, user_id):
    users_col.update_one(
        {"_id": user_id},
        {"$set": {f"warns_{chat_id}": 0}},
        upsert=True
    )
    
