import os
import asyncio
import threading
import sqlite3
import time
import subprocess
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
def home(): return "YaelSaver Watermark Pro Active!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 2. AYARLAR ---
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") 
# Kendi ID'ni buraya sayı olarak yaz. Tırnak koyma!
ADMINS = [8291313483]
OWNER_CONTACT = "@yasin33" 

# MARKALAMA AYARLARI
WATERMARK_TEXT = "TG:StreetagencyTR"

# --- 3. İSTEMCİLER ---
bot = TelegramClient('bot_sess', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
userbot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. MARKALAMA MOTORU (SİHİR BURADA) ---
def add_watermark(input_path):
    """
    Dosya türüne göre (Foto/Video) üzerine yazı yazar.
    Eski dosyayı siler, yeni dosyanın yolunu döndürür.
    """
    output_path = "wm_" + input_path
    
    try:
        # FOTOĞRAF İSE
        if input_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            img = Image.open(input_path)
            draw = ImageDraw.Draw(img)
            
            # Font boyutu resme göre ayarla (Genişliğin %5'i kadar)
            fontsize = int(img.width * 0.05)
            if fontsize < 20: fontsize = 20
            
            # Basit font (Render'da ttf olmayabilir, default kullanıyoruz)
            try:
                font = ImageFont.truetype("arial.ttf", fontsize)
            except:
                font = ImageFont.load_default()

            # Yazı boyutunu hesapla
            # Pillow sürümüne göre bbox veya textsize kullanılır, basit tutalım:
            text_w = fontsize * len(WATERMARK_TEXT) * 0.6 # Tahmini genişlik
            
            # Konum: Üst Orta (Y=20 piksel aşağıda)
            x = (img.width - text_w) / 2
            y = 20
            
            # Siyah çerçeve (Gölge) + Beyaz Yazı (Okunurluk için)
            draw.text((x+2, y+2), WATERMARK_TEXT, font=font, fill="black")
            draw.text((x, y), WATERMARK_TEXT, font=font, fill="white")
            
            img.save(output_path)
            return output_path

        # VİDEO İSE (FFMPEG KULLANIR)
        elif input_path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
            # FFmpeg komutu: Tepeye ortala, beyaz yazı, 24px
            # x=(w-text_w)/2 : Yatayda ortala
            # y=20 : Tepeden 20px aşağı
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', f"drawtext=text='{WATERMARK_TEXT}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=20:shadowcolor=black:shadowx=2:shadowy=2",
                '-codec:a', 'copy', # Sesi kopyala (Hız için)
                output_path
            ]
            
            # Komutu çalıştır
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path
            
    except Exception as e:
        print(f"Markalama Hatası: {e}")
        return input_path # Hata olursa orjinalini döndür

    return input_path

# --- 5. YARDIMCI FONKSİYONLAR ---
def init_db():
    conn = sqlite3.connect('yaelsaver.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_vip INTEGER DEFAULT 0)''')
    conn.commit(); conn.close()

def get_user(uid):
    conn = sqlite3.connect('yaelsaver.db', check_same_thread=False)
    u = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return u if u else (uid, 0)

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

async def progress_callback(current, total, event, last_update_time):
    now = time.time()
    if now - last_update_time[0] < 5: return 
    last_update_time[0] = now
    percent = (current / total) * 100
    try:
        await event.edit(f"⬇️ **İndiriliyor:** %{percent:.1f}")
    except: pass

# --- 6. KOMUTLAR ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline("📸 Markalı Medya Transfer", b"help_media")],
        [Button.inline("📥 Tekli İndir (Markalı)", b"help_single")]
    ]
    await event.respond(f"👋 **YaelSaver Watermark Modu**\n\nTüm içeriklere otomatik olarak `{WATERMARK_TEXT}` yazılacak.", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"help_"))
async def help_btn(event):
    d = event.data.decode()
    if "media" in d: text = "📸 **MARKALI TRANSFER**\n\nKomut: `/medya [Kaynak] [Hedef]`\n\nVideolara ve fotolara yazı yazar, öyle atar."
    elif "single" in d: text = "📥 **TEKLİ**\n\nKomut: `/tekli [Link]`\n\nİndirip markalayıp atar."
    await event.answer(text, alert=True)

@bot.on(events.NewMessage(pattern='/tekli'))
async def single(event):
    try: link = event.text.split()[1]
    except: return await event.respond("Link?")
    inf = parse_link(link)
    msg = await event.respond("⬇️ İndiriliyor...")
    try:
        m = await userbot.get_messages(inf["peer"], ids=inf["msg_id"])
        path = await userbot.download_media(m)
        
        await msg.edit("⚙️ **Marka Basılıyor...**")
        new_path = await asyncio.to_thread(add_watermark, path)
        
        await msg.edit("⬆️ Yükleniyor...")
        await bot.send_file(event.chat_id, new_path, caption=m.text or "")
        
        if os.path.exists(path): os.remove(path)
        if os.path.exists(new_path) and new_path != path: os.remove(new_path)
        await msg.delete()
    except Exception as e: await msg.edit(f"Hata: {e}")
        
