# TASK LIST — IP Radar Implementation

## FASE 1: MVP (Target: Hari 1–3)

### 🏗️ Setup & Fondasi

- [x] **[SETUP-1]** Inisialisasi project structure sesuai folder layout di `flow.md`
- [x] **[SETUP-2]** Buat virtual environment Python & `requirements.txt`
  - FastAPI, uvicorn[standard], sqlalchemy, pymysql, alembic, jinja2, python-multipart, apscheduler, icmplib, openpyxl, python-dotenv, passlib[bcrypt], python-jose
- [x] **[SETUP-3]** Buat file `.env` (DATABASE_URL, SECRET_KEY, SCRIPT_API_TOKEN, PING_INTERVAL)
- [x] **[SETUP-4]** Setup `database.py` (SQLAlchemy engine + session factory)
- [x] **[SETUP-5]** Buat semua SQLAlchemy models (users, devices, device_specs, ip_pool, device_history, notifications, topology_edges, scan_logs)
- [x] **[SETUP-6]** Setup Alembic & generate migration awal (buat semua tabel di `db_aplikasi`)
- [x] **[SETUP-7]** Buat `main.py` entry point (mount static, include routers, startup event untuk APScheduler)
- [x] **[SETUP-8]** Buat `base.html` template (navbar, sidebar, content block, notif bell)
- [x] **[SETUP-9]** Integrasikan Tailwind CSS (download tailwind.min.css atau CDN play untuk dev)

---

### 🔐 Autentikasi

- [x] **[AUTH-1]** Buat router `routers/auth.py`: GET/POST `/login`, GET `/logout`
- [x] **[AUTH-2]** Implementasi session cookie (JWT atau signed cookie via `python-jose`)
- [x] **[AUTH-3]** Dependency `get_current_user` untuk proteksi semua route
- [x] **[AUTH-4]** Dependency `require_admin` untuk proteksi route aksi (CRUD)
- [x] **[AUTH-5]** Buat template `templates/auth/login.html` (form login yang premium/beautiful)
- [x] **[AUTH-6]** Seeder: pastikan koneksi ke tabel `users` yang sudah ada berjalan dengan benar

---

### 📊 Dashboard

- [x] **[DASH-1]** Buat router `routers/dashboard.py`: GET `/dashboard`
- [x] **[DASH-2]** Query statistik: total devices per tipe, per status (online/offline/unknown)
- [x] **[DASH-3]** Query IP usage: per seksi (used/free/reserved/conflict)
- [x] **[DASH-4]** Query: 5 notifikasi/alert terbaru
- [x] **[DASH-5]** Buat template `templates/dashboard/index.html`
  - Widget statistik dengan angka besar + icon
  - Chart donut distribusi perangkat (Chart.js)
  - IP usage progress bar per seksi
  - Tabel alert terbaru
- [x] **[DASH-6]** API endpoint `GET /api/v1/dashboard/stats` (JSON) untuk auto-refresh polling tiap 30 detik via JS

---

### 🖥️ Manajemen Perangkat

- [x] **[DEV-1]** Buat router `routers/devices.py`
- [x] **[DEV-2]** `GET /devices` — Daftar perangkat dengan filter (seksi, tipe, status) + pagination + search
- [x] **[DEV-3]** `GET /devices/{id}` — Detail perangkat (info + specs + history kepemilikan)
- [x] **[DEV-4]** `GET /devices/create` + `POST /devices/create` — Tambah perangkat manual (Admin only)
- [x] **[DEV-5]** `GET /devices/{id}/edit` + `POST /devices/{id}/edit` — Edit perangkat (Admin only)
- [x] **[DEV-6]** `POST /devices/{id}/assign` — Assign pemilik (Admin only), insert `device_history`
- [x] **[DEV-7]** `POST /devices/import` — Import dari file Excel/CSV (Admin only)
  - Validasi format kolom
  - Skip baris duplikat (berdasarkan MAC atau IP)
  - Tampilkan ringkasan hasil import (berhasil: X, gagal: Y, duplikat: Z)
- [x] **[DEV-8]** `GET /devices/export` — Export ke CSV (Admin & Viewer)
- [x] **[DEV-9]** Buat templates: `devices/list.html`, `devices/detail.html`, `devices/form.html`
- [x] **[DEV-10]** Service `services/ip_service.py` / Router: validasi IP dua arah saat create/edit (autofill seksi & dynamic select list)

