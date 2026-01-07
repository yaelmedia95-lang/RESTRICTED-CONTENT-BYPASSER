import os
import asyncio
import logging
import time
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait

# =========================================================
#                   AYARLAR (BURAYI DOLDUR)
# =========================================================
# Render ayarlarıyla uğraşma, direkt buraya yaz.
API_ID = 30647156                 # Sayı olarak yaz (Tırnak yok)
API_HASH = "11d0174f807a8974a955520b8c968b4d"   # Tırnak içinde
BOT_TOKEN = "8222579881:AAG_dMd0q_LpV9m04cMU8iEF10oywzn5WMU"  # Tırnak içinde
SESSION_STRING = "BAIr9ZEAlWiDmclnEB1z-veEwVkt6D04C0iXJ0G9ld5eZrPCzYKxYLuEDjHwWJWRvpcoF4pnlf7YfQloMbWXro7CzTUr7voqb1KI43J-59ODW_T93-pC5Y-L97wiYaqgJ__rqgO5o_jokVHAiJFuWKpt1XwgbOMjAAP-p6BO-3Z_-rq7jpya6LtnneiInJQ4g08klsSjpNbyqE1oylfzDN9S6-cHgmRE85JuI030go_bICw01GwbdA_s3WRpgKx8BpJd3QGdV1zgiPQN0xH-l9ufUVsGRT9CWN1Y-FfRy7huBKVH3WUdTpCj0yb3twPYVoCufehDAs5ZF6obCf4vbtFSMxPRZgAAAAHuM2dLAA" # Tırnak içinde

# =========================================================
#                 WEB SERVER (RENDER İÇİN)
# =========================================================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return "Bot ve Userbot Calisiyor!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================================================
#                 BOT KURULUMU
# =========================================================
bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
userbot = Client("my_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

# Küresel durdurma bayrağı
DURDUR = False

# =========================================================
#                 KOMUTLAR
# =========================================================

@bot.on_message(filters.command("start"))
async def start_msg(client, message):
    await message.reply(
        "👋 **Medya Transfer Botu (Kısıtlama Yok)**\n\n"
        "Komut: `/transfer KAYNAK HEDEF`\n"
        "Örnek: `/transfer https://t.me/gizlikanal https://t.me/benimkanal`\n\n"
        "⚠️ **Not:** Bot herkese açıktır. Kaynak kanaldaki kısıtlı içerikleri indirip yükler."
    )

@bot.on_message(filters.command("iptal"))
async def iptal_et(client, message):
    global DURDUR
    DURDUR = True
    await message.reply("🛑 İşlem iptal ediliyor...")

@bot.on_message(filters.command("transfer"))
async def transfer_baslat(client, message):
    global DURDUR
    DURDUR = False

    # Argüman kontrolü
    try:
        args = message.text.split()
        kaynak = args[1]
        hedef = args[2]
    except:
        await message.reply("❌ **Hatalı Kullanım!**\n`/transfer kaynak_link hedef_link`")
        return

    bilgi_mesaji = await message.reply("🔄 **Kanallara bağlanılıyor...**")

    try:
        # Linkleri Userbot ile çöz (Çünkü gizli kanalları sadece Userbot görür)
        try:
            chat_source = await userbot.get_chat(kaynak)
            chat_target = await userbot.get_chat(hedef)
        except Exception as e:
            await bilgi_mesaji.edit(f"❌ Kanal bulunamadı veya üye değilsin!\nHata: {e}")
            return

        await bilgi_mesaji.edit(f"🚀 **İşlem Başlıyor!**\n\n📤 Kaynak: {chat_source.title}\n📥 Hedef: {chat_target.title}\n\n_Medyalar indiriliyor ve yükleniyor..._")

        sayac = 0
        
        # Geçmişi tarama (En eskiden en yeniye değil, en yeniden eskiye tarar varsayılan olarak)
        # Amaç aktarım olduğu için genelde eskiye gitmek istersen parametre değişmeli.
        # Basitlik olsun diye son mesajları tarıyoruz.
        async for msg in userbot.get_chat_history(chat_source.id):
            if DURDUR:
                await bot.send_message(message.chat.id, "🛑 **İşlem kullanıcı tarafından durduruldu.**")
                break

            # Sadece Video ve Fotoğraf (Metinleri atlar)
            if msg.photo or msg.video:
                try:
                    # 1. Dosyayı Render Sunucusuna İndir (Çünkü İletim Yasak)
                    # Dosya yolunu al
                    dosya_yolu = await userbot.download_media(msg)
                    
                    if not dosya_yolu:
                        continue

                    # 2. Hedefe Yükle (Userbot senin ağzından yükler)
                    caption = msg.caption if msg.caption else ""
                    
                    if msg.video:
                        await userbot.send_video(chat_target.id, video=dosya_yolu, caption=caption)
                    elif msg.photo:
                        await userbot.send_photo(chat_target.id, photo=dosya_yolu, caption=caption)
                    
                    sayac += 1
                    
                    # 3. Dosyayı Sil (Render diskini doldurmamak için ŞART)
                    if os.path.exists(dosya_yolu):
                        os.remove(dosya_yolu)

                    # Log ver (Her 5 medyada bir mesajı güncelle)
                    if sayac % 5 == 0:
                        try:
                            await bilgi_mesaji.edit(f"🔄 **Devam Ediyor...**\nTaşınan Medya: {sayac}")
                        except:
                            pass

                    # Spam Koruması (Bekleme)
                    await asyncio.sleep(4)

                except FloodWait as e:
                    await asyncio.sleep(e.value + 5)
                except Exception as e:
                    logger.error(f"Hata: {e}")
                    # Hata olsa bile dosyayı silmeye çalış
                    if 'dosya_yolu' in locals() and os.path.exists(dosya_yolu):
                        os.remove(dosya_yolu)

        await bot.send_message(message.chat.id, f"✅ **İşlem Tamamlandı!**\nToplam {sayac} medya taşındı.")

    except Exception as e:
        await bot.send_message(message.chat.id, f"❌ **Genel Hata:** {e}")


# =========================================================
#                 BAŞLATMA
# =========================================================
async def main():
    # Önce botları başlat
    await bot.start()
    await userbot.start()
    logger.info("✅ SİSTEM HAZIR!")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == '__main__':
    # Web serverı ayrı threadde aç
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # Botu başlat
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