@bot.on(events.NewMessage(pattern='/id'))
async def my_id(event):
    # Bu komut senin ID'ni ve Admin olup olmadığını söyler
    uid = event.sender_id
    is_admin = uid in ADMINS
    await event.respond(f"🆔 **Senin ID:** `{uid}`\n👮 **Admin Yetkisi:** {is_admin}")
    
@bot.on(events.NewMessage(pattern='/medya'))
async def media_transfer(event):
    if event.sender_id not in ADMINS: return await event.respond("🔒 Sadece Admin.")
    try: args = event.text.split(); src_l, dst_l = args[1], args[2]
    except: return await event.respond("`/medya [Kaynak] [Hedef]`")

    status = await event.respond("♻️ **Markalı Transfer Başlıyor...**")
    src = parse_link(src_l); dst = parse_link(dst_l)
    start_id = src["msg_id"] if src["msg_id"] else 1

    try:
        input_ch = await userbot.get_input_entity(src["peer"])
        output_ch = await userbot.get_input_entity(dst["peer"])
        count = 0
        
        async for msg in userbot.iter_messages(input_ch, min_id=(start_id-1), reverse=True):
            if isinstance(msg, MessageService): continue
            if not msg.media: continue
            
            try:
                dl_msg = None
                file_size = 0
                if hasattr(msg, 'document') and msg.document: file_size = msg.document.size
                elif hasattr(msg, 'photo') and msg.photo: file_size = 5 * 1024 * 1024

                # İlerleme göstergesi
                last_time = [0]
                if file_size > 50 * 1024 * 1024: 
                     dl_msg = await bot.send_message(event.chat_id, f"⬇️ **Büyük Dosya İniyor...**")

                # İndir
                path = await userbot.download_media(msg, progress_callback=lambda c, t: progress_callback(c, t, dl_msg, last_time) if dl_msg else None)

                # Markala (Video işleme zaman alır, kullanıcıya bilgi ver)
                if dl_msg: await dl_msg.edit("⚙️ **Yazı Yazılıyor... (Render)**")
                new_path = await asyncio.to_thread(add_watermark, path)

                # Yükle
                if dl_msg: await dl_msg.edit("⬆️ **Yükleniyor...**")
                await userbot.send_file(output_ch, new_path, caption=msg.text or "")
                
                # Sil
                if os.path.exists(path): os.remove(path)
                if os.path.exists(new_path) and new_path != path: os.remove(new_path)
                if dl_msg: await dl_msg.delete()

                count += 1
                await status.edit(f"✅ Taşınan: {count}")
                
                # Soğuma süresi
                if file_size > 50 * 1024 * 1024: await asyncio.sleep(5)
                else: await asyncio.sleep(2)

            except Exception as e:
                print(f"Hata: {e}")

        await status.edit(f"✅ **BİTTİ!** Toplam: {count}")
    except Exception as e: await status.edit(f"Hata: {e}")
# --- MODÜL: KATIL (/katil) ---
@bot.on(events.NewMessage(pattern='/katil'))
async def join_channel(event):
    # Sadece adminler kullanabilsin (İsteğe bağlı, herkes kullansın dersen bu satırı sil)
    if event.sender_id not in ADMINS: return await event.respond("🔒 Sadece Admin.")

    try: link = event.text.split()[1]
    except: return await event.respond("⚠️ **Kullanım:** `/katil [Davet Linki]`")
    
    msg = await event.respond("🔐 **Giriş deneniyor...**")
    
    try:
        # Davet linki ise (t.me/+AbCd...)
        if "+" in link or "joinchat" in link:
            hash_code = link.split('+')[-1]
            await userbot(ImportChatInviteRequest(hash_code))
        # Normal link ise (t.me/kanaladi)
        else:
            username = link.replace("https://t.me/", "").replace("t.me/", "")
            await userbot(JoinChannelRequest(username))
            
        await msg.edit("✅ **Başarıyla Katıldım!**\nŞimdi `/medya` komutunu kullanabilirsin.")
        
    except UserAlreadyParticipantError:
        await msg.edit("✅ **Zaten Üyeyim.** Sorun yok, devam et.")
    except Exception as e:
        await msg.edit(f"❌ **Giremedim:** `{str(e)}`\nLinkin doğru olduğundan veya banlı olmadığından emin ol.")
# --- MAIN ---
def main():
    threading.Thread(target=run_web).start()
    print("🚀 YaelSaver Watermark Active!")
    userbot.start()
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()
