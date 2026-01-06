import os
import asyncio
import threading
import sqlite3
import time
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import MessageService
from flask import Flask

# --- 1. RENDER WEB SUNUCUSU ---
app = Flask(__name__)
@app.route('/')
def home(): return "YaelSaver Media Pro (Fast Mode) Active!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 2. AYARLAR ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
ADMINS = list(map(int, os.environ.get("ALLOWED_USERS", "").split(","))) if os.environ.get("ALLOWED_USERS") else []
OWNER_CONTACT = "@yasin33" 

# --- 3. İSTEMCİLER ---
bot = TelegramClient('bot_sess', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
userbot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. YARDIMCI FONKSİYONLAR ---
def init_db():
    conn = sqlite3.connect('yaelsaver.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_vip INTEGER DEFAULT 0)''')
    conn.commit(); conn.close()

# Link Çözücü
def parse_link(link):
    data = {"peer": None, "msg_id": None, "topic_id": None}
    link = link.strip()
    try:
        if "t.me/c/" in link: 
            parts = link.split("t.me/c/")[1].split("?")[0].split("/")
            data["peer"] = int("-100" + parts[0])
            if len(parts) >= 2: data["msg_id"] = int(parts[-1])
            if len(parts) == 3: data["topic_id"] = int(parts[-2])
        elif "t.me/" in link: 
            parts = link.split("t.me/")[1].split("?")[0].split("/")
            data["peer"] = parts[0]
            if len(parts) >= 2: data["msg_id"] = int(parts[-1])
    except: pass
    return data

# İlerleme Çubuğu
async def progress_callback(current, total, event, last_update_time):
    now = time.time()
    if now - last_update_time[0] < 5: return 
    last_update_time[0] = now
    percent = (current / total) * 100
    try:
        await event.edit(f"⬇️ **İndiriliyor:** %{percent:.1f}\n💾 `{current//1024//1024}MB / {total//1024//1024}MB`")
    except: pass

# --- 5. BOT KOMUTLARI ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    buttons = [
        [Button.inline("📸 Sadece Medya Transfer", b"help_media")],
        [Button.inline("🚀 Full Kanal Transfer", b"help_trans")],
        [Button.inline("📥 Tekli İndir", b"help_single")]
    ]
    await event.respond(f"👋 **YaelSaver Hızlı Mod (5sn)**\n\nID: `{uid}`\n\nVideolar arası bekleme süresi **5 saniyeye** düşürüldü.", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"help_"))
async def help_btn(event):
    d = event.data.decode()
    if "media" in d: text = "📸 **SADECE MEDYA**\n\nKomut: `/medya [Kaynak] [Hedef]`\n\nYazıları atlar, sadece video/foto çeker."
    elif "trans" in d: text = "🚀 **FULL TRANSFER**\n\nKomut: `/transfer [Kaynak] [Hedef]`\n\nHer şeyi kopyalar."
    elif "single" in d: text = "📥 **TEKLİ İNDİRME**\n\nKomut: `/tekli [Link]`"
    await event.answer(text, alert=True)

# --- MODÜL: KATIL ---
@bot.on(events.NewMessage(pattern='/join'))
async def join(event):
    try: await userbot(ImportChatInviteRequest(event.text.split('+')[-1])); await event.respond("✅ Girdim.")
    except: await event.respond("❌ Hata. Linki kontrol et.")

# --- MODÜL: TEKLİ ---
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
        await bot.send_file(event.chat_id, path, caption=m.text or "")
        os.remove(path)
        await msg.delete()
    except Exception as e: await msg.edit(f"Hata: {e}")

