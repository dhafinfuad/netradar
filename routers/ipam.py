from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.user import User
from models.ip_pool import IpPool
from models.device import Device
from dependencies import get_current_user, require_admin
from fastapi.templating import Jinja2Templates
import socket
import struct

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def sort_ips(ip_list):
    """Sorts a list of IpPool objects by their IP address numerically."""
    try:
        return sorted(ip_list, key=lambda x: struct.unpack("!L", socket.inet_aton(x.ip_address))[0])
    except:
        return ip_list

@router.get("/ipam", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), seksi: Optional[str] = None, q: Optional[str] = None, error: Optional[str] = None):
    from models.setting import Setting
    import json
    seksi_setting = db.query(Setting).filter(Setting.key == "seksi_ranges").first()
    if seksi_setting and seksi_setting.value:
        seksi_data = json.loads(seksi_setting.value)
        
        def get_min_ip_val(s_name):
            range_str = seksi_data.get(s_name, "")
            try:
                start_ip = range_str.split('-')[0].strip()
                import socket, struct
                return struct.unpack("!L", socket.inet_aton(start_ip))[0]
            except:
                return float('inf')
                
        seksi_list = sorted(list(seksi_data.keys()), key=get_min_ip_val)
    else:
        seksi_list = [
            'Subbagian Umum dan Kepatuhan Internal', 'Seksi Pelayanan', 
            'Seksi Penjaminan Kualitas Data', 'Seksi Pemeriksaan, Penilaian, dan Penagihan',
            'Seksi Pengawasan I', 'Seksi Pengawasan II', 'Seksi Pengawasan III',
            'Seksi Pengawasan IV', 'Seksi Pengawasan V', 'Seksi Pengawasan VI',
            'Fungsional Pemeriksa', 'Kepala Kantor', 'Administrator'
        ]
    
    # Fetch all IPs
    query = db.query(IpPool)
    if seksi:
        query = query.filter(IpPool.seksi == seksi)
    all_ips = query.all()
    
    # Fetch all devices to join device info manually
    from sqlalchemy.orm import joinedload
    devices = {d.id: d for d in db.query(Device).options(joinedload(Device.user)).all()}

    # Group by seksi
    grouped_ips = {s: [] for s in seksi_list}
    for ip in all_ips:
        if ip.device_id and ip.device_id in devices:
            ip.device_info = devices[ip.device_id]
        else:
            ip.device_info = None
            # Auto-repair ghost allocations
            if ip.status == 'used':
                ip.status = 'free'
                ip.device_id = None
                ip.hostname = None
                db.add(ip)
                db.commit()
            
        if ip.seksi not in grouped_ips:
            grouped_ips[ip.seksi] = []
            if ip.seksi not in seksi_list:
                seksi_list.append(ip.seksi)
                
        grouped_ips[ip.seksi].append(ip)

    # Attach rogue device info for conflicts
    from models.unknown_device import UnknownDevice
    from utils import normalize_mac
    
    pending_unknowns = db.query(UnknownDevice).filter(UnknownDevice.status == 'pending').order_by(UnknownDevice.last_seen.desc()).all()
    devices_by_mac = {normalize_mac(d.mac_address): d for d in devices.values() if d.mac_address}
    
    registered_macs_by_ip = {}
    for d in devices.values():
        if d.ip_address and d.mac_address:
            norm = normalize_mac(d.mac_address)
            if norm:
                registered_macs_by_ip.setdefault(d.ip_address, set()).add(norm)
    
    # Auto-resolve any unknown device entries whose MAC is already registered for that IP
    need_commit = False
    valid_pending_unknowns_by_ip = {}
    for uk in pending_unknowns:
        uk_mac = normalize_mac(uk.mac_address)
        reg_macs = registered_macs_by_ip.get(uk.ip_address, set())
        if uk_mac and uk_mac in reg_macs:
            uk.status = 'resolved'
            need_commit = True
        else:
            if uk.ip_address not in valid_pending_unknowns_by_ip:
                valid_pending_unknowns_by_ip[uk.ip_address] = uk

    for s, ips in grouped_ips.items():
        for ip in ips:
            ip.rogue_name = None
            ip.active_mac = None
            reg_macs = registered_macs_by_ip.get(ip.ip_address, set())
            reg_mac = normalize_mac(ip.device_info.mac_address) if (ip.device_info and ip.device_info.mac_address) else None
            
            uk = valid_pending_unknowns_by_ip.get(ip.ip_address)
            if uk and uk.mac_address:
                ip.active_mac = normalize_mac(uk.mac_address)
                rogue_dev = devices_by_mac.get(ip.active_mac) if ip.active_mac else None
                
                is_same_mac = bool(ip.active_mac and ip.active_mac in reg_macs)
                is_same_device = bool(rogue_dev and ip.device_info and rogue_dev.id == ip.device_info.id)
                is_same_user = bool(rogue_dev and ip.device_info and rogue_dev.user_id and rogue_dev.user_id == ip.device_info.user_id)
                is_same_ip = bool(rogue_dev and rogue_dev.ip_address == ip.ip_address)
                
                if is_same_mac or is_same_device or is_same_user or is_same_ip:
                    ip.rogue_name = None
                    if ip.status == 'conflict':
                        ip.status = 'used' if ip.device_id else ('reserved' if ip.reserved_for else 'free')
                        pool = db.query(IpPool).filter(IpPool.ip_address == ip.ip_address).first()
                        if pool:
                            pool.status = ip.status
                        uk.status = 'resolved'
                        need_commit = True
                else:
                    if rogue_dev and rogue_dev.user:
                        rogue_ip_suffix = f" (IP .{rogue_dev.ip_address.split('.')[-1]})" if rogue_dev.ip_address else ""
                        ip.rogue_name = f"{rogue_dev.user.name}{rogue_ip_suffix}"
                    else:
                        ip.rogue_name = "Perangkat Tidak Dikenal"
            else:
                if ip.status == 'conflict':
                    ip.status = 'used' if ip.device_id else ('reserved' if ip.reserved_for else 'free')
                    pool = db.query(IpPool).filter(IpPool.ip_address == ip.ip_address).first()
                    if pool:
                        pool.status = ip.status
                    need_commit = True

    if need_commit:
        db.commit()
                        
    # Sort IPs within each group
    for s in grouped_ips:
        grouped_ips[s] = sort_ips(grouped_ips[s])
        
    return templates.TemplateResponse(
        request=request, 
        name="ipam/index.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "ipam",
            "grouped_ips": grouped_ips,
            "seksi_list": seksi_list,
            "selected_seksi": seksi,
            "q": q or "",
            "error": error
        }
    )


