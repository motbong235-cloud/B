# -*- coding: utf-8 -*-
"""
=============================================================================
🤖 TELEGRAM BOT HOSTING SYSTEM - FULL COMPLETE SOURCE CODE
- Bot Token: 8915733015:AAFq15SoM6ZMVAiqd4jz0NcMBlEf-kWrCRk
- Admin ID: 8648924435
- Admin Username: @PoSovannaReach
=============================================================================
"""

import os
import sys
import re
import time
import shutil
import sqlite3
import random
import string
import datetime
import zipfile
import subprocess
import threading
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)

# ---------------------------------------------------------------------------
# ⚙️ កំណត់រចនាសម្ព័ន្ធ (Configurations)
# ---------------------------------------------------------------------------
TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))

if not TOKEN:
    raise SystemExit("❌ សូមកំណត់ Environment Variable ឈ្មោះ BOT_TOKEN មុននឹងដំណើរការ Bot!")
if not ADMIN_ID:
    raise SystemExit("❌ សូមកំណត់ Environment Variable ឈ្មោះ ADMIN_ID មុននឹងដំណើរការ Bot!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR ដាក់លើ Render Persistent Disk (mount path) ដើម្បីកុំអោយទិន្នន័យបាត់ពេល Redeploy
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
DB_PATH = os.path.join(DATA_DIR, 'bot_database.db')

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# Global process tracking & user session state
running_processes = {}  # {host_id: subprocess.Popen}
host_start_times = {}   # {host_id: timestamp}
user_state = {}         # {user_id: {'state': ..., 'data': ...}}

# ---------------------------------------------------------------------------
# 🗄 ការគ្រប់គ្រង DATABASE (SQLite)
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'active',
            quota INTEGER DEFAULT 0,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key_code TEXT PRIMARY KEY,
            days INTEGER DEFAULT 30,
            status TEXT DEFAULT 'active',
            created_by INTEGER DEFAULT 0,
            used_by INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS hostings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT,
            bot_token TEXT,
            main_file TEXT,
            folder_path TEXT,
            status TEXT DEFAULT 'offline',
            pid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            package_name TEXT,
            days INTEGER,
            price REAL,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS shop_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            days INTEGER,
            price REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            file_id TEXT,
            extra_type TEXT
        )
    ''')
    
    # បន្ថែម Column សម្រាប់ថ្ងៃផុតកំណត់ (ជៀសវាង Error បើមានស្រាប់)
    try:
        c.execute("ALTER TABLE keys ADD COLUMN expire_at TIMESTAMP")
        c.execute("ALTER TABLE keys ADD COLUMN used_at TIMESTAMP")
    except:
        pass
    
    # Insert default shop packages if none exist
    c.execute("SELECT COUNT(*) FROM shop_packages")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO shop_packages (name, days, price) VALUES ('ជួល ១ ថ្ងៃ', 1, 0.5)")
        c.execute("INSERT INTO shop_packages (name, days, price) VALUES ('ជួល ១ ខែ', 30, 5.0)")
        c.execute("INSERT INTO shop_packages (name, days, price) VALUES ('ជួល ៣ ខែ', 90, 13.0)")

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------------------------
# 🎛 KEYBOARDS / MENUS (ប៊ូតុងទាំងអស់)
# ---------------------------------------------------------------------------
def get_main_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton('🛒 ទិញ Key Shop'),
        KeyboardButton('👉 បញ្ចូល Key'),
        KeyboardButton('📊 ផ្ទាំងព័ត៌មាន (Dashboard)'),
        KeyboardButton('⚙️ ការកំណត់'),
        KeyboardButton('➕ បន្ថែម Hosting ថ្មី'),
        KeyboardButton('📂 មើល Hosting របស់ខ្ញុំ')
    )
    return m

def get_admin_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton('📊 ស្ថិតិប្រព័ន្ធ'),
        KeyboardButton('📢 Broadcast'),
        KeyboardButton('👤 បញ្ជី Users ទាំងអស់'),
        KeyboardButton('📅 មើល Hosting ទាំងអស់'),
        KeyboardButton('➕ បន្ថែម Hosting User'),
        KeyboardButton('🔖 ធ្វើ Backup ឥឡូវនេះ'),
        KeyboardButton('🖼 ដាក់ QR ដោយដៃ'),
        KeyboardButton('🗑 លុប QR ដោយដៃ'),
        KeyboardButton('🔐 បង្កើត Key'),
        KeyboardButton('✏️ អេតបូតុង/នឹងដាក់ថ្ងៃ'),
        KeyboardButton('🗑 លុបបូតុង'),
        KeyboardButton('✏️ ដាក់តម្លៃបូតុង'),
        KeyboardButton('🖼 Wellcome'),
        KeyboardButton('🗑 លុប Welcome'),
        KeyboardButton('💸 ប្រាក់ចំណូល'),
        KeyboardButton('🗑 លុប User ផុតកំណត់')
    )
    return m

def get_settings_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton('🌐 ប្ដូរភាសា'),
        KeyboardButton('⏰ កំណត់ Time Zone'),
        KeyboardButton('🔄 Auto Restart'),
        KeyboardButton('💾 Auto Backup'),
        KeyboardButton('🔙 ត្រឡប់ក្រោយ')
    )
    return m

def get_hosting_actions_menu(host_id):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton(f'▶️ ចាប់ផ្ដើម Bot (ID:{host_id})'),
        KeyboardButton(f'⏹ បពា្ឈប់ Bot (ID:{host_id})'),
        KeyboardButton(f'🔄 ចាប់ផ្ដើមឡើងវិញ (ID:{host_id})'),
        KeyboardButton(f'📊 មើលស្ថានភាព (ID:{host_id})'),
        KeyboardButton(f'⏱️ មើលរយៈពេលដំណើរការ (ID:{host_id})'),
        KeyboardButton(f'📜 មើលកំណត់ហេតុ (Logs) (ID:{host_id})'),
        KeyboardButton(f'📁 គ្រប់គ្រងឯកសារ (ID:{host_id})'),
        KeyboardButton(f'🗑 លុប Hosting (ID:{host_id})'),
        KeyboardButton('🔙 ត្រឡប់ក្រោយ')
    )
    return m

def get_file_manager_menu(host_id):
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        KeyboardButton('📤 Upload File'),
        KeyboardButton('📥 Download File'),
        KeyboardButton('📦 ពន្លា ZIP'),
        KeyboardButton('🗑️ លុបឯកសារ'),
        KeyboardButton('🛠 ដំឡើង Library (pip)'),
        KeyboardButton('📜 មើល Library'),
        KeyboardButton(f'🔙 ត្រឡប់ទៅ Hosting (ID:{host_id})')
    )
    return m

# ---------------------------------------------------------------------------
# 🛠 HELPER FUNCTIONS (ការស្រង់ Token, Process, Logs)
# ---------------------------------------------------------------------------
def extract_token_from_folder(folder_path):
    """ស្កេនរក Telegram Bot Token ក្នុង File .py ទាំងអស់ស្វ័យប្រវត្តិ"""
    token_pattern = re.compile(r'([0-9]{8,10}:[a-zA-Z0-9_-]{35})')
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        matches = token_pattern.findall(content)
                        if matches:
                            return matches[0]
                except:
                    pass
    return "មិនស្គាល់ Token"

def find_main_file(folder_path):
    """ស្វែងរក main file សម្រាប់រត់ (.py)"""
    candidates = ['main.py', 'bot.py', 'app.py', 'run.py', 'index.py']
    for cand in candidates:
        cand_path = os.path.join(folder_path, cand)
        if os.path.exists(cand_path):
            return cand
    for file in os.listdir(folder_path):
        if file.endswith('.py'):
            return file
    return None

def start_bot_process(host_id):
    """បញ្ឆេះ process របស់ bot 100% មិនគាំង"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT folder_path, main_file FROM hostings WHERE id=?", (host_id,))
    row = c.fetchone()
    conn.close()

    if not row or not row['folder_path'] or not row['main_file']:
        return False, "រកមិនឃើញឯកសារកូដសម្រាប់ដំណើរការទេ!"

    folder = row['folder_path']
    main_file = row['main_file']
    full_script = os.path.join(folder, main_file)

    if not os.path.exists(full_script):
        return False, f"រកមិនឃើញ File {main_file} នៅក្នុងថតទេ!"

    # បើកំពុងដើររួចហើយ ឈប់សិន
    stop_bot_process(host_id)

    log_path = os.path.join(folder, 'host.log')
    log_file = open(log_path, 'a', encoding='utf-8', errors='ignore')
    log_file.write(f"\n\n=== [STARTING BOT AT {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
    log_file.flush()

    try:
        # បញ្ឆេះ subprocess ឯករាជ្យ
        proc = subprocess.Popen(
            [sys.executable, main_file],
            cwd=folder,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL
        )
        running_processes[str(host_id)] = proc
        host_start_times[str(host_id)] = time.time()

        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE hostings SET pid=?, status='online' WHERE id=?", (proc.pid, host_id))
        conn.commit()
        conn.close()
        return True, proc.pid
    except Exception as e:
        return False, str(e)

def stop_bot_process(host_id):
    """បិទ process bot"""
    str_id = str(host_id)
    if str_id in running_processes:
        proc = running_processes[str_id]
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass
        del running_processes[str_id]

    if str_id in host_start_times:
        del host_start_times[str_id]

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE hostings SET pid=0, status='offline' WHERE id=?", (host_id,))
    conn.commit()
    conn.close()
    return True

# ---------------------------------------------------------------------------
# 🚀 START & WELCOME HANDLER
# ---------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    c.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    
    c.execute("SELECT value, file_id, extra_type FROM settings WHERE key='welcome_msg'")
    welcome_setting = c.fetchone()
    conn.commit()
    conn.close()

    user_state[user_id] = {'state': None, 'data': {}}

    if user_id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "👑 <b>សូមស្វាគមន៍ Admin មកកាន់ផ្ទាំងគ្រប់គ្រងប្រព័ន្ធ!</b>\nសូមជ្រើសរើសម៉ឺនុយខាងក្រោម៖",
            reply_markup=get_admin_menu()
        )
        return

    # Check Custom Welcome
    if welcome_setting and welcome_setting['value']:
        val = welcome_setting['value']
        fid = welcome_setting['file_id']
        etype = welcome_setting['extra_type']
        if etype == 'photo' and fid:
            bot.send_photo(message.chat.id, photo=fid, caption=val, reply_markup=get_main_menu())
            return
        elif etype == 'sticker' and fid:
            bot.send_sticker(message.chat.id, sticker=fid)
            if val: bot.send_message(message.chat.id, val, reply_markup=get_main_menu())
            return
        elif val:
            bot.send_message(message.chat.id, val, reply_markup=get_main_menu())
            return

    # Default Welcome
    default_text = (
        "🤖 <b>សូមស្វាគមន៍មកកាន់ប្រព័ន្ធ Telegram Bot Hosting!</b> 🚀\n\n"
        "✨ សេវាកម្ម Hosting កូដ Telegram Bot រហ័ស ទាន់ចិត្ត និងមានស្ថិរភាព ១០០%។\n"
        "👉 សូមចុចជ្រើសរើសមុខងារតាមប៊ូតុងខាងក្រោម៖"
    )
    bot.send_message(message.chat.id, default_text, reply_markup=get_main_menu())

# ---------------------------------------------------------------------------
# 📊 ផ្ទាំងព័ត៌មាន (DASHBOARD)
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == '📊 ផ្ទាំងព័ត៌មាន (Dashboard)')
def handle_dashboard(message):
    user_id = message.from_user.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT quota, used FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM hostings WHERE user_id=? AND status='online'", (user_id,))
    running = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM hostings WHERE user_id=? AND status='offline'", (user_id,))
    stopped = c.fetchone()[0]
    conn.close()

    quota = u['quota'] if u else 0
    used = u['used'] if u else 0

    text = (
        "📊 <b>ផ្ទាំងព័ត៌មាន (Dashboard)</b>\n\n"
        f"📦 កូតាសរុប: <b>{quota}</b> Slot\n"
        f"✅ កំពុងប្រើប្រាស់: <b>{used}</b> Slot\n"
        f"🟢 កំពុងដើរ: <b>{running}</b>\n"
        f"🔴 ឈប់ដើរ: <b>{stopped}</b>"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu())

# ---------------------------------------------------------------------------
# ⚙️ ការកំណត់ (SETTINGS)
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == '⚙️ ការកំណត់')
def handle_settings(message):
    bot.send_message(message.chat.id, "⚙️ <b>ការកំណត់ប្រព័ន្ធ</b>", reply_markup=get_settings_menu())

@bot.message_handler(func=lambda m: m.text == '🌐 ប្ដូរភាសា')
def handle_lang(message):
    bot.send_message(message.chat.id, "✅ មុខងារនេះបានកំណត់ជាលំនាំដើម (ភាសាខ្មែរ / UTC+7)។")

@bot.message_handler(func=lambda m: m.text == '⏰ កំណត់ Time Zone')
def handle_timezone(message):
    bot.send_message(message.chat.id, "✅ មុខងារនេះបានកំណត់ជាលំនាំដើម (ភាសាខ្មែរ / UTC+7)។")

@bot.message_handler(func=lambda m: m.text == '🔄 Auto Restart')
def handle_auto_restart(message):
    bot.send_message(message.chat.id, "✅ Auto Restart ត្រូវបាន បិទ ជោគជ័យ!")

@bot.message_handler(func=lambda m: m.text == '💾 Auto Backup')
def handle_auto_backup(message):
    bot.send_message(message.chat.id, "✅ Auto Backup ត្រូវបាន បិទ ជោគជ័យ!")

@bot.message_handler(func=lambda m: m.text == '🔙 ត្រឡប់ក្រោយ')
def handle_back_btn(message):
    handle_start(message)

# ---------------------------------------------------------------------------
# 🛒 ទិញ KEY SHOP & 👉 បញ្ចូល KEY
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == '🛒 ទិញ Key Shop')
def handle_key_shop(message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM shop_packages")
    pkgs = c.fetchall()
    conn.close()

    markup = InlineKeyboardMarkup()
    for p in pkgs:
        markup.add(InlineKeyboardButton(f"💳 {p['name']} ({p['days']}ថ្ងៃ) - ${p['price']}", callback_data=f"buy_pkg_{p['id']}"))
    markup.add(InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ", callback_data="close_shop_menu"))

    bot.send_message(message.chat.id, "🛒 <b>សូមបងរើសថ្ងៃខែដែលចង់ជួល៖</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'close_shop_menu')
def handle_close_shop(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_pkg_'))
def handle_select_pkg(call):
    pkg_id = call.data.split('_')[2]
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM shop_packages WHERE id=?", (pkg_id,))
    pkg = c.fetchone()
    
    c.execute("SELECT file_id, value FROM settings WHERE key='qr_payment'")
    qr_data = c.fetchone()
    conn.close()

    if not pkg:
        bot.answer_callback_query(call.id, "កញ្ចប់នេះមិនមានទេ!")
        return

    user_state[call.from_user.id] = {
        'state': 'WAITING_RECEIPT',
        'pkg_name': pkg['name'],
        'days': pkg['days'],
        'price': pkg['price']
    }

    bot.delete_message(call.message.chat.id, call.message.message_id)
    caption = (
        f"📦 <b>កញ្ចប់ដែលអ្នកបានជ្រើសរើស:</b> {pkg['name']}\n"
        f"⏳ <b>រយៈពេល:</b> {pkg['days']} ថ្ងៃ\n"
        f"💵 <b>តម្លៃ:</b> ${pkg['price']}\n\n"
        "👉 សូមស្កេន QR ខាងក្រោមដើម្បីបង់ប្រាក់ រួចថតរូបវិក្កយបត្រ (Screenshot) ផ្ញើចូលទីនេះ៖"
    )

    if qr_data and qr_data['file_id']:
        bot.send_photo(call.message.chat.id, photo=qr_data['file_id'], caption=caption)
    else:
        bot.send_message(call.message.chat.id, caption)

@bot.message_handler(func=lambda m: m.text == '👉 បញ្ចូល Key')
def handle_enter_key_btn(message):
    user_state[message.from_user.id] = {'state': 'WAITING_LICENSE_KEY'}
    bot.send_message(message.chat.id, "👉 <b>សូមវាយ License Key របស់អ្នក:</b>")

# ---------------------------------------------------------------------------
# ➕ បន្ថែម HOSTING ថ្មី & UPLOAD (.PY / .ZIP)
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == '➕ បន្ថែម Hosting ថ្មី')
def handle_add_hosting_btn(message):
    user_id = message.from_user.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT quota, used FROM users WHERE user_id=?", (user_id,))
    u = c.fetchone()
    conn.close()

    quota = u['quota'] if u else 0
    used = u['used'] if u else 0

    if quota <= used:
        bot.send_message(
            message.chat.id,
            f"❌ <b>អ្នកមិនមានកូតាគ្រប់គ្រាន់ទេ!</b>\n\n📦 កូតារបស់អ្នក: {quota} Slot (ប្រើអស់ {used} Slot)\n👉 សូមចុច <b>🛒 ទិញ Key Shop</b> ឬ <b>👉 បញ្ចូល Key</b> ដើម្បីបន្ថែម Slot។",
            reply_markup=get_main_menu()
        )
        return

    user_state[user_id] = {'state': 'WAITING_HOST_FILE'}
    text = (
        "📤 <b>Upload ឯកសារ (.py ឬ .zip):</b>\n\n"
        "⚠️ ប្រព័ន្ធនឹងទាញ Token និងបញ្ឆេះកូដដោយស្វ័យប្រវត្តិ។"
    )
    bot.send_message(message.chat.id, text)

# ---------------------------------------------------------------------------
# 📂 មើល HOSTING របស់ខ្ញុំ & HOSTING MANAGEMENT
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == '📂 មើល Hosting របស់ខ្ញុំ')
def handle_my_hostings_list(message):
    user_id = message.from_user.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM hostings WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "📂 <b>អ្នកមិនទាន់មាន Hosting ណាមួយនៅឡើយទេ!</b>\nសូមចុច <b>➕ បន្ថែម Hosting ថ្មី</b> ដើម្បីដាក់កូដ។", reply_markup=get_main_menu())
        return

    text = "📂 <b>វាយ ID នៃ Hosting ដែលអ្នកចង់គ្រប់គ្រង៖</b>\n\n"
    for r in rows:
        status_icon = "🟢 online" if r['status'] == 'online' else "🔴 offline"
        text += f"🆔 <code>{r['id']}</code> | 🤖 {r['bot_name']} | {status_icon}\n"

    user_state[user_id] = {'state': 'WAITING_HOST_ID_SELECT'}
    bot.send_message(message.chat.id, text)

# Handling Actions on Hostings
@bot.message_handler(func=lambda m: m.text and (
    m.text.startswith('▶️ ចាប់ផ្ដើម Bot') or
    m.text.startswith('⏹ បពា្ឈប់ Bot') or
    m.text.startswith('🔄 ចាប់ផ្ដើមឡើងវិញ') or
    m.text.startswith('📊 មើលស្ថានភាព') or
    m.text.startswith('⏱️ មើលរយៈពេលដំណើរការ') or
    m.text.startswith('📜 មើលកំណត់ហេតុ (Logs)') or
    m.text.startswith('📁 គ្រប់គ្រងឯកសារ') or
    m.text.startswith('🗑 លុប Hosting')
))
def handle_hosting_controls(message):
    text = message.text
    try:
        host_id = int(re.search(r'ID:(\d+)', text).group(1))
    except:
        bot.send_message(message.chat.id, "❌ ID មិនត្រឹមត្រូវ!")
        return

    # Verify ownership
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM hostings WHERE id=?", (host_id,))
    host = c.fetchone()
    conn.close()

    if not host or (host['user_id'] != message.from_user.id and message.from_user.id != ADMIN_ID):
        bot.send_message(message.chat.id, "❌ រកមិនឃើញ Hosting នេះ ឬអ្នកគ្មានសិទ្ធិគ្រប់គ្រងទេ!")
        return

    if text.startswith('▶️ ចាប់ផ្ដើម Bot'):
        success, res = start_bot_process(host_id)
        if success:
            bot.send_message(message.chat.id, f"✅ Bot បានចាប់ផ្ដើមបញ្ឆេះ! (PID: {res})\nសូមចូល មើលកំណត់ហេតុ (Logs) ដើម្បីដឹងថាវាដើរឬគាំង។", reply_markup=get_hosting_actions_menu(host_id))
        else:
            bot.send_message(message.chat.id, f"❌ បរាជ័យក្នុងការបញ្ឆេះ Bot:\n{res}", reply_markup=get_hosting_actions_menu(host_id))

    elif text.startswith('⏹ បពា្ឈប់ Bot'):
        stop_bot_process(host_id)
        bot.send_message(message.chat.id, "✅ Bot ត្រូវបានបញ្ឈប់ (Offline)!", reply_markup=get_hosting_actions_menu(host_id))

    elif text.startswith('🔄 ចាប់ផ្ដើមឡើងវិញ'):
        stop_bot_process(host_id)
        time.sleep(1)
        success, res = start_bot_process(host_id)
        if success:
            bot.send_message(message.chat.id, f"✅ Bot ត្រូវបានចាប់ផ្ដើមឡើងវិញជោគជ័យ! (PID: {res})", reply_markup=get_hosting_actions_menu(host_id))
        else:
            bot.send_message(message.chat.id, f"❌ បរាជ័យក្នុងការ Restart: {res}", reply_markup=get_hosting_actions_menu(host_id))

    elif text.startswith('📊 មើលស្ថានភាព'):
        is_online = str(host_id) in running_processes
        status_text = f"🟢 ស្ថានភាព: Online (PID: {host['pid']})" if is_online else "🔴 ស្ថានភាព: Offline"
        bot.send_message(message.chat.id, status_text, reply_markup=get_hosting_actions_menu(host_id))

    elif text.startswith('⏱️ មើលរយៈពេលដំណើរការ'):
        if str(host_id) in host_start_times and str(host_id) in running_processes:
            elapsed = int(time.time() - host_start_times[str(host_id)])
            hours, rem = divmod(elapsed, 3600)
            mins, secs = divmod(rem, 60)
            bot.send_message(message.chat.id, f"⏱️ <b>រយៈពេលដំណើរការ:</b> {hours} ម៉ោង {mins} នាទី {secs} វិនាទី")
        else:
            bot.send_message(message.chat.id, "⏱️ <b>Bot មិនទាន់ដំណើរការនៅឡើយទេ (Offline)</b>")

    elif text.startswith('📜 មើលកំណត់ហេតុ (Logs)'):
        log_file = os.path.join(host['folder_path'], 'host.log')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    last_lines = "".join(lines[-35:]) if lines else "គ្មានកំណត់ហេតុនៅឡើយទេ..."
                bot.send_message(message.chat.id, f"📜 <b>កំណត់ហេតុ (Logs) ចុងក្រោយ៖</b>\n\n<pre>{last_lines}</pre>", reply_markup=get_hosting_actions_menu(host_id))
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ មិនអាចអាន Logs បានទេ: {e}")
        else:
            bot.send_message(message.chat.id, "📜 <b>កំណត់ហេតុ (Logs) ចុងក្រោយ៖</b>\n\n<i>មិនទាន់មានទិន្នន័យ Log ទេ...</i>")

    elif text.startswith('📁 គ្រប់គ្រងឯកសារ'):
        bot.send_message(message.chat.id, "📁 <b>File Manager Active</b>", reply_markup=get_file_manager_menu(host_id))

    elif text.startswith('🗑 លុប Hosting'):
        user_state[message.from_user.id] = {'state': 'CONFIRM_DELETE_HOST', 'host_id': host_id}
        bot.send_message(message.chat.id, "⚠️ <b>តើអ្នកប្រាកដទេ?</b>\nវាយពាក្យ <code>yes</code> ដើម្បីលុប។")

# ---------------------------------------------------------------------------
# 📁 FILE MANAGER SUB-ACTIONS
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text and (
    m.text == '📤 Upload File' or
    m.text == '📥 Download File' or
    m.text == '📦 ពន្លា ZIP' or
    m.text == '🗑️ លុបឯកសារ' or
    m.text == '🛠 ដំឡើង Library (pip)' or
    m.text == '📜 មើល Library' or
    m.text.startswith('🔙 ត្រឡប់ទៅ Hosting')
))
def handle_file_manager_actions(message):
    text = message.text
    user_id = message.from_user.id

    if text.startswith('🔙 ត្រឡប់ទៅ Hosting'):
        host_id = int(re.search(r'ID:(\d+)', text).group(1))
        bot.send_message(message.chat.id, f"📂 <b>គ្រប់គ្រង Hosting ID: {host_id}</b>", reply_markup=get_hosting_actions_menu(host_id))
        return

    # Check last active host_id from session or DB
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, folder_path FROM hostings WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        bot.send_message(message.chat.id, "❌ មិនមាន Hosting សកម្មទេ!", reply_markup=get_main_menu())
        return

    host_id = row['id']
    folder = row['folder_path']

    if text == '📤 Upload File':
        user_state[user_id] = {'state': 'FM_UPLOAD_FILE', 'host_id': host_id, 'folder': folder}
        bot.send_message(message.chat.id, "📤 <b>សូម Upload ឯកសារចូលមកទីនេះ៖</b>")

    elif text == '📥 Download File':
        files = os.listdir(folder) if os.path.exists(folder) else []
        file_list_str = "\n".join([f"• <code>{f}</code>" for f in files]) if files else "<i>គ្មានឯកសារទេ</i>"
        user_state[user_id] = {'state': 'FM_DOWNLOAD_FILE', 'host_id': host_id, 'folder': folder}
        bot.send_message(message.chat.id, f"📂 <b>បញ្ជី File:</b>\n{file_list_str}\n\n✍️ <b>វាយឈ្មោះ File Download:</b>")

    elif text == '📦 ពន្លា ZIP':
        zips = [f for f in os.listdir(folder) if f.endswith('.zip')] if os.path.exists(folder) else []
        if not zips:
            bot.send_message(message.chat.id, "❌ គ្មាន File .zip នៅក្នុង Hosting នេះទេ!")
            return
        for z in zips:
            try:
                with zipfile.ZipFile(os.path.join(folder, z), 'r') as zip_ref:
                    zip_ref.extractall(folder)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ បរាជ័យក្នុងការពន្លា {z}: {e}")
                return
        bot.send_message(message.chat.id, "✅ បានពន្លា ZIP ជោគជ័យទាំងអស់!")

    elif text == '🗑️ លុបឯកសារ':
        files = os.listdir(folder) if os.path.exists(folder) else []
        file_list_str = "\n".join([f"• <code>{f}</code>" for f in files]) if files else "<i>គ្មានឯកសារទេ</i>"
        user_state[user_id] = {'state': 'FM_DELETE_FILE', 'host_id': host_id, 'folder': folder}
        bot.send_message(message.chat.id, f"📂 <b>បញ្ជី File:</b>\n{file_list_str}\n\n✍️ <b>វាយឈ្មោះ File ដែលចង់លុប:</b>")

    elif text == '🛠 ដំឡើង Library (pip)':
        user_state[user_id] = {'state': 'FM_PIP_INSTALL', 'host_id': host_id}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយឈ្មោះ Library (ឧ. pyTelegramBotAPI, aiogram, pyrogram):</b>")

    elif text == '📜 មើល Library':
        libs = "📦 <b>បញ្ជី Library ដែលគាំទ្ររួចជាស្រេច (Supported):</b>\n\n"
        supported = ['pyTelegramBotAPI (telebot)', 'aiogram', 'pyrogram', 'requests', 'sqlite3', 'tgcrypto', 'pillow', 'aiohttp', 'cryptography', 'flask']
        for s in supported:
            libs += f"✅ {s}\n"
        libs += "\n💡 អ្នកក៏អាចប្រើ <b>🛠 ដំឡើង Library (pip)</b> ដើម្បីដំឡើង Library ថ្មីៗបន្ថែមទៀតបានគ្រប់ពេល!"
        bot.send_message(message.chat.id, libs)

# ---------------------------------------------------------------------------
# 👑 ADMIN ACTIONS & MANAGEMENT
# ---------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    '📊 ស្ថិតិប្រព័ន្ធ', '📢 Broadcast', '👤 បញ្ជី Users ទាំងអស់',
    '📅 មើល Hosting ទាំងអស់', '➕ បន្ថែម Hosting User', '🔖 ធ្វើ Backup ឥឡូវនេះ',
    '🖼 ដាក់ QR ដោយដៃ', '🗑 លុប QR ដោយដៃ', '🔐 បង្កើត Key',
    '✏️ អេតបូតុង/នឹងដាក់ថ្ងៃ', '🗑 លុបបូតុង', '✏️ ដាក់តម្លៃបូតុង',
    '🖼 Wellcome', '🗑 លុប Welcome', '💸 ប្រាក់ចំណូល', '🗑 លុប User ផុតកំណត់'
])
def handle_admin_commands(message):
    text = message.text
    user_id = message.from_user.id

    if text == '📊 ស្ថិតិប្រព័ន្ធ':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM hostings")
        total_host = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM hostings WHERE status='online'")
        online_host = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys")
        total_keys = c.fetchone()[0]
        conn.close()

        stats = (
            "📊 <b>ស្ថិតិប្រព័ន្ធទាំងមូល (System Statistics)</b>\n\n"
            f"👤 សមាជិកសរុប: <b>{total_users}</b> នាក់\n"
            f"📦 Hosting សរុប: <b>{total_host}</b>\n"
            f"🟢 Bot កំពុងដំណើរការ: <b>{online_host}</b>\n"
            f"🔐 Key បង្កើតសរុប: <b>{total_keys}</b>"
        )
        bot.send_message(message.chat.id, stats)

    elif text == '📢 Broadcast':
        user_state[user_id] = {'state': 'ADMIN_BROADCAST'}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយសារដែលអ្នកចង់ផ្ញើទៅកាន់ Users ទាំងអស់៖</b>")

    elif text == '👤 បញ្ជី Users ទាំងអស់':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id, username, quota, used FROM users ORDER BY created_at DESC LIMIT 50")
        users = c.fetchall()
        conn.close()

        msg = "👤 <b>បញ្ជី Users (៥០ នាក់ចុងក្រោយ)៖</b>\n\n"
        for u in users:
            msg += f"• <code>{u['user_id']}</code> (@{u['username']}) | Quota: {u['quota']} (Used: {u['used']})\n"
        bot.send_message(message.chat.id, msg)

    elif text == '📅 មើល Hosting ទាំងអស់':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM hostings ORDER BY id DESC LIMIT 50")
        hosts = c.fetchall()
        conn.close()

        msg = "📅 <b>បញ្ជី Hosting ទាំងអស់ (៥០ ចុងក្រោយ)៖</b>\n\n"
        for h in hosts:
            icon = "🟢" if h['status'] == 'online' else "🔴"
            msg += f"🆔 {h['id']} | User: <code>{h['user_id']}</code> | 🤖 {h['bot_name']} | {icon}\n"
        bot.send_message(message.chat.id, msg)

    elif text == '➕ បន្ថែម Hosting User':
        user_state[user_id] = {'state': 'ADMIN_ADD_QUOTA'}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយ: UserID ចំនួនSlot (ឧ. 123456789 2):</b>")

    elif text == '🔖 ធ្វើ Backup ឥឡូវនេះ':
        if os.path.exists(DB_PATH):
            bot.send_message(message.chat.id, "⏳ កំពុងបង្កើត Backup Database...")
            with open(DB_PATH, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ នេះជា File Database Backup របស់អ្នក!")
        else:
            bot.send_message(message.chat.id, "❌ រកមិនឃើញ Database ទេ!")

    elif text == '🖼 ដាក់ QR ដោយដៃ':
        user_state[user_id] = {'state': 'ADMIN_SET_QR'}
        bot.send_message(message.chat.id, "📸 <b>សូម Upload រូបភាព QR Code សម្រាប់ទទួលប្រាក់៖</b>")

    elif text == '🗑 លុប QR ដោយដៃ':
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM settings WHERE key='qr_payment'")
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ បានលុប QR Code រួចរាល់!")

    elif text == '🔐 បង្កើត Key':
        user_state[user_id] = {'state': 'ADMIN_GEN_KEY'}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយចំនួនថ្ងៃដែលចង់បង្កើត (ឧ. 30):</b>")

    elif text == '✏️ អេតបូតុង/នឹងដាក់ថ្ងៃ':
        user_state[user_id] = {'state': 'ADMIN_ADD_PKG_NAME'}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយឈ្មោះប៊ូតុង (ឧទាហរណ៍: 1 ថ្ងៃ = 24 ម៉ោង):</b>")

    elif text == '🗑 លុបបូតុង':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM shop_packages")
        pkgs = c.fetchall()
        conn.close()
        markup = InlineKeyboardMarkup()
        for p in pkgs:
            markup.add(InlineKeyboardButton(f"❌ លុប {p['name']}", callback_data=f"del_pkg_{p['id']}"))
        bot.send_message(message.chat.id, "🗑 <b>សូមជ្រើសរើសប៊ូតុងដែលចង់លុប៖</b>", reply_markup=markup)

    elif text == '✏️ ដាក់តម្លៃបូតុង':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM shop_packages")
        pkgs = c.fetchall()
        conn.close()
        
        if not pkgs:
            bot.send_message(message.chat.id, "❌ មិនទាន់មានកញ្ចប់ណាមួយទេ!")
            return
            
        markup = InlineKeyboardMarkup()
        for p in pkgs:
            markup.add(InlineKeyboardButton(f"📝 កែ {p['name']} (${p['price']})", callback_data=f"edit_pkg_{p['id']}"))
        
        bot.send_message(message.chat.id, "📝 <b>សូមជ្រើសរើសប៊ូតុងដែលអ្នកចង់កែប្រែតម្លៃ៖</b>", reply_markup=markup)

    elif text == '🖼 Wellcome':
        user_state[user_id] = {'state': 'ADMIN_SET_WELCOME'}
        bot.send_message(message.chat.id, "📸 <b>សូមផ្ញើរូបភាព ឬ Sticker ព្រមទាំងសរសេរអក្សរ Caption សម្រាប់ Welcome៖</b>")

    elif text == '🗑 លុប Welcome':
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM settings WHERE key='welcome_msg'")
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ បានលុបសារ Welcome ជោគជ័យ!")
        
    elif text == '💸 ប្រាក់ចំណូល':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT SUM(price) FROM payments WHERE status='approved'")
        total = c.fetchone()[0] or 0.0
        conn.close()
        bot.send_message(message.chat.id, f"💸 <b>ប្រាក់ចំណូលសរុប (Total Revenue):</b> <b>${total:.2f}</b>")

    elif text == '🗑 លុប User ផុតកំណត់':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT used_by FROM keys WHERE status='expired'")
        expired_users = c.fetchall()
        
        count_deleted = 0
        for u in expired_users:
            uid = u[0]
            # បិទ Bot និងលុប File
            c.execute("SELECT id, folder_path FROM hostings WHERE user_id=?", (uid,))
            hosts = c.fetchall()
            for h in hosts:
                stop_bot_process(h['id'])
                if h['folder_path'] and os.path.exists(h['folder_path']):
                    shutil.rmtree(h['folder_path'], ignore_errors=True)
            # លុបទិន្នន័យពី Database
            c.execute("DELETE FROM hostings WHERE user_id=?", (uid,))
            c.execute("UPDATE users SET used = 0 WHERE user_id=?", (uid,))
            count_deleted += 1
            
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ <b>បានលុប Hosting របស់ User ដែលផុតកំណត់ចំនួន {count_deleted} នាក់!</b>")

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_pkg_'))
def handle_edit_package_price(call):
    if call.from_user.id != ADMIN_ID: return
    pkg_id = call.data.split('_')[2]
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM shop_packages WHERE id=?", (pkg_id,))
    pkg = c.fetchone()
    conn.close()
    
    if not pkg:
        bot.answer_callback_query(call.id, "រកមិនឃើញកញ្ចប់នេះទេ!")
        return
        
    user_state[call.from_user.id] = {'state': 'ADMIN_EDIT_PRICE_VALUE', 'pkg_id': pkg_id, 'pkg_name': pkg['name']}
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, f"✍️ <b>សូមវាយតម្លៃថ្មីសម្រាប់កញ្ចប់ «{pkg['name']}» (ឧទាហរណ៍: 5.5):</b>")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_pkg_'))
def handle_delete_package(call):
    if call.from_user.id != ADMIN_ID: return
    pkg_id = call.data.split('_')[2]
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM shop_packages WHERE id=?", (pkg_id,))
    conn.commit()
    conn.close()
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "✅ បានលុបប៊ូតុងកញ្ចប់ជោគជ័យ!")

# ---------------------------------------------------------------------------
# 💳 PAYMENT APPROVAL / REJECTION (ADMIN)
# ---------------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_appr_') or call.data.startswith('pay_rejc_'))
def handle_pay_decision(call):
    if call.from_user.id != ADMIN_ID: return
    
    parts = call.data.split('_')
    action_type = parts[1] # 'appr' or 'rejc'
    pay_id = parts[2]
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE id=?", (pay_id,))
    payment = c.fetchone()

    if not payment:
        bot.answer_callback_query(call.id, "រកមិនឃើញទិន្នន័យបង់ប្រាក់ទេ!")
        conn.close()
        return

    if action_type == 'appr': # Approve
        # Generate License Key: BABY-HOSTING-XXXXXX
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_key = f"BABY-HOSTING-{random_code}"
        
        c.execute("INSERT INTO keys (key_code, days, status, created_by) VALUES (?, ?, 'active', ?)", (new_key, payment['days'], ADMIN_ID))
        c.execute("UPDATE payments SET status='approved' WHERE id=?", (pay_id,))
        conn.commit()
        conn.close()

        # Send Key to User
        msg_user = (
            "✅ <b>ការទូទាត់របស់អ្នកត្រូវបានអនុម័តជោគជ័យ!</b>\n\n"
            f"📦 <b>កញ្ចប់:</b> {payment['package_name']} ({payment['days']} ថ្ងៃ)\n"
            f"🔑 <b>License Key របស់អ្នក:</b> <code>{new_key}</code>\n\n"
            "👉 សូមចុច <b>👉 បញ្ចូល Key</b> រួច Paste Key នេះដើម្បីទទួលបាន Slot ដំណើរការ!"
        )
        try:
            bot.send_message(payment['user_id'], msg_user, reply_markup=get_main_menu())
        except:
            pass

        bot.edit_message_caption(
            caption=f"✅ <b>បានអនុម័តជោគជ័យ!</b>\nUser: <code>{payment['user_id']}</code>\nKey: <code>{new_key}</code>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else: # Reject
        c.execute("UPDATE payments SET status='rejected' WHERE id=?", (pay_id,))
        conn.commit()
        conn.close()
        try:
            bot.send_message(payment['user_id'], "❌ <b>វិក្កយបត្ររបស់អ្នកត្រូវបានបដិសេធដោយ Admin!</b>\nសូមទាក់ទងមកកាន់ @PoSovannaReach សម្រាប់ព័ត៌មានបន្ថែម។")
        except:
            pass
        bot.edit_message_caption(
            caption=f"❌ <b>បានបដិសេធវិក្កយបត្រ!</b>\nUser: <code>{payment['user_id']}</code>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

# ---------------------------------------------------------------------------
# 📥 MESSAGE DISPATCHER (TEXT, DOCUMENT, PHOTO)
# ---------------------------------------------------------------------------
@bot.message_handler(content_types=['text', 'photo', 'document', 'sticker'])
def handle_all_inputs(message):
    user_id = message.from_user.id
    state_info = user_state.get(user_id, {})
    curr_state = state_info.get('state')

    # 1. បញ្ចូល License Key
    if curr_state == 'WAITING_LICENSE_KEY' and message.text:
        key_input = message.text.strip().upper()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM keys WHERE key_code=?", (key_input,))
        k = c.fetchone()

        if k and k['status'] == 'active':
            days = k['days']
            username = message.from_user.username or message.from_user.first_name
            c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            
            # បញ្ជាក់ Key ថាបានប្រើប្រាស់, បន្ថែម Slot និងកំណត់ថ្ងៃផុតកំណត់
            c.execute(f"UPDATE keys SET status='used', used_by=?, used_at=CURRENT_TIMESTAMP, expire_at=DATETIME(CURRENT_TIMESTAMP, '+{days} days') WHERE key_code=?", (user_id, key_input))
            c.execute("UPDATE users SET quota = quota + 1 WHERE user_id=?", (user_id,))
            
            c.execute("SELECT quota FROM users WHERE user_id=?", (user_id,))
            new_quota = c.fetchone()['quota']
            
            conn.commit()
            conn.close()
            user_state[user_id] = {'state': None}
            
            # លោតសារបញ្ជាក់យ៉ាងច្បាស់លាស់
            success_msg = (
                "✅ <b>បញ្ចូល License Key ជោគជ័យ!</b> 🚀\n\n"
                f"🎉 <b>អបអរសាទរ!</b> អ្នកទទួលបាន <b>+1 Slot</b> ថ្មីសម្រាប់ប្រើប្រាស់។\n"
                f"⏳ <b>រយៈពេលសុពលភាព:</b> <b>{days} ថ្ងៃ</b>\n"
                f"📦 <b>កូតាសរុបរបស់អ្នកឥឡូវនេះគឺ:</b> {new_quota} Slot\n\n"
                "👉 សូមចូលទៅ <b>➕ បន្ថែម Hosting ថ្មី</b> ដើម្បីដាក់កូដរបស់អ្នក!"
            )
            bot.send_message(message.chat.id, success_msg, reply_markup=get_main_menu())
        else:
            conn.close()
            bot.send_message(message.chat.id, "❌ <b>License Key មិនត្រឹមត្រូវ ឬត្រូវបានប្រើប្រាស់រួចហើយ!</b>\nសូមពិនិត្យឡើងវិញ។")
        return

    # 2. ជ្រើសរើស Hosting ID
    if curr_state == 'WAITING_HOST_ID_SELECT' and message.text:
        try:
            h_id = int(message.text.strip())
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM hostings WHERE id=? AND (user_id=? OR ?=?)", (h_id, user_id, user_id, ADMIN_ID))
            row = c.fetchone()
            conn.close()
            if row:
                user_state[user_id] = {'state': None}
                bot.send_message(message.chat.id, f"📂 <b>ផ្ទាំងគ្រប់គ្រង Hosting ID: {h_id}</b>", reply_markup=get_hosting_actions_menu(h_id))
            else:
                bot.send_message(message.chat.id, "❌ រកមិនឃើញ Hosting នេះទេ!")
        except:
            bot.send_message(message.chat.id, "❌ សូមវាយជាលេខ ID!")
        return

    # 3. បញ្ជាក់ការលុប Hosting
    if curr_state == 'CONFIRM_DELETE_HOST' and message.text:
        host_id = state_info.get('host_id')
        if message.text.strip().lower() == 'yes':
            stop_bot_process(host_id)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT folder_path FROM hostings WHERE id=?", (host_id,))
            h = c.fetchone()
            if h and h['folder_path'] and os.path.exists(h['folder_path']):
                try:
                    shutil.rmtree(h['folder_path'])
                except:
                    pass
            c.execute("DELETE FROM hostings WHERE id=?", (host_id,))
            c.execute("UPDATE users SET used = MAX(0, used - 1) WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
            user_state[user_id] = {'state': None}
            bot.send_message(message.chat.id, "✅ <b>បានលុប Hosting ជោគជ័យ!</b>", reply_markup=get_main_menu())
        else:
            user_state[user_id] = {'state': None}
            bot.send_message(message.chat.id, "❌ ការលុបត្រូវបានបោះបង់!", reply_markup=get_hosting_actions_menu(host_id))
        return

    # 4. Upload វិក្កយបត្រទិញ Key
    if curr_state == 'WAITING_RECEIPT' and message.photo:
        photo_id = message.photo[-1].file_id
        pkg_name = state_info.get('pkg_name', 'Custom')
        days = state_info.get('days', 30)
        price = state_info.get('price', 0.0)

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO payments (user_id, package_name, days, price, photo_id) VALUES (?, ?, ?, ?, ?)", (user_id, pkg_name, days, price, photo_id))
        pay_id = c.lastrowid
        conn.commit()
        conn.close()

        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, "✅ <b>វិក្កយបត្ររបស់អ្នកត្រូវបានបញ្ជូនទៅ Admin ហើយ!</b>\nសូមរង់ចាំការពិនិត្យនិងផ្ញើ Key ជូនក្នុងពេលបន្តិចទៀតនេះ។", reply_markup=get_main_menu())

        # Notify Admin
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ បញ្ជាក់ (Approve)", callback_data=f"pay_appr_{pay_id}"),
            InlineKeyboardButton("❌ បោះបង់", callback_data=f"pay_rejc_{pay_id}")
        )
        caption = (
            f"🔔 <b>មានការទិញ Key ថ្មី!</b>\n"
            f"👤 User: <code>{user_id}</code> (@{message.from_user.username or 'N/A'})\n"
            f"📦 កញ្ចប់: <b>{pkg_name}</b> ({days} ថ្ងៃ)\n"
            f"💵 តម្លៃ: <b>${price}</b>"
        )
        bot.send_photo(ADMIN_ID, photo=photo_id, caption=caption, reply_markup=markup)
        return

    # 5. Upload File បង្កើត Hosting ថ្មី (.py ឬ .zip ធម្មតាវិញ)
    if curr_state == 'WAITING_HOST_FILE' and message.document:
        doc = message.document
        fname = doc.file_name
        # អនុញ្ញាតអោយ Upload ទាំង .py និង .zip ដដែល
        if not (fname.endswith('.py') or fname.endswith('.zip')):
            bot.send_message(message.chat.id, "❌ សូម Upload តែ File <b>.py</b> ឬ <b>.zip</b> ប៉ុណ្ណោះ!")
            return

        bot.send_message(message.chat.id, "⏳ <b>កំពុងទាញយក និងដំឡើង Hosting របស់អ្នក...</b>")
        
        host_unique_dir = os.path.join(DOWNLOADS_DIR, f"{user_id}_{int(time.time())}")
        os.makedirs(host_unique_dir, exist_ok=True)
        local_filepath = os.path.join(host_unique_dir, fname)

        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(local_filepath, 'wb') as f:
            f.write(downloaded)

        if fname.endswith('.zip'):
            try:
                with zipfile.ZipFile(local_filepath, 'r') as zip_ref:
                    zip_ref.extractall(host_unique_dir)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ បរាជ័យក្នុងការពន្លា ZIP: {e}")
                return

        main_file = find_main_file(host_unique_dir)
        if not main_file:
            bot.send_message(message.chat.id, "❌ រកមិនឃើញ File .py ណាមួយនៅក្នុងគម្រោងរបស់អ្នកទេ! សូមពិនិត្យ File ឡើងវិញ។")
            return

        extracted_token = extract_token_from_folder(host_unique_dir)
        bot_username = "TelegramBot"

        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO hostings (user_id, bot_name, bot_token, main_file, folder_path, status)
            VALUES (?, ?, ?, ?, ?, 'offline')
        ''', (user_id, fname, extracted_token, main_file, host_unique_dir))
        new_host_id = c.lastrowid
        c.execute("UPDATE users SET used = used + 1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

        # Auto Run Code 100% ភ្លាមៗ
        start_bot_process(new_host_id)

        success_msg = (
            "✅ <b>បង្កើត Hosting ជោគជ័យហើយ!</b>\n\n"
            f"🛡 ឈ្មោះ : <b>{fname}</b>\n"
            f"🤖 Bot : <b>@{bot_username}</b>\n"
            f"🔑 Token : <code>{extracted_token}</code>\n\n"
            "👉 ចូលទៅ <b>📂 មើល Hosting របស់ខ្ញុំ</b> ដើម្បីគ្រប់គ្រង។"
        )
        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, success_msg, reply_markup=get_main_menu())
        return

    # 6. File Manager: Upload File ចូល Folder
    if curr_state == 'FM_UPLOAD_FILE' and message.document:
        folder = state_info.get('folder')
        host_id = state_info.get('host_id')
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        dest_path = os.path.join(folder, message.document.file_name)
        with open(dest_path, 'wb') as f:
            f.write(downloaded)
        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, f"✅ បាន Upload ឯកសារ <code>{message.document.file_name}</code> ជោគជ័យ!", reply_markup=get_file_manager_menu(host_id))
        return

    # 7. File Manager: Download File
    if curr_state == 'FM_DOWNLOAD_FILE' and message.text:
        folder = state_info.get('folder')
        host_id = state_info.get('host_id')
        req_file = os.path.join(folder, message.text.strip())
        if os.path.exists(req_file) and os.path.isfile(req_file):
            with open(req_file, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📥 ឯកសារ: {message.text.strip()}")
        else:
            bot.send_message(message.chat.id, "❌ រកមិនឃើញ File នេះទេ!")
        user_state[user_id] = {'state': None}
        return

    # 8. File Manager: Delete File
    if curr_state == 'FM_DELETE_FILE' and message.text:
        folder = state_info.get('folder')
        host_id = state_info.get('host_id')
        del_file = os.path.join(folder, message.text.strip())
        if os.path.exists(del_file):
            try:
                os.remove(del_file)
                bot.send_message(message.chat.id, f"✅ បានលុបឯកសារ <code>{message.text.strip()}</code> ជោគជ័យ!", reply_markup=get_file_manager_menu(host_id))
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ មិនអាចលុបបានទេ: {e}")
        else:
            bot.send_message(message.chat.id, "❌ រកមិនឃើញ File នេះទេ!")
        user_state[user_id] = {'state': None}
        return

    # 9. File Manager: Pip Install
    if curr_state == 'FM_PIP_INSTALL' and message.text:
        host_id = state_info.get('host_id')
        lib = message.text.strip()
        bot.send_message(message.chat.id, f"⏳ <b>កំពុងដំឡើង {lib} តាមរយៈ pip...</b>")
        try:
            res = subprocess.run([sys.executable, "-m", "pip", "install", lib], capture_output=True, text=True, timeout=90)
            output = res.stdout[-800:] if res.stdout else res.stderr[-800:]
            bot.send_message(message.chat.id, f"✅ <b>លទ្ធផលដំឡើង:</b>\n<pre>{output}</pre>", reply_markup=get_file_manager_menu(host_id))
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ បរាជ័យក្នុងការដំឡើង: {e}", reply_markup=get_file_manager_menu(host_id))
        user_state[user_id] = {'state': None}
        return

    # 10. Admin: Broadcast
    if curr_state == 'ADMIN_BROADCAST' and user_id == ADMIN_ID and message.text:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        all_u = c.fetchall()
        conn.close()

        success_c = 0
        failed_c = 0
        for u in all_u:
            try:
                bot.send_message(u['user_id'], message.text)
                success_c += 1
            except:
                failed_c += 1
        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, f"📢 <b>លទ្ធផល Broadcast:</b>\n\n✅ ជោគជ័យ: {success_c}\n❌ បរាជ័យ: {failed_c}", reply_markup=get_admin_menu())
        return

    # 11. Admin: Add Quota
    if curr_state == 'ADMIN_ADD_QUOTA' and user_id == ADMIN_ID and message.text:
        try:
            target_uid, slots = message.text.strip().split()
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (int(target_uid), "Unknown"))
            c.execute("UPDATE users SET quota = quota + ? WHERE user_id=?", (int(slots), int(target_uid)))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ បានបន្ថែម {slots} Slot ជូន User <code>{target_uid}</code> ជោគជ័យ!", reply_markup=get_admin_menu())
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ បរាជ័យ: {e}")
        user_state[user_id] = {'state': None}
        return

    # 12. Admin: Set QR
    if curr_state == 'ADMIN_SET_QR' and user_id == ADMIN_ID and message.photo:
        photo_id = message.photo[-1].file_id
        conn = get_db()
        c = conn.cursor()
        c.execute("REPLACE INTO settings (key, value, file_id, extra_type) VALUES ('qr_payment', 'Custom QR', ?, 'photo')", (photo_id,))
        conn.commit()
        conn.close()
        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, "✅ <b>បានកំណត់រូបភាព QR Code ជោគជ័យ!</b>", reply_markup=get_admin_menu())
        return

    # 13. Admin: Generate Key
    if curr_state == 'ADMIN_GEN_KEY' and user_id == ADMIN_ID and message.text:
        try:
            days = int(message.text.strip())
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_key = f"BABY-HOSTING-{random_code}"

            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO keys (key_code, days, status, created_by) VALUES (?, ?, 'active', ?)", (new_key, days, ADMIN_ID))
            conn.commit()
            conn.close()

            user_state[user_id] = {'state': None}
            bot.send_message(message.chat.id, f"✅ <b>បង្កើត License Key ជោគជ័យ!</b>\n\n🔑 Key: <code>{new_key}</code>\n⏳ ចំនួន: <b>{days}</b> ថ្ងៃ", reply_markup=get_admin_menu())
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ សូមវាយជាលេខថ្ងៃ: {e}")
        return

    # 14. Admin: Add Package - Step 1 (Name)
    if curr_state == 'ADMIN_ADD_PKG_NAME' and user_id == ADMIN_ID and message.text:
        user_state[user_id] = {'state': 'ADMIN_ADD_PKG_DAYS', 'pkg_name': message.text.strip()}
        bot.send_message(message.chat.id, "✍️ <b>សូមវាយចំនួនថ្ងៃសម្រាប់កញ្ចប់នេះ (ឧទាហរណ៍: 1):</b>")
        return

    # 14. Admin: Add Package - Step 2 (Days)
    if curr_state == 'ADMIN_ADD_PKG_DAYS' and user_id == ADMIN_ID and message.text:
        try:
            days = int(message.text.strip())
            user_state[user_id] = {'state': 'ADMIN_ADD_PKG_PRICE', 'pkg_name': state_info['pkg_name'], 'pkg_days': days}
            bot.send_message(message.chat.id, "✍️ <b>សូមវាយតម្លៃលក់គិតជាដុល្លារ (ឧទាហរណ៍: 1.5):</b>")
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយជាលេខ (ឧទាហរណ៍: 1)!")
        return

    # 14. Admin: Add Package - Step 3 (Price)
    if curr_state == 'ADMIN_ADD_PKG_PRICE' and user_id == ADMIN_ID and message.text:
        try:
            p_name = state_info['pkg_name']
            p_days = state_info['pkg_days']
            p_price = float(message.text.strip())
            
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO shop_packages (name, days, price) VALUES (?, ?, ?)", (p_name, p_days, p_price))
            conn.commit()
            conn.close()
            
            user_state[user_id] = {'state': None}
            bot.send_message(message.chat.id, f"✅ បានបន្ថែមប៊ូតុង <b>{p_name}</b> ({p_days}ថ្ងៃ - ${p_price}) ជោគជ័យ!", reply_markup=get_admin_menu())
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយតម្លៃជាលេខ (ឧទាហរណ៍: 1.5)!")
        return

    # 15. Admin: Edit Price Value
    if curr_state == 'ADMIN_EDIT_PRICE_VALUE' and user_id == ADMIN_ID and message.text:
        try:
            pkg_id = state_info['pkg_id']
            pkg_name = state_info['pkg_name']
            new_price = float(message.text.strip())
            
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE shop_packages SET price=? WHERE id=?", (new_price, int(pkg_id)))
            conn.commit()
            conn.close()
            
            user_state[user_id] = {'state': None}
            bot.send_message(message.chat.id, f"✅ បានកែប្រែតម្លៃកញ្ចប់ <b>{pkg_name}</b> ទៅជា <b>${new_price}</b> ជោគជ័យ!", reply_markup=get_admin_menu())
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយតម្លៃជាលេខ (ឧទាហរណ៍: 5.5)!")
        return

    # 16. Admin: Set Welcome
    if curr_state == 'ADMIN_SET_WELCOME' and user_id == ADMIN_ID:
        conn = get_db()
        c = conn.cursor()
        if message.photo:
            fid = message.photo[-1].file_id
            cap = message.caption or "សូមស្វាគមន៍មកកាន់ប្រព័ន្ធ Bot Hosting!"
            c.execute("REPLACE INTO settings (key, value, file_id, extra_type) VALUES ('welcome_msg', ?, ?, 'photo')", (cap, fid))
        elif message.sticker:
            fid = message.sticker.file_id
            c.execute("REPLACE INTO settings (key, value, file_id, extra_type) VALUES ('welcome_msg', 'សូមស្វាគមន៍!', ?, 'sticker')", (fid,))
        elif message.text:
            c.execute("REPLACE INTO settings (key, value, file_id, extra_type) VALUES ('welcome_msg', ?, '', 'text')", (message.text,))
        conn.commit()
        conn.close()
        user_state[user_id] = {'state': None}
        bot.send_message(message.chat.id, "✅ បានកំណត់រូបភាព/សារ Welcome ជោគជ័យ!", reply_markup=get_admin_menu())
        return

