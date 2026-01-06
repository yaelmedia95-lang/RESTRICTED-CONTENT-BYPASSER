# Python 3.10 tabanlı hafif sistem
FROM python:3.10-slim

# Çalışma klasörü
WORKDIR /app

# SİHİR BURADA: FFmpeg ve Font kütüphanelerini kuruyoruz
RUN apt-get update && \
    apt-get install -y ffmpeg libfreetype6-dev libjpeg-dev fontconfig && \
    rm -rf /var/lib/apt/lists/*

# Dosyaları kopyala
COPY . .

# Python kütüphanelerini yükle
RUN pip install --no-cache-dir -r requirements.txt

# Botu başlat
CMD ["python", "main.py"]