---

### 🌐 IP Address Management (IPAM)

- [x] **[IPAM-1]** Buat router `routers/ipam.py`
- [x] **[IPAM-2]** `GET /ipam` — Halaman utama IPAM, pilih seksi
- [x] **[IPAM-3]** `GET /ipam/{seksi_id}` — IP Grid: tampilkan setiap IP dalam range sebagai kotak berwarna
  - Hijau = Used | Abu = Free | Kuning = Reserved | Merah = Conflict
- [x] **[IPAM-4]** `POST /ipam/reserve` — Reservasi IP untuk perangkat/pegawai (Admin only)
- [x] **[IPAM-5]** `POST /ipam/unreserve` — Bebaskan IP reservasi (Admin only)
- [x] **[IPAM-6]** Seed data / Alokasi `ip_pool` per seksi (`POST /ipam/allocate`)
- [x] **[IPAM-7]** Buat template `templates/ipam/index.html` (grid IP visual, legend warna, modal interaktif)

---

### 📡 Monitoring Real-Time (Ping Scheduler)

- [x] **[PING-1]** Buat `services/ping_service.py`
  - Fungsi async `ping_ip(ip)` → return `(is_online, response_time_ms)`
  - Fungsi `run_ping_scan()` → ping semua devices secara paralel (asyncio.gather, batch 50)
- [x] **[PING-2]** Cross-platform: gunakan ICMP subprocess/socket ping (Windows & Linux compatible)
- [x] **[PING-3]** Register APScheduler job di `main.py` startup: `run_ping_scan` tiap 3 menit (dapat dikonfigurasi)
- [x] **[PING-4]** Setelah scan: update `devices.status`, `devices.last_seen`, insert `scan_logs`
- [x] **[PING-5]** Deteksi & notifikasi: perangkat baru offline, insert `notifications`
- [x] **[PING-6]** Endpoint `GET /api/v1/status` + `POST /api/v1/status/scan` (pemindaian otomatis & manual trigger dari UI)

---

### 👥 Manajemen Pegawai

- [x] **[EMP-1]** Buat router `routers/employees.py`
- [x] **[EMP-2]** `GET /employees` — Daftar pegawai + perangkat yang dimiliki
- [x] **[EMP-3]** `GET /employees/{id}` — Detail pegawai + semua perangkat + riwayat kepemilikan
- [x] **[EMP-4]** Buat template `templates/employees/index.html`, `employees/detail.html`

---

### 🗺️ Topografi Jaringan

- [x] **[TOPO-1]** Buat router `routers/topology.py`
- [x] **[TOPO-2]** `GET /topology` — Halaman diagram (render template)
- [x] **[TOPO-3]** `GET /api/v1/topology/data` — Return nodes + edges dalam format JSON untuk vis-network
- [x] **[TOPO-4]** `PUT /api/v1/topology/nodes/{id}/position` — Simpan posisi X,Y setelah drag
- [x] **[TOPO-5]** `POST /api/v1/topology/edges` + `DELETE /api/v1/topology/edges/{id}` — Kelola koneksi (Admin)
- [x] **[TOPO-6]** Buat template `templates/topology/index.html`
  - Load vis-network.min.js
  - Definisikan icon per device_type (SVG atau Font Awesome)
  - Warna node: hijau=online, merah=offline, abu=unknown
  - Popup detail saat klik node
  - Konteks menu kanan untuk tambah/hapus edge (Admin only)

---

### 🔌 PowerShell Collector Script

- [x] **[PS-1]** Buat `scripts/collect_and_push.ps1`
  - Parameter input: SERVER_URL, TARGET_IP, SUBNET, GATEWAY, DNS1, DNS2, SEKSI, PEGAWAI_ID
  - Step 1: Set IP statik via `netsh`
  - Step 2: Kumpulkan data via WMI (MAC, hostname, CPU, RAM, Storage, OS)
  - Step 3: POST ke `{SERVER_URL}/api/v1/devices/register` dengan token autentikasi
  - Error handling & output yang informatif
- [x] **[PS-2]** Buat `scripts/collect_and_push.bat` — Wrapper BAT agar mudah dijalankan (double-click as Admin)
- [x] **[PS-3]** Buat API endpoint `POST /api/v1/devices/register` di `routers/api/v1/devices.py`
  - Validasi `X-Script-Token` header
  - Upsert device berdasarkan MAC address (insert jika baru, update jika sudah ada)
  - Simpan specs ke `device_specs`
  - Update `ip_pool` (tandai IP sebagai Used)
