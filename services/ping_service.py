import asyncio
import platform
import re
import datetime
import subprocess
import concurrent.futures

# Dedicated executor untuk proses ping & ARP (subprocess-heavy)
# Dipisah dari db_executor untuk mencegah ThreadPool deadlock:
# tanpa pemisahan, ARP tidak bisa dapat thread karena sudah habis dipakai ping.
ping_executor = concurrent.futures.ThreadPoolExecutor(max_workers=20, thread_name_prefix="ping_worker")

# Dedicated executor untuk operasi database (fetch & update)
# Dipisah agar database tidak pernah kekurangan thread meskipun ping sedang penuh.
db_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="db_worker")

from database import SessionLocal
from models.device import Device
from models.ip_pool import IpPool
from models.scan_log import ScanLog
from models.notification import Notification
from models.unknown_device import UnknownDevice
from utils import normalize_mac
from sqlalchemy import func

async def ping_ip(ip: str, timeout_ms: int = 1000) -> tuple:
    """
    Cross-platform ICMP ping function.
    Returns (is_online: bool, response_time_ms: float | None).
    """
    system_name = platform.system().lower()
    param = '-n' if system_name == 'windows' else '-c'
    timeout_param = '-w' if system_name == 'windows' else '-W'
    timeout_val = str(timeout_ms) if system_name == 'windows' else str(int(timeout_ms / 1000) or 1)

    cmd = ['ping', param, '1', timeout_param, timeout_val, ip]

    def run_ping():
        # Use standard subprocess.run to avoid Uvicorn WindowsSelectorEventLoop limitations
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if system_name == 'windows' else 0
        )

    try:
        loop = asyncio.get_running_loop()
        proc = await loop.run_in_executor(ping_executor, run_ping)
        
        if proc.returncode == 0:
            out_str = proc.stdout.decode('utf-8', errors='ignore')
            # Successful ping MUST contain TTL= in stdout
            if 'ttl=' in out_str.lower():
                match = re.search(r'(?:time|waktu)[=<]\s*(\d+(?:\.\d+)?)\s*ms', out_str, re.IGNORECASE)
                rtt = float(match.group(1)) if match else 1.0
                return True, rtt
        return False, None
    except Exception as e:
        print(f"[Ping Error on {ip}]: {type(e).__name__} - {e}")
        return False, None

