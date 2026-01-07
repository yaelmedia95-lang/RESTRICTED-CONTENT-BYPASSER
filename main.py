import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid

# =========================================================
#                   AYARLAR (BURAYI DOLDUR)
# =========================================================
API_ID = 30647156                 # Sayı olarak yaz (Tırnak yok)
API_HASH = "11d0174f807a8974a955520b8c968b4d"   # Tırnak içinde
BOT_TOKEN = "8222579881:AAG_dMd0q_LpV9m04cMU8iEF10oywzn5WMU"  # Tırnak içinde
SESSION_STRING = "BAIr9ZEAlWiDmclnEB1z-veEwVkt6D04C0iXJ0G9ld5eZrPCzYKxYLuEDjHwWJWRvpcoF4pnlf7YfQloMbWXro7CzTUr7voqb1KI43J-59ODW_T93-pC5Y-L97wiYaqgJ__rqgO5o_jokVHAiJFuWKpt1XwgbOMjAAP-p6BO-3Z_-rq7jpya6LtnneiInJQ4g08klsSjpNbyqE1oylfzDN9S6-cHgmRE85JuI030go_bICw01GwbdA_s3WRpgKx8BpJd3QGdV1zgiPQN0xH-l9ufUVsGRT9CWN1Y-FfRy7huBKVH3WUdTpCj0yb3twPYVoCufehDAs5ZF6obCf4vbtFSMxPRZgAAAAHuM2dLAA" # Tırnak içinde

