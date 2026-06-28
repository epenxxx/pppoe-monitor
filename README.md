Cara Menjalankan di Server Ubuntu

1. Pastikan docker dan docker-compose sudah terinstal di server Ubuntu Anda.
2. Letakkan semua file di atas sesuai struktur direktori.
3. Buka terminal/SSH, masuk ke folder pppoe-monitor, lalu jalankan perintah:

    docker compose up -d --build
   
4. Buka browser dan akses http://<IP-SERVER-UBUNTU>:5050
5. Lakukan Registrasi Akun pertama kali (hanya bisa 1 akun demi keamanan).
6. Setelah login, Anda tinggal mengisi Token Telegram, Chat ID, dan konfigurasi API MikroTik Anda lalu klik Simpan.

Skrip secara otomatis akan berjalan, tersinkronisasi, dan langsung mengirim notifikasi telegram saat ada log logged in atau logged out terbaca dari server!
