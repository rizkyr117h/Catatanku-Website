# 🗒️ Catatanku — Production Deployment Guide

Stack: **Python Flask** + **PostgreSQL** + **Redis** + **Nginx** + **Docker**

---

## 📁 Struktur Proyek

```
catatanku/
├── app/
│   ├── __init__.py          # App factory, extensions
│   ├── models.py            # SQLAlchemy models
│   └── routes/
│       ├── auth.py          # Register, Login, Refresh, Logout
│       ├── notes.py         # CRUD catatan
│       └── tags.py          # CRUD tag kustom
├── postgres/
│   └── init.sql             # Schema PostgreSQL + indexes + triggers
├── nginx/
│   ├── nginx.conf           # Reverse proxy + SSL + rate limiting
│   └── certs/               # Taruh SSL certificate di sini
│       ├── fullchain.pem
│       └── privkey.pem
├── wsgi.py                  # Gunicorn entrypoint
├── requirements.txt
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full production stack
├── .env.example             # Template environment variables
└── .dockerignore
```

---

## 🚀 Cara Deploy

### 1. Persiapan Server

```bash
# Install Docker & Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo apt install docker-compose-plugin -y
```

### 2. Clone & Setup

```bash
git clone <repo-url> catatanku
cd catatanku

# Buat file .env dari template
cp .env.example .env
nano .env   # Isi semua nilai yang wajib diganti!
```

### 3. Generate Secret Keys

```bash
# Jalankan di terminal untuk generate key yang aman:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 4. Setup SSL Certificate

```bash
# Opsi A: Let's Encrypt (gratis, direkomendasikan)
sudo apt install certbot -y
sudo certbot certonly --standalone -d catatanku.example.com

mkdir -p nginx/certs
sudo cp /etc/letsencrypt/live/catatanku.example.com/fullchain.pem nginx/certs/
sudo cp /etc/letsencrypt/live/catatanku.example.com/privkey.pem   nginx/certs/
sudo chown -R $USER:$USER nginx/certs/

# Opsi B: Self-signed (development/testing saja)
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/privkey.pem \
  -out    nginx/certs/fullchain.pem \
  -subj "/CN=localhost"
```

### 5. Deploy Frontend (HTML)

```bash
# Taruh file catatan-pribadi.html ke folder static yang di-mount nginx
mkdir -p static
cp catatan-pribadi.html static/index.html
```

### 6. Build & Run

```bash
# Build image
docker compose build

# Jalankan semua service
docker compose up -d

# Cek status
docker compose ps
docker compose logs -f app
```

### 7. Verifikasi

```bash
# Health check
curl https://catatanku.example.com/api/health

# Test register
curl -X POST https://catatanku.example.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"aku","email":"aku@email.com","password":"password123"}'
```

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/auth/register` | Daftar akun baru |
| POST | `/api/auth/login` | Login, dapat token |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout, revoke token |
| GET  | `/api/auth/me` | Info user saat ini |

### Notes
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET    | `/api/notes/` | List catatan (filter, search, paginate) |
| POST   | `/api/notes/` | Buat catatan baru |
| GET    | `/api/notes/<id>` | Detail catatan |
| PUT    | `/api/notes/<id>` | Update catatan |
| DELETE | `/api/notes/<id>` | Hapus permanen (harus di trash dulu) |
| DELETE | `/api/notes/trash/empty` | Kosongkan semua trash |

**Query params untuk GET /api/notes/:**
- `filter`: `all` | `pinned` | `trash` | `deadline` | `todo` | `tag`
- `tag_id`: ID tag untuk filter
- `q`: kata kunci pencarian
- `page`, `per_page`: pagination

### Tags
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET    | `/api/tags/` | List semua tag |
| POST   | `/api/tags/` | Buat tag baru |
| PUT    | `/api/tags/<id>` | Update tag |
| DELETE | `/api/tags/<id>` | Hapus tag |

---

## 🔐 Security Features

- ✅ JWT Access Token (1 jam) + Refresh Token (30 hari)
- ✅ Refresh token rotation — token lama direvoke setelah refresh
- ✅ Bcrypt password hashing
- ✅ Rate limiting: 10 req/menit untuk auth, 60/menit untuk API
- ✅ CORS whitelist per domain
- ✅ Security headers (HSTS, CSP, X-Frame-Options, dll)
- ✅ Non-root Docker user
- ✅ Internal Docker network (DB tidak expose ke luar)
- ✅ Multi-stage Docker build (image lebih kecil & aman)
- ✅ PostgreSQL triggers untuk `updated_at`
- ✅ Input validation & sanitization

---

## 🛠️ Perintah Berguna

```bash
# Lihat log realtime
docker compose logs -f

# Masuk ke container app
docker compose exec app bash

# Masuk ke PostgreSQL
docker compose exec db psql -U catatanku_user -d catatanku

# Restart satu service
docker compose restart app

# Update & redeploy
git pull
docker compose build app
docker compose up -d --no-deps app

# Lihat backup database
ls -lh db_backups/

# Scale app (lebih banyak worker)
docker compose up -d --scale app=3
```

---

## ⚠️ Checklist Sebelum Go-Live

- [ ] Semua nilai di `.env` sudah diisi dan aman
- [ ] SSL certificate sudah terpasang
- [ ] Domain sudah diarahkan ke server
- [ ] `.env` tidak masuk ke Git (ada di `.gitignore`)
- [ ] Firewall hanya buka port 80 dan 443
- [ ] Backup otomatis berjalan (`docker compose logs db_backup`)
- [ ] Test semua endpoint API
