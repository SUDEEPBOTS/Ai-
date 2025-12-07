import os
import json
import asyncio
import nest_asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from core.db import update_user, log_event
from core.ai_manager import ai_engine

nest_asyncio.apply()
app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

bot_app = Application.builder().token(TOKEN).build()

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Namaste! Main Yuki hoon. Group Security Active hai! 🛡️")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Checking...")
    await msg.edit_text("Pong! ⚡ System Super Fast.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = """
📜 **Yuki Bot Help**
/start - Restart Bot
/ping - Check Speed
/id - Get User ID
/report - Report to Admin
/ban - Ban User (Reply karke)
    """
    await update.message.reply_text(txt, parse_mode="Markdown")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(f"👤 **User ID:** `{user.id}`\n💬 **Chat ID:** `{chat.id}`", parse_mode="Markdown")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admins ko report bhej di gayi hai! (Simulation)")

async def manual_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if user.id != OWNER_ID:
        await msg.reply_text("❌ Aap Owner nahi ho!")
        return
    
    if not msg.reply_to_message:
        await msg.reply_text("Kisi ke message par reply karke /ban likho.")
        return

    target = msg.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(msg.chat_id, target.id)
        await msg.reply_text(f"🚫 Banned {target.first_name}!")
    except Exception as e:
        await msg.reply_text(f"Error: {e}")

# --- MESSAGE HANDLER (AI) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.text: return

    # Trigger AI only on Mention, Reply, or DM
    is_mentioned = f"@{context.bot.username}" in msg.text or "yuki" in msg.text.lower()
    is_reply = (msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id)
    is_dm = update.effective_chat.type == 'private'

    if is_mentioned or is_reply or is_dm:
        response_text = ai_engine.get_response(msg.text, is_owner=(update.effective_user.id == OWNER_ID))
        
        try:
            # Clean JSON
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            reply = data.get("reply", str(data))
            action = data.get("action", "")

            if action == "ban":
                 await context.bot.ban_chat_member(msg.chat_id, update.effective_user.id)
                 await msg.reply_text(f"🚫 {reply}")
            else:
                 await msg.reply_text(reply)
        except:
            # Agar JSON fail ho jaye to direct text bhej do
            await msg.reply_text(response_text)

# Register Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("ping", ping))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(CommandHandler("id", id_command))
bot_app.add_handler(CommandHandler("report", report_command))
bot_app.add_handler(CommandHandler("ban", manual_ban))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.process_update(update))
        return "OK"
    return "Not Allowed"
    