async def get_mac_from_arp(ip: str) -> str:
    system_name = platform.system().lower()
    if system_name != 'windows':
        try:
            with open('/proc/net/arp', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip:
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00":
                            return normalize_mac(mac)
        except FileNotFoundError:
            pass

    def run_arp():
        if system_name == 'windows':
            return subprocess.run(['arp', '-a', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            return subprocess.run(['arp', '-n', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        loop = asyncio.get_running_loop()
        proc = await loop.run_in_executor(ping_executor, run_arp)
        if proc.returncode == 0:
            out_str = proc.stdout.decode('utf-8', errors='ignore')
            match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', out_str)
            if match:
                return normalize_mac(match.group(0))
    except Exception as e:
        print(f"[ARP Error on {ip}]: {e}")
    return None

async def ping_worker(sem: asyncio.Semaphore, ip: str) -> tuple:
    async with sem:
        is_online, rtt = await ping_ip(ip)
        mac = None
        if is_online:
            mac = await get_mac_from_arp(ip)
        return ip, is_online, rtt, mac

def fetch_target_ips_sync():
    target_ips = set()
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.ip_address.isnot(None)).all()
        for d in devices:
            if d.ip_address:
                target_ips.add(d.ip_address)

        pools = db.query(IpPool).all()
        for p in pools:
            if p.ip_address:
                target_ips.add(p.ip_address)
    finally:
        db.close()
    return target_ips

def update_database_from_ping_sync(results, now):
    db = SessionLocal()
    processed_macs = set()
    try:
        for ip, is_online, rtt, raw_mac in results:
            mac = normalize_mac(raw_mac)
            # 1. Update Device status if registered
            all_devices_on_ip = db.query(Device).filter(Device.ip_address == ip).all()
            device = all_devices_on_ip[0] if all_devices_on_ip else None
            is_mac_conflict = False
            
            if device:
                registered_macs = {normalize_mac(d.mac_address) for d in all_devices_on_ip if d.mac_address}
                
                if is_online and mac and registered_macs and mac not in registered_macs:
                    # Check if MAC belongs to another device owned by the same user
                    scanned_dev = db.query(Device).filter(func.upper(Device.mac_address) == mac).first() if mac else None
                    if scanned_dev and device.user_id and scanned_dev.user_id == device.user_id:
                        is_mac_conflict = False
                    else:
                        is_mac_conflict = True
                    
                old_status = device.status
                if is_mac_conflict:
                    device.status = "offline"
                else:
                    device.status = "online" if is_online else "offline"
                    if is_online:
                        device.last_seen = now

                if old_status == "online" and device.status == "offline" and not is_mac_conflict:
                    db.add(Notification(
                        type="device_offline",
                        message=f"Perangkat {device.hostname} ({ip}) tidak merespon (Offline).",
                        target_role="Administrator"
                    ))

            # 2. Update IP Pool status for Conflict / Active Unregistered IP
            pool_entry = db.query(IpPool).filter(IpPool.ip_address == ip).first()
            if pool_entry:
                if is_online:
                    if is_mac_conflict:
                        if pool_entry.status != 'conflict':
                            pool_entry.status = 'conflict'
                            db.add(Notification(
                                type="ip_conflict",
                                message=f"Terdeteksi IP Conflict / Pembajak pada IP {ip}. MAC: {mac}",
                                target_role="Administrator"
                            ))
                    elif not pool_entry.device_id:
                        if pool_entry.status == 'reserved' or pool_entry.reserved_for:
                            # Preserve reservation even if ping scan detects active IP
                            pass
                        elif pool_entry.status != 'unregistered':
                            pool_entry.status = 'unregistered'
                            db.add(Notification(
                                type="ip_conflict",
                                message=f"Terdeteksi Penghuni Liar (belum terdaftar) pada IP {ip}. MAC: {mac}",
                                target_role="Administrator"
                            ))
                    else:
                        if pool_entry.status in ['conflict', 'unregistered']:
                            pool_entry.status = 'used'
                            uks = db.query(UnknownDevice).filter(UnknownDevice.ip_address == ip, UnknownDevice.status == 'pending').all()
                            for uk in uks:
                                uk.status = 'resolved'
                else:
                    # If offline and it was in conflict or unregistered, revert to normal
                    if pool_entry.status in ['conflict', 'unregistered']:
                        if pool_entry.device_id:
                            pool_entry.status = 'used'
                        elif pool_entry.reserved_for:
                            pool_entry.status = 'reserved'
                        else:
                            pool_entry.status = 'free'
                    
            # 2.5 Log Unknown Device if it's online but not registered OR if it's a MAC conflict
            if is_online and (not device or is_mac_conflict):
                uk = None
                if mac:
                    uk = db.query(UnknownDevice).filter(func.upper(UnknownDevice.mac_address) == mac).first()
                if not uk:
                    uk = db.query(UnknownDevice).filter(UnknownDevice.ip_address == ip).first()
                
                if uk:
                    uk.ip_address = ip
                    uk.last_seen = now
                    if mac and normalize_mac(uk.mac_address) != mac:
                        uk.mac_address = mac
                    if uk.status == 'resolved':
                        uk.status = 'pending'
                    if mac:
                        processed_macs.add(mac)
                else:
                    if mac not in processed_macs:
                        uk = UnknownDevice(
                            ip_address=ip,
                            mac_address=mac,
                            vendor="Unknown",
                            status="pending",
                            first_seen=now,
                            last_seen=now
                        )
                        db.add(uk)
                        if mac:
                            processed_macs.add(mac)

            # 3. Log into ScanLog
            db.add(ScanLog(
                ip_address=ip,
                is_online=is_online,
                scanned_at=now,
                response_time_ms=rtt
            ))

        # Cleanup old scan_logs to prevent database bloat (keep last 5000 records)
        total_logs = db.query(ScanLog).count()
        if total_logs > 5000:
            # Find the ID of the 5000th newest record
            cutoff_log = db.query(ScanLog).order_by(ScanLog.id.desc()).offset(5000).first()
            if cutoff_log:
                db.query(ScanLog).filter(ScanLog.id <= cutoff_log.id).delete(synchronize_session=False)

        db.commit()
        print(f"[PingScan Success] Scanned {len(results)} IPs at {now}")
    except Exception as e:
        db.rollback()
        print(f"[PingScan Error] {e}")
    finally:
        db.close()


async def run_ping_scan():
    """
    Fungsi utama untuk menscan semua IP yang ada di sistem (Perangkat + Pool).
    Menggunakan executor terpisah untuk ping dan DB untuk mencegah ThreadPool deadlock.
    Dilengkapi timeout global 120 detik agar satu siklus scan tidak bisa memblokir
    event loop FastAPI selamanya (misal: saat ada IP dengan firewall 'diam'/filtered).
    """
    loop = asyncio.get_running_loop()

    # PHASE 1: Fetch Target IPs — gunakan db_executor (bukan ping_executor)
    target_ips = await loop.run_in_executor(db_executor, fetch_target_ips_sync)

    if not target_ips:
        return

    print(f"[PingScan] Starting scan for {len(target_ips)} IPs...")

    # PHASE 2: Perform Ping — dengan timeout global 120 detik per siklus
    # Semaphore(20) disesuaikan dengan max_workers ping_executor
    sem = asyncio.Semaphore(20)
    tasks = [ping_worker(sem, ip) for ip in target_ips]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=120  # Maksimal 2 menit per siklus scan
        )
    except asyncio.TimeoutError:
        print("[PingScan] WARNING: Siklus scan melebihi batas waktu 120 detik dan dibatalkan.")
        return

    # Filter out exception results dari gather (jika ada task yang gagal)
    valid_results = [r for r in results if not isinstance(r, Exception)]

    now = datetime.datetime.now()

    # PHASE 3: Update Database — gunakan db_executor (bukan ping_executor)
    await loop.run_in_executor(db_executor, update_database_from_ping_sync, valid_results, now)