- [x] **[PS-4]** Buat halaman panduan script di aplikasi: `/docs/script-guide` — instruksi cara jalankan

---

## FASE 2: Fitur Lengkap (Target: Hari 4–5)

### 🔔 Sistem Notifikasi In-App

- [x] **[NOTIF-1]** Bell icon di navbar dengan badge jumlah notifikasi belum dibaca
- [x] **[NOTIF-2]** `GET /api/v1/notifications` — Ambil notifikasi terbaru (AJAX polling tiap 30 detik)
- [x] **[NOTIF-3]** `POST /api/v1/notifications/{id}/read` — Tandai satu notifikasi sebagai dibaca
- [x] **[NOTIF-4]** `POST /api/v1/notifications/read-all` — Tandai semua dibaca
- [x] **[NOTIF-5]** Halaman `/notifications` — Daftar semua notifikasi historis

---

### 📋 Laporan & Export

- [x] ~~**[RPT-1]** Halaman `/reports` — menu pilihan laporan~~ (Dibatalkan)
- [x] **[RPT-2]** Export: Inventaris lengkap semua perangkat (CSV) terintegrasi ke `/devices`
- [x] ~~**[RPT-3]** Export: Daftar IP assignment per seksi (CSV)~~ (Dibatalkan)
- [x] ~~**[RPT-4]** Export: Daftar kepemilikan perangkat per pegawai (CSV)~~ (Dibatalkan)
- [x] ~~**[RPT-5]** Export: Riwayat perpindahan kepemilikan (CSV)~~ (Dibatalkan)

---

### ⚙️ Konfigurasi Admin

- [x] **[CFG-1]** Halaman `/admin/settings` — konfigurasi sistem
- [x] **[CFG-2]** Konfigurasi IP Range per seksi (mapping nama seksi ke range IP awal-akhir)
- [x] **[CFG-3]** Konfigurasi ping interval (default: 3 menit)
- [x] **[CFG-4]** Konfigurasi SCRIPT_API_TOKEN (untuk regenerasi token jika bocor)
- [x] **[CFG-5]** Tampilkan log scan terakhir (waktu, jumlah device, berhasil/gagal)

---

### 🔍 Scan Unknown Device

- [x] **[SCAN-1]** Fitur scan subnet: ping range IP dan deteksi MAC via ARP untuk IP yang merespon tapi belum terdaftar
- [x] **[SCAN-2]** Tampilkan daftar "Unknown Device" di halaman khusus dengan opsi "Tambahkan ke inventory"
- [x] **[SCAN-3]** Trigger scan manual via tombol di halaman IPAM atau Dashboard

---

### 🎨 Polish & UX

- [x] **[UX-1]** Refaktor Komponen UI Reusable (Jinja2 Macros: Navbar, Modal, Button, Form, Status)
- [x] **[UX-2]** Toast/snackbar notification melayang untuk feedback aksi (berhasil/gagal)
- [x] **[UX-3]** Konfirmasi modal untuk aksi destructive (hapus perangkat, bebaskan IP)
- [x] **[UX-4]** Responsive layout untuk tampilan mobile
- [x] **[UX-5]** Navigasi instan layaknya Livewire (HTMX Boost + top progress loading bar)
- [x] **[UX-6]** Breadcrumb / tombol kembali kontekstual (IPAM <-> Perangkat)
- [x] **[UX-7]** Empty state & styling grid box IPAM (size + 20%)

---

## DEPLOYMENT

- [x] **[DEPLOY-1]** Test lengkap di Laragon (Windows 11)
- [x] **[DEPLOY-2]** Buat `Dockerfile` untuk containerisasi
- [x] **[DEPLOY-3]** Buat `docker-compose.yml` (app + optional MySQL jika tidak shared)
- [x] **[DEPLOY-4]** Dokumentasi deployment ke 1Panel (Nginx config, env vars, startup)
- [x] **[DEPLOY-5]** Buat script migrasi database untuk environment production

---

## FASE 3: Optimasi & Perbaikan Tampilan Mobile (Responsive UI/UX)

