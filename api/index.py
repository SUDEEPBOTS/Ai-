import os
import json
import asyncio
import nest_asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from core.db import update_user, log_event
from core.ai_manager import ai_engine

# Asyncio fix for Vercel
nest_asyncio.apply()

app = Flask(__name__)

# Config Variables
TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# Bot Application Setup (Global)
bot_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user(user.id, user.username, user.first_name)
    await update.message.reply_text(f"Namaste {user.first_name}! Main Yuki hoon. Is group ki security AI.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Pinging...")
    # Calculate simple ping logic here if needed
    await msg.edit_text("Pong! ⚡ System Active.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    
    if not msg.text: return

    # 1. Save User to DB
    update_user(user.id, user.username, user.first_name)

    # 2. Check Permissions
    is_owner = (user.id == OWNER_ID)
    # Admin check (Simplified for speed, real logic would check chat_member)
    is_admin = is_owner # Defaulting admins to owner for this snippet, can expand later

    # 3. AI Trigger Logic (Reply only if mentioned, replied to, or in DM)
    is_mentioned = f"@{context.bot.username}" in msg.text or "yuki" in msg.text.lower()
    is_reply_to_bot = (msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id)
    is_dm = chat.type == 'private'

    if is_mentioned or is_reply_to_bot or is_dm:
        # AI se pucho
        ai_raw_response = ai_engine.get_response(msg.text, is_admin, is_owner)
        
        try:
            # JSON clean karna (kabhi kabhi AI extra text deta hai)
            clean_json = ai_raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            action = data.get("action", "reply")
            reply_text = data.get("reply", "...")

            # Actions Handle Karo
            if action == "ban" and not is_owner:
                # Ban logic with Appeal Button
                appeal_btn = InlineKeyboardButton("Appeal Unban", url=f"https://t.me/{context.bot.username}?start=appeal")
                kb = InlineKeyboardMarkup([[appeal_btn]])
                
                await context.bot.ban_chat_member(chat.id, user.id)
                await msg.reply_text(f"🚫 {reply_text}", reply_markup=kb)
                log_event(chat.id, "BAN", f"User {user.id} banned by AI")
            
            elif action == "ban_target" and is_admin:
                # Agar admin ne kisi aur ko ban karne ko bola (Reply wale user ko)
                if msg.reply_to_message:
                    target = msg.reply_to_message.from_user
                    if target.id != OWNER_ID:
                        await context.bot.ban_chat_member(chat.id, target.id)
                        await msg.reply_text(f"Done Sir! Banned {target.first_name}.")
                    else:
                        await msg.reply_text("Main Owner ko ban nahi kar sakti!")
            
            else:
                # Normal Reply
                await msg.reply_text(reply_text)

        except Exception as e:
            # Fallback agar JSON parsing fail ho
            await msg.reply_text(ai_raw_response)

# Handlers add karna
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("ping", ping))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        # Process Update
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        
        # Async loop manage karna Vercel ke liye
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize and Process
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.process_update(update))
        
        return "OK"
    return "Not Allowed"

@app.route('/')
def home():
    return "Yuki Bot is Online!"
