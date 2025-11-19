# Temel Python imajı
FROM python:3.11-slim

# Çalışma dizini
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Portu expose et
EXPOSE 5000

# Container başlatıldığında çalışacak komut
CMD ["python", "app.py"]