### 📱 Header & Mobile Navigation Drawer
- [x] **[MOB-NAV-1]** Tambahkan tombol Hamburger di `templates/components/navbar.html` untuk tampilan layar `lg:hidden`
- [x] **[MOB-NAV-2]** Buat Mobile Drawer Slide-Over Menu (back-drop shadow, animasi slide, profil user, unread notif badge, dan daftar menu lengkap)
- [x] **[MOB-NAV-3]** Integrasikan event listener JavaScript untuk membuka/menutup drawer (klik hamburger, klik backdrop, tekan ESC, dan otomatis tutup saat HTMX navigate)

---

### 📱 Responsive Mobile Card View pada Tabel Data
- [x] **[MOB-DEV-1]** Buat tampilan Kartu Perangkat Responsive (`block md:hidden`) di `templates/devices/list.html` untuk menggantikan tabel horizontal di HP
- [x] **[MOB-DEV-2]** Tampilkan detail ringkas pada kartu: Hostname, Tipe Icon, Status Badge, IP & MAC Address, Seksi/Lokasi, Pemilik, dan Tombol Aksi Cepat
- [x] **[MOB-DEV-3]** Tata ulang form filter & search di mobile agar dapat tersusun secara kaskade/stacked tanpa memakan ruang berlebih

---

### 📱 Optimalisasi Grid IPAM & Modal Sentuh
- [x] **[MOB-IPAM-1]** Ubah grid IP di `templates/ipam/index.html` menjadi `grid-cols-4 sm:grid-cols-6 md:grid-cols-12 lg:grid-cols-16` untuk memperbesar touch target IP di HP
- [x] **[MOB-IPAM-2]** Sesuaikan padding sel IP (`h-11 w-full`) agar nyaman ditekan dengan jari (minimum touch target 44px)
- [x] **[MOB-IPAM-3]** Rapikan badge Legend IPAM pada tampilan HP agar tidak bertumpukan
- [x] **[MOB-IPAM-4]** Tata ulang tombol aksi modal IP (`ipModal`) menjadi vertikal full-width di HP (`flex-col-reverse sm:flex-row-reverse`)

---

### 📱 Peta Topologi & Kontrol Sentuh
- [x] **[MOB-TOPO-1]** Sesuaikan tinggi kanvas topologi di `templates/topology/index.html` untuk mobile (`calc(100vh - 280px)`, min-height 380px)
- [x] **[MOB-TOPO-2]** Tambahkan Floating Action Button (FAB) kontrol: Reset View & Fit Zoom di atas kanvas topologi
- [x] **[MOB-TOPO-3]** Ubah sidebar daftar koneksi di HP menjadi collapsible sheet / modal toggleable agar tidak menghabiskan ruang vertikal

---

### 📱 Pencegahan iOS Auto-Zoom & Form/Modal Mobile Polish
- [x] **[MOB-FORM-1]** Ubah `font-size` input form dari `text-sm` (14px) menjadi `text-base md:text-sm` (16px di mobile) pada `components/modal.html`, `auth/login.html`, dan `employees/index.html` untuk cegah auto-zoom Safari iOS
- [x] **[MOB-FORM-2]** Sesuaikan posisi Toast Notification (`#toast-notification`) di `templates/base.html` agar muncul di bagian bawah layar HP (`bottom-4 left-4 right-4 sm:top-20 sm:right-5 sm:left-auto`)
- [x] **[MOB-FORM-3]** Sesuaikan grid 2-kolom (`grid-cols-2 lg:grid-cols-4`) untuk Stat Cards pada `templates/dashboard/index.html` di layar mobile

---

## Urutan Prioritas Pengerjaan (Disarankan)

```
Hari 1:  SETUP-1 s/d SETUP-9 → AUTH-1 s/d AUTH-6 → DASH-1 s/d DASH-6
Hari 2:  DEV-1 s/d DEV-10 → IPAM-1 s/d IPAM-7 → PS-1 s/d PS-4
Hari 3:  PING-1 s/d PING-6 → EMP-1 s/d EMP-4 → TOPO-1 s/d TOPO-6
Hari 4:  NOTIF-1 s/d NOTIF-5 → RPT-1 s/d RPT-5 → CFG-1 s/d CFG-5
Hari 5:  SCAN-1 s/d SCAN-3 → UX-1 s/d UX-7 → DEPLOY-1 s/d DEPLOY-5
Mobile:  MOB-NAV-1..3 → MOB-DEV-1..3 → MOB-IPAM-1..4 → MOB-TOPO-1..3 → MOB-FORM-1..3
```
