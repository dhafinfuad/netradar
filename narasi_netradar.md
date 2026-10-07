**NETRADAR**  
Sistem Informasi Manajemen Aset Jaringan & IPAM Terpadu: Monitoring Real-Time, Pemetaan Topologi Jaringan Interaktif, Audit Spesifikasi Hardware Otomatis, & Tata Kelola Kepemilikan Perangkat.

Python 3.11  
FastAPI  
SQLAlchemy  
Tailwind CSS  
Jinja2  
vis-network  
APScheduler  
SSE Real-Time  
PowerShell WMI  
MySQL  
Docker  

### STUDI KASUS ARSITEKTUR
**NetRadar — Ekosistem Manajemen Aset Jaringan, IPAM Terstruktur, & Monitoring Real-Time**  
✕   

#### Latar Belakang
Sebelum sistem NetRadar dibangun, pengelolaan infrastruktur jaringan dan inventaris perangkat TI di lingkungan KPP Madya Malang masih mengandalkan pencatatan terpisah pada lembar kerja spreadsheet manual serta pemindaian sewaktu-waktu menggunakan *Advanced IP Scanner* dan *ESMC*. Pendekatan konvensional ini kerap memicu berbagai kendala operasional: penetapan alamat IP yang tersebar acak tanpa alokasi subnet terstandar per seksi, tingginya frekuensi konflik IP (*IP conflict*) yang mengganggu kelancaran koneksi kerja pegawai, ketiadaan data kepemilikan perangkat yang menghubungkan alamat fisik/MAC dengan identitas pegawai penanggung jawab, serta lambatnya identifikasi perangkat asing (*rogue/unknown devices*) yang menyusup ke intranet kantor. Selain itu, inventarisasi spesifikasi fisik komputer dinas (CPU, RAM, tipe storage SSD/HDD) harus diperiksa secara manual satu per satu dari meja ke meja.

Sistem NetRadar dirancang sebagai *single source of truth* (sumber kebenaran tunggal) untuk mengotomatisasi pengawasan dan tata kelola aset jaringan kantor ke dalam satu ekosistem berbasis web terpusat. Aplikasi ini menggabungkan mesin pemindaian *asynchronous* otomatis berbasis ICMP/ARP, visualisasi matriks IPAM (*IP Address Management*) interaktif, diagram topologi jaringan visual, hingga skrip otomasi ekstraksi spesifikasi hardware via PowerShell WMI.

---

#### Cakupan 4 Modul Utama Aplikasi

**1. Manajemen Alokasi & IPAM Terstruktur (IP Address Management)**  
**IP RADAR**  
Tata kelola penetapan IP Address berbasis kuota dan segmentasi subnet per seksi (11–20 unit kerja). Dilengkapi visualisasi matriks *grid* warna-warni yang intuitif untuk mengidentifikasi status setiap IP secara instan (Hijau: Tersedia/Free, Merah: Digunakan/Used, Kuning: Direservasi/Reserved, dan Oranye: Terindikasi Konflik/Conflict). Memiliki sistem validasi ketat yang otomatis memblokir atau memperingatkan penetapan IP di luar rentang subnet seksi, fitur pemesanan (*reservasi*) IP sebelum perangkat terpasang fisik, modal inspeksi detail pemegang IP, serta fasilitas ekspor rekapitulasi ke format spreadsheet terstandar.

**2. Pemantauan Jaringan Real-Time & Radar Perangkat Liar (Rogue Scanner)**  
**MONITORING & SCANNER**  
Pusat pengawasan konektivitas jaringan kantor yang beroperasi tanpa henti. Memanfaatkan *background scheduler* cerdas (APScheduler + icmplib) yang mengeksekusi pemindaian *ping asynchronous* ke ratusan perangkat setiap 3 menit secara paralel tanpa membebani lalu lintas data lokal. Setiap perubahan status (Online/Offline) dan perangkat asing baru yang tidak terdaftar (*unknown/rogue devices*) langsung diidentifikasi secara otomatis. Informasi mutakhir disiarkan secara langsung (*live streaming*) ke dasbor eksekutif dan bilah notifikasi menggunakan protokol *Server-Sent Events* (SSE) tanpa memerlukan muat ulang (*reload*) halaman.

