# ─── Stage 1: Base Image ──────────────────────────────────────
# Pakai Python 3.11 slim — versi ringan tanpa tools yang tidak diperlukan
# "slim" artinya ukuran image lebih kecil, lebih cepat di-download
FROM python:3.11-slim

# ─── Set Working Directory ────────────────────────────────────
# Semua perintah berikutnya dijalankan dari folder /app di dalam container
WORKDIR /app

# ─── Install System Dependencies ─────────────────────────────
# Beberapa library Python butuh tools sistem ini untuk compile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ─── Copy Requirements Dulu ───────────────────────────────────
# Kenapa requirements.txt di-copy duluan sebelum kode?
# Docker punya cache layer — kalau requirements tidak berubah,
# Docker tidak perlu install ulang dari awal setiap kali kode berubah.
# Ini menghemat waktu build drastis!
COPY requirements.txt .

# ─── Install Python Dependencies ─────────────────────────────
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Copy Kode Aplikasi ───────────────────────────────────────
COPY app/ ./app/
COPY data/models/ ./data/models/
COPY data/policy_docs/ ./data/policy_docs/

# ─── Buat Folder yang Dibutuhkan ──────────────────────────────
RUN mkdir -p data/chroma_db data/mlflow data/drift_reports

# ─── Environment Variables Default ───────────────────────────
# Nilai default — akan di-override oleh docker-compose.yml
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ─── Expose Port ──────────────────────────────────────────────
# Beritahu Docker bahwa container ini "mendengarkan" di port 8000
EXPOSE 8000

# ─── Entrypoint ───────────────────────────────────────────────
# Perintah yang dijalankan saat container dinyalakan
# Pakai "0.0.0.0" supaya bisa diakses dari luar container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]