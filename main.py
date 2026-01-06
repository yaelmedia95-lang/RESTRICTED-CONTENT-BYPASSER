import os
import asyncio
import logging
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, UserAlreadyParticipant

# ==================== AYARLAR ====================
API_ID = 36435345
API_HASH = "28cfcf7036020a54feadb2d8b29d94d0"
BOT_TOKEN = "8440950309:AAFvLpo6vGgHobQ_nVvEYznXxQ-lOJaZdoI"
SESSION = "AQIr9ZEAUCTYUJZlXguOCl_q1zJUgBSGOvrc4NPxDp2yEAfuKPU48S_eaQRcYzopnGP7yrD1CA5NSmiw1U218k1tJ74lO8vsdPeYpGCLjhqhR8ij3Ojklac1iLoHQIhnD1_o57tS9LR8Qqva2fS-thC74U5movfvj-2bIw_ZeZHo9CZo0c-QF-WAVj6aNDNVO4OTA9tP9xmDSJpiAAdWu02PSLLwbcWCnsmg7Z1dAjKEZtksSw1aCimCXsbAmswyMAlF1OJc4oN5fWdPfnG9XBEQtIrfg8zj2bXwkDHRITknFAX9F9Ay7FW1gP_CpSRSMYdtC9RsbUrdb7xQ-z_yDFr0q0kS1wAAAAHi9E9wAA"

# Logları Kapat
logging.basicConfig(level=logging.ERROR)

bot = Client("yael_render", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
ub = Client("yael_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, in_memory=True)

# Küresel Sohbet Hafızası
CHAT_DB = {}

# ==================== 1. PRE-LOADER (ERİŞİM GARANTİSİ) ====================
async def load_all_chats():
    print("⏳ [SİSTEM] Erişim anahtarları güncelleniyor...")
    try:
        async for dialog in ub.get_dialogs():
            CHAT_DB[dialog.chat.id] = dialog.chat
    except: pass
    print(f"✅ [HAZIR] {len(CHAT_DB)} kanal hafızada. Kısıtlama delmeye hazır!")

# ==================== 2. LİNK ÇÖZÜCÜ ====================
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

# ==================== 3. TRANSFER KOMUTU (BYPASS MODU) ====================
@bot.on_message(filters.command("transfer"))
async def transfer(c, m):
    try: src_l, dst_l = m.command[1], m.command[2]
    except: await m.reply("⚠️ `/transfer [Kaynak] [Hedef]`"); return

    status = await m.reply("🔄 **Userbot Bağlanıyor...**")
    src, dst = parse_link(src_l), parse_link(dst_l)

    # KAYNAK KANALI BULMA (DB KULLANARAK)
    source_chat = None
    if isinstance(src["chat_id"], int):
        if src["chat_id"] in CHAT_DB: source_chat = CHAT_DB[src["chat_id"]]
        else: await status.edit("❌ Kanal listede yok. `/katil [Link]` yap."); return
    else:
        try: source_chat = await ub.get_chat(src["chat_id"])
        except: await status.edit("❌ Erişim yok."); return

    # SON MESAJI BUL
    last_id = 0
    async for x in ub.get_chat_history(source_chat.id, limit=1): last_id = x.id
    
    if last_id == 0: await status.edit("❌ Kanal boş."); return

    start = src["msg_id"] if src["msg_id"] > 1 else 1
    await status.edit(f"🚀 **BYPASS MODU AKTİF**\n`{source_chat.title}` kopyalanıyor...\nDiski korumak için 'İndir-Sil' yapılacak.")

    success = 0
    # 50'şer 50'şer işle (Render RAM'ini yormamak için düşük tuttum)
    for i in range(start, last_id + 1, 50):
        end = min(i + 49, last_id)
        ids = list(range(i, end + 1))
        
        try:
            msgs = await ub.get_messages(source_chat.id, ids)
            for msg in msgs:
                if not msg or msg.empty or msg.service: continue
                
                # Topic Filtresi
                if src["topic_id"] and getattr(msg, "message_thread_id", None) != src["topic_id"]: continue

                kwrgs = {}
                if dst["topic_id"]: kwrgs["message_thread_id"] = dst["topic_id"]

                # --- KRİTİK BÖLÜM: BYPASS MANTIĞI ---
                try:
                    # 1. Önce normal kopyalamayı dene (Hızlıdır, kısıtlama yoksa çalışır)
                    await msg.copy(dst["chat_id"], **kwrgs)
                except:
                    # 2. Hata verirse (Protected Content), İNDİR-YÜKLE yap
                    try:
                        # Dosya yolu belirle (Render'ın geçici klasörü)
                        path = await ub.download_media(msg)
                        
                        # Caption
                        cap = msg.caption or ""
                        
                        # Yükle
                        if msg.video: await ub.send_video(dst["chat_id"], path, caption=cap, **kwrgs)
                        elif msg.photo: await ub.send_photo(dst["chat_id"], path, caption=cap, **kwrgs)
                        elif msg.document: await ub.send_document(dst["chat_id"], path, caption=cap, **kwrgs)
                        elif msg.text: await ub.send_message(dst["chat_id"], msg.text, **kwrgs)
                        
                        # HEMAN SİL (Render Diskini Koru)
                        if os.path.exists(path): os.remove(path)
                    except Exception as e:
                        print(f"Hata: {e}")
                        pass # Geç, takılma
                
                success += 1
                
            await status.edit(f"✅ İlerleme: {end}/{last_id} (Başarılı: {success})")
            await asyncio.sleep(2) 
            
        except FloodWait as fw:
            await status.edit(f"😴 {fw.value}sn Mola..."); await asyncio.sleep(fw.value + 5)
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
    print("🚀 BOT BAŞLATILIYOR...")
    ub.start()
    bot.start()
    
    # Render açılır açılmaz hafızayı doldur
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_all_chats())
    
    print("✅ SİSTEM HAZIR!")
    idle()
