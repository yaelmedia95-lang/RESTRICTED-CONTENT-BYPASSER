import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait

# =========================================================
#                   AYARLAR (BURAYI DOLDUR)
# =========================================================
# Tırnakların içine kendi bilgilerini yaz
API_ID = 30647156                 # Sayı olarak yaz (Tırnak yok)
API_HASH = "11d0174f807a8974a955520b8c968b4d"   # Tırnak içinde
BOT_TOKEN = "8222579881:AAG_dMd0q_LpV9m04cMU8iEF10oywzn5WMU"  # Tırnak içinde
SESSION_STRING = "BAIr9ZEAlWiDmclnEB1z-veEwVkt6D04C0iXJ0G9ld5eZrPCzYKxYLuEDjHwWJWRvpcoF4pnlf7YfQloMbWXro7CzTUr7voqb1KI43J-59ODW_T93-pC5Y-L97wiYaqgJ__rqgO5o_jokVHAiJFuWKpt1XwgbOMjAAP-p6BO-3Z_-rq7jpya6LtnneiInJQ4g08klsSjpNbyqE1oylfzDN9S6-cHgmRE85JuI030go_bICw01GwbdA_s3WRpgKx8BpJd3QGdV1zgiPQN0xH-l9ufUVsGRT9CWN1Y-FfRy7huBKVH3WUdTpCj0yb3twPYVoCufehDAs5ZF6obCf4vbtFSMxPRZgAAAAHuM2dLAA" # Tırnak içinde