**3. Inventaris Aset Digital & Audit Spesifikasi Otomatis**  
**DEVICE INVENTORY & COLLECTOR**  
Basis data aset perangkat keras kantor yang komprehensif (PC Desktop, Laptop, Printer, Router, Switch, Akses Poin, dan Perangkat IoT). Mengintegrasikan skrip otomasi klien berbasis PowerShell (`.ps1`) yang dapat dieksekusi administrator untuk secara otomatis membaca spesifikasi jeroan komputer target melalui WMI query (Merk & Model CPU, Kapasitas & Tipe RAM, Jenis Penyimpanan SSD/HDD, Versi OS, hingga Alamat Fisik/MAC) dan mengonfigurasi IP perangkat secara otomatis. Dilengkapi modul manajemen kepemilikan pegawai, riwayat mutasi aset (*audit trail* perpindahan pemegang barang), serta impor dan ekspor massal data perangkat berbasis berkas CSV/Excel.

**4. Pemetaan Graf Topologi Jaringan Visual Interaktif**  
**TOPOLOGI JARINGAN**  
Visualisasi arsitektur interkoneksi jaringan kantor secara visual berbasis graf dinamis (*vis-network*). Memetakan jalur relasi perangkat mulai dari Gateway Utama, Switch Distribusi per lantai/ruangan, hingga ke node perangkat pengguna akhir (*end-user devices*). Dilengkapi indikator status warna dinamis (Hijau: Aktif, Merah: Terputus/Mati, Abu-abu: Tidak Diketahui), fitur tata letak interaktif *drag-and-drop* dengan penyimpanan otomatis koordinat posisi di database, modal penambahan/pemutusan relasi koneksi antar-perangkat, serta panel inspeksi detail perangkat saat node diklik.

---

#### Spesifikasi Rekayasa & Tata Kelola Keamanan

* **High-Performance Asynchronous Python Stack & Live SSE Streaming**  
  Dibangun menggunakan arsitektur modern Python 3.11 dan **FastAPI** (ASGI) yang terkenal sangat cepat dan efisien dalam menangani operasi I/O jaringan non-blocking. Dipadukan dengan *engine* template server-side rendering **Jinja2**, utilitas tata letak modern **Tailwind CSS**, dan *asynchronous background workers* (**APScheduler**). Pembaruan status perangkat dan peringatan bahaya diantarkan secara *real-time* ke peramban pengguna menggunakan protokol hemat daya **Server-Sent Events** (SSE) berlatensi rendah.

* **Single Source of Truth, RBAC, & Shared Database Integration**  
  Terintegrasi mulus dengan basis data terpadu (`db_aplikasi`), menyelaraskan otentikasi aman pengguna berbasis **NIP Pendek** (9 digit) dan pemetaan seksi organisasi internal. Menerapkan kontrol akses berbasis peran (*Role-Based Access Control* / RBAC) yang ketat: hak akses penuh (*Full CRUD*, eksekusi scanning, konfigurasi IP pool, dan mutasi aset) bagi Administrator Seksi Penjaminan Kualitas Data, serta mode peninjauan (*Read-Only*) bagi staf seksi lain demi menjaga integritas data infrastruktur.

* **Agentless WMI Telemetry & Isolated Containerized Deployment**  
  Mengimplementasikan pendekatan audit perangkat keras semi-otomatis melalui skrip **PowerShell Core WMI** tanpa perlu menginstal aplikasi agen pihak ketiga yang memberatkan komputer dinas pegawai. Seluruh ekosistem aplikasi diorkestrasikan ke dalam kontainer terisolasi **Docker** dan **Docker Compose**, menjamin konsistensi lingkungan *deployment*, efisiensi sumber daya server, serta kemudahan pemeliharaan berkala di lingkungan server internal berbasis **1Panel / Linux Debian**.
