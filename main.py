import os
import asyncio
import threading
import time
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageService
from flask import Flask

# --- 1. RENDER WEB SUNUCUSU (Keep-Alive için) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "YaelSaver Transfer Bot Active!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 2. AYARLAR (Render Environment Variables) ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 

# SENİN ID'N (Admin Kontrolü)
try:
    ADMINS = [int(x) for x in os.environ.get("ADMIN_ID", "8291313483").split()]
except:
    ADMINS = [8291313483]

# --- 3. İSTEMCİLER ---
# Bot: Komutları dinler
bot = TelegramClient('bot_sess', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
# Userbot: Dosyaları indirir ve yükler (Senin hesabın)
userbot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. YARDIMCI FONKSİYONLAR ---
def parse_link(link):
    """Linkten Kanal ID ve Mesaj ID çeker"""
    data = {"peer": None, "msg_id": 1}
    link = link.strip()
    try:
        if "t.me/c/" in link: 
            parts = link.split("t.me/c/")[1].split("?")[0].split("/")
            data["peer"] = int("-100" + parts[0])
            if len(parts) >= 2 and parts[-1].isdigit(): data["msg_id"] = int(parts[-1])
        elif "t.me/" in link: 
            parts = link.split("t.me/")[1].split("?")[0].split("/")
            data["peer"] = parts[0]
            if len(parts) >= 2 and parts[-1].isdigit(): data["msg_id"] = int(parts[-1])
    except: pass
    return data

async def progress_callback(current, total, event, last_update_time):
    """İndirme/Yükleme yüzdesini gösterir"""
    now = time.time()
    if now - last_update_time[0] < 5: return 
    last_update_time[0] = now
    percent = (current / total) * 100
    try: await event.edit(f"⬇️ **İşleniyor:** %{percent:.1f}")
    except: pass

# --- 5. KOMUTLAR ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(f"👋 **Transfer Bot Hazır!**\n\nFiligran yok, sadece saf aktarım.\n\n`/medya [KaynakLink] [HedefLink]`")

# KANALA KATILMA (Gizli kanallar için şart)
@bot.on(events.NewMessage(pattern='/katil'))
async def join_channel(event):
    if event.sender_id not in ADMINS: return
    try: 
        link = event.text.split()[1]
        if "+" in link or "joinchat" in link: 
            await userbot(ImportChatInviteRequest(link.split('+')[-1]))
        else: 
            await userbot(JoinChannelRequest(link.replace("https://t.me/","")))
        await event.respond("✅ Userbot kanala katıldı.")
    except Exception as e: 
        await event.respond(f"❌ Hata: {e}")

# ANA KOMUT: MEDYA TRANSFERİ
@bot.on(events.NewMessage(pattern='/medya'))
async def media_transfer(event):
    if event.sender_id not in ADMINS: return await event.respond("🔒 Yetkisiz işlem.")
    
    try: 
        args = event.text.split()
        src_l, dst_l = args[1], args[2]
    except: 
        return await event.respond("⚠️ **Kullanım:** `/medya [Kaynak_Link] [Hedef_Link]`")

    status = await event.respond(f"🚀 **Transfer Başlatılıyor...**\n`{src_l}` -> `{dst_l}`")
    
    src = parse_link(src_l)
    dst = parse_link(dst_l)
    start_id = src["msg_id"]

    try:
        input_ch = await userbot.get_input_entity(src["peer"])
        output_ch = await userbot.get_input_entity(dst["peer"])
        
        count = 0
        skipped = 0
        
        # start_id'den başlayıp geçmişe değil, start_id'den başlayıp YENİYE doğru gitmek mantıklıdır genelde.
        # Ama senin eski kodunda 'reverse=True' vardı (Eskiden yeniye). Onu korudum.
        # min_id=(start_id-1) diyerek o mesajdan sonrakileri alır.
        
        async for msg in userbot.iter_messages(input_ch, min_id=(start_id-1), reverse=True):
            if isinstance(msg, MessageService): continue
            
            # Sadece medyası olanları al
            if not msg.media: 
                skipped += 1
                continue
            
            try:
                dl_msg = None
                file_size = 0
                
                # Dosya boyutu kontrolü (Sadece bilgilendirme için)
                if hasattr(msg, 'document') and msg.document: file_size = msg.document.size
                elif hasattr(msg, 'photo') and msg.photo: file_size = 5 * 1024 * 1024 # Tahmini

                last_time = [0]
                
                # Çok büyükse bilgi ver
                if file_size > 100 * 1024 * 1024: 
                      dl_msg = await bot.send_message(event.chat_id, f"⬇️ **Büyük dosya indiriliyor...**")

                # 1. İNDİR (Userbot indirir)
                path = await userbot.download_media(
                    msg, 
                    progress_callback=lambda c, t: progress_callback(c, t, dl_msg, last_time) if dl_msg else None
                )

                # 2. YÜKLE (Userbot hedefe atar)
                if dl_msg: await dl_msg.edit("⬆️ **Yükleniyor...**")
                
                # caption="" yaptık, yani yazıları sildik. Sadece medya gider.
                await userbot.send_file(output_ch, path, caption="") 

                # 3. TEMİZLE (Sunucuda yer kaplamasın)
                if os.path.exists(path): os.remove(path)
                if dl_msg: await dl_msg.delete()

                count += 1
                
                # Render/Telegram limitlerine takılmamak için bekleme
                if file_size > 50 * 1024 * 1024: 
                    await asyncio.sleep(4)
                else: 
                    await asyncio.sleep(1)

                # 5 mesajda bir ana durumu güncelle
                if count % 5 == 0: 
                    await status.edit(f"📸 **Durum:** {count} adet medya aktarıldı.")

            except Exception as e: 
                print(f"Transfer Hatası (Msg ID: {msg.id}): {e}")
                # Hata olsa bile döngüyü kırma, sıradakine geç

        await status.edit(f"✅ **İŞLEM TAMAMLANDI!**\n🎉 Toplam `{count}` medya aktarıldı.")

    except Exception as e: 
        await status.edit(f"❌ **Genel Hata:** {str(e)}\n\n*Userbot'un kaynak kanalda olduğundan emin ol.*")

# TEKLİ LİNK İNDİRİP SANA ATAR (TEST İÇİN)
@bot.on(events.NewMessage(pattern='/tekli'))
async def single(event):
    try: link = event.text.split()[1]
    except: return await event.respond("Link?")
    
    inf = parse_link(link)
    msg = await event.respond("⬇️ İndiriliyor...")
    
    try:
        m = await userbot.get_messages(inf["peer"], ids=inf["msg_id"])
        path = await userbot.download_media(m)
        
        await msg.edit("⬆️ Yükleniyor...")
        await bot.send_file(event.chat_id, path, caption="") 
        
        os.remove(path)
        await msg.delete()
    except Exception as e: 
        await msg.edit(f"Hata: {e}")

def main():
    # Flask sunucusu ayrı thread'de çalışır
    threading.Thread(target=run_web).start()
    print("🚀 Sistem Başlatıldı!")
    userbot.start()
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
