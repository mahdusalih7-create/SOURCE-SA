import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded

# --- البيانات الأساسية للبوت ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN") 

bot = Client(
    None,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

user_steps = {}
log_channels = {}
spam_status = {}
auto_reply_config = {}
client_limiter = asyncio.Semaphore(150)  # عدد العملاء المتزامنين

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

        # 1. أوامر الرد التلقائي
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

        # 2. ضبط قناة التخزين
        @user_client.on_message(filters.me & filters.regex(r"^\.ضبط قناة تخزين"))
        async def set_log_channel(client, message):
            log_channels[user_id] = message.chat.id
            await message.edit("تم حبيبي اي شي يصير يجيك هنا")

        # 3. تسجيل الرسائل الخاصة
        @user_client.on_message(filters.private & ~filters.me)
        async def logger_and_reply(client, message):
            config = auto_reply_config.get(user_id)
            if config and config.get("active"):
                try: await message.reply(config["text"])
                except: pass

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

        # 4. سبام
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


# --- واجهة بدء البوت ---
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply(
        "هلاو حبيبي 😎 اختر الطريقة:\n"
        "1️⃣ أرسل 'رقم' لاستخدام رقم الهاتف\n"
        "2️⃣ أرسل 'سيزون' لاستخدام Session String"
    )
    user_steps[message.chat.id] = {"step": "choose_method"}


@bot.on_message(filters.text & filters.private)
async def flow_handler(client, message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    if chat_id in user_steps:

        step = user_steps[chat_id]["step"]

        # --- اختيار طريقة التسجيل ---
        if step == "choose_method":
            if text == "رقم":
                user_steps[chat_id]["step"] = "phone"
                await message.reply("تمام 😎، أرسل رقمك بصيغة +964xxxxxxxxxxx")
            elif text == "سيزون":
                user_steps[chat_id]["step"] = "session"
                await message.reply("تمام 😎، أرسل API_ID")
            else:
                await message.reply("أرسل 'رقم' أو 'سيزون' فقط.")

        # --- خطوات رقم الهاتف ---
        elif step == "phone":
            temp_client = Client(None, api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            try:
                code_info = await temp_client.send_code(message.text)
                user_steps[chat_id] = {
                    "client": temp_client,
                    "phone": message.text,
                    "hash": code_info.phone_code_hash,
                    "step": "code"
                }
                await message.reply("👌 تمام، أرسل كود التحقق الذي وصلك.")
            except:
                await message.reply("خطأ، تحقق من الرقم وحاول مرة ثانية.")

        elif step == "code":
            data = user_steps[chat_id]
            try:
                await data["client"].sign_in(data["phone"], data["hash"], message.text.replace(" ", ""))
                session = await data["client"].export_session_string()
                await data["client"].disconnect()
                asyncio.create_task(start_user_logic(session, chat_id))
                await message.reply("✅ تم التفعيل بنجاح، استمتع بالأوامر!")
                del user_steps[chat_id]
            except SessionPasswordNeeded:
                user_steps[chat_id]["step"] = "pass"
                await message.reply("أرسل كلمة المرور لحسابك.")
            except:
                await message.reply("خطأ أثناء تسجيل الدخول، حاول مرة ثانية.")

        elif step == "pass":
            data = user_steps[chat_id]
            try:
                await data["client"].check_password(message.text)
                session = await data["client"].export_session_string()
                await data["client"].disconnect()
                asyncio.create_task(start_user_logic(session, chat_id))
                await message.reply("✅ تم التفعيل بنجاح، استمتع بالأوامر!")
                del user_steps[chat_id]
            except:
                await message.reply("خطأ في كلمة المرور، حاول مرة ثانية.")

        # --- خطوات Session String ---
        elif step == "session":
            user_steps[chat_id]["step"] = "session_api"
            user_steps[chat_id]["session_data"] = {"session_string": message.text}
            await message.reply("👌 الآن أرسل API_HASH")

        elif step == "session_api":
            user_steps[chat_id]["session_data"]["api_hash"] = message.text
            user_steps[chat_id]["step"] = "session_id"
            await message.reply("👌 الآن أرسل API_ID")

        elif step == "session_id":
            session_data = user_steps[chat_id]["session_data"]
            user_steps[chat_id]["step"] = None
            session_client = Client(
                None,
                api_id=int(message.text),
                api_hash=session_data["api_hash"],
                session_string=session_data["session_string"],
                in_memory=True
            )
            asyncio.create_task(start_user_logic(session_data["session_string"], chat_id))
            await message.reply("✅ تم التفعيل بالـ Session String بنجاح!")
            del user_steps[chat_id]


print("🚀 البوت يعمل الآن بنظام الذاكرة المطلق...")
bot.run()
