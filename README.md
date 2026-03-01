# Catatanku — Development Setup

## Jalankan

```bash
# 1. Clone / upload project ke server
cd ~/catatanku

# 2. Sesuaikan .env jika perlu (sudah ada default untuk dev)
nano .env

# 3. Build dan jalankan
docker compose up -d

# 4. Cek
curl http://localhost:4502/api/health
```

App berjalan di **http://server-ip:4502**

---

## Setup Nginx Manual (opsional)

```bash
# Copy config
sudo cp nginx.conf.example /etc/nginx/sites-available/catatanku
sudo ln -s /etc/nginx/sites-available/catatanku /etc/nginx/sites-enabled/

# Taruh file frontend
sudo mkdir -p /var/www/catatanku
sudo cp catatan-pribadi.html /var/www/catatanku/index.html

# Test dan reload
sudo nginx -t && sudo systemctl reload nginx
```

## Setup SSL Manual (setelah Nginx jalan)

```bash
sudo certbot --nginx -d catatanku.rizkytech.cloud
```

Certbot akan otomatis update config Nginx untuk HTTPS.

---

## Perintah berguna

```bash
docker compose logs -f        # lihat log
docker compose restart app    # restart flask
docker compose down           # matikan semua
docker compose up -d --build  # rebuild dan jalankan
```
