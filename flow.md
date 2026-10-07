# FLOW — IP Radar: Application & Data Flow

## 1. Arsitektur Aplikasi

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT BROWSER                        │
│              (Admin / Viewer — Chrome/Edge)              │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / SSE (polling)
                        ▼
┌─────────────────────────────────────────────────────────┐
│              FASTAPI APPLICATION SERVER                  │
│                (uvicorn, port 8000)                      │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Routers    │  │  Services    │  │  Schedulers   │  │
│  │ (endpoints) │  │ (biz logic)  │  │ (APScheduler) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         └────────────────┼──────────────────┘           │
│                          ▼                              │
│              ┌──────────────────────┐                   │
│              │  SQLAlchemy ORM      │                   │
│              │  (models + queries)  │                   │
│              └──────────┬───────────┘                   │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              MySQL DATABASE (db_aplikasi)                │
│   [users][devices][device_specs][ip_pool]               │
│   [device_history][notifications][topology_edges]        │
│   [scan_logs]                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│         CLIENT MACHINES (Windows 10/11 Pegawai)          │
│                                                          │
│   Jalankan: collect_and_push.ps1 (manual by admin)       │
│   → Set IP/Gateway/DNS                                   │
│   → Kumpulkan hardware info (WMI)                        │
│   → POST /api/v1/devices/register ke FastAPI server      │
└─────────────────────────────────────────────────────────┘
```

---

## 2. User Flow — Login & Autentikasi

```
[User buka browser] → GET /login
        │
        ▼
[Tampil form login: username + password]
        │
        ▼
[POST /auth/login]
        │
   ┌────┴────┐
   │ Validasi │ → cek tabel users di db_aplikasi
   └────┬────┘
        │
  ┌─────┴──────┐
  │            │
[Berhasil]   [Gagal]
  │            │
  ▼            ▼
[Set cookie  [Tampil pesan
 session]    error, kembali
  │          ke form]
  ▼
[Cek role: Administrator / Viewer]
  │
  ├── Administrator → Redirect ke /dashboard (full access)
  └── Viewer       → Redirect ke /dashboard (read-only, semua tombol aksi disembunyikan)
```

---

## 3. Flow — Dashboard

```
GET /dashboard
        │
        ▼
[Query DB: hitung total devices, online, offline, unknown]
[Query DB: hitung IP free/used/reserved per seksi]
[Query DB: ambil 5 notifikasi/alert terbaru]
        │
        ▼
[Render dashboard.html via Jinja2]
        │
        ├── Widget: Total Devices (PC: X, Laptop: X, Printer: X, dll)
        ├── Widget: Status Bar (Online: X | Offline: X | Unknown: X)
        ├── Widget: IP Usage per Seksi (progress bar per seksi)
        ├── Tabel: Alert terbaru (IP konflik, perangkat down)
        └── [Auto-refresh via JS polling tiap 30 detik ke GET /api/v1/dashboard/stats]
```

---

## 4. Flow — PowerShell Data Collector (Script di Komputer Pegawai)

```
[Admin buka komputer pegawai]
        │
        ▼
[Admin jalankan: collect_and_push.ps1 as Administrator]
        │
        ▼
[Script: Baca parameter dari file config atau input prompt]
  → SERVER_URL = "http://10.x.x.x:8000"
  → TARGET_IP  = "10.12.13.25"
  → GATEWAY    = "10.12.13.1"
  → DNS        = "10.x.x.x"
  → SEKSI      = "Pelayanan"
        │
        ▼
[Step 1: Set Network Configuration]
  → netsh interface ip set address [NIC] static [IP] [Mask] [Gateway]
  → netsh interface ip set dns [NIC] static [DNS]
        │
        ▼
[Step 2: Ambil Data Hardware via WMI/PowerShell]
  → MAC Address    : Get-NetAdapter | Select-Object MacAddress
  → Hostname       : $env:COMPUTERNAME
  → CPU Brand/Model: Get-WmiObject Win32_Processor
  → RAM Total/Type : Get-WmiObject Win32_PhysicalMemory
  → Storage        : Get-WmiObject Win32_DiskDrive
  → OS Version     : Get-WmiObject Win32_OperatingSystem
        │
        ▼
