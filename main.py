import os
import asyncio
import threading
import sqlite3
import time
import subprocess
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import MessageService
from flask import Flask

# --- 1. RENDER WEB SUNUCUSU ---
app = Flask(__name__)
@app.route('/')
def home(): return "YaelSaver with Emergency Brake!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 2. AYARLAR ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 

# SENİN ID'N
ADMINS = [8291313483] 

WATERMARK_TEXT = "TG:StreetagencyTR"

# EL FRENİ İÇİN GLOBAL DEĞİŞKEN
STOP_FLAGS = {} 

# --- 3. İSTEMCİLER ---
bot = TelegramClient('bot_sess', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
userbot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. MARKALAMA MOTORU ---
def check_font():
    if not os.path.exists("font.ttf"):
        try:
            url = "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab-Bold.ttf"
            r = requests.get(url, allow_redirects=True)
            open('font.ttf', 'wb').write(r.content)
        except: pass

def add_watermark(input_path):
    output_path = "wm_" + input_path
    check_font()
    try:
        if input_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            img = Image.open(input_path).convert("RGBA")
            if img.width < 500:
                base_width = 500
                w_percent = (base_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            fontsize = int(img.width * 0.08)
            try: font = ImageFont.truetype("font.ttf", fontsize)
            except: font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
            text_w = bbox[2] - bbox[0]
            x, y = (img.width - text_w) / 2, 30
            draw.text((x, y), WATERMARK_TEXT, font=font, fill="white", stroke_width=3, stroke_fill="black")
            out = Image.alpha_composite(img, txt_layer).convert("RGB")
            out.save(output_path, quality=95)
            return output_path
        elif input_path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
            try: subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: return input_path
            cmd = ['ffmpeg', '-y', '-i', input_path, '-vf', f"drawtext=fontfile=font.ttf:text='{WATERMARK_TEXT}':fontcolor=white:fontsize=h/15:x=(w-text_w)/2:y=30:shadowcolor=black:shadowx=3:shadowy=3", '-codec:a', 'copy', '-preset', 'ultrafast', output_path]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path
    except: return input_path
    return input_path

# --- 5. YARDIMCI ---
def parse_link(link):
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
    now = time.time()
    if now - last_update_time[0] < 5: return 
    last_update_time[0] = now
    percent = (current / total) * 100
    try: await event.edit(f"⬇️ **İndiriliyor:** %{percent:.1f}")
    except: pass

# --- 6. KOMUTLAR ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(f"👋 **YaelSaver + El Freni**\n\nİşlemi durdurmak için `/iptal` yazabilirsin.")

# KATIL
@bot.on(events.NewMessage(pattern='/katil'))
async def join_channel(event):
    if event.sender_id not in ADMINS: return
    try: 
        link = event.text.split()[1]
        if "+" in link or "joinchat" in link: await userbot(ImportChatInviteRequest(link.split('+')[-1]))
        else: await userbot(JoinChannelRequest(link.replace("https://t.me/","")))
        await event.respond("✅ Girdim.")
    except Exception as e: await event.respond(f"❌ Hata: {e}")

# --- YENİ KOMUT: İPTAL (EL FRENİ) ---
@bot.on(events.NewMessage(pattern='/iptal'))
async def stop_process(event):
    if event.sender_id not in ADMINS: return
    
    # Bayrağı kaldır
    STOP_FLAGS[event.sender_id] = True
    await event.respond("🛑 **EL FRENİ ÇEKİLDİ!**\n\nMevcut dosya biter bitmez işlem durdurulacak.\nLütfen bekleyin...")

# --- MEDYA TRANSFER ---
@bot.on(events.NewMessage(pattern='/medya'))
async def media_transfer(event):
    if event.sender_id not in ADMINS: return await event.respond("🔒 Yetkisiz.")
    try: args = event.text.split(); src_l, dst_l = args[1], args[2]
    except: return await event.respond("⚠️ `/medya [Kaynak] [Hedef]`")

    status = await event.respond("♻️ **Analiz...**\nDurdurmak için `/iptal` yaz.")
    src = parse_link(src_l); dst = parse_link(dst_l)
    
    # Başlarken bayrağı indir (Reset)
    STOP_FLAGS[event.sender_id] = False

    try:
        input_ch = await userbot.get_input_entity(src["peer"])
        output_ch = await userbot.get_input_entity(dst["peer"])
        count = 0
        skipped = 0
        
        async for msg in userbot.iter_messages(input_ch, min_id=(src["msg_id"]-1), reverse=True):
            
            # --- EL FRENİ KONTROLÜ ---
            if STOP_FLAGS.get(event.sender_id, False):
                await status.edit(f"🛑 **İŞLEM İPTAL EDİLDİ!**\n\n✅ Taşınan: {count}\n🗑 Atlanan: {skipped}\n\nSistem durdu.")
                STOP_FLAGS[event.sender_id] = False # Sıfırla
                return # Döngüden ve fonksiyondan çık
            # -------------------------

            if isinstance(msg, MessageService): continue
            
            if not msg.media: 
                skipped += 1; continue
            
            try:
                dl_msg = None
                file_size = 0
                if hasattr(msg, 'document') and msg.document: file_size = msg.document.size
                elif hasattr(msg, 'photo') and msg.photo: file_size = 5 * 1024 * 1024

                last_time = [0]
                if file_size > 100 * 1024 * 1024: 
                     dl_msg = await bot.send_message(event.chat_id, f"⬇️ **Büyük Dosya...**")

                # İndir
                path = await userbot.download_media(msg, progress_callback=lambda c, t: progress_callback(c, t, dl_msg, last_time) if dl_msg else None)

                # Markala
                if dl_msg: await dl_msg.edit("⚙️ **Markalanıyor...**")
                new_path = await asyncio.to_thread(add_watermark, path)

                # Yükle (YAZISIZ)
                if dl_msg: await dl_msg.edit("⬆️ **Yükleniyor...**")
                await userbot.send_file(output_ch, new_path, caption="") 

                if os.path.exists(path): os.remove(path)
                if os.path.exists(new_path) and new_path != path: os.remove(new_path)
                if dl_msg: await dl_msg.delete()

                count += 1
                if file_size > 50 * 1024 * 1024: await asyncio.sleep(5)
                else: await asyncio.sleep(2)

                if count % 5 == 0: await status.edit(f"📸 **Durum:** {count} taşındı.")

            except Exception as e: print(f"Hata: {e}")

        await status.edit(f"✅ **BİTTİ!**\n📸 Toplam: {count}")
    except Exception as e: await status.edit(f"❌ Hata: {str(e)}")

# TEKLİ
@bot.on(events.NewMessage(pattern='/tekli'))
async def single(event):
    try: link = event.text.split()[1]
    except: return await event.respond("Link?")
    inf = parse_link(link)
    msg = await event.respond("⬇️ İndiriliyor...")
    try:
        m = await userbot.get_messages(inf["peer"], ids=inf["msg_id"])
        path = await userbot.download_media(m)
        new_path = await asyncio.to_thread(add_watermark, path)
        await bot.send_file(event.chat_id, new_path, caption="") 
        os.remove(path); 
        if new_path != path: os.remove(new_path)
        await msg.delete()
    except Exception as e: await msg.edit(f"Hata: {e}")

# MAIN
def main():
    threading.Thread(target=run_web).start()
    print("🚀 YaelSaver Brake Edition Started!")
    userbot.start()
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
