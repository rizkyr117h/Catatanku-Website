# Catatanku — Deploy Guide (Simpel)

## Struktur
```
catatanku/
├── app/
│   ├── __init__.py
│   ├── models.py
│   └── routes/
│       ├── auth.py
│       ├── notes.py
│       └── tags.py
├── static/
│   └── index.html        ← taruh file catatan-pribadi.html di sini
├── wsgi.py
├── requirements.txt
├── Dockerfile
├── Caddyfile             ← SSL otomatis, tanpa ribet
├── docker-compose.yml
└── .env
```

---

## Deploy (5 langkah)

### 1. Upload project ke server
```bash
scp -r catatanku-simple/ user@server:~/catatanku
cd ~/catatanku
```

### 2. Buat file .env
```bash
cp .env.example .env
nano .env   # isi nilai-nilainya
```

Generate secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Taruh file frontend
```bash
mkdir -p static
cp /path/to/catatan-pribadi.html static/index.html
```

### 4. Jalankan
```bash
docker compose up -d
```

Selesai! Caddy otomatis mengurus SSL Let's Encrypt. Tidak perlu setup cert manual.

### 5. Cek status
```bash
docker compose ps
curl https://catatanku.rizkytech.cloud/api/health
```

---

## Perintah berguna
```bash
# Lihat log
docker compose logs -f

# Restart
docker compose restart

# Update app
docker compose build app && docker compose up -d --no-deps app

# Masuk ke database
docker compose exec db psql -U catatanku_user -d catatanku
```

## API Endpoints

| Method | URL | Keterangan |
|--------|-----|------------|
| POST | `/api/auth/register` | Daftar |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Refresh token |
| GET  | `/api/auth/me` | Info user |
| GET  | `/api/notes/` | List catatan |
| POST | `/api/notes/` | Buat catatan |
| PUT  | `/api/notes/<id>` | Update catatan |
| DELETE | `/api/notes/<id>` | Hapus permanen |
| GET  | `/api/tags/` | List tag |
| POST | `/api/tags/` | Buat tag |
