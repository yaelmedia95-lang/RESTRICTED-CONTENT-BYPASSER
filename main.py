import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# --- AYARLAR ---
API_ID = 36435345            # Kendi API ID'n
API_HASH = '28cfcf7036020a54feadb2d8b29d94d0' # Kendi API Hash'in

# Render için DOSYA ADI yerine SESSION STRING kullanıyoruz.
# Buraya '1ApWap...' gibi o çok uzun kodu yapıştıracaksın.
SESSION_STRING = '1AZWarzsBu3vjal260TB2-ZOCuy65W6nHHQoCHrq5AyW-7AvENKQGam2rORZKJ26O2_PnQ4WLbHFzYv4bordhqKbfjPTDOe5szkPyraLYsj_cwcPMi3MZdV7lS3knHuV-tbApmCDb96BNdSdiMnv-xfYbv6OrmeocQqXyS92G9wisUmDPcFY5S4e_qJlGGx1dM9FcrLaIAYQEmxebuwWUR_GO2QxEAzo5Vz6593aDdsxUC74GH2hGL-Qk2_78jEcGqZgwBykIiSnAkAyhy-9L7R2hsOFCfNLIx1zc9rWRy2aRqUvu__wpsdaQM65BgU38HkmYS7NcRAJ4_kkvfwN9a7YMAos6NXs='

# StringSession kullanarak client oluşturuyoruz (Dosya oluşturmaz)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# İşlemi durdurmak için kontrol
is_running = False

# KOMUT: /medya kaynak hedef
@client.on(events.NewMessage(pattern=r'^/medya', outgoing=True))
async def medya_tasi(event):
    global is_running
    
    if is_running:
        await event.edit("⚠️ Zaten bir işlem devam ediyor! Önce /iptal yaz.")
        return

    args = event.message.text.split()
    
    if len(args) != 3:
        await event.edit("❌ **Hatalı kullanım!**\nDoğrusu: `/medya @kaynak @hedef`\nveya: `/medya https://t.me/kaynak https://t.me/hedef`")
        return

    source_input = args[1]
    target_input = args[2]

    await event.edit(f"🔄 **Medya Kopyalama Başlıyor...**\n📤 Kaynak: {source_input}\n📥 Hedef: {target_input}\n\n_Durdurmak için /iptal yaz._")
    is_running = True

    try:
        try:
            source_entity = await client.get_entity(source_input)
            target_entity = await client.get_entity(target_input)
        except Exception as e:
            await event.reply(f"❌ Kanal bulunamadı! Linkleri kontrol et.\nHata: {e}")
            is_running = False
            return

        counter = 0
        # Kaynaktaki mesajları en eskiden (reverse=True) tarar
        async for message in client.iter_messages(source_entity, reverse=True):
            
            if not is_running:
                await client.send_message("me", f"🛑 **İşlem iptal edildi.**\nToplam kopyalanan: {counter}")
                break

            try:
                # SADECE MEDYA KONTROLÜ
                if message.media:  
                    await client.send_message(target_entity, message)
                    counter += 1
                    
                    print(f"Medya {counter} kopyalandı...")
                    await asyncio.sleep(3) # Spam yememek için bekleme

            except FloodWaitError as e:
                print(f"⚠️ Telegram durdurdu. {e.seconds} saniye bekleniyor...")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"Hata (Mesaj ID: {message.id}): {e}")

        if is_running:
            await client.send_message("me", f"✅ **İşlem Tamamlandı!**\nToplam {counter} medya kopyalandı.")

    except Exception as e:
        await client.send_message("me", f"❌ **Genel Hata:** {e}")
    finally:
        is_running = False

# KOMUT: /iptal
@client.on(events.NewMessage(pattern=r'^/iptal', outgoing=True))
async def iptal_et(event):
    global is_running
    if is_running:
        is_running = False
        await event.edit("🛑 **İptal ediliyor... Lütfen bekleyin.**")
    else:
        await event.edit("⚠️ Zaten çalışan bir işlem yok.")

print("Bot aktif! '/medya kaynak hedef' yazarak başlatabilirsin.")
client.start()
client.run_until_disconnected()