# ---------------------------------------------------------------------------
# ⏰ BACKGROUND TASK (ពិនិត្យការផុតកំណត់ Key ស្វ័យប្រវត្តិ)
# ---------------------------------------------------------------------------
def check_key_expirations():
    """ស្កេនរកមើល User ណាដែលដល់ថ្ងៃផុតកំណត់ ដើម្បីលុប Slot ស្វ័យប្រវត្តិ"""
    while True:
        try:
            conn = get_db()
            c = conn.cursor()
            # ស្វែងរក Key ដែលផុតកំណត់
            c.execute("SELECT key_code, used_by FROM keys WHERE status='used' AND expire_at <= CURRENT_TIMESTAMP")
            expired_keys = c.fetchall()
            
            for k in expired_keys:
                uid = k['used_by']
                kcode = k['key_code']
                
                # ប្តូរ Status Key ទៅជា expired និងដក Quota
                c.execute("UPDATE keys SET status='expired' WHERE key_code=?", (kcode,))
                c.execute("UPDATE users SET quota = MAX(0, quota - 1) WHERE user_id=?", (uid,))
                
                # ផ្ញើសារប្រាប់ User ថាផុតកំណត់
                try:
                    msg = (
                        "⚠️ <b>សេចក្តីជូនដំណឹងពីប្រព័ន្ធ!</b>\n\n"
                        f"License Key របស់អ្នក <code>{kcode}</code> <b>បានផុតកំណត់ហើយ!</b>\n"
                        "Slot ចំនួន 1 ត្រូវបានប្រព័ន្ធដកហូតយកវិញ។\n"
                        "👉 សូមចូលទៅ <b>🛒 ទិញ Key Shop</b> ដើម្បីបន្តប្រើប្រាស់សេវាកម្មរបស់យើង!"
                    )
                    bot.send_message(uid, msg)
                except Exception:
                    pass
                    
            conn.commit()
            conn.close()
        except Exception as e:
            print("Expiration Checker Error:", e)
        time.sleep(60) # ពិនិត្យរៀងរាល់ 1 នាទីម្តង

# បញ្ឆេះមុខងារពិនិត្យការផុតកំណត់ Key អោយដើរនៅពីក្រោយ
threading.Thread(target=check_key_expirations, daemon=True).start()

# ---------------------------------------------------------------------------
# 🔄 POLLING AUTO-RECONNECT (ការពារមិនឱ្យគាំង)
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=====================================================")
    print("🚀 TELEGRAM BOT HOSTING SYSTEM IS RUNNING 100%...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🤖 Bot Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    print("=====================================================")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as err:
            print(f"⚠️ [Connection Notice]: {err}")
            time.sleep(3)