import os
import asyncio
import logging
import time
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, PeerIdInvalid

# ==================== 1. WEB SERVER ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "📸 Media Transfer Bot Aktif! 🎥"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==================== 2. AYARLAR ====================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Logging
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot ve Userbot
bot = Client("media_transfer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# Tek userbot
userbot = None
if SESSION_STRING:
    userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

# Global kontrol
ABORT_FLAG = False

# ==================== 3. SAĞLAM İNDİRİCİ ====================
async def download_with_verification(ub, msg, retries=3):
    """
    Dosyayı indirir ve boyutunu kontrol eder.
    Eksikse silip tekrar dener.
    """
    expected_size = 0
    
    if msg.video:
        expected_size = msg.video.file_size
    elif msg.photo:
        # Photo için en büyük boyutu al
        expected_size = msg.photo.file_size if hasattr(msg.photo, 'file_size') else 0
    
    if expected_size == 0:
        logger.warning(f"Boyut bilgisi yok, doğrulama yapılamıyor (msg {msg.id})")
        return None
    
    file_path = None
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"İndirme denemesi {attempt}/{retries} (msg {msg.id})")
            
            file_path = await ub.download_media(msg)
            
            if file_path and os.path.exists(file_path):
                actual_size = os.path.getsize(file_path)
                
                # %95 tolerans
                if actual_size >= expected_size * 0.95:
                    logger.info(f"✅ İndirme başarılı: {actual_size}/{expected_size} byte")
                    return file_path
                else:
                    logger.warning(f"⚠️ Eksik indi ({actual_size}/{expected_size}), tekrar deneniyor...")
                    os.remove(file_path)
            
        except Exception as e:
            logger.error(f"İndirme hatası ({attempt}): {e}")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        
        await asyncio.sleep(2)
    
    logger.error(f"❌ {retries} deneme sonrası başarısız")
    return None

# ==================== 4. LİNK PARSER ====================
def parse_telegram_link(link):
    """
    Telegram linkini parse eder
    
    Desteklenen formatlar:
    - https://t.me/12672 → Tüm grup
    - https://t.me/12672/122 → 122'den başla
    - https://t.me/c/1234567890/123 → Private chat, 123'ten başla
    - -1001234567890 → Direkt ID
    - -1001234567890/123 → ID + başlangıç mesajı
    
    Returns:
        dict: {"chat_id": int, "start_msg_id": int or None}
    """
    result = {"chat_id": None, "start_msg_id": None}
    
    link = str(link).strip()
    
    try:
        # Format 1: https://t.me/c/1234567890/123
        if "/c/" in link:
            parts = link.split("/c/")[1].split("/")
            result["chat_id"] = int(f"-100{parts[0]}")
            if len(parts) >= 2 and parts[1].isdigit():
                result["start_msg_id"] = int(parts[1])
        
        # Format 2: https://t.me/12672/122
        elif "t.me/" in link and "/" in link.split("t.me/")[1]:
            parts = link.split("t.me/")[1].split("/")
            
            # Eğer sadece sayı ise, ID olarak al
            if parts[0].replace("-", "").isdigit():
                result["chat_id"] = int(parts[0]) if not parts[0].startswith("-") else int(parts[0])
                if len(parts) >= 2 and parts[1].isdigit():
                    result["start_msg_id"] = int(parts[1])
            else:
                # Username ise (örn: @kanal)
                result["chat_id"] = parts[0]
                if len(parts) >= 2 and parts[1].isdigit():
                    result["start_msg_id"] = int(parts[1])
        
        # Format 3: Sadece ID (örn: -1001234567890 veya -1001234567890/123)
        elif "/" in link and link.split("/")[0].replace("-", "").isdigit():
            parts = link.split("/")
            result["chat_id"] = int(parts[0])
            if len(parts) >= 2 and parts[1].isdigit():
                result["start_msg_id"] = int(parts[1])
        
        # Format 4: Sadece ID (örn: -1001234567890)
        elif link.replace("-", "").isdigit():
            result["chat_id"] = int(link)
        
        # Format 5: Username (örn: @kanal)
        else:
            result["chat_id"] = link
    
    except Exception as e:
        logger.error(f"Link parse hatası: {e}")
        return None
    
    return result if result["chat_id"] else None