# =========================================================
#                 WEB SERVER
# =========================================================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return "Bot Aktif! PeerIdInvalid Fixlendi."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================================================
#                 BOT KURULUMU
# =========================================================
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
userbot = Client("userbot_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

DURDUR = False

# =========================================================
#             AKILLI LINK ÇÖZÜCÜ (FIX)
# =========================================================
def linki_coz(link):
    """
    Her türlü Telegram linkini doğru ID veya Username formatına çevirir.
    """
    link = link.strip()
    link = link.replace("https://", "").replace("http://", "").replace("t.me/", "")
    
    chat_identifier = None
    msg_id = None
    
    parts = link.split("/")
    
    # 1. Private Kanal Linki (c/123456789/100)
    if "c/" in link:
        # t.me/c/1234567890/100
        # Pyrogram için ID: -1001234567890 olmalı
        raw_id = parts[1]
        chat_identifier = int("-100" + raw_id)
        if len(parts) > 2:
            msg_id = int(parts[2])

    # 2. Public Kanal Linki (username/100)
    else:
        # t.me/kanaladi/100
        chat_identifier = parts[0] # Username string olarak kalmalı
        if len(parts) > 1:
            try:
                msg_id = int(parts[1])
            except:
                pass

    return chat_identifier, msg_id

# =========================================================
#                 KOMUTLAR
# =========================================================

@bot.on_message(filters.command("start"))
async def start_msg(client, message):
    await message.reply(
        "👋 **Medya Transfer Botu (v2.0 Fix)**\n\n"
        "✅ `PeerIdInvalid` Koruması Aktif\n"
        "✅ İletim Kısıtlı İçerik İndirici Aktif\n\n"
        "**Komutlar:**\n"
        "1️⃣ `/tekli https://t.me/c/123456/100` (Tek mesaj)\n"
        "2️⃣ `/transfer https://t.me/c/kaynak https://t.me/hedef`"
    )

@bot.on_message(filters.command("iptal"))
async def iptal_et(client, message):
    global DURDUR
    DURDUR = True
    await message.reply("🛑 İşlem iptal edildi.")

# --- TEKLİ İNDİRME ---
@bot.on_message(filters.command("tekli"))
async def tekli_indir(client, message):
    try:
        link = message.text.split()[1]
    except:
        await message.reply("❌ Link girmedin!")
        return

    bilgi = await message.reply("🔄 **Analiz ediliyor...**")
    
    try:
        chat_id, msg_id = linki_coz(link)
        
        if not msg_id:
            await bilgi.edit("❌ Linkte mesaj numarası yok! (Örn: /1203)")
            return

        # Önce Chat'i hafızaya al (PeerIdInvalid Önleyici)
        try:
            chat_info = await userbot.get_chat(chat_id)
        except Exception as e:
            await bilgi.edit(f"❌ Userbot kanalı göremiyor!\nHata: {e}\n\n*Çözüm:* Userbot hesabınla o kanala gir ve bir mesaj yaz veya okundu yap.")
            return

        # Şimdi mesajı çek
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not msg or msg.empty:
            await bilgi.edit("❌ Mesaj bulunamadı veya silinmiş.")
            return

        if not (msg.photo or msg.video):
            await bilgi.edit("❌ Bu mesajda medya yok.")
            return

        await bilgi.edit("📥 **İndiriliyor (Kısıtlı içerik modu)...**")
        
        # İndir
        dosya = await userbot.download_media(msg)
        
        await bilgi.edit("📤 **Sana gönderiliyor...**")
        
        # Gönder (Userbot değil BOT gönderiyor ki temiz olsun)
        # Eğer dosya çok büyükse Userbot ile göndermek daha güvenli olabilir
        try:
            if msg.video:
                await bot.send_video(message.chat.id, video=dosya, caption=msg.caption)
            elif msg.photo:
                await bot.send_photo(message.chat.id, photo=dosya, caption=msg.caption)
        except:
            # Bot atamazsa Userbot atsın (Yedek)
            if msg.video:
                await userbot.send_video(message.chat.id, video=dosya, caption=msg.caption)
            elif msg.photo:
                await userbot.send_photo(message.chat.id, photo=dosya, caption=msg.caption)

        # Sil
        os.remove(dosya)
        await bilgi.delete()

    except Exception as e:
        await bilgi.edit(f"❌ Hata: {e}")
        if 'dosya' in locals() and os.path.exists(dosya):
            os.remove(dosya)

# --- TOPLU TRANSFER ---
@bot.on_message(filters.command("transfer"))
async def transfer_baslat(client, message):
    global DURDUR
    DURDUR = False

    try:
        args = message.text.split()
        link_kaynak = args[1]
        link_hedef = args[2]
    except:
        await message.reply("❌ **Kullanım:** `/transfer kaynak hedef`")
        return

    durum = await message.reply("🔄 **Bağlantılar kontrol ediliyor...**")

    try:
        src_id, src_msg = linki_coz(link_kaynak)
        dst_id, _ = linki_coz(link_hedef)

        # PeerIdInvalid Fix: Önce Chat objelerini çek
        try:
            src_chat = await userbot.get_chat(src_id)
            dst_chat = await userbot.get_chat(dst_id)
        except PeerIdInvalid:
            await durum.edit("❌ **PeerIdInvalid Hatası!**\nUserbot bu kanalı hafızasında bulamadı. Lütfen Userbot hesabınla o kanala girip bir mesajı görüntüle.")
            return
        except Exception as e:
            await durum.edit(f"❌ Kanal hatası: {e}")
            return

        await durum.edit(f"🚀 **Başlıyor...**\nKaynak: {src_chat.title}\nHedef: {dst_chat.title}")

        sayac = 0
        
        # Mesajları tarama
        async for msg in userbot.get_chat_history(src_id, reverse=True):
            if DURDUR:
                await bot.send_message(message.chat.id, "🛑 Durduruldu.")
                break
            
            # Başlangıç mesajından öncesini atla
            if src_msg and msg.id < src_msg:
                continue

            if msg.photo or msg.video:
                try:
                    # İndir
                    dosya = await userbot.download_media(msg)
                    if not dosya: continue

                    # Yükle
                    txt = msg.caption or ""
                    if msg.video:
                        await userbot.send_video(dst_id, video=dosya, caption=txt)
                    else:
                        await userbot.send_photo(dst_id, photo=dosya, caption=txt)

                    sayac += 1
                    os.remove(dosya)

                    if sayac % 5 == 0:
                        try: await durum.edit(f"🔄 **Taşınıyor:** {sayac} adet")
                        except: pass
                    
                    await asyncio.sleep(4)

                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.error(f"Transfer hata: {e}")
                    if 'dosya' in locals() and os.path.exists(dosya):
                        os.remove(dosya)

        await bot.send_message(message.chat.id, f"✅ **BİTTİ!**\nToplam {sayac} adet.")

    except Exception as e:
        await durum.edit(f"❌ Genel Hata: {e}")

# =========================================================
#                 BAŞLATMA (ÖNEMLİ KISIM)
# =========================================================
async def main():
    logger.info("Botlar başlatılıyor...")
    await bot.start()
    await userbot.start()
    
    # --- İŞTE ÇÖZÜM BURASI ---
    logger.info("♻️ Önbellek yenileniyor (PeerIdInvalid Fix)...")
    try:
        # Dialogları çekerek Userbot'un hafızasını tazeliyoruz.
        # Bu işlem sayesinde bot "ben bu kanalı tanıyorum" der.
        await userbot.get_dialogs(limit=50) 
        logger.info("✅ Önbellek yenilendi!")
    except Exception as e:
        logger.warning(f"⚠️ Önbellek yenilenirken hata (önemsiz olabilir): {e}")

    logger.info("Sistem Hazır!")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
