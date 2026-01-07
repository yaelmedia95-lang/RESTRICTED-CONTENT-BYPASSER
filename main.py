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
    return "Bot Aktif! Kanal Tarama Modu Açık."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================================================
#                 BOTLAR
# =========================================================
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
userbot = Client("userbot_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

DURDUR = False

# =========================================================
#             HATA ÇÖZÜCÜ FONKSİYONLAR
# =========================================================

def linki_coz(link):
    """Linkten ID ve Mesaj Numarasını ayıklar"""
    link = link.strip().replace("https://", "").replace("http://", "").replace("t.me/", "")
    
    chat_identifier = None
    msg_id = None
    
    parts = link.split("/")
    
    # Özel Kanal (c/12345/10)
    if "c/" in link:
        # ID her zaman -100 ile başlar
        raw_id = parts[1]
        chat_identifier = int("-100" + raw_id)
        if len(parts) > 2:
            try: msg_id = int(parts[2])
            except: pass
            
    # Genel Kanal (kanaladi/10)
    else:
        chat_identifier = parts[0]
        if len(parts) > 1:
            try: msg_id = int(parts[1])
            except: pass

    return chat_identifier, msg_id

async def get_chat_guvenli(chat_id):
    """
    Bu fonksiyon PeerIdInvalid hatasını çözmek için dialogları tarar.
    """
    try:
        # Önce direkt dene
        chat = await userbot.get_chat(chat_id)
        return chat
    except (PeerIdInvalid, ChannelInvalid):
        logger.warning(f"⚠️ Kanal ({chat_id}) direkt bulunamadı, liste taranıyor...")
        
        # Bulamazsa senin tüm sohbetlerini tarayıp ID eşleştirmeye çalışır
        async for dialog in userbot.get_dialogs():
            if dialog.chat.id == chat_id:
                return dialog.chat
            
            # Eğer kullanıcı adı varsa ve eşleşiyorsa
            if isinstance(chat_id, str) and dialog.chat.username and dialog.chat.username.lower() == chat_id.lower():
                return dialog.chat
                
        # Hala bulunamadıysa patlar
        raise ValueError("Kanal bulunamadı! Userbot bu kanala üye mi?")

# =========================================================
#                 KOMUTLAR
# =========================================================

@bot.on_message(filters.command("start"))
async def start_msg(client, message):
    await message.reply(
        "🛠 **Gelişmiş Medya Transfer Botu**\n\n"
        "Userbot tüm kanallarını taradı ve hafızaya aldı.\n"
        "Artık `PeerIdInvalid` hatası almamalısın.\n\n"
        "▶️ `/transfer KAYNAK HEDEF`\n"
        "▶️ `/tekli LINK`"
    )

@bot.on_message(filters.command("iptal"))
async def iptal_et(client, message):
    global DURDUR
    DURDUR = True
    await message.reply("🛑 İşlem durduruluyor...")

@bot.on_message(filters.command("transfer"))
async def transfer_baslat(client, message):
    global DURDUR
    DURDUR = False

    try:
        args = message.text.split()
        link_kaynak = args[1]
        link_hedef = args[2]
    except:
        await message.reply("❌ **Kullanım:** `/transfer https://t.me/c/kaynak/10 https://t.me/hedef`")
        return

    durum = await message.reply("🔄 **Kanallar aranıyor (Geniş Tarama)...**")

    try:
        src_id, src_msg_id = linki_coz(link_kaynak)
        dst_id, _ = linki_coz(link_hedef)

        # GÜVENLİ GET CHAT (HATA ÇÖZÜCÜ)
        try:
            src_chat = await get_chat_guvenli(src_id)
            dst_chat = await get_chat_guvenli(dst_id)
        except Exception as e:
            await durum.edit(f"❌ **Kanal Bulunamadı!**\n\nUserbot hesabınla o kanala girip son mesaja bakman gerekebilir.\n**Hata:** {e}")
            return

        baslangic = f"Mesaj {src_msg_id}'den itibaren" if src_msg_id else "En Baştan"
        
        await durum.edit(
            f"🚀 **Transfer Başlıyor!**\n\n"
            f"📤 **Kaynak:** {src_chat.title}\n"
            f"📥 **Hedef:** {dst_chat.title}\n"
            f"📍 **Mod:** {baslangic}\n"
            f"📂 **İçerik:** Sadece Video/Foto"
        )

        sayac = 0
        
        # Mesajları Çekme
        async for msg in userbot.get_chat_history(src_chat.id, reverse=True):
            if DURDUR:
                await bot.send_message(message.chat.id, "🛑 Durduruldu.")
                break

            # Başlangıç mesajından öncesini atla
            if src_msg_id and msg.id < src_msg_id:
                continue

            # Sadece Medya
            if msg.photo or msg.video:
                try:
                    # İndir
                    dosya = await userbot.download_media(msg)
                    if not dosya: continue

                    # Yükle
                    txt = msg.caption or ""
                    if msg.video:
                        await userbot.send_video(dst_chat.id, video=dosya, caption=txt)
                    else:
                        await userbot.send_photo(dst_chat.id, photo=dosya, caption=txt)

                    sayac += 1
                    os.remove(dosya) # Sil

                    if sayac % 5 == 0:
                        try: await durum.edit(f"🔄 **Aktarılıyor...**\nToplam: {sayac}")
                        except: pass
                    
                    await asyncio.sleep(4) # Spam Koruması

                except FloodWait as fw:
                    logger.warning(f"FloodWait: {fw.value}s")
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.error(f"Transfer Hatası: {e}")
                    if 'dosya' in locals() and os.path.exists(dosya):
                        os.remove(dosya)

        await bot.send_message(message.chat.id, f"✅ **İşlem Bitti!** Toplam {sayac} medya.")

    except Exception as e:
        await durum.edit(f"❌ Beklenmeyen Hata: {e}")

# --- TEKLİ İNDİRME ---
@bot.on_message(filters.command("tekli"))
async def tekli_indir(client, message):
    try:
        link = message.text.split()[1]
        chat_id, msg_id = linki_coz(link)
    except:
        await message.reply("❌ Link hatalı.")
        return

    msj = await message.reply("🔍 **Medya aranıyor...**")

    try:
        # Güvenli Chat Bulucu
        chat = await get_chat_guvenli(chat_id)
        
        msg = await userbot.get_messages(chat.id, msg_id)
        
        if not (msg.photo or msg.video):
            await msj.edit("❌ Medya yok.")
            return

        await msj.edit("📥 **İndiriliyor...**")
        dosya = await userbot.download_media(msg)
        
        await msj.edit("📤 **Gönderiliyor...**")
        
        if msg.video:
            await bot.send_video(message.chat.id, video=dosya, caption=msg.caption)
        else:
            await bot.send_photo(message.chat.id, photo=dosya, caption=msg.caption)
            
        os.remove(dosya)
        await msj.delete()

    except Exception as e:
        await msj.edit(f"❌ Hata: {e}")

# =========================================================
#                 BAŞLATMA (HAYAT KURTARAN KISIM)
# =========================================================
async def main():
    logger.info("Botlar Başlatılıyor...")
    await bot.start()
    await userbot.start()
    
    logger.info("♻️ KANALLAR TARANIYOR (BU BİRAZ SÜREBİLİR)...")
    logger.info("Bu işlem 'PeerIdInvalid' hatasını önlemek içindir.")
    
    sayac = 0
    # Userbot'un tüm sohbetlerini çekiyoruz ki AccessHash'leri hafızaya alsın.
    try:
        async for dialog in userbot.get_dialogs():
            sayac += 1
            # Sadece çekmek yetiyor, Pyrogram otomatik cachler.
        logger.info(f"✅ {sayac} adet sohbet hafızaya alındı!")
    except Exception as e:
        logger.error(f"Tarama sırasında hata (önemsiz olabilir): {e}")

    logger.info("🚀 SİSTEM HAZIR!")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