# ==================== 5. KOMUTLAR ====================
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(
        "📸 **Media Transfer Bot**\n\n"
        "**Özellikler:**\n"
        "• Sadece video ve fotoğraf transfer eder\n"
        "• Boyut doğrulama (eksik indirme önlenir)\n"
        "• Metadata korunur (video süresi vb.)\n\n"
        "**Komutlar:**\n"
        "/transfer KAYNAK HEDEF - Transfer başlat\n"
        "/iptal - İşlemi durdur\n\n"
        "**Link Formatları:**\n"
        "• `https://t.me/12672` → Tüm grup\n"
        "• `https://t.me/12672/122` → 122'den başla\n"
        "• `-1001234567890` → Direkt ID\n"
        "• `-1001234567890/123` → 123'ten başla\n\n"
        "**Örnek:**\n"
        "`/transfer https://t.me/12672 https://t.me/hedefkanal`\n"
        "`/transfer https://t.me/12672/122 -1001234567890`"
    )

@bot.on_message(filters.command("iptal") & filters.private)
async def cancel_process(client, message):
    global ABORT_FLAG
    ABORT_FLAG = True
    await message.reply("🛑 **Transfer iptal ediliyor...**")
    logger.info(f"İptal komutu: {message.from_user.id}")

@bot.on_message(filters.command("transfer") & filters.private)
async def transfer_media(client, message):
    global ABORT_FLAG
    ABORT_FLAG = False
    
    # Userbot kontrolü
    if not userbot:
        await message.reply("❌ **Userbot bağlı değil!**\n\nSESSION_STRING environment variable'ı ekleyin.")
        return
    
    # Güvenli bekleme süresi
    SAFETY_DELAY = 3
    
    # Parametreleri parse et
    try:
        src_link = message.command[1]
        dst_link = message.command[2]
    except:
        await message.reply(
            "❌ **Hatalı kullanım!**\n\n"
            "Doğru format:\n"
            "`/transfer KAYNAK HEDEF`\n\n"
            "Örnekler:\n"
            "`/transfer https://t.me/12672 https://t.me/hedefkanal`\n"
            "`/transfer https://t.me/12672/122 -1001234567890`"
        )
        return
    
    status = await message.reply("🔄 **Linkler analiz ediliyor...**")
    
    # Userbot hafızasını tazele
    try:
        async for d in userbot.get_dialogs(limit=50):
            pass
    except:
        pass
    
    # Linkleri parse et
    src = parse_telegram_link(src_link)
    dst = parse_telegram_link(dst_link)
    
    if not src or not dst:
        await status.edit(
            "❌ **Link parse edilemedi!**\n\n"
            "Desteklenen formatlar:\n"
            "• `https://t.me/12672`\n"
            "• `https://t.me/12672/122`\n"
            "• `-1001234567890`\n"
            "• `-1001234567890/123`"
        )
        return
    
    logger.info(f"Kaynak: {src}")
    logger.info(f"Hedef: {dst}")
    
    # Mesajları topla
    start_text = 'Tüm grup' if not src['start_msg_id'] else f'Mesaj {src["start_msg_id"]}'
    
    await status.edit(
        f"📸 **Medya taranıyor...**\n\n"
        f"Kaynak: `{src['chat_id']}`\n"
        f"Başlangıç: {start_text}\n\n"
        f"Sadece **video ve fotoğraf** transfer edilecek."
    )
    
    media_messages = []
    
    try:
        count = 0
        
        async for msg in userbot.get_chat_history(src["chat_id"]):
            if ABORT_FLAG:
                break
            
            # Başlangıç mesajından öncesini atla
            if src["start_msg_id"] and msg.id > src["start_msg_id"]:
                continue
            
            # Sadece video ve foto
            if msg.video or msg.photo:
                media_messages.append(msg.id)
                count += 1
                
                # Her 50 mesajda bir rapor ver
                if count % 50 == 0:
                    try:
                        await status.edit(
                            f"📸 **Medya taranıyor...**\n\n"
                            f"Bulunan: {count} medya\n"
                            f"(Video ve fotoğraf)"
                        )
                    except:
                        pass
    
    except Exception as e:
        await status.edit(f"❌ **Tarama hatası:**\n`{str(e)}`")
        logger.error(f"Tarama hatası: {e}")
        return
    
    # Ters çevir (eskiden yeniye)
    media_messages.reverse()
    total = len(media_messages)
    
    if total == 0:
        await status.edit("❌ **Hiç medya bulunamadı!**\n\nGrupda video veya fotoğraf yok.")
        return
    
    await status.edit(
        f"🚀 **Transfer başlıyor!**\n\n"
        f"📊 Toplam: {total} medya\n"
        f"📸 Fotoğraf + 🎥 Video\n"
        f"✅ Boyut doğrulamalı indirme\n"
        f"⏱️ Tahmini süre: {(total * SAFETY_DELAY) // 60} dakika"
    )
    
    # Transfer döngüsü
    success = 0
    failed = 0
    
    for idx, msg_id in enumerate(media_messages, 1):
        if ABORT_FLAG:
            await status.edit("🛑 **Transfer iptal edildi!**")
            logger.info("Transfer kullanıcı tarafından iptal edildi")
            return
        
        try:
            # Mesajı al
            msg = await userbot.get_messages(src["chat_id"], msg_id)
            
            if not msg or msg.empty:
                failed += 1
                continue
            
            # Hedef için parametreler
            send_args = {}
            if dst.get("start_msg_id"):
                send_args["reply_to_message_id"] = dst["start_msg_id"]
            
            # İndir
            file_path = await download_with_verification(userbot, msg, retries=3)
            
            if file_path:
                caption = msg.caption or ""
                
                try:
                    # Video
                    if msg.video:
                        await userbot.send_video(
                            dst["chat_id"],
                            file_path,
                            caption=caption,
                            duration=msg.video.duration,
                            width=msg.video.width,
                            height=msg.video.height,
                            **send_args
                        )
                        logger.info(f"✅ Video gönderildi (msg {msg_id})")
                    
                    # Foto
                    elif msg.photo:
                        await userbot.send_photo(
                            dst["chat_id"],
                            file_path,
                            caption=caption,
                            **send_args
                        )
                        logger.info(f"✅ Foto gönderildi (msg {msg_id})")
                    
                    success += 1
                
                except Exception as upload_err:
                    logger.error(f"Yükleme hatası (msg {msg_id}): {upload_err}")
                    failed += 1
                
                finally:
                    # Dosyayı sil
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            else:
                logger.warning(f"İndirme başarısız (msg {msg_id})")
                failed += 1
            
            # Güvenli bekleme
            await asyncio.sleep(SAFETY_DELAY)
            
            # Her 10 medyada bir rapor
            if idx % 10 == 0:
                try:
                    percent = int((idx / total) * 100)
                    await status.edit(
                        f"🔄 **Transfer devam ediyor...**\n\n"
                        f"📊 İlerleme: {idx}/{total} (%{percent})\n"
                        f"✅ Başarılı: {success}\n"
                        f"❌ Başarısız: {failed}\n\n"
                        f"⏱️ Kalan: ~{((total - idx) * SAFETY_DELAY) // 60} dk"
                    )
                except:
                    pass
        
        except FloodWait as fw:
            logger.warning(f"FloodWait: {fw.value}s")
            await asyncio.sleep(fw.value + 5)
        
        except Exception as e:
            logger.error(f"Transfer hatası (msg {msg_id}): {e}")
            failed += 1
    
    # Bitiş raporu
    await status.edit(
        f"🏁 **Transfer tamamlandı!**\n\n"
        f"✅ Başarılı: {success}\n"
        f"❌ Başarısız: {failed}\n"
        f"📊 Toplam: {total}\n\n"
        f"📸 Sadece video ve fotoğraf transfer edildi."
    )
    
    logger.info(f"Transfer tamamlandı: {success}/{total} başarılı")

# ==================== 6. BAŞLATMA ====================
async def main():
    logger.info("🚀 Media Transfer Bot başlatılıyor...")
    
    # Web server
    keep_alive()
    logger.info("✅ Web server başlatıldı")
    
    # Bot başlat
    await bot.start()
    logger.info("✅ Bot başlatıldı")
    
    # Userbot başlat
    if userbot:
        try:
            await userbot.start()
            logger.info("✅ Userbot başlatıldı")
        except Exception as e:
            logger.error(f"❌ Userbot başlatılamadı: {e}")
    else:
        logger.warning("⚠️ SESSION_STRING yok! Userbot başlatılamadı.")
    
    logger.info("✅ Sistem hazır, komutlar bekleniyor...")
    
    # Çalışmaya devam et
    await idle()
    
    # Kapat
    await bot.stop()
    if userbot:
        try:
            await userbot.stop()
        except:
            pass

if __name__ == '__main__':
    asyncio.run(main())
