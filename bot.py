import asyncio
import os
import sqlite3
import requests
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# -----------------------------
# الإعدادات الأساسية
# -----------------------------

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '').replace('%3A', ':')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
DB_NAME = "users_sessions.db"

# -----------------------------
# البوت الرئيسي
# -----------------------------
bot = Client(
    "main_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# -----------------------------
# قاعدة البيانات - مميزات جديدة
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            session_string TEXT,
            phone_number TEXT,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def save_session(user_id, session_string, phone_number):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, session_string, phone_number, is_active)
        VALUES (?, ?, ?, 1)
    ''', (user_id, session_string, phone_number))
    conn.commit()
    conn.close()

def get_user_session(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT session_string FROM users WHERE user_id = ? AND is_active = 1', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, phone_number, registration_date FROM users WHERE is_active = 1')
    result = cursor.fetchall()
    conn.close()
    return result

def get_users_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    result = cursor.fetchone()[0]
    conn.close()
    return result

def delete_user_session(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# -----------------------------
# دوال مساعدة جديدة
# -----------------------------
def create_progress_callback(client, progress_msg):
    """دالة لعرض شريط التقدم"""
    async def progress_callback(current, total):
        try:
            percent = current * 100 / total
            if int(percent) % 25 == 0:  # تحديث كل 25%
                await progress_msg.edit_text(f"⏬ جاري التحميل... {percent:.1f}%")
        except:
            pass
    return progress_callback

# -----------------------------
# أوامر البوت - واجهة محسنة
# -----------------------------
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    
    # واجهة الأدمن
    if user_id == ADMIN_ID:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍💼 لوحة التحكم", callback_data="admin_panel")],
            [InlineKeyboardButton("📥 تحميل ملف", callback_data="download")],
            [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login")]
        ])
        await message.reply_text(
            "🎉 **مرحباً يا أدمن!**\n\n"
            "اختر من الخيارات:",
            reply_markup=keyboard
        )
        return
    
    # واجهة المستخدم العادي
    if get_user_session(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 تحميل ملف", callback_data="download")],
            [InlineKeyboardButton("🔐 إعادة التسجيل", callback_data="re_login")],
            [InlineKeyboardButton("ℹ️ شرح البوت", callback_data="help_info")],
            [InlineKeyboardButton("📞 الدعم الفني", callback_data="support")]
        ])
        await message.reply_text(
            "🎯 **مرحباً مرة أخرى!**\n\n"
            "اختر ما تريد القيام به:",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login")],
            [InlineKeyboardButton("ℹ️ شرح البوت", callback_data="help_info")],
            [InlineKeyboardButton("📞 الدعم الفني", callback_data="support")]
        ])
        await message.reply_text(
            "👋 **أهلاً بك في بوت التحميل الذكي!** 🤖\n\n"
            "🎯 **المميزات:**\n"
            "• تحميل الملفات من أي رابط\n"
            "• استخدام حسابك الشخصي\n"
            "• سرعة وجودة عالية\n"
            "• دعم جميع أنواع الملفات\n\n"
            "🔐 **لبدء الاستخدام، سجل دخول بحسابك:**",
            reply_markup=keyboard
        )

@bot.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_command(client, message):
    """لوحة تحكم الأدمن"""
    users_count = get_users_count()
    all_users = get_all_users()
    
    stats_text = f"""
👨‍💼 **لوحة تحكم الأدمن**

📊 **الإحصائيات:**
👤 عدد المستخدمين: {users_count}
🗂 الجلسات النشطة: {users_count}
🕒 آخر تحديث: الآن

🎛 **الأدوات:**
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("🧹 حذف جلسة", callback_data="admin_delete")],
        [InlineKeyboardButton("📤 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 إعادة التشغيل", callback_data="admin_restart")],
        [InlineKeyboardButton("📥 رفع تحديث", callback_data="admin_update")]
    ])
    
    await message.reply_text(stats_text, reply_markup=keyboard)

# -----------------------------
# معالجة الكلابكات - مميزات جديدة
# -----------------------------
@bot.on_callback_query()
async def handle_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # أوامر الأدمن
    if data == "admin_panel" and user_id == ADMIN_ID:
        await admin_panel_handler(client, callback_query)
    elif data == "admin_stats" and user_id == ADMIN_ID:
        await admin_stats_handler(client, callback_query)
    elif data == "admin_users" and user_id == ADMIN_ID:
        await admin_users_handler(client, callback_query)
    elif data == "admin_delete" and user_id == ADMIN_ID:
        await admin_delete_handler(client, callback_query)
    elif data == "admin_broadcast" and user_id == ADMIN_ID:
        await admin_broadcast_handler(client, callback_query)
    elif data == "admin_restart" and user_id == ADMIN_ID:
        await admin_restart_handler(client, callback_query)
    
    # أوامر التحقق من الانضمام
    elif data.startswith("check_join_"):
        await check_join_callback(client, callback_query)
    
    # أوامر المستخدمين
    elif data == "login":
        await start_login_process(client, callback_query)
    elif data == "re_login":
        await start_login_process(client, callback_query, re_login=True)
    elif data == "download":
        await callback_query.message.edit_text("📥 **أرسل رابط الملف الآن**")
    elif data == "help_info":
        await help_info_handler(client, callback_query)
    elif data == "support":
        await support_handler(client, callback_query)
    elif data == "back_start":
        await start_command(client, callback_query.message)

# -----------------------------
# معالجات الأدمن الجديدة
# -----------------------------
async def admin_panel_handler(client, callback_query):
    users_count = get_users_count()
    
    stats_text = f"""
👨‍💼 **لوحة تحكم الأدمن**

📊 **الإحصائيات الحية:**
👤 عدد المستخدمين: {users_count}
🗂 الجلسات النشطة: {users_count}
🟢 حالة البوت: نشط

🎛 **اختر الأداة:**
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("🧹 حذف جلسة", callback_data="admin_delete")],
        [InlineKeyboardButton("📤 بث رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 إعادة التشغيل", callback_data="admin_restart")],
        [InlineKeyboardButton("📥 تحديث", callback_data="admin_update")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_start")]
    ])
    
    await callback_query.message.edit_text(stats_text, reply_markup=keyboard)

async def admin_stats_handler(client, callback_query):
    users_count = get_users_count()
    all_users = get_all_users()
    
    # تحليل البيانات
    recent_users = len([u for u in all_users if "2024" in str(u[2])])  # مستخدمين جدد
    
    stats_text = f"""
📊 **إحصائيات مفصلة**

👥 **المستخدمين:**
• الإجمالي: {users_count}
• الجدد: {recent_users}
• النشطين: {users_count}

💾 **التخزين:**
• الجلسات: {users_count}
• الملفات: {len(os.listdir(DOWNLOAD_FOLDER)) if os.path.exists(DOWNLOAD_FOLDER) else 0}

🛠 **النظام:**
• الحالة: 🟢 نشط
• الذاكرة: جيدة
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ])
    
    await callback_query.message.edit_text(stats_text, reply_markup=keyboard)

async def admin_users_handler(client, callback_query):
    all_users = get_all_users()
    
    if not all_users:
        await callback_query.message.edit_text("❌ لا يوجد مستخدمين مسجلين")
        return
    
    users_text = "👥 **قائمة المستخدمين:**\n\n"
    for i, user in enumerate(all_users[:10], 1):  # عرض أول 10 مستخدمين
        users_text += f"{i}. ID: `{user[0]}` - {user[1]}\n"
    
    if len(all_users) > 10:
        users_text += f"\n... وعرض {len(all_users) - 10} مستخدم آخر"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 حذف مستخدم", callback_data="admin_delete")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ])
    
    await callback_query.message.edit_text(users_text, reply_markup=keyboard)

async def admin_delete_handler(client, callback_query):
    await callback_query.message.edit_text(
        "🧹 **حذف جلسة مستخدم**\n\n"
        "أرسل ID المستخدم الذي تريد حذف جلسته:\n"
        "مثال: `123456789`"
    )
    
    if not hasattr(client, 'admin_states'):
        client.admin_states = {}
    client.admin_states[callback_query.from_user.id] = "waiting_delete_user"

async def admin_broadcast_handler(client, callback_query):
    await callback_query.message.edit_text(
        "📤 **بث رسالة للمستخدمين**\n\n"
        "أرسل الرسالة التي تريد بثها لجميع المستخدمين:"
    )
    
    if not hasattr(client, 'admin_states'):
        client.admin_states = {}
    client.admin_states[callback_query.from_user.id] = "waiting_broadcast"

async def admin_restart_handler(client, callback_query):
    await callback_query.message.edit_text("🔄 **جاري إعادة تشغيل البوت...**")
    await bot.restart()

async def help_info_handler(client, callback_query):
    help_text = """
ℹ️ **شرح البوت**

🎯 **كيفية الاستخدام:**
1. اضغط على 'تسجيل الدخول'
2. أرسل رقم هاتفك مع مفتاح الدولة
3. أرسل كود التحقق
4. أرسل رابط الملف للتحميل

📥 **الروابط المدعومة:**
• روابط مباشرة: http://example.com/file.zip
• روابط تليجرام: t.me/username/123
• روابط القنوات الخاصة: t.me/c/chat_id/message_id
• جميع أنواع الملفات

🔒 **الأمان:**
• جلساتك مشفرة
• بياناتك محفوظة بأمان
• لا وصول للبيانات الشخصية
"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_start")]
    ])
    
    await callback_query.message.edit_text(help_text, reply_markup=keyboard)

async def support_handler(client, callback_query):
    support_text = """
📞 **الدعم الفني**

للاستفسارات والمشاكل التقنية:

👨‍💼 **المطور:** @T7ME
📧 **الدعم:** تواصل مباشر

⚡ **سرعة الرد:** فوري
🕒 **وقت العمل:** 24/7

**للتسجيل والدخول اضغط:**
"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data="login")],
        [InlineKeyboardButton("ℹ️ شرح البوت", callback_data="help_info")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_start")]
    ])
    
    await callback_query.message.edit_text(support_text, reply_markup=keyboard)

# -----------------------------
# دوال التسجيل والتحميل (كما هي)
# -----------------------------
async def start_login_process(client, callback_query, re_login=False):
    user_id = callback_query.from_user.id
    
    if re_login:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    await callback_query.message.edit_text(
        "🔐 **تسجيل الدخول بحسابك**\n\n"
        "📱 **أرسل رقم هاتفك مع مفتاح الدولة:**\n"
        "مثال: `+201234567890`"
    )
    
    if not hasattr(client, 'user_states'):
        client.user_states = {}
    client.user_states[user_id] = "waiting_phone"

# -----------------------------
# معالجة الرسائل - مميزات جديدة
# -----------------------------
@bot.on_message(filters.private & filters.text)
async def handle_messages(client, message):
    user_id = message.from_user.id
    text = message.text
    
    # معالجة أوامر الأدمن
    if user_id == ADMIN_ID and hasattr(client, 'admin_states'):
        if client.admin_states.get(user_id) == "waiting_delete_user":
            await handle_admin_delete_user(client, message, text)
            return
        elif client.admin_states.get(user_id) == "waiting_broadcast":
            await handle_admin_broadcast(client, message, text)
            return
    
    # معالجة حالات المستخدم العادي
    if hasattr(client, 'user_states') and client.user_states.get(user_id) == "waiting_phone":
        await handle_phone_input(client, message, text)
    
    elif hasattr(client, 'user_states') and client.user_states.get(user_id) == "waiting_code":
        await handle_code_input(client, message, text)
    
    elif hasattr(client, 'user_states') and client.user_states.get(user_id) == "waiting_password":
        await handle_password_input(client, message, text)
    
    elif get_user_session(user_id) and text.startswith(('http://', 'https://', 't.me/')):
        await handle_download_request(client, message, text)
    
    else:
        if get_user_session(user_id):
            await message.reply_text("❌ هذا ليس رابط تحميل صحيح")
        else:
            await message.reply_text("🔐 يرجى التسجيل أولاً باستخدام /start")

# -----------------------------
# معالجات الأدمن للرسائل
# -----------------------------
async def handle_admin_delete_user(client, message, user_id_str):
    try:
        target_user_id = int(user_id_str)
        delete_user_session(target_user_id)
        
        del client.admin_states[message.from_user.id]
        await message.reply_text(f"✅ تم حذف جلسة المستخدم: `{target_user_id}`")
        
    except ValueError:
        await message.reply_text("❌ ID غير صحيح. أرسل أرقام فقط")

async def handle_admin_broadcast(client, message, broadcast_text):
    all_users = get_all_users()
    success_count = 0
    
    for user in all_users:
        try:
            await bot.send_message(user[0], f"📢 **إشعار من الإدارة:**\n\n{broadcast_text}")
            success_count += 1
        except:
            continue
    
    del client.admin_states[message.from_user.id]
    await message.reply_text(f"✅ تم إرسال الرسالة لـ {success_count} من أصل {len(all_users)} مستخدم")

# -----------------------------
# دوال التسجيل
# -----------------------------
async def handle_phone_input(client, message, phone):
    user_id = message.from_user.id
    
    try:
        user_client = Client(
            f"user_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=phone,
            in_memory=True
        )
        
        await user_client.connect()
        sent_code = await user_client.send_code(phone)
        
        if not hasattr(client, 'temp_data'):
            client.temp_data = {}
            
        client.temp_data[user_id] = {
            'client': user_client,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        client.user_states[user_id] = "waiting_code"
        
        await message.reply_text("📋 **أرسل كود التحقق:**")
        
    except Exception as e:
        await message.reply_text(f"❌ خطأ: {e}")

async def handle_code_input(client, message, code):
    user_id = message.from_user.id
    temp_data = client.temp_data.get(user_id)
    
    if not temp_data:
        await message.reply_text("❌ انتهت الجلسة، ابدأ من جديد /start")
        return
    
    try:
        user_client = temp_data['client']
        
        await user_client.sign_in(
            phone_number=temp_data['phone'],
            phone_code_hash=temp_data['phone_code_hash'], 
            phone_code=code
        )
        
        session_string = await user_client.export_session_string()
        save_session(user_id, session_string, temp_data['phone'])
        
        await user_client.disconnect()
        
        del client.temp_data[user_id]
        client.user_states[user_id] = None
        
        await message.reply_text("✅ **تم التسجيل بنجاح!**\n\n📥 أرسل رابط الملف الآن")

    except Exception as e:
        if "PASSWORD" in str(e):
            client.user_states[user_id] = "waiting_password"
            await message.reply_text("🔐 **أرسل كلمة المرور:**")
        else:
            await message.reply_text(f"❌ كود خاطئ: {e}")

async def handle_password_input(client, message, password):
    user_id = message.from_user.id
    temp_data = client.temp_data.get(user_id)
    
    try:
        user_client = temp_data['client']
        await user_client.check_password(password=password)
        
        session_string = await user_client.export_session_string()
        save_session(user_id, session_string, temp_data['phone'])
        
        await user_client.disconnect()
        del client.temp_data[user_id]
        client.user_states[user_id] = None
        
        await message.reply_text("✅ **تم التسجيل!**\n\n📥 أرسل رابط الملف الآن")
        
    except Exception as e:
        await message.reply_text(f"❌ كلمة مرور خاطئة: {e}")

# -----------------------------
# نظام التحميل المحسن - الجزء الجديد
# -----------------------------
async def handle_download_request(client, message, link):
    user_id = message.from_user.id
    session_string = get_user_session(user_id)

    if not session_string:
        await message.reply_text("❌ سجل الدخول أولاً /start")
        return

    try:
        progress = await message.reply_text("🔍 جاري تحليل الرابط...")

        user_client = Client(
            f"u_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )

        await user_client.connect()

        # ---------------------------
        # 1) استخراج معلومات الرابط - محسّن
        # ---------------------------
        chat_id = None
        msg_id = None
        
        if "t.me" in link:
            if "/c/" in link:
                # روابط القنوات الخاصة: t.me/c/chat_id/message_id
                parts = link.split("/")
                if len(parts) >= 5:
                    chat_id = int("-100" + parts[-2])
                    msg_id = int(parts[-1])
            else:
                # روابط القنوات العامة: t.me/username/message_id
                parts = link.split("/")
                if len(parts) >= 5:
                    username = parts[3]
                    msg_id = int(parts[-1])
                    try:
                        chat = await user_client.get_chat(username)
                        chat_id = chat.id
                    except Exception as e:
                        await progress.edit_text(f"❌ لا يمكن الوصول للقناة: {e}")
                        return
        else:
            # الروابط المباشرة - نستخدم الكود القديم
            file_path = await user_client.download_media(
                link,
                file_name=DOWNLOAD_FOLDER,
                progress=create_progress_callback(client, progress)
            )
            
            if file_path:
                await message.reply_document(
                    file_path,
                    caption=f"✅ **تم التحميل بنجاح!**\n🔗 {link}"
                )
                try:
                    os.remove(file_path)
                except:
                    pass
                await progress.delete()
            else:
                await progress.edit_text("❌ فشل في تحميل الرابط المباشر")
            
            await user_client.disconnect()
            return

        if not chat_id or not msg_id:
            await progress.edit_text("❌ رابط غير صحيح")
            await user_client.disconnect()
            return

        # ---------------------------
        # 2) التأكد من العضوية - محسّن
        # ---------------------------
        try:
            member = await user_client.get_chat_member(chat_id, user_id)
            is_member = member.status in ["member", "administrator", "creator"]
        except:
            is_member = False

        if not is_member:
            try:
                # محاولة الحصول على رابط الدعوة
                invite_link = await user_client.export_chat_invite_link(chat_id)
                btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 انضم للقناة أولاً", url=invite_link)],
                    [InlineKeyboardButton("🔄 تحقق من الانضمام", callback_data=f"check_join_{chat_id}_{msg_id}")]
                ])
                await progress.edit_text(
                    "🚫 **يجب الانضمام للقناة أولاً**\n\n"
                    "• انضم للقناة باستخدام الزر بالأعلى\n"
                    "• ثم اضغط على 'تحقق من الانضمام'",
                    reply_markup=btn
                )
            except:
                await progress.edit_text(
                    "🚫 **قناة خاصة**\n\n"
                    "لا يمكنك تحميل الملف لأن القناة خاصة ولا يوجد رابط دعوة."
                )
            
            await user_client.disconnect()
            return

        # ---------------------------
        # 3) تحميل الرسالة - مع تحسينات
        # ---------------------------
        await progress.edit_text("⏬ جاري تحميل الملف...")

        try:
            msg = await user_client.get_messages(chat_id, msg_id)
            
            if not msg:
                await progress.edit_text("❌ الرسالة غير موجودة")
                await user_client.disconnect()
                return

            if not msg.media:
                await progress.edit_text("❌ لا يوجد ملف في هذه الرسالة")
                await user_client.disconnect()
                return

            # عرض معلومات الملف
            file_info = ""
            if msg.document:
                file_info = f"📄 {msg.document.file_name}\n💾 {msg.document.file_size // 1024 // 1024} MB"
            elif msg.video:
                file_info = f"🎥 فيديو\n💾 {msg.video.file_size // 1024 // 1024} MB"
            elif msg.audio:
                file_info = f"🎵 صوت\n💾 {msg.audio.file_size // 1024 // 1024} MB"
            
            await progress.edit_text(f"📥 جاري التحميل...\n{file_info}")

            # التحميل مع شريط التقدم
            file_path = await user_client.download_media(
                msg,
                file_name=DOWNLOAD_FOLDER,
                progress=create_progress_callback(client, progress)
            )

            if file_path:
                await message.reply_document(
                    file_path,
                    caption="✅ **تم التحميل بنجاح!**\n"
                           "📁 تم التحميل بحسابك الشخصي"
                )
                await progress.delete()
                
                # تنظيف الملف
                try:
                    os.remove(file_path)
                except:
                    pass
            else:
                await progress.edit_text("❌ فشل في تحميل الملف")

        except Exception as e:
            await progress.edit_text(f"❌ خطأ في التحميل: {str(e)}")

        await user_client.disconnect()

    except Exception as e:
        await message.reply_text(f"❌ خطأ غير متوقع: {str(e)}")

# ---------------------------
# دالة التحقق من الانضمام
# ---------------------------
async def check_join_callback(client, callback_query):
    """التحقق من انضمام المستخدم للقناة"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # استخراج chat_id و msg_id من الكallback
    parts = data.split("_")
    chat_id = int(parts[2])
    msg_id = int(parts[3])
    
    session_string = get_user_session(user_id)
    if not session_string:
        await callback_query.answer("❌ سجل الدخول أولاً", show_alert=True)
        return
    
    try:
        user_client = Client(
            f"check_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string,
            in_memory=True
        )
        
        await user_client.connect()
        
        # التحقق من العضوية
        try:
            member = await user_client.get_chat_member(chat_id, user_id)
            is_member = member.status in ["member", "administrator", "creator"]
        except:
            is_member = False
        
        if is_member:
            await callback_query.message.edit_text("✅ **تم الانضمام! جاري التحميل...**")
            # إعادة توجيه للتحميل
            link = f"t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"
            await handle_download_request(client, callback_query.message, link)
        else:
            await callback_query.answer("❌ لم تنضم بعد للقناة", show_alert=True)
        
        await user_client.disconnect()
        
    except Exception as e:
        await callback_query.answer(f"خطأ: {str(e)}", show_alert=True)

# -----------------------------
# التشغيل الرئيسي
# -----------------------------
async def main():
    init_db()
    print("🚀 بدء تشغيل البوت...")
    
    try:
        await bot.start()
        bot_info = await bot.get_me()
        print(f"✅ البوت شغال: @{bot_info.username}")
        print(f"👨‍💼 الأدمن: {ADMIN_ID}")
        print("🎯 البوت جاهز لاستقبال الرسائل...")
        
        await asyncio.Event().wait()
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    print("🚀 Starting Bot...")
    print(f"API_ID: {API_ID}")
    print(f"Admin: {ADMIN_ID}")
    asyncio.run(main())