[Step 3: Kirim data ke server via HTTP POST]
  → POST http://SERVER_URL/api/v1/devices/register
  → Body: JSON {hostname, ip, mac, seksi, specs: {...}}
  → Header: X-Script-Token: [secret_token]
        │
   ┌────┴────┐
   │ Response │
   └────┬────┘
        │
  ┌─────┴──────┐
  │            │
[200 OK]    [Error]
  │            │
  ▼            ▼
[Print: "IP   [Print: "GAGAL:
 berhasil      [error message]"
 dikonfigurasi  Catat di log.txt]
 & data
 terkirim!"]
```

---

## 5. Flow — Background Ping Scheduler

```
[APScheduler: job tiap 3 menit]
        │
        ▼
[Query DB: ambil semua devices dengan ip_address != null]
        │
        ▼
[Bagi menjadi batch (50 IP paralel menggunakan asyncio)]
        │
        ▼
[Untuk setiap IP: kirim ICMP ping (icmplib/ping3)]
        │
   ┌────┴────┐
   │ Hasil   │
   └────┬────┘
        │
  ┌─────┴──────┐
  │            │
[Reply OK]   [Timeout/No reply]
  │            │
  ▼            ▼
[Update DB:  [Update DB:
 is_online=1  is_online=0
 last_seen=   ]
 now()]       │
  │           ▼
  │     [Cek: apakah sebelumnya is_online=1?]
  │           │
  │     [Ya → buat notifikasi "Perangkat [hostname] offline"]
  │
  ▼
[Insert scan_log: {ip, is_online, scanned_at, response_time_ms}]
        │
        ▼
[Cek IP konflik: ada 2+ devices dengan ip_address sama?]
  → Jika ya: buat notifikasi "IP konflik terdeteksi: [IP]"
        │
        ▼
[Selesai, tunggu interval berikutnya]
```

---

## 6. Flow — Manajemen Perangkat (Device CRUD)

```
GET /devices → [Daftar semua perangkat dengan filter & pagination]
        │
        ├── Filter: seksi, device_type, status, search hostname/IP
        ├── Klik baris → GET /devices/{id} → detail perangkat + specs + history kepemilikan
        │
        ├── [Admin] Tombol "Tambah Manual" → GET /devices/create
        │                                    POST /devices/create
        │                                    → Validasi IP (sudah dipakai? di luar range?)
        │                                    → Insert ke devices & ip_pool
        │
        ├── [Admin] Tombol "Edit" → GET /devices/{id}/edit
        │                           PUT /devices/{id}
        │
        ├── [Admin] Tombol "Assign Pemilik" → Modal: pilih pegawai
        │                                    POST /devices/{id}/assign
        │                                    → Update devices.user_id
        │                                    → Insert device_history
        │
        ├── [Admin] Tombol "Import CSV" → Upload file Excel/CSV
        │                                 POST /devices/import
        │                                 → Parse & validasi baris per baris
        │                                 → Insert valid, skip duplikat (laporan hasil)
        │
        └── [Admin] Tombol "Export CSV" → GET /devices/export?format=csv
                                          → Generate file & download
```

---

## 7. Flow — IP Address Management (IPAM)

```
GET /ipam → [Pilih seksi]
        │
        ▼
[Render IP Grid: setiap IP dalam range seksi ditampilkan sebagai kotak]
  → Hijau  = Used (klik → detail perangkat)
  → Abu-abu = Free (klik → form reservasi cepat)
  → Kuning = Reserved (klik → info reservasi)
  → Merah  = Conflict (klik → lihat perangkat yang konflik)
        │
        ├── [Admin] Tombol "Reservasi IP" → POST /ipam/reserve
        │
        ├── [Admin] Tombol "Bebaskan IP" → POST /ipam/release
        │
        └── Notifikasi merah jika ada perangkat IP di luar range seksinya