@router.post("/ipam/reserve")
def reserve_ip(ip_address: str = Form(...), reserved_for: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    ip = db.query(IpPool).filter(IpPool.ip_address == ip_address).first()
    if ip and not ip.device_id:
        ip.status = 'reserved'
        ip.reserved_for = reserved_for
        db.commit()
    msg = f"IP Address {ip_address} berhasil dipesan!"
    return RedirectResponse(url=f"/ipam?msg={quote(msg)}", status_code=303)

@router.post("/ipam/unreserve")
def unreserve_ip(ip_address: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    ip = db.query(IpPool).filter(IpPool.ip_address == ip_address).first()
    if ip and ip.status == 'reserved':
        ip.status = 'free'
        ip.reserved_for = None
        db.commit()
    msg = f"Pesanan IP Address {ip_address} berhasil dibatalkan!"
    return RedirectResponse(url=f"/ipam?msg={quote(msg)}", status_code=303)

@router.get("/ipam/export")
def export_ipam_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    seksi: Optional[str] = None,
    status: Optional[str] = None
):
    import csv
    import io
    from datetime import datetime
    from fastapi.responses import Response
    from sqlalchemy.orm import joinedload
    from models.unknown_device import UnknownDevice

    # Query all IpPool entries
    query = db.query(IpPool)
    if seksi and seksi.strip() and seksi != "-- Semua Seksi --" and seksi != "Semua Seksi":
        query = query.filter(IpPool.seksi == seksi.strip())

    all_ips = query.all()

    # Sort numerically by IP
    try:
        all_ips = sorted(all_ips, key=lambda x: struct.unpack("!L", socket.inet_aton(x.ip_address))[0])
    except Exception:
        pass

    # Load devices & unknown devices
    devices = {d.id: d for d in db.query(Device).options(joinedload(Device.user)).all()}
    unknowns = {u.ip_address: u for u in db.query(UnknownDevice).all()}

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Microsoft Excel
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "No", "IP Address", "Seksi Alokasi", "Status",
        "Hostname", "MAC Address", "Tipe / Brand Perangkat",
        "Pemilik / Pegawai", "Status Perangkat", "Terakhir Terlihat", "Reservasi / Catatan"
    ])

    row_num = 1
    for ip in all_ips:
        dev = devices.get(ip.device_id) if ip.device_id else None
        unk = unknowns.get(ip.ip_address)

        # Calculate effective status
        eff_status = ip.status or "free"
        if ip.status == 'used' and dev and dev.seksi and dev.seksi != ip.seksi:
            eff_status = "salah_seksi"

        # Apply status filter if provided
        if status and status.strip() and status != "-- Semua Status --" and status != "Semua Status":
            st_clean = status.strip().lower()
            if st_clean != eff_status.lower():
                continue

        # Extract display fields
        hostname = dev.hostname if dev and dev.hostname else "-"
        mac = dev.mac_address if dev and dev.mac_address else (unk.mac_address if unk and unk.mac_address else "-")
        brand = dev.brand if dev and dev.brand else (unk.vendor if unk and unk.vendor else "-")
        owner = dev.user.name if dev and dev.user and dev.user.name else "-"
        dev_status = dev.status if dev and dev.status else ("online" if unk else "-")

        last_seen = "-"
        if dev and dev.last_seen:
            last_seen = dev.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        elif unk and unk.last_seen:
            last_seen = unk.last_seen.strftime('%Y-%m-%d %H:%M:%S')

        notes = ip.reserved_for or ip.notes or "-"

        writer.writerow([
            row_num,
            ip.ip_address,
            ip.seksi,
            eff_status.upper() if eff_status != "salah_seksi" else "SALAH SEKSI",
            hostname,
            mac,
            brand,
            owner,
            dev_status,
            last_seen,
            notes
        ])
        row_num += 1

    csv_content = output.getvalue()
    filename = f"export_ipam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content.encode('utf-8'),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )

