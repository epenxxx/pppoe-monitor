# PPPoE Monitor by ZYLVEmedia

Sistem monitoring PPPoE MikroTik terpusat menggunakan Docker. Proyek ini mendengarkan log jaringan secara langsung (Syslog UDP), menyinkronkan status user aktif, dan mengirimkan notifikasi *Login/Logout* secara real-time ke Telegram. Dilengkapi dengan Web Dashboard berbasis Flask untuk pengaturan yang mudah tanpa perlu menyentuh kode.

## Fitur Utama
- **Web Dashboard:** Konfigurasi API Telegram, Router IP, dan Identity via antarmuka web (Port `5050`).
- **Internal Syslog Server:** Menangkap log MikroTik via UDP Port `514` (Tanpa mapping file syslog OS).
- **Auto-Sync:** Membaca data *Secrets* dan *Active* secara cerdas.
- **Auto-Restart:** Sistem melakukan restart mandiri setiap 1 jam untuk menjaga stabilitas memori.
- **Portable:** Berbasis Docker, mudah dipindahkan antar server Ubuntu/Linux.

## 🚀 Cara Instalasi di Server Ubuntu

1. **Clone Repositori:**
   ```bash
   git clone https://github.com/epenxxx/pppoe-monitor.git
   cd pppoe-monitor

2. Jalankan Docker Compose:
   ```bash
   docker compose up -d --build

3. Buka Port Firewall (Jika UFW aktif):
   ```bash
   sudo ufw allow 5050/tcp
   sudo ufw allow 514/udp

4. Akses Dashboard:
    Buka browser dan akses http://<IP_SERVER_UBUNTU>:5050. Buat akun baru, lalu masukkan Token Telegram dan detail API MikroTik Anda.

⚙️ Konfigurasi di MikroTik

Agar MikroTik Anda mengirimkan log ke aplikasi ini, jalankan perintah berikut di New Terminal MikroTik Anda (ganti IP_SERVER_UBUNTU dengan IP server Docker Anda):
```bash
/system logging action add name=remoteLog target=remote remote=IP_SERVER_UBUNTU remote-port=514
/system logging add topics=pppoe,info action=remoteLog

```
⚙️ Catatan Pembaruan

Jika Anda mengubah konfigurasi atau memperbarui repositori, hapus database lama agar tidak terjadi bentrok struktur:
```bash
rm instance/database.db
docker compose down
docker compose up -d --build