# --- MODÜL: MEDYA TRANSFER (GÜNCELLENMİŞ HIZLI SÜRÜM) ---
@bot.on(events.NewMessage(pattern='/medya'))
async def media_transfer(event):
    if event.sender_id not in ADMINS: return await event.respond("🔒 Sadece Admin.")

    try: args = event.text.split(); src_l, dst_l = args[1], args[2]
    except: return await event.respond("⚠️ **Kullanım:** `/medya [Kaynak] [Hedef]`")

    status = await event.respond("♻️ **Medya Analizi Başlıyor...**")

    src = parse_link(src_l)
    dst = parse_link(dst_l)
    start_id = src["msg_id"] if src["msg_id"] else 1

    try:
        input_ch = await userbot.get_input_entity(src["peer"])
        output_ch = await userbot.get_input_entity(dst["peer"])

        count = 0
        skipped = 0
        
        async for msg in userbot.iter_messages(input_ch, min_id=(start_id-1), reverse=True):
            if isinstance(msg, MessageService): continue
            
            # Sadece medya (Foto, Video, Belge)
            if not msg.media:
                skipped += 1
                continue
            
            try:
                file_size = 0
                if hasattr(msg, 'document') and msg.document: file_size = msg.document.size
                elif hasattr(msg, 'photo') and msg.photo: file_size = 5 * 1024 * 1024 

                last_time = [0]
                dl_msg = None
                
                # Çok büyük dosyalarda (100MB+) bilgi mesajı at
                if file_size > 100 * 1024 * 1024: 
                     dl_msg = await bot.send_message(event.chat_id, f"⬇️ **Büyük Dosya:** {file_size//1024//1024} MB")

                # İNDİR
                path = await userbot.download_media(
                    msg, 
                    progress_callback=lambda c, t: progress_callback(c, t, dl_msg, last_time) if dl_msg else None
                )

                # YÜKLE
                if dl_msg: await dl_msg.edit("⬆️ **Yükleniyor...**")
                await userbot.send_file(output_ch, path, caption=msg.text or "")
                
                # SİL
                os.remove(path)
                if dl_msg: await dl_msg.delete()

                count += 1
                
                # --- HIZ AYARI BURADA ---
                if file_size > 50 * 1024 * 1024: 
                    await asyncio.sleep(5) # Eskiden 10 idi, şimdi 5 saniye
                else:
                    await asyncio.sleep(2) # Küçük dosyalarda 2 saniye

                if count % 5 == 0: 
                    await status.edit(f"📸 **Durum:**\n✅ Taşınan: {count}\n🗑 Atlanan Metin: {skipped}")

            except Exception as e:
                print(f"Hata: {e}")
                pass

        await status.edit(f"✅ **BİTTİ!**\n📸 Toplam: {count}\n🗑 Atlanan: {skipped}")

    except Exception as e:
        await status.edit(f"❌ Hata: {str(e)}")

# --- MODÜL: FULL TRANSFER ---
@bot.on(events.NewMessage(pattern='/transfer'))
async def full_trans(event):
    if event.sender_id not in ADMINS: return
    try: args = event.text.split(); src_l, dst_l = args[1], args[2]
    except: return await event.respond("`/transfer [Src] [Dst]`")
    
    status = await event.respond("🚀 **Full Transfer...**")
    src, dst = parse_link(src_l), parse_link(dst_l)
    start_id = src["msg_id"] if src["msg_id"] else 1
    
    try:
        inp = await userbot.get_input_entity(src["peer"])
        out = await userbot.get_input_entity(dst["peer"])
        count = 0
        
        async for msg in userbot.iter_messages(inp, min_id=(start_id-1), reverse=True):
            if isinstance(msg, MessageService): continue
            try:
                if msg.media:
                    path = await userbot.download_media(msg)
                    await userbot.send_file(out, path, caption=msg.text or "")
                    os.remove(path)
                elif msg.text:
                    await userbot.send_message(out, msg.text)
                count += 1
                if count % 10 == 0: await status.edit(f"🚀 {count}")
                await asyncio.sleep(2) 
            except: pass
            
        await status.edit(f"✅ Bitti: {count}")
    except Exception as e: await status.edit(f"Hata: {e}")

# --- MAIN ---
def main():
    init_db()
    threading.Thread(target=run_web).start()
    print("🚀 YaelSaver Fast Mode Started!")
    userbot.start()
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
