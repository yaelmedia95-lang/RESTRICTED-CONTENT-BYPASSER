import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelPrivate, ChannelInvalid

# =========================================================
#                   AYARLAR (DOLDUR)
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
    return "Bot Aktif! 406 Fix Devrede."

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
#             ÖZEL HATA ÇÖZÜCÜ (BURASI ÖNEMLİ)
# =========================================================

async def force_find_chat(chat_id):
    """
    Eğer get_chat hata verirse, bu fonksiyon kullanıcının TÜM dialoglarını
    tek tek gezerek o ID'ye sahip kanalı bulur ve nesnesini döndürür.
    Bu yöntem AccessHash hatasını %100 çözer.
    """
    logger.info(f"⚠️ Derin tarama yapılıyor: {chat_id}")
    
    # 1. Eğer chat_id string ise (username) ve başında @ yoksa ekle
    if isinstance(chat_id, str) and not chat_id.startswith("-100"):
        if not chat_id.startswith("@"): chat_id = "@" + chat_id
        try:
            return await userbot.get_chat(chat_id)
        except:
            pass # Username ile bulamazsa devam et

    # 2. Dialogları gez (Kesin Çözüm)
    async for dialog in userbot.get_dialogs():
        # ID eşleşiyor mu?
        if str(dialog.chat.id) == str(chat_id):
            logger.info(f"✅ Kanal bulundu: {dialog.chat.title}")
            return dialog.chat
    
    # Bulunamazsa
    raise ValueError(f"Kanal ({chat_id}) senin sohbet listende bulunamadı! Userbot grupta mı?")

def linki_coz(link):
    """Linkten ID ve Mesaj Numarasını ayıklar"""
    link = link.strip().replace("https://", "").replace("http://", "").replace("t.me/", "")
    
    chat_identifier = None
    msg_id = None
    parts = link.split("/")
    
    # Özel Kanal (c/12345/10)
    if "c/" in link:
        raw_id = parts[1]
        chat_identifier = int("-100" + raw_id) # Private kanallar -100 ile başlar
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

# =========================================================
#                 KOMUTLAR
# =========================================================

@bot.on_message(filters.command("start"))
async def start_msg(client, message):
    await message.reply(
        "🛠 **406 Hata Çözücü Bot**\n\n"
        "Eğer 'Channel Private' hatası alırsan bot senin listeni tarayıp o kanalı bulacak.\n\n"
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
        await message.reply("❌ **Kullanım:** `/transfer https://t.me/c/1234/100 https://t.me/hedef`")
        return

    durum = await message.reply("🔄 **Kanal listende aranıyor...**")

    try:
        src_id, src_msg_id = linki_coz(link_kaynak)
        dst_id, _ = linki_coz(link_hedef)

        # KAYNAK KANALI BUL (ZORLA)
        try:
            src_chat = await force_find_chat(src_id)
        except Exception as e:
            await durum.edit(f"❌ **Kaynak Kanal Hatası:**\n{e}\n\nUserbot o grupta değil mi?")
            return

        # HEDEF KANALI BUL (ZORLA)
        try:
            dst_chat = await force_find_chat(dst_id)
        except Exception as e:
            await durum.edit(f"❌ **Hedef Kanal Hatası:**\n{e}")
            return

        baslangic = f"Mesaj {src_msg_id}'den itibaren" if src_msg_id else "En Baştan"
        
        await durum.edit(
            f"🚀 **Transfer Başlıyor!**\n\n"
            f"📤 **Kaynak:** {src_chat.title}\n"
            f"📥 **Hedef:** {dst_chat.title}\n"
            f"📍 **Mod:** {baslangic}\n"
            f"⚠️ **Yön:** En Yeniden -> En Eskiye"
        )

        sayac = 0
        
        # TARAMA
        async for msg in userbot.get_chat_history(src_chat.id):
            if DURDUR:
                await bot.send_message(message.chat.id, "🛑 Durduruldu.")
                break

            # Başlangıç mesajından öncesini atla (ID küçüldükçe eskiye gider)
            if src_msg_id and msg.id < src_msg_id:
                break 

            if msg.photo or msg.video:
                try:
                    # İNDİR
                    dosya = await userbot.download_media(msg)
                    if not dosya: continue

                    # YÜKLE
                    txt = msg.caption or ""
                    if msg.video:
                        await userbot.send_video(dst_chat.id, video=dosya, caption=txt)
                    else:
                        await userbot.send_photo(dst_chat.id, photo=dosya, caption=txt)

                    sayac += 1
                    os.remove(dosya)

                    if sayac % 5 == 0:
                        try: await durum.edit(f"🔄 **Aktarılıyor...**\nToplam: {sayac}")
                        except: pass
                    
                    await asyncio.sleep(4)

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

    msj = await message.reply("🔍 **Kanal listende aranıyor...**")

    try:
        # ZORLA BUL
        chat = await force_find_chat(chat_id)
        
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
#                 BAŞLATMA
# =========================================================
async def main():
    logger.info("Sistem başlatılıyor...")
    await bot.start()
    await userbot.start()
    logger.info("✅ Botlar hazır!")
    await idle()
    await bot.stop()
    await userbot.stop()

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