```

---

## 8. Flow — Network Topology

```
GET /topology
        │
        ▼
[Query DB: semua devices + topology_edges]
        │
        ▼
[Render topology.html]
  → Load vis-network library (JS)
  → Inisialisasi nodes dari data devices (icon per tipe, warna per status)
  → Inisialisasi edges dari topology_edges
        │
        ▼
[User interaksi:]
  ├── Drag node → posisi tersimpan otomatis via PUT /api/v1/topology/nodes/{id}/position
  ├── Klik node → tampil popup: hostname, IP, status, pemilik, seksi
  ├── [Admin] Klik kanan node → menu: Tambah koneksi, Hapus koneksi
  ├── [Admin] POST /api/v1/topology/edges → tambah edge baru
  └── [Admin] DELETE /api/v1/topology/edges/{id} → hapus edge
```

---

## 9. Deployment Flow

### Development (Laragon — Windows 11)

```
[Laragon running MySQL]
        │
[Buat virtual environment Python]
  → python -m venv .venv
  → .venv\Scripts\activate
  → pip install fastapi uvicorn sqlalchemy pymysql alembic apscheduler jinja2 icmplib
        │
[Jalankan FastAPI]
  → uvicorn main:app --reload --host 0.0.0.0 --port 8000
        │
[Akses via browser: http://localhost:8000]
```

### Production (1Panel — Debian/Proxmox)

```
[Push kode ke GitHub/GitLab]
        │
[1Panel: buat environment Python / Docker container]
  → docker build -t ipradar .
  → docker run -d -p 8000:8000 --env-file .env ipradar
        │
[1Panel: setup Nginx reverse proxy]
  → http://ipradar.internal → proxy_pass http://localhost:8000
        │
[Database: gunakan MySQL yang sudah ada di 1Panel]
  → Update .env: DATABASE_URL=mysql+pymysql://user:pass@localhost/db_aplikasi
```

---

## 10. Struktur Folder Proyek

```
ipradar/
├── main.py                    # Entry point FastAPI
├── config.py                  # Settings (DB URL, secret, interval)
├── database.py                # SQLAlchemy engine & session
├── models/                    # SQLAlchemy models
│   ├── device.py
│   ├── user.py
│   ├── ip_pool.py
│   ├── topology.py
│   └── notification.py
├── routers/                   # FastAPI routers (endpoint handlers)
│   ├── auth.py
│   ├── dashboard.py
│   ├── devices.py
│   ├── ipam.py
│   ├── topology.py
│   ├── employees.py
│   └── api/                   # API endpoints (untuk script & AJAX)
│       └── v1/
│           ├── devices.py     # POST /register (dari PowerShell)
│           ├── status.py      # GET status real-time
│           └── topology.py
├── services/                  # Business logic
│   ├── ping_service.py        # ICMP ping & scheduler
│   ├── ip_service.py          # Validasi & manajemen IP
│   └── import_service.py      # Import CSV/Excel
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Layout utama (navbar, sidebar)
│   ├── auth/
│   │   └── login.html
│   ├── dashboard/
│   │   └── index.html
│   ├── devices/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html
│   ├── ipam/
│   │   └── index.html
│   ├── topology/
│   │   └── index.html
│   └── employees/
│       └── index.html
├── static/                    # CSS, JS, images
│   ├── css/
│   │   └── tailwind.min.css
│   ├── js/
│   │   ├── vis-network.min.js
│   │   └── app.js
│   └── icons/                 # Icon per tipe perangkat
├── scripts/                   # PowerShell scripts untuk client
│   ├── collect_and_push.ps1
│   └── collect_and_push.bat   # Wrapper BAT untuk easy run
├── alembic/                   # Database migrations
│   └── versions/
├── .env                       # Environment variables (tidak di-commit)
├── requirements.txt
└── Dockerfile
```