# =========================================================
#                 WEB SERVER (RENDER KAPANMASIN DİYE)
# =========================================================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return "Bot Aktif! Video/Foto Transferi Hazır."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================================================
#                 BOT BAŞLATMA
# =========================================================
bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
userbot = Client("my_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

DURDUR = False

# =========================================================
#                 YARDIMCI FONKSİYONLAR
# =========================================================
def linki_coz(link):
    """Linkten Chat ID ve Mesaj ID'sini ayıklar"""
    link = link.replace("https://t.me/", "").replace("http://t.me/", "")
    
    if "c/" in link: # Özel kanal (t.me/c/123123/12)
        parts = link.split("/")
        # t.me/c/123456/789 -> chat_id: -100123456, msg_id: 789
        if len(parts) >= 3:
            return int("-100" + parts[1]), int(parts[2])
        elif len(parts) == 2:
            return int("-100" + parts[1]), None
            
    else: # Genel kanal (t.me/kanaladi/12)
        parts = link.split("/")
        chat_id = parts[0]
        msg_id = int(parts[1]) if len(parts) > 1 else None
        return chat_id, msg_id
        
    return None, None

# =========================================================
#                 KOMUTLAR
# =========================================================

@bot.on_message(filters.command("start"))
async def start_msg(client, message):
    await message.reply(
        "👋 **Medya Transfer Botu**\n\n"
        "1️⃣ **Toplu Transfer:**\n"
        "`/transfer https://t.me/kaynak https://t.me/hedef`\n"
        "_(Kanal linki atarsan baştan başlar, mesaj linki atarsan oradan devam eder)_\n\n"
        "2️⃣ **Tekli İndirme:**\n"
        "`/tekli https://t.me/kanal/123`\n"
        "_(Sadece o videoyu/fotoyu indirip buraya atar)_"
    )

@bot.on_message(filters.command("iptal"))
async def iptal_et(client, message):
    global DURDUR
    DURDUR = True
    await message.reply("🛑 İşlem iptal edildi.")

# --- TEKLİ İNDİRME KOMUTU ---
@bot.on_message(filters.command("tekli"))
async def tekli_indir(client, message):
    try:
        link = message.text.split()[1]
    except:
        await message.reply("❌ Link girmedin!\nÖrnek: `/tekli https://t.me/kanal/1550`")
        return

    bilgi = await message.reply("🔄 **Medya aranıyor ve indiriliyor...**")
    
    try:
        chat_id, msg_id = linki_coz(link)
        if not msg_id:
            await bilgi.edit("❌ Tekli indirme için mesaj ID'si lazım (Linkin sonunda sayı olmalı).")
            return

        # Mesajı al
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not (msg.photo or msg.video):
            await bilgi.edit("❌ Bu mesajda Video veya Fotoğraf yok (Metin olabilir).")
            return

        # İndir
        yol = await userbot.download_media(msg)
        await bilgi.edit("📤 **İndi, sana yükleniyor...**")
        
        # Bota geri gönder (Komutu yazan kişiye)
        if msg.video:
            await bot.send_video(message.chat.id, video=yol, caption=msg.caption)
        elif msg.photo:
            await bot.send_photo(message.chat.id, photo=yol, caption=msg.caption)
            
        # Sil
        os.remove(yol)
        await bilgi.delete()
        
    except Exception as e:
        await bilgi.edit(f"❌ Hata: {e}")

# --- TOPLU TRANSFER KOMUTU ---
@bot.on_message(filters.command("transfer"))
async def transfer_baslat(client, message):
    global DURDUR
    DURDUR = False

    try:
        args = message.text.split()
        link_kaynak = args[1]
        link_hedef = args[2]
    except:
        await message.reply("❌ **Hatalı Kullanım!**\n`/transfer kaynak_link hedef_link`")
        return

    durum_msj = await message.reply("🔄 **Bağlantı kuruluyor...**")

    try:
        # Kaynak bilgilerini çöz
        src_id, src_start_msg = linki_coz(link_kaynak)
        dst_id, _ = linki_coz(link_hedef)

        # Chat objelerini al (Doğrulama için)
        try:
            chat_source = await userbot.get_chat(src_id)
            chat_target = await userbot.get_chat(dst_id)
        except Exception as e:
            await durum_msj.edit(f"❌ Kanala erişilemedi! Userbot üye mi?\nHata: {e}")
            return

        baslangic_bilgisi = "En Baştan" if not src_start_msg else f"Mesaj {src_start_msg}'den itibaren"
        
        await durum_msj.edit(
            f"🚀 **Transfer Başlıyor!**\n\n"
            f"📤 Kaynak: {chat_source.title}\n"
            f"📥 Hedef: {chat_target.title}\n"
            f"📍 Başlangıç: {baslangic_bilgisi}\n\n"
            f"⚠️ _Sadece Video ve Fotolar alınacak._"
        )

        sayac = 0
        
        # Döngüyü kuruyoruz
        # Eğer mesaj ID verildiyse oradan başlar, verilmediyse en baştan (reverse=True)
        # reverse=True: En eskiden en yeniye doğru gider.
        
        async for msg in userbot.get_chat_history(chat_source.id, reverse=True):
            if DURDUR:
                await bot.send_message(message.chat.id, "🛑 İşlem durduruldu.")
                break

            # Eğer kullanıcı "t.me/kanal/500" dediyse, ID'si 500'den küçük olanları atla
            if src_start_msg and msg.id < src_start_msg:
                continue

            # FİLTRE: Sadece Video ve Foto
            if msg.photo or msg.video:
                try:
                    # Dosyayı İndir (İletim Yasağını Delmek İçin)
                    dosya = await userbot.download_media(msg)
                    
                    if not dosya: continue # İndirme başarısızsa geç

                    # Hedefe Yükle
                    kty = msg.caption or ""
                    
                    if msg.video:
                        await userbot.send_video(chat_target.id, video=dosya, caption=kty)
                    else:
                        await userbot.send_photo(chat_target.id, photo=dosya, caption=kty)
                    
                    sayac += 1
                    
                    # Dosyayı SİL (Disk dolmasın)
                    if os.path.exists(dosya):
                        os.remove(dosya)

                    # Bilgi ver (Her 5 medyada bir)
                    if sayac % 5 == 0:
                        try:
                            await durum_msj.edit(f"🔄 **Transfer Sürüyor...**\n✅ Taşınan: {sayac}")
                        except: pass
                    
                    # Spam koruması
                    await asyncio.sleep(4)

                except FloodWait as fw:
                    logger.warning(f"FloodWait: {fw.value} saniye bekleniyor.")
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.error(f"Mesaj {msg.id} hatası: {e}")
                    if 'dosya' in locals() and os.path.exists(dosya):
                        os.remove(dosya)

        await bot.send_message(message.chat.id, f"✅ **BİTTİ!**\nToplam {sayac} medya aktarıldı.")

    except Exception as e:
        await bot.send_message(message.chat.id, f"❌ **Genel Hata:** {e}")

# =========================================================
#                 BAŞLATMA
# =========================================================
async def main():
    await bot.start()
    await userbot.start()
    logger.info("✅ SİSTEM TAMAMEN HAZIR!")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
