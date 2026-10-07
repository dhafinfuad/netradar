# PRD — IP Radar: Network Asset & IP Management System

## 1. Ringkasan Eksekutif

**IP Radar** adalah aplikasi manajemen aset jaringan dan IP terpusat yang dibangun di atas stack **FastAPI + Jinja2 + Tailwind CSS + MySQL**. Aplikasi ini menggantikan proses manual menggunakan Advanced IP Scanner dan ESMC, dengan memberikan visibilitas penuh terhadap seluruh perangkat jaringan, manajemen IP terstruktur per seksi, monitoring status real-time, dan inventaris hardware yang lengkap.

---

## 2. Latar Belakang & Masalah

| Masalah | Dampak |
|---|---|
| IP tersebar acak tanpa standar per seksi | Sulit ditelusuri, konflik IP sering terjadi |
| Tidak ada data kepemilikan perangkat | Sulit pertanggungjawaban aset |
| Harus scan manual dengan Advanced IP Scanner | Tidak real-time, tidak terintegrasi |
| Tidak ada inventaris hardware terpusat | Tidak ada gambaran kondisi aset IT |
| Tidak bisa tahu perangkat mana yang kena virus tanpa ESMC | Respons lambat terhadap insiden |

---

## 3. Tujuan Produk

1. **Visibilitas Real-Time**: Mengetahui status (aktif/mati) seluruh ~250 perangkat jaringan setiap 1–5 menit secara otomatis.
2. **Manajemen IP Terstruktur**: Mengelola, mereservasi, dan memvalidasi IP per seksi (11–20 seksi).
3. **Inventaris Aset Digital**: Menyimpan data lengkap hardware (CPU, RAM, Storage, MAC Address) yang dikumpulkan via script PowerShell.
4. **Kepemilikan Perangkat**: Menghubungkan setiap perangkat ke pegawai pemiliknya.
5. **Topografi Jaringan Visual**: Menampilkan diagram jaringan interaktif (drag & drop).
6. **Satu Sumber Kebenaran**: Menggantikan spreadsheet, Advanced IP Scanner, dan ESMC sebagai referensi utama kondisi jaringan.

---

## 4. Pengguna & Peran

| Peran | Akses | Keterangan |
|---|---|---|
| **Administrator** | Full CRUD + Aksi | Seluruh pegawai Seksi Penjaminan Kualitas Data |
| **Viewer** | Read-Only | Pegawai seksi lain, hanya dapat melihat data tanpa tombol aksi apapun |

> **Catatan**: Data pengguna diambil dari tabel `users` di database `db_aplikasi` yang sudah ada (shared database dengan aplikasi Laravel).

---

## 5. Ruang Lingkup — Fase 1 (MVP: Hari 1–3)

### 5.1 Modul Dashboard
- Statistik ringkasan: total perangkat, jumlah aktif, jumlah mati, IP kosong per seksi
- Grafik donut: distribusi perangkat per tipe (PC, Laptop, Printer, dll)
- Daftar alert terbaru (IP konflik, perangkat yang tiba-tiba down)
- Widget IP Pool: bar usage per seksi

### 5.2 Modul Manajemen Perangkat (Device Inventory)
- Daftar seluruh perangkat dengan filter: seksi, tipe, status, pemilik
- Detail perangkat: MAC, IP, hostname, merk/model, spesifikasi CPU/RAM/Storage
- Status badge real-time (Online/Offline/Unknown)
- CRUD manual untuk menambah/edit/hapus perangkat
- Import perangkat dari file Excel/CSV
- Export data ke Excel/CSV

### 5.3 Modul IP Address Management (IPAM)
- Tabel IP Pool per seksi: tampilkan setiap IP dalam range, statusnya (Used/Free/Reserved/Conflict)
- Reservasi IP untuk perangkat/pegawai tertentu
- Deteksi otomatis IP konflik (dua perangkat dengan IP sama)
- Validasi: tandai perangkat yang IP-nya di luar range seksinya

### 5.4 Modul Monitoring Real-Time
- Background scheduler (APScheduler) melakukan ping ke semua IP terdaftar tiap 3 menit
- Update status last_seen dan is_online di database
- WebSocket atau auto-refresh halaman (polling tiap 30 detik di frontend)
- History uptime sederhana (kapan terakhir online/offline)

### 5.5 PowerShell Data Collector Script
- Script `.ps1` / `.bat` yang dijalankan admin secara manual di komputer target
- Fungsi: set IP/Gateway/DNS sesuai konfigurasi yang dikirim dari server
- Fungsi: kumpulkan data (MAC, CPU, RAM, Storage, Hostname) dan kirim via HTTP POST ke API server
- Output: konfirmasi berhasil/gagal di console
- Dapat dijalankan as Administrator

### 5.6 Modul Manajemen Pegawai
- Daftar pegawai dengan seksi dan perangkat yang dimiliki
- Assign/reassign perangkat ke pegawai
- Riwayat perpindahan kepemilikan perangkat (audit trail)

### 5.7 Modul Topografi Jaringan
- Diagram visual interaktif menggunakan library JavaScript (vis-network atau GoJS)
- Node: Switch, Router, Komputer, Laptop, Printer, Hub, dll (dengan icon berbeda per tipe)
- Edge/garis: representasi koneksi antar perangkat
- Warna node berdasarkan status (hijau=online, merah=offline, abu=unknown)
- Drag & drop posisi node, posisi tersimpan di database
- Klik node → popup detail perangkat

