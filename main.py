import os
import asyncio
import re
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait

# --- RENDER ENVIRONMENT VARIABLES ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # BotFather'dan aldığın token
SESSION = os.environ.get("SESSION")      # Senin hesabın (işi yapacak olan)
ADMIN_ID = int(os.environ.get("ADMIN_ID")) # Sadece sen komut verebil diye

# --- İKİ AYRI İSTEMCİ KURUYORUZ ---
# 1. Bot (Komutları dinler)
bot = Client("bot_runner", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 2. User (Geçmişi tarar ve kopyalar)
user = Client("user_runner", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)

# Global değişkenler
is_running = False
cancel_process = False

def get_chat_id_from_link(link):
    if "t.me/c/" in link:
        match = re.search(r"t\.me/c/(\d+)", link)
        if match: return int("-100" + match.group(1))
    elif "t.me/" in link:
        match = re.search(r"t\.me/([\w\d_]+)", link)
        if match: return match.group(1)
    return None

# --- KOMUTLAR (BOT ÜZERİNDEN) ---

@bot.on_message(filters.command("calis") & filters.user(ADMIN_ID))
async def start_transfer(client, message):
    global is_running, cancel_process
    
    if is_running:
        await message.reply("❌ **Şu an çalışan bir işlem var.** Bitmesini bekle veya `/iptal` yaz.")
        return

    if len(message.command) < 2:
        await message.reply("⚠️ **Kullanım:** `/calis https://t.me/kaynak_linki`\n\nLinkteki medya dosyalarını bu gruba çeker.")
        return

    link = message.command[1]
    
    # Bot cevap veriyor ama işlemi USER yapacak
    status_msg = await message.reply(f"🤖 **Bot:** Emir alındı.\n🕵️ **User:** Kaynak analiz ediliyor...\n`{link}`")
    
    # Linki çözümle
    source_chat = get_chat_id_from_link(link)
    target_chat = message.chat.id # Komutun yazıldığı yer

    if not source_chat:
        await status_msg.edit("❌ Link geçersiz. Düzgün bir mesaj linki gir.")
        return

    is_running = True
    cancel_process = False

    media_messages = []

    try:
        # --- 1. TARAMA (USER HESABI YAPAR) ---
        # Bot geçmişi göremez, o yüzden 'user' client'ı kullanıyoruz
        async for msg in user.get_chat_history(source_chat):
            if cancel_process: break
            if msg.photo or msg.video:
                media_messages.append(msg.id)
        
        if cancel_process:
            await status_msg.edit("🛑 İşlem tarama sırasında iptal edildi.")
            is_running = False
            return

        total_count = len(media_messages)
        if total_count == 0:
            await status_msg.edit("❌ Bu kaynakta hiç medya bulunamadı.")
            is_running = False
            return

        media_messages.reverse() # Eskiden yeniye
        
        await status_msg.edit(f"✅ **Liste Hazır!**\n\n📂 Toplam Medya: `{total_count}`\n🚀 **Transfer Başlıyor...**")
        
        # --- 2. AKTARIM (USER HESABI YAPAR) ---
        sent_count = 0
        
        for msg_id in media_messages:
            if cancel_process:
                await status_msg.edit(f"🛑 **İşlem Durduruldu!**\n📊 İlerleme: {sent_count}/{total_count}")
                is_running = False
                return

            try:
                # Kopyalama işlemini User hesabı yapar (Bot yapamaz çünkü kaynağı görmüyor)
                await user.copy_message(
                    chat_id=target_chat,
                    from_chat_id=source_chat,
                    message_id=msg_id,
                    caption="" 
                )
                sent_count += 1

                # Bot durumu günceller
                if sent_count % 20 == 0:
                    try:
                        await status_msg.edit(f"🔄 **Aktarılıyor...**\n\n📊 Durum: `{sent_count}/{total_count}`\n❌ İptal: `/iptal`")
                    except: pass
                
                await asyncio.sleep(0.5)

            except FloodWait as e:
                print(f"Flood: {e.value} sn")
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"Hata: {e}")

        await status_msg.edit(f"✅ **GÖREV TAMAMLANDI!**\n\n🎉 Toplam `{sent_count}` adet medya başarıyla kopyalandı.")

    except Exception as e:
        await status_msg.edit(f"❌ **Hata:** {str(e)}\n\n*Not: User hesabın kaynak kanalda, Bot hesabın bu grupta admin olduğundan emin ol.*")
    
    finally:
        is_running = False

@bot.on_message(filters.command("iptal") & filters.user(ADMIN_ID))
async def cancel_transfer(client, message):
    global cancel_process
    cancel_process = True
    await message.reply("🛑 **İptal sinyali gönderildi...** Userbot işlemi durduracak.")

async def main():
    print("Bot ve Userbot başlatılıyor...")
    await user.start()
    await bot.start()
    print("Sistem Aktif! Botuna /calis komutu verebilirsin.")
    await idle()
    await user.stop()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
