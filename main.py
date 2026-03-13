import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded

# --- البيانات الأساسية (يفضل وضعها في Railway Variables) ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# اسم الجلسة للسيرفر
bot = Client(
    "railway_session", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    device_model="Railway Server",
    system_version="Linux"
)

user_steps = {}
log_channels = {} 
spam_status = {}
auto_reply_config = {} 

async def start_user_logic(session_string, user_id):
    user_client = Client(
        name=f"user_{user_id}", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=session_string,
        in_memory=True
    )

    @user_client.on_message(filters.me & filters.regex(r"^\.تفعيل رد تلقائي (.+)"))
    async def enable_reply(client, message):
        reply_text = message.matches[0].group(1)
        auto_reply_config[user_id] = {"text": reply_text, "active": True}
        await message.edit(f"✅ تم تفعيل الرد:\n({reply_text})")

    @user_client.on_message(filters.me & filters.regex(r"^\.تعطيل رد تلقائي"))
    async def disable_reply(client, message):
        if user_id in auto_reply_config:
            auto_reply_config[user_id]["active"] = False
        await message.edit("❌ تم تعطيل الرد.")

    @user_client.on_message(filters.me & filters.regex(r"^\.ضبط قناة تخزين"))
    async def set_log_channel(client, message):
        log_channels[user_id] = message.chat.id
        await message.edit("✅ تم ضبط قناة التخزين بنجاح.")

    @user_client.on_message(filters.private & ~filters.me)
    async def logger_and_reply(client, message):
        config = auto_reply_config.get(user_id)
        if config and config.get("active"):
            try: await message.reply(config["text"])
            except: pass
        
        if user_id in log_channels:
            log_id = log_channels[user_id]
            try:
                if message.media:
                    file_path = await client.download_media(message)
                    await client.send_document(log_id, document=file_path, caption=f"👤 من: {message.from_user.mention}")
                    if os.path.exists(file_path): os.remove(file_path)
                else:
                    await message.copy(log_id)
            except: pass

    @user_client.on_message(filters.me & filters.regex(r"^\.سبام (.+)"))
    async def start_spam(client, message):
        chat_id = message.chat.id
        text_to_spam = message.matches[0].group(1)
        spam_status[(user_id, chat_id)] = True
        await message.delete()
        while spam_status.get((user_id, chat_id)):
            await client.send_message(chat_id, text_to_spam)
            await asyncio.sleep(1.0) # زيادة الوقت قليلاً لثبات السيرفر

    @user_client.on_message(filters.me & filters.text)
    async def stop_spam(client, message):
        if message.text == ".كافي سبام":
            spam_status[(user_id, message.chat.id)] = False
            await message.edit("🛑 توقف السبام.")

    await user_client.start()

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply("🚀 البوت يعمل على Railway!\nأرسل رقمك الآن: `+964xxxxxxxxxxx`")

@bot.on_message(filters.text & filters.private)
async def flow_handler(client, message):
    chat_id = message.chat.id
    if message.text.startswith("+"):
        temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
        await temp_client.connect()
        try:
            code_info = await temp_client.send_code(message.text)
            user_steps[chat_id] = {"client": temp_client, "phone": message.text, "hash": code_info.phone_code_hash, "step": "code"}
            await message.reply("📩 أرسل كود التحقق الآن:")
        except Exception as e:
            await message.reply(f"❌ خطأ: {e}")
    elif chat_id in user_steps and user_steps[chat_id]["step"] == "code":
        data = user_steps[chat_id]
        try:
            await data["client"].sign_in(data["phone"], data["hash"], message.text.replace(" ", ""))
            session = await data["client"].export_session_string()
            asyncio.create_task(start_user_logic(session, chat_id))
            await message.reply("✅ تم التفعيل بنجاح!")
            del user_steps[chat_id]
        except SessionPasswordNeeded:
            user_steps[chat_id]["step"] = "pass"
            await message.reply("🔐 أرسل رمز التحقق بخطوتين:")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")
    elif chat_id in user_steps and user_steps[chat_id]["step"] == "pass":
        data = user_steps[chat_id]
        try:
            await data["client"].check_password(message.text)
            session = await data["client"].export_session_string()
            asyncio.create_task(start_user_logic(session, chat_id))
            await message.reply("✅ تم التفعيل!")
            del user_steps[chat_id]
        except Exception:
            await message.reply("❌ الباسورد خطأ.")

print("🚀 Starting Bot on Railway...")
bot.run()
