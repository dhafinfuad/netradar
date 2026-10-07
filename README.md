# NetRadar — Network Asset & IPAM Management System

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**NetRadar** adalah sistem informasi manajemen aset jaringan dan *IP Address Management* (IPAM) terpadu berbasis web. Sistem ini dirancang untuk memantau konektivitas jaringan secara *real-time*, memvisualisasikan diagram topologi interaktif, mengaudit spesifikasi *hardware* komputer dinas secara otomatis melalui PowerShell WMI, serta mencegah konflik IP dengan segmentasi subnet per unit kerja.

---

## 🌟 Fitur Unggulan

### 1. Manajemen Alokasi & IPAM Terstruktur (IP Address Management)
* **Visualisasi Matriks Grid IP**: Pemetaan status IP per seksi / divisi dengan kode warna intuitif:
  * 🟢 **Tersedia (Free)**: Siap digunakan untuk perangkat baru.
  * 🔴 **Digunakan (Used)**: Sedang aktif terpasang pada perangkat terdaftar.
  * 🟡 **Direservasi (Reserved)**: Ditandai khusus untuk kebutuhan perangkat mendatang.
  * 🟠 **Konflik (Conflict)**: Peringatan otomatis jika terjadi duplikasi alokasi IP.
* **Validasi Subnet**: Mencegah kesalahan alokasi IP di luar rentang subnet unit kerja terkait.
* **Ekspor Rekapitulasi**: Kemudahan unduh data alokasi IP ke format Excel (`.xlsx`).

### 2. Pemantauan Real-Time & Rogue Device Scanner
* **Background Scanning Terjadwal**: Ditenagai oleh *APScheduler* dan *icmplib* untuk *asynchronous ping* ke seluruh perangkat jaringan setiap beberapa menit tanpa membebani lalu lintas intranet.
* **Deteksi Perangkat Asing (Unknown/Rogue Devices)**: Otomatis mendeteksi perangkat liar yang tersambung ke jaringan lokal namun belum tercatat dalam database inventaris.
* **Live SSE Updates**: Menggunakan protokol *Server-Sent Events* (SSE) untuk menyiarkan status perangkat (*Online/Offline*) dan notifikasi sistem secara langsung ke dashboard tanpa perlu *refresh* halaman.

### 3. Inventaris Aset Digital & Audit Hardware Otomatis
* **Audit Spesifikasi Otomatis**: Integrasi skrip *PowerShell WMI* (`IPRadar_Installer.ps1`) untuk membaca spesifikasi perangkat keras komputer klien (Merk/Model CPU, Kapasitas RAM, Tipe Penyimpanan SSD/HDD, Versi OS, hingga Alamat Fisik/MAC) dan mendaftarkannya secara otomatis.
* **Tata Kelola Kepemilikan & Audit Trail**: Melacak riwayat mutasi perpindahan penanggung jawab perangkat antar pegawai.
* **Impor & Ekspor Massal**: Dukungan pengelolaan data aset perangkat berbasis spreadsheet.

### 4. Diagram Topologi Jaringan Interaktif
* **Pemetaan Visual Berbasis Graf**: Ditenagai oleh pustaka *vis-network* untuk memetakan hubungan hierarki antar-perangkat (Gateway Inti $\rightarrow$ Switch Distribusi $\rightarrow$ Komputer/Printer Klien).
* **Interaksi Drag & Drop**: Penyimpanan posisi node secara otomatis ke database untuk fleksibilitas tata letak.

---

## 📸 Antarmuka Aplikasi (Preview)

| Dashboard Utama & Metrik Real-Time | Manajemen Alokasi IPAM Grid |
| :---: | :---: |
| ![Dashboard](portfolio_screenshots/02_halaman_dashboard.png) | ![IPAM](portfolio_screenshots/06_halaman_ipam_grid.png) |

| Inventaris Perangkat & Status | Pemetaan Topologi Jaringan Interaktif |
| :---: | :---: |
| ![Devices](portfolio_screenshots/03_halaman_devices_list.png) | ![Topology](portfolio_screenshots/09_halaman_topologi_jaringan.png) |

| Radar Perangkat Asing (Rogue Scanner) | Profil & Kartu Aset Pegawai |
| :---: | :---: |
| ![Scanner](portfolio_screenshots/10_halaman_scanner_unknown_devices.png) | ![Employees](portfolio_screenshots/07_halaman_pegawai_cards.png) |

---

## 🛠️ Tech Stack & Arsitektur

* **Backend**: Python 3.11, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn (ASGI)
* **Database & ORM**: MySQL / MariaDB, [SQLAlchemy 2.0](https://www.sqlalchemy.org/), Alembic (Database Migrations)
* **Frontend**: Jinja2 Templates, [Tailwind CSS](https://tailwindcss.com/), [vis-network](https://visjs.github.io/vis-network/standalone/umd/vis-network.min.js), Chart.js
* **Networking & Telemetry**: `icmplib`, `APScheduler`, Server-Sent Events (SSE), PowerShell Core WMI
* **Deployment**: Docker & Docker Compose

---

## 🚀 Panduan Instalasi & Menjalankan

### Prasyarat
* Python 3.11 atau lebih baru
* MySQL Server (atau MariaDB)
* Docker & Docker Compose (opsional, direkomendasikan untuk deployment)

### 1. Kloning Repositori & Persiapan Environment
```bash
git clone https://github.com/username/netradar.git
cd netradar

# Salin template environment
cp .env.example .env
```

Sesuaikan konfigurasi pada file `.env`:
```env
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/db_aplikasi
SECRET_KEY=ganti_dengan_kunci_rahasia_acak
SCRIPT_API_TOKEN=token_skrip_pengumpul_data
PING_INTERVAL_MINUTES=3
```

### 2. Menjalankan secara Lokal

1. **Buat dan aktifkan virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Pasang dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan migrasi database**:
   ```bash
   alembic upgrade head
   ```

4. *(Opsional)* **Isi data dummy untuk pengujian awal**:
   ```bash
   python scripts/seed_dummy.py
   ```

5. **Jalankan server aplikasi**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Buka browser dan akses `http://localhost:8000`.

---

### 3. Menjalankan dengan Docker Compose

Untuk mendeteksi MAC address pada subnet lokal secara optimal, container dijalankan menggunakan mode `network_mode: "host"`:

```bash
docker compose up -d --build
```

---

## 🔒 Tata Kelola Keamanan & Hak Akses (RBAC)

1. **Administrator**: Akses penuh untuk manajemen aset (CRUD perangkat, konfigurasi IP pool, pemetaan topologi, dan pemicu pemindaian manual).
2. **Viewer / Pengguna**: Akses *read-only* untuk memantau status jaringan dan ketersediaan IP tanpa hak manipulasi konfigurasi.

---

## 📄 Lisensi

Proyek ini didistribusikan di bawah lisensi **MIT License**. Silakan gunakan dan sesuaikan untuk kebutuhan organisasi Anda.
