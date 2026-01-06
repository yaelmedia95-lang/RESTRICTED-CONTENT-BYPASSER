import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait

# ==================== AYARLAR (Render Environment'tan Çeker) ====================
# Eğer Render'a Env girmeyi beceremezsen tırnak içlerine kendi bilgilerini yazabilirsin.
API_ID = int(os.environ.get("API_ID", "36435345"))
API_HASH = os.environ.get("API_HASH", "28cfcf7036020a54feadb2d8b29d94d0")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8440950309:AAFvLpo6vGgHobQ_nVvEYznXxQ-lOJaZdoI")
SESSION = os.environ.get("SESSION_STRING", "AQIr9ZEAUCTYUJZlXguOCl_q1zJUgBSGOvrc4NPxDp2yEAfuKPU48S_eaQRcYzopnGP7yrD1CA5NSmiw1U218k1tJ74lO8vsdPeYpGCLjhqhR8ij3Ojklac1iLoHQIhnD1_o57tS9LR8Qqva2fS-thC74U5movfvj-2bIw_ZeZHo9CZo0c-QF-WAVj6aNDNVO4OTA9tP9xmDSJpiAAdWu02PSLLwbcWCnsmg7Z1dAjKEZtksSw1aCimCXsbAmswyMAlF1OJc4oN5fWdPfnG9XBEQtIrfg8zj2bXwkDHRITknFAX9F9Ay7FW1gP_CpSRSMYdtC9RsbUrdb7xQ-z_yDFr0q0kS1wAAAAHi9E9wAA")

# Logları Kapat (Hız için)
logging.basicConfig(level=logging.ERROR)

# İstemciler
bot = Client("render_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
ub = Client("render_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, in_memory=True)

# Küresel Sohbet Hafızası
CHAT_DB = {}

# ==================== 1. WEB SERVER (7/24 KEEP ALIVE) ====================
app = Flask(__name__)

@app.route('/')
def home(): return "Bot Çalışıyor! ⚡"

def run_web():
    # Render PORT'u otomatik atar, yoksa 8080 kullanır
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==================== 2. PRE-LOADER (ERİŞİM GARANTİSİ) ====================
async def load_all_chats():
    print("⏳ [SİSTEM] Erişim anahtarları güncelleniyor...")
    try:
        async for dialog in ub.get_dialogs():
            CHAT_DB[dialog.chat.id] = dialog.chat
    except: pass
    print(f"✅ [HAZIR] {len(CHAT_DB)} kanal hafızada.")

# ==================== 3. LİNK ÇÖZÜCÜ ====================
def parse_link(link):
    data = {"chat_id": None, "msg_id": 1, "topic_id": None}
    link = str(link).strip()
    try:
        if "t.me/c/" in link:
            parts = link.split("t.me/c/")[1].split("?")[0].split("/")
            data["chat_id"] = int("-100" + parts[0])
            if len(parts) >= 3:
                data["topic_id"] = int(parts[1])
                data["msg_id"] = int(parts[2])
            elif len(parts) == 2:
                data["msg_id"] = int(parts[1])
        elif "t.me/" in link:
            parts = link.split("t.me/")[1].split("?")[0].split("/")
            data["chat_id"] = parts[0]
            if len(parts) >= 3: data["msg_id"] = int(parts[2])
            elif len(parts) == 2 and parts[1].isdigit(): data["msg_id"] = int(parts[1])
    except: pass
    return data

# ==================== 4. TRANSFER (BYPASS MODU) ====================
@bot.on_message(filters.command("transfer"))
async def transfer(c, m):
    try: src_l, dst_l = m.command[1], m.command[2]
    except: await m.reply("⚠️ `/transfer [Kaynak] [Hedef]`"); return

    status = await m.reply("🔄 **Userbot Bağlanıyor...**")
    src, dst = parse_link(src_l), parse_link(dst_l)

    # KAYNAK KANALI BULMA
    source_chat = None
    if isinstance(src["chat_id"], int):
        if src["chat_id"] in CHAT_DB: source_chat = CHAT_DB[src["chat_id"]]
        else: await status.edit("❌ Kanal listede yok. `/katil [Link]` yap."); return
    else:
        try: source_chat = await ub.get_chat(src["chat_id"])
        except: await status.edit("❌ Erişim yok."); return

    # SON MESAJI BUL
    last_id = 0
    try:
        async for x in ub.get_chat_history(source_chat.id, limit=1): last_id = x.id
    except: pass
    
    if last_id == 0: await status.edit("❌ Kanal boş."); return

    start = src["msg_id"] if src["msg_id"] > 1 else 1
    await status.edit(f"🚀 **Render Modu Aktif**\n`{source_chat.title}` kopyalanıyor...\nDiski korumak için 'İndir-Sil' yapılacak.")

    success = 0
    # 20'şer 20'şer işle (Render RAM'ini patlatmamak için ideal sayı)
    for i in range(start, last_id + 1, 20):
        end = min(i + 19, last_id)
        ids = list(range(i, end + 1))
        
        try:
            msgs = await ub.get_messages(source_chat.id, ids)
            for msg in msgs:
                if not msg or msg.empty or msg.service: continue
                
                # Topic Filtresi
                if src["topic_id"] and getattr(msg, "message_thread_id", None) != src["topic_id"]: continue

                kwrgs = {}
                if dst["topic_id"]: kwrgs["message_thread_id"] = dst["topic_id"]

                try:
                    # 1. Önce normal kopyalamayı dene (Hızlıdır)
                    await msg.copy(dst["chat_id"], **kwrgs)
                except:
                    # 2. Hata verirse (Kısıtlı İçerik), İNDİR-YÜKLE yap
                    try:
                        # Dosya yolu (Render geçici disk)
                        path = await ub.download_media(msg)
                        
                        if msg.video: await ub.send_video(dst["chat_id"], path, caption=msg.caption, **kwrgs)
                        elif msg.photo: await ub.send_photo(dst["chat_id"], path, caption=msg.caption, **kwrgs)
                        elif msg.document: await ub.send_document(dst["chat_id"], path, caption=msg.caption, **kwrgs)
                        elif msg.text: await ub.send_message(dst["chat_id"], msg.text, **kwrgs)
                        
                        # HEMAN SİL (Render Diskini Koru)
                        if os.path.exists(path): os.remove(path)
                    except: pass
                
                success += 1
                
            await status.edit(f"✅ İlerleme: {end}/{last_id} (Başarılı: {success})")
            
        except FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
        except Exception: pass

    await status.edit(f"🏁 **BİTTİ:** {success} içerik taşındı.")

@bot.on_message(filters.command("katil"))
async def katil(c, m):
    try: await ub.join_chat(m.command[1]); await m.reply("✅ Girildi, liste yenileniyor...")
    except: pass
    await load_all_chats()
    await m.reply("✅ Hazır.")

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 RENDER BOT BAŞLATILIYOR...")
    keep_alive() # Flask sunucusunu başlat
    ub.start()
    bot.start()
    
    # Render açılır açılmaz hafızayı doldur
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_all_chats())
    
    print("✅ SİSTEM HAZIR!")
    idle()
