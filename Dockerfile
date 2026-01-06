# 1. Python 3.10 yüklü hafif bir Linux sürümü kullan
FROM python:3.10-slim

# 2. Çalışma klasörünü ayarla
WORKDIR /app

# 3. Gerekli sistem araçlarını ve FFMPEG'i kur (Video işlemek için şart)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 4. Dosyaları kopyala
COPY . .

# 5. Python kütüphanelerini yükle
RUN pip install --no-cache-dir -r requirements.txt

# 6. Botu başlat
CMD ["python", "main.py"]
