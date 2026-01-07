import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, idle

# --- 1. LOGLAMA AYARLARI ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 2. WEB SERVER (Render'ı Kandırmak İçin Şart) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Calisiyor! Hata varsa loglara bak."

def run_flask():
    # Render PORT verirse onu kullan, vermezse 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 3. GÜVENLİ DEĞİŞKEN ALIMI ---
def get_env(name, required=False):
    val = os.environ.get(name, "").strip()
    if required and not val:
        logger.error(f"❌ KRİTİK HATA: {name} Render ayarlarında yok!")
    return val

API_ID = get_env("API_ID", True)
API_HASH = get_env("API_HASH", True)
BOT_TOKEN = get_env("BOT_TOKEN", True)
SESSION_STRING = get_env("SESSION_STRING", False)

# API_ID Sayı mı kontrolü (Çökmemesi için)
try:
    API_ID = int(API_ID)
except:
    logger.error("❌ API_ID sayı değil! Ayarları kontrol et.")
    API_ID = 0

# --- 4. BOT TANIMLAMA ---
bot = None
userbot = None

if API_ID and API_HASH and BOT_TOKEN:
    try:
        bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
    except Exception as e:
        logger.error(f"❌ Bot kurulum hatası: {e}")

if SESSION_STRING:
    try:
        userbot = Client("my_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)
    except Exception as e:
        logger.error(f"❌ Userbot kurulum hatası: {e}")

# --- 5. ANA ÇALIŞMA MANTIĞI ---
async def start_services():
    logger.info("🚀 Servisler başlatılıyor...")

    # Bot Başlat
    if bot:
        try:
            await bot.start()
            me = await bot.get_me()
            logger.info(f"✅ BOT BAŞARIYLA AÇILDI: @{me.username}")
        except Exception as e:
            logger.error(f"❌ Bot bağlanamadı: {e}")
    else:
        logger.warning("⚠️ Bot ayarları eksik olduğu için başlatılamadı.")

    # Userbot Başlat
    if userbot:
        try:
            await userbot.start()
            me = await userbot.get_me()
            logger.info(f"✅ USERBOT BAŞARIYLA AÇILDI: {me.first_name}")
        except Exception as e:
            logger.error(f"❌ Userbot bağlanamadı (Session String bozuk olabilir): {e}")
            logger.info("ℹ️ Bot çalışmaya devam edecek, sadece Userbot devre dışı.")
    else:
        logger.warning("⚠️ Session String yok, Userbot çalışmayacak.")

    logger.info("🛡️ Sistem Idle moduna geçiyor (Kapanmaması için)...")
    await idle()

# --- 6. UYGULAMAYI BAŞLAT ---
if __name__ == '__main__':
    # Flask'ı ayrı kanalda başlat (Bu sayede kod çökse bile site açılır)
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Botu başlat
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Genel Hata: {e}")
        # Hata olsa bile kapanmasın diye sonsuz döngü (Log okuyabilmek için)
        import time
        while True:
            time.sleep(60)
