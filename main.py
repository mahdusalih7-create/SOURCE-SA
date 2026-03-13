import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.errors import SessionPasswordNeeded

# --- البيانات الأساسية ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN") 

# --- بوت التليجرام الرئيسي ---
bot = Client(
    None,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# --- متغيرات البوت ---
user_steps = {}
log_channels = {}
spam_status = {}
auto_reply_config = {}

# --- تحديد عدد العملاء المتزامنين لتجنب ضغط السيرفر ---
client_limiter = asyncio.Semaphore(100)  # يمكن زيادة الرقم حسب قوة السيرفر

# --- دالة تشغيل العميل لكل مستخدم ---
async def start_user_logic(session_string, user_id):
    async with client_limiter:
        user_client = Client(
            None,
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )

        # 1. أوامر التحكم بالرد التلقائي
        @user_client.on_message(filters.me & filters.regex(r"^\.تفعيل رد تلقائي (.+)"))
        async def enable_reply(client, message):
            reply_text = message.matches[0].group(1)
            auto_reply_config[user_id] = {"text": reply_text, "active": True}
            await message.edit(f"✅ تم تفعيل الرد التلقائي:\n({reply_text})")

        @user_client.on_message(filters.me & filters.regex(r"^\.تعطيل رد تلقائي"))
        async def disable_reply(client, message):
            if user_id in auto_reply_config:
                auto_reply_config[user_id]["active"] = False
            await message.edit("❌ تم تعطيل الرد التلقائي.")

        # 2. أمر ضبط قناة التخزين
        @user_client.on_message(filters.me & filters.regex(r"^\.ضبط قناة تخزين"))
        async def set_log_channel(client, message):
            log_channels[user_id] = message.chat.id
            await message.edit("تم حبيبي اي شي يصير يجيك هنا")

        # 3. معالج الرسائل الخاصة
        @user_client.on_message(filters.private & ~filters.me)
        async def logger_and_reply(client, message):
            config = auto_reply_config.get(user_id)
            if config and config.get("active"):
                try: 
                    await message.reply(config["text"])
                except: 
                    pass
            
            if user_id in log_channels:
                log_id = log_channels[user_id]
                now = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
                username = f"@{message.from_user.username}" if message.from_user.username else "ماعنده يوزر"
                
                info_text = (
                    f"⚠️ **اكو واحد دز شي**\n"
                    f"👤 **الي رسلها:** {message.from_user.mention}\n"
                    f"🆔 **اليوزر:** {username}\n"
                    f"📟 **الايدي:** `{message.from_user.id}`\n"
                    f"⏰ **شوكت انرسلت:** `{now}`\n"
                    f"⬇️ **رسالته جوة مباشرة:**"
                )
                await client.send_message(log_id, info_text)

                try:
                    if message.media:
                        file_path = await client.download_media(message)
                        await client.send_document(log_id, document=file_path, caption="هههههه هاي الصورة المؤقتة")
                        if os.path.exists(file_path): os.remove(file_path)
                    else:
                        await message.copy(log_id)
                except:
                    await client.send_message(log_id, f"صارت مشكلة على حظك")
                await client.send_message(log_id, "───────")

        # 4. أوامر السبام
        @user_client.on_message(filters.me & filters.regex(r"^\.سبام (.+)"))
        async def start_spam(client, message):
            chat_id = message.chat.id
            text_to_spam = message.matches[0].group(1)
            spam_status[(user_id, chat_id)] = True
            await message.delete()
            while spam_status.get((user_id, chat_id)):
                await client.send_message(chat_id, text_to_spam)
                await asyncio.sleep(0.6)

        @user_client.on_message(filters.me & filters.text)
        async def stop_spam(client, message):
            if message.text == ".كافي سبام":
                spam_status[(user_id, message.chat.id)] = False
                await message.edit("تم حبيبي")

        await user_client.start()


# --- واجهة تسجيل الدخول ---
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply("هلاو حبيبي احبنك لان استخدمت البوت مالي ارسلي رقمك مثل هيج +964xxxxxxxxxxx")


@bot.on_message(filters.text & filters.private)
async def flow_handler(client, message):
    chat_id = message.chat.id
    welcome_msg = (
        "✅ **تم التفعيل روح تونس هذني الاوامر:**\n\n"
        "1️⃣ `.تفعيل رد تلقائي (الكلمة)` و `.تعطيل رد تلقائي`\n"
        "2️⃣ `.سبام (الكلمة)` و `.كافي سبام`\n"
        "3️⃣ `.ضبط قناة تخزين` (لمشاهدة المحذوفات والموقوت)\n\n"
        "⚠️ *ملاحظة: اشتركوا بقناة التحديثات: https://t.me/UPSASOURCE"
    )

    if message.text.startswith("+"):
        temp_client = Client(
            None,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        await temp_client.connect()
        try:
            code_info = await temp_client.send_code(message.text)
            user_steps[chat_id] = {
                "client": temp_client,
                "phone": message.text,
                "hash": code_info.phone_code_hash,
                "step": "code"
            }
            await message.reply("ارسلي كود التحقق الي اجاك بليز 👉🏻👈🏻")
        except Exception:
            await message.reply("خطا")
    elif chat_id in user_steps and user_steps[chat_id]["step"] == "code":
        data = user_steps[chat_id]
        try:
            await data["client"].sign_in(data["phone"], data["hash"], message.text.replace(" ", ""))
            session = await data["client"].export_session_string()
            await data["client"].disconnect()
            asyncio.create_task(start_user_logic(session, chat_id))
            await message.reply(welcome_msg)
            del user_steps[chat_id]
        except SessionPasswordNeeded:
            user_steps[chat_id]["step"] = "pass"
            await message.reply("ارسلي مالتك الباسورد ياحلو 😜")
        except Exception:
            await message.reply("عندك خطا")
    elif chat_id in user_steps and user_steps[chat_id]["step"] == "pass":
        data = user_steps[chat_id]
        try:
            await data["client"].check_password(message.text)
            session = await data["client"].export_session_string()
            await data["client"].disconnect()
            asyncio.create_task(start_user_logic(session, chat_id))
            await message.reply(welcome_msg)
            del user_steps[chat_id]
        except Exception:
            await message.reply("صار خطا")


print("🚀 البوت يعمل الآن بنظام الذاكرة المطلق...")
bot.run()
