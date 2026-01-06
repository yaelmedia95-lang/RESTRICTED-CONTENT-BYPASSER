import os
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# --- ENVIRONMENT VARIABLES (RENDER AYARLARI) ---
# Render'da bu isimlerle değişkenleri tanımlayacaksın
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION") # String Session buraya
ADMIN_ID = int(os.environ.get("ADMIN_ID")) # Senin ID'n (Başkası kullanamasın diye)

# Bot Token bu senaryoda (Userbot kopyalaması) teknik olarak şart değil 
# ama senin yapında varsa dursun, Client sadece session ile de kalkar.
# Biz doğrudan Userbot (Session) üzerinden gideceğiz ki her yere erişebilsin.

app = Client(
    "render_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION
)

# Durum Kontrolü
is_running = False
cancel_process = False

def get_chat_id_from_link(link):
    if "t.me/c/" in link:
        # Private Link: https://t.me/c/123456789/123
        match = re.search(r"t\.me/c/(\d+)", link)
        if match:
            return int("-100" + match.group(1))
    elif "t.me/" in link:
        # Public Link: https://t.me/kullaniciadi/123
        match = re.search(r"t\.me/([\w\d_]+)", link)
        if match:
            return match.group(1)
    return None

@app.on_message(filters.command("calis", prefixes=".") & filters.user(ADMIN_ID))
async def start_transfer(client, message):
    global is_running, cancel_process
    
    if is_running:
        await message.edit("❌ **Sırada işlem var.** Bitmesini bekle veya `.iptal` yaz.")
        return

    if len(message.command) < 2:
        await message.edit("⚠️ **Kullanım:** `.calis <mesaj_linki>`\n\nLinkteki kanalı tarar ve bulunduğun yere kopyalar.")
        return

    link = message.command[1]
    source_chat = get_chat_id_from_link(link)

    if not source_chat:
        await message.edit("❌ Linkten kanal ID'si çözülemedi. Düzgün bir mesaj linki ver.")
        return

    is_running = True
    cancel_process = False
    target_chat = message.chat.id # Komutu nereye yazdıysan oraya atar
    
    status_msg = await message.edit(f"🕵️ **Hedef Taranıyor...**\n`{link}`\n\nBu işlem kanalın büyüklüğüne göre sürebilir.")

    media_messages = []
    
    try:
        # --- 1. TARAMA MODU ---
        async for msg in app.get_chat_history(source_chat):
            if cancel_process:
                break
            # Sadece Fotoğraf ve Video (Metinleri, dosyaları siktir et)
            if msg.photo or msg.video:
                media_messages.append(msg.id)
        
        if cancel_process:
            await status_msg.edit("🛑 Tarama iptal edildi.")
            is_running = False
            return

        total_count = len(media_messages)
        if total_count == 0:
            await status_msg.edit("❌ Bu kanalda kopyalanacak fotoğraf/video bulunamadı.")
            is_running = False
            return

        # Listeyi ters çevir (Eskiden yeniye gitmesi için)
        media_messages.reverse()

        await status_msg.edit(f"✅ **Analiz Bitti!**\n\n📂 Toplam Medya: `{total_count}` adet.\n🚀 **Transfer Başlıyor...**")
        await asyncio.sleep(2)

        # --- 2. TRANSFER MODU ---
        sent_count = 0
        
        for msg_id in media_messages:
            if cancel_process:
                await status_msg.edit(f"🛑 **İşlem Yarıda Kesildi!**\n\n📊 İlerleme: {sent_count}/{total_count}")
                is_running = False
                return

            try:
                # Caption (yazı) yok, sadece medya
                await app.copy_message(
                    chat_id=target_chat,
                    from_chat_id=source_chat,
                    message_id=msg_id,
                    caption="" 
                )
                sent_count += 1

                # Her 20 mesajda bir rapor ver
                if sent_count % 20 == 0:
                    try:
                        await status_msg.edit(f"🔄 **Aktarılıyor...**\n\n📊 Durum: `{sent_count}/{total_count}`\n❌ Durdurmak için: `.iptal`")
                    except:
                        pass # Floodwait yerse editlemeyi pas geç, işleme devam et
                
                # Render sunucusu hızlıdır, Telegram bizi banlamasın diye minik bekleme
                await asyncio.sleep(0.5)

            except FloodWait as e:
                # Telegram "yavaş ol" derse bekle
                print(f"FloodWait: {e.value} saniye.")
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Hata (ID: {msg_id}): {e}")
                # Tekil hata olursa (mesela silinmiş mesaj) devam et

        await status_msg.edit(f"✅ **BİTTİ!**\n\n🎉 Toplam `{sent_count}` medya başarıyla bu gruba aktarıldı.")

    except Exception as e:
        await status_msg.edit(f"❌ **Kritik Hata:** {str(e)}")
    
    finally:
        is_running = False

@app.on_message(filters.command("iptal", prefixes=".") & filters.user(ADMIN_ID))
async def cancel_transfer(client, message):
    global cancel_process
    cancel_process = True
    await message.edit("🛑 **İptal sinyali yollandı...** Mevcut işlem durduruluyor.")

# Render için Keep-Alive
print("Userbot Başlatıldı. Komut bekleniyor...")
app.run()
