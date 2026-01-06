import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle, enums
from pyrogram.errors import FloodWait

# ==================== AYARLAR ====================
# Render Environment'a eklediysen oradan çeker, yoksa buraya yaz
API_ID = int(os.environ.get("API_ID", "36435345"))
API_HASH = os.environ.get("API_HASH", "28cfcf7036020a54feadb2d8b29d94d0")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8440950309:AAFvLpo6vGgHobQ_nVvEYznXxQ-lOJaZdoI")
SESSION = os.environ.get("SESSION_STRING", "AQIr9ZEAUCTYUJZlXguOCl_q1zJUgBSGOvrc4NPxDp2yEAfuKPU48S_eaQRcYzopnGP7yrD1CA5NSmiw1U218k1tJ74lO8vsdPeYpGCLjhqhR8ij3Ojklac1iLoHQIhnD1_o57tS9LR8Qqva2fS-thC74U5movfvj-2bIw_ZeZHo9CZo0c-QF-WAVj6aNDNVO4OTA9tP9xmDSJpiAAdWu02PSLLwbcWCnsmg7Z1dAjKEZtksSw1aCimCXsbAmswyMAlF1OJc4oN5fWdPfnG9XBEQtIrfg8zj2bXwkDHRITknFAX9F9Ay7FW1gP_CpSRSMYdtC9RsbUrdb7xQ-z_yDFr0q0kS1wAAAAHi9E9wAA")

logging.basicConfig(level=logging.ERROR)

bot = Client("render_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
ub = Client("render_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, in_memory=True)

# Web Server (Render kapanmasın diye)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Aktif"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
def keep_alive(): 
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==================== 1. /kontrol (KANIT KOMUTU) ====================
@bot.on_message(filters.command("kontrol"))
async def list_chats(c, m):
    status = await m.reply("📂 **Kanal Listen Taranıyor...**\nBotun gördüğü her şeyi sana dosya olarak atacağım.")
    
    chat_list_text = "--- BOTUN GORDUGU KANALLAR ---\n"
    chat_list_text += "Kullanim: Buradaki ID'yi kopyala, /baslat komutuna yapistir.\n\n"
    
    count = 0
    try:
        # Userbot'un tüm sohbetlerini çek
        async for dialog in ub.get_dialogs():
            # Sadece Kanal ve Grupları al
            if dialog.chat.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
                line = f"ADI: {dialog.chat.title}  |  ID: {dialog.chat.id}\n"
                chat_list_text += line
                count += 1
    except Exception as e:
        await status.edit(f"❌ Liste alınırken hata oluştu: {e}")
        return

    # Dosyaya yaz ve gönder
    file_path = "kanallar.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(chat_list_text)

    await m.reply_document(
        file_path, 
        caption=f"✅ **Toplam {count} adet kanal/grup bulundu.**\n\n1. Dosyayı aç.\n2. Kaynak kanalını bul.\n3. ID'sini (örn: -100123456) kopyala.\n4. `/baslat` komutunu kullan."
    )
    if os.path.exists(file_path): os.remove(file_path)
    await status.delete()

# ==================== 2. /baslat (ID İLE TRANSFER) ====================
@bot.on_message(filters.command("baslat"))
async def start_transfer(c, m):
    # Kullanım: /baslat [KAYNAK_ID] [HEDEF_ID] [SON_KAC_MESAJ]
    # Örnek: /baslat -1001111111 -1002222222 100
    try:
        args = m.command
        if len(args) < 3:
            await m.reply("⚠️ **HATA:** Lütfen ID kullanın.\n\n`/baslat [KAYNAK_ID] [HEDEF_ID]`\n\nID'leri `/kontrol` komutuyla öğrenebilirsin.")
            return

        src_id = int(args[1]) # Link değil, direkt ID (-100...)
        dst_id = int(args[2]) # Link değil, direkt ID (-100...)
        
        # Opsiyonel: Kaç mesajdan başlasın? (Varsayılan: En baştan, yani 1)
        start_msg_id = 1 
        if len(args) >= 4:
             # Eğer 4. parametre varsa, onu başlangıç mesajı olarak al
             start_msg_id = int(args[3])

    except ValueError:
        await m.reply("❌ ID'ler sayı olmalıdır! Link yapıştırma, ID yapıştır.")
        return

    status = await m.reply(f"🚀 **İşlem Başlıyor...**\nKaynak ID: `{src_id}`\nHedef ID: `{dst_id}`")

    # Erişim Testi
    try:
        chat_obj = await ub.get_chat(src_id)
        await status.edit(f"✅ **Kanal Doğrulandı:** `{chat_obj.title}`\nMesajlar taşınıyor...")
    except Exception as e:
        await status.edit(f"❌ **ERİŞİM YOK!**\nUserbot bu ID'yi (`{src_id}`) göremiyor.\nLütfen `/kontrol` listesinden ID'yi doğru aldığından emin ol.\nHata: `{e}`")
        return

    # Son mesajı bul
    last_id = 0
    async for x in ub.get_chat_history(src_id, limit=1): last_id = x.id
    
    if last_id == 0: await status.edit("❌ Kanal boş."); return

    await status.edit(f"📦 Transfer Başladı: `{start_msg_id}` -> `{last_id}`")

    success = 0
    # Render Diskini korumak için 20'şerli paketler
    for i in range(start_msg_id, last_id + 1, 20):
        end = min(i + 19, last_id)
        ids = list(range(i, end + 1))
        
        try:
            msgs = await ub.get_messages(src_id, ids)
            for msg in msgs:
                if not msg or msg.empty or msg.service: continue
                
                try:
                    # 1. Normal Kopyala
                    await msg.copy(dst_id)
                except:
                    # 2. İndir - Yükle - Sil (Bypass)
                    try:
                        path = await ub.download_media(msg)
                        if msg.caption: cap = msg.caption
                        else: cap = ""
                        
                        if msg.video: await ub.send_video(dst_id, path, caption=cap)
                        elif msg.photo: await ub.send_photo(dst_id, path, caption=cap)
                        elif msg.document: await ub.send_document(dst_id, path, caption=cap)
                        elif msg.text: await ub.send_message(dst_id, msg.text)
                        
                        if os.path.exists(path): os.remove(path)
                    except: pass
                
                success += 1
            
            await status.edit(f"✅ İlerleme: {end}/{last_id} (Başarılı: {success})")
            
        except FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
        except Exception: pass

    await status.edit(f"🏁 **BİTTİ:** Toplam {success} mesaj.")

if __name__ == "__main__":
    keep_alive()
    ub.start()
    bot.start()
    idle()
