import os
import asyncio
import threading
import sqlite3
import time
import subprocess
import requests # Font indirmek için
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
def home(): return "YaelSaver Watermark FIXED Active!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 2. AYARLAR ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
# KENDİ ID'Nİ BURAYA YAZ:
ADMINS = [8291313483] 

WATERMARK_TEXT = "TG:StreetagencyTR"

# --- 3. İSTEMCİLER ---
bot = TelegramClient('bot_sess', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
userbot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. MARKALAMA MOTORU (GÜNCELLENDİ) ---
def check_font():
    """Font dosyası yoksa indirir, böylece yazı kesin görünür"""
    if not os.path.exists("font.ttf"):
        print("Font indiriliyor...")
        url = "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab-Bold.ttf"
        r = requests.get(url, allow_redirects=True)
        open('font.ttf', 'wb').write(r.content)

def add_watermark(input_path):
    output_path = "wm_" + input_path
    check_font() # Font kontrolü

    try:
        # --- FOTOĞRAF ---
        if input_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            img = Image.open(input_path).convert("RGBA")
            
            # Resim çok küçükse büyüt (Yazı sığsın diye)
            if img.width < 500:
                base_width = 500
                w_percent = (base_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

            # Şeffaf katman oluştur
            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            # Font boyutu: Resim genişliğinin %8'i
            fontsize = int(img.width * 0.08)
            try: font = ImageFont.truetype("font.ttf", fontsize)
            except: font = ImageFont.load_default()

            # Yazıyı ölç
            bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Konum: Üst Orta (Tepeden 30px aşağı)
            x = (img.width - text_w) / 2
            y = 30
            
            # Siyah Çerçeve (Stroke)
            stroke_width = 3
            draw.text((x, y), WATERMARK_TEXT, font=font, fill="white", stroke_width=stroke_width, stroke_fill="black")
            
            # Katmanları birleştir
            out = Image.alpha_composite(img, txt_layer)
            out = out.convert("RGB")
            out.save(output_path, quality=95)
            return output_path

        # --- VİDEO (FFMPEG) ---
        elif input_path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
            # FFmpeg kontrolü
            try:
                subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except:
                print("HATA: FFmpeg yüklü değil!")
                return input_path # FFmpeg yoksa orjinalini dön

            # Komut: Üstte, Beyaz, Siyah Gölgeli, Ortalı
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', f"drawtext=fontfile=font.ttf:text='{WATERMARK_TEXT}':fontcolor=white:fontsize=h/15:x=(w-text_w)/2:y=30:shadowcolor=black:shadowx=3:shadowy=3",
                '-codec:a', 'copy', 
                '-preset', 'ultrafast', # Hızlı render için
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path
            
    except Exception as e:
        print(f"Markalama Hatası: {e}")
        return input_path 

    return input_path

# --- 5. DİĞER FONKSİYONLAR AYNI KALIYOR ---
def init_db():
    conn = sqlite3.connect('yaelsaver.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_vip INTEGER DEFAULT 0)''')
    conn.commit(); conn.close()

def parse_link(link):
    data = {"peer": None, "msg_id": 1, "topic_id": None}
    link = link.strip()
    try:
        if "t.me/c/" in link: 
            parts = link.split("t.me/c/")[1].split("?")[0].split("/")
            data["peer"] = int("-100" + parts[0])
            if len(parts) >= 2 and parts[-1].isdigit(): data["msg_id"] = int(parts[-1])
            if len(parts) == 3: data["topic_id"] = int(parts[-2])
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
    await event.respond(f"👋 **YaelSaver Fixed**\n\nMarkalama motoru güçlendirildi.")

@bot.on(events.NewMessage(pattern='/tekli'))
async def single(event):
    try: link = event.text.split()[1]
    except: return await event.respond("Link?")
    inf = parse_link(link)
    msg = await event.respond("⬇️ İndiriliyor...")
    try:
        m = await userbot.get_messages(inf["peer"], ids=inf["msg_id"])
        path = await userbot.download_media(m)
        
        await msg.edit("⚙️ **Marka Basılıyor (Font + FFmpeg)...**")
        # Arka planda çalıştır
        new_path = await asyncio.to_thread(add_watermark, path)
        
        # Eğer yeni dosya oluşmadıysa hata vardır
        if new_path == path:
            await msg.edit("⚠️ **Uyarı:** Marka basılamadı (FFmpeg eksik olabilir). Orjinali atılıyor.")
        
        await msg.edit("⬆️ Yükleniyor...")
        await bot.send_file(event.chat_id, new_path, caption=m.text or "")
        
        if os.path.exists(path): os.remove(path)
        if os.path.exists(new_path) and new_path != path: os.remove(new_path)
        await msg.delete()
    except Exception as e: await msg.edit(f"Hata: {e}")

# ... Diğer komutlar (Medya, Transfer) önceki kodla aynı ...
# (Transfer ve Medya komutlarını önceki cevaptan alıp buraya ekleyebilirsin, 
# ama en önemlisi 'add_watermark' fonksiyonunun bu yeni halidir)

# --- DAMGA KOMUTU ---
@userbot.on(events.NewMessage(pattern=r'^/damga$', outgoing=True))
async def markala_eski(event):
    if not event.is_reply: return
    reply_msg = await event.get_reply_message()
    if not reply_msg.media or not reply_msg.out: return
    status = await event.edit("⚙️ **Markalanıyor...**")
    try:
        path = await userbot.download_media(reply_msg)
        new_path = await asyncio.to_thread(add_watermark, path)
        await userbot.edit_message(event.chat_id, reply_msg.id, file=new_path, text=reply_msg.text or "")
        await status.edit("✅ Tamam."); os.remove(path); 
        if new_path != path: os.remove(new_path)
        await asyncio.sleep(3); await status.delete()
    except: pass

# --- MAIN ---
def main():
    threading.Thread(target=run_web).start()
    print("🚀 YaelSaver FIXED Started!")
    userbot.start()
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
