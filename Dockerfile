FROM python:3.10-slim

WORKDIR /app

# FFmpeg ve Fontları Kur (Video ve Foto için hayati önem taşır)
RUN apt-get update && \
    apt-get install -y ffmpeg libfreetype6-dev libjpeg-dev fontconfig && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