---

## 6. Ruang Lingkup — Fase 2 (Hari 4–5, Fitur Lengkap)

- Notifikasi in-app (bell icon) untuk alert: IP konflik, perangkat down, perangkat baru terdeteksi
- Scan via SNMP untuk perangkat jaringan aktif (switch, router, printer)
- Halaman laporan & export (inventaris lengkap, daftar IP, daftar kepemilikan)
- Konfigurasi range IP per seksi (CRUD range)
- Scan otomatis subnet untuk deteksi perangkat baru yang belum terdaftar (unknown device)

---

## 7. Fitur di Luar Cakupan (Out of Scope)

- Integrasi dengan SIMPEG/HRIS eksternal
- Two-Factor Authentication (2FA)
- Multi-tenant / multi-kantor
- Bandwidth monitoring
- Patch management / remote deployment

---

## 8. Pertimbangan Teknologi

### Stack yang Dipilih

| Layer | Teknologi | Alasan |
|---|---|---|
| Backend | **FastAPI** (Python) | Async, cepat, auto docs (Swagger), ideal untuk API + background task |
| Frontend Template | **Jinja2** | Terintegrasi native dengan FastAPI, SSR, tidak perlu JS framework terpisah |
| Styling | **Tailwind CSS v3** | Utility-first, cepat dikembangkan, DaisyUI bisa ditambahkan |
| Database | **MySQL** (shared `db_aplikasi`) | Sudah ada, familiar, tidak perlu migrasi data users |
| ORM | **SQLAlchemy** + Alembic | Standar industri Python, mendukung migrasi schema |
| Background Task | **APScheduler** | Ringan, terintegrasi dengan FastAPI, untuk jadwal ping |
| Real-time | **SSE (Server-Sent Events)** atau polling | SSE lebih ringan dari WebSocket untuk use case ini |
| Network Topology | **vis-network** (JS library) | Open source, kuat, mendukung drag & drop, banyak contoh |
| Ping/Scan | **icmplib** (Windows) → **ping3** atau **subprocess nmap** (Linux) | Cross-platform, akan dikondisikan saat deploy ke Debian |
| Script Client | **PowerShell** `.ps1` | Native Windows, bisa jalankan WMI query untuk hardware info |
| Deployment Dev | **Laragon** (Python via uvicorn) | Mudah untuk dev lokal Windows |
| Deployment Prod | **1Panel** on Debian/Proxmox | Docker container atau systemd service |

### Mengapa FastAPI + Jinja2 vs Alternatif?

- **vs Laravel Livewire**: FastAPI lebih cepat untuk API-first, script PowerShell tinggal POST ke endpoint. Namun tidak bisa share session dengan Laravel yang ada.
- **vs Reflex**: Reflex masih muda (v0.x), kurang stabil untuk produksi. FastAPI lebih battle-tested.
- **vs Next.js**: Memerlukan skill JavaScript yang lebih dalam; FastAPI+Jinja2 tetap full-Python.

> **Catatan Penting**: Karena berbeda stack (FastAPI vs Laravel), sharing session login langsung tidak bisa. Solusi: IP Radar menggunakan tabel `users` yang sama di MySQL (`db_aplikasi`), dengan JWT atau cookie session sendiri.

---

## 9. Model Data (Entities)

```
users           → id, name, nip_pendek, nip, jabatan, seksi, tim, target_kegiatan, email_verified_at, password, remember_token, created_at, updated_at
devices         → id, hostname, ip_address, mac_address, device_type, brand, model, 
                  status, last_seen, user_id (FK), seksi, topology_x, topology_y
device_specs    → id, device_id (FK), cpu_brand, cpu_model, ram_total, ram_type, ram_brand,
                  storage_capacity, storage_type, storage_brand, os_version, collected_at
ip_pool         → id, seksi, ip_address, status (free/used/reserved/conflict), 
                  device_id (FK, nullable), reserved_for, notes
device_history  → id, device_id (FK), from_user_id, to_user_id, changed_at, changed_by, notes
notifications   → id, type, message, is_read, created_at, target_role
topology_edges  → id, from_device_id (FK), to_device_id (FK), label, created_at
scan_logs       → id, ip_address, is_online, scanned_at, response_time_ms
```

---

## 10. Non-Functional Requirements

| Aspek | Target |
|---|---|
| Waktu respons halaman | < 2 detik |
| Interval scan/ping | 3 menit (configurable) |
| Concurrency | 50 perangkat di-ping paralel (async) |
| Skalabilitas | Mendukung hingga 500 perangkat tanpa tuning |
| Browser support | Chrome, Firefox, Edge (modern browser) |
| Responsif | Desktop-first (bisa diakses dari mobile untuk lihat-lihat) |

---

## 11. Kesuksesan Produk

| Metrik | Target |
|---|---|
| Seluruh ~250 perangkat terdaftar | 100% dalam 2 minggu setelah go-live |
| Tidak ada IP konflik | 0 konflik setelah IP dirapi-kan |
| Admin dapat lihat status semua perangkat | Tanpa membuka Advanced IP Scanner |
| Semua komputer pegawai memiliki pemilik | 100% terdata dalam 1 bulan |
