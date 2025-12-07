import os
import json
import asyncio
import nest_asyncio
import random
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from core.db import set_group_config, get_group_config, add_sticker, get_random_sticker, add_warning, reset_warnings
from core.ai_manager import ai_engine

nest_asyncio.apply()
app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

bot_app = Application.builder().token(TOKEN).build()

# --- HELPER: Admin Check & Auto Delete ---
async def check_admin(update, context):
    chat = update.effective_chat
    user = update.effective_user
    
    # Command Message Delete kar do (Safai ke liye)
    try:
        await update.message.delete()
    except:
        pass # Agar delete permission nahi hai to ignore

    if user.id == OWNER_ID: return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

# --- MODERATION COMMANDS (Mute, Warn, Kick) ---

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    
    msg = update.effective_message
    if not msg.reply_to_message:
        await context.bot.send_message(msg.chat_id, "ℹ️ Kisi user ke message pe reply karke /mute likho.")
        return

    target = msg.reply_to_message.from_user
    if target.id == OWNER_ID:
        await context.bot.send_message(msg.chat_id, "👑 Maalik ko mute nahi karungi!")
        return

    # Mute Logic (Send Messages = False)
    permissions = ChatPermissions(can_send_messages=False)
    try:
        await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions)
        await context.bot.send_message(msg.chat_id, f"🤐 **Muted:** {target.first_name} ab bol nahi payega.", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(msg.chat_id, f"Error: {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    
    msg = update.effective_message
    if not msg.reply_to_message: return

    target = msg.reply_to_message.from_user
    # Permissions wapis de do
    permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    try:
        await context.bot.restrict_chat_member(msg.chat_id, target.id, permissions)
        await context.bot.send_message(msg.chat_id, f"🗣 **Unmuted:** {target.first_name} ab bol sakta hai.", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(msg.chat_id, f"Error: {e}")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    msg = update.effective_message
    if not msg.reply_to_message: return
    
    target = msg.reply_to_message.from_user
    if target.id == OWNER_ID: return

    try:
        await context.bot.ban_chat_member(msg.chat_id, target.id)
        await context.bot.unban_chat_member(msg.chat_id, target.id) # Unban immediately so they can join back
        await context.bot.send_message(msg.chat_id, f"👢 **Kicked:** {target.first_name} ko bahar fenk diya.", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(msg.chat_id, f"Error: {e}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context): return
    msg = update.effective_message
    if not msg.reply_to_message: return

    target = msg.reply_to_message.from_user
    if target.id == OWNER_ID: return

    # DB me warn count badhao
    warns = add_warning(msg.chat_id, target.id)
    limit = 3
    
    if warns >= limit:
        # Ban user
        try:
            await context.bot.ban_chat_member(msg.chat_id, target.id)
            await context.bot.send_message(msg.chat_id, f"🚫 **Banned:** {target.first_name} (3/3 Warnings Limit Reached).", parse_mode="Markdown")
            reset_warnings(msg.chat_id, target.id) # Reset after ban
        except Exception as e:
            await context.bot.send_message(msg.chat_id, f"Error banning: {e}")
    else:
        await context.bot.send_message(msg.chat_id, f"⚠️ **Warning:** {target.first_name} ({warns}/{limit})\nSudhar jao warna ban padega!", parse_mode="Markdown")

# --- OTHER COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Namaste! Yuki Security with Sticker AI Online. 🛡️")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = """
🔥 **Yuki Commands:**
/warn - Warning do (3 pe Ban)
/mute - Chup karao
/unmute - Bolne do
/kick - Group se nikalo
/ban - Permanent Ban
/setwelcome - Welcome message set karo
    """
    await update.message.reply_text(txt)

# --- STICKER LEARNING & AI ---

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    file_id = update.message.sticker.file_id
    
    # Agar Owner Sticker bhejta hai, to Bot usse seekh legi
    if user.id == OWNER_ID:
        add_sticker(file_id)
        # 10% chance ki bot reply me yahi sticker bheje owner ko khush karne ke liye
        if random.random() < 0.1:
            await update.message.reply_sticker(file_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.text: return
    
    is_owner = (update.effective_user.id == OWNER_ID)
    
    # AI Logic Call
    is_mentioned = f"@{context.bot.username}" in msg.text or "yuki" in msg.text.lower()
    is_reply = (msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id)
    is_dm = update.effective_chat.type == 'private'

    if is_mentioned or is_reply or is_dm:
        response = ai_engine.get_response(msg.text, is_owner=is_owner)
        
        try:
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            reply_text = data.get("reply", "")
            action = data.get("action", "")

            # Action Handling
            if action == "ban" and not is_owner:
                 await context.bot.delete_message(msg.chat_id, msg.message_id) # Delete abusive msg
                 await context.bot.ban_chat_member(msg.chat_id, update.effective_user.id)
                 await msg.reply_text(f"🚫 Banned for abuse.")
            
            else:
                # Reply Text
                await msg.reply_text(reply_text)
                
                # STICKER LOGIC: 30% Chance ki bot reply ke baad sticker bhi bheje
                if random.random() < 0.3:
                    sticker_id = get_random_sticker()
                    if sticker_id:
                        await context.bot.send_sticker(msg.chat_id, sticker_id)

        except:
            await msg.reply_text(response)

# Handlers Register
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(CommandHandler("mute", mute_command))
bot_app.add_handler(CommandHandler("unmute", unmute_command))
bot_app.add_handler(CommandHandler("warn", warn_command))
bot_app.add_handler(CommandHandler("kick", kick_command))
# Sticker Handler (Naya feature)
bot_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
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
    
