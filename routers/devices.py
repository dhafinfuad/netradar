from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from database import get_db
from models.user import User
from models.device import Device
from models.ip_pool import IpPool
from models.device_history import DeviceHistory
from dependencies import get_current_user, require_admin
from fastapi.templating import Jinja2Templates
from datetime import datetime
from pydantic import BaseModel
from fastapi import Header, HTTPException
from config import SCRIPT_API_TOKEN
from models.device_spec import DeviceSpec
from utils import normalize_mac

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/fix-ghost-ips")
def fix_ghost_ips(db: Session = Depends(get_db)):
    # 1. Temukan IP yang statusnya used tapi tidak punya device
    ghost_ips = db.query(IpPool).filter(IpPool.status == 'used', IpPool.device_id.is_(None)).all()
    count_ips = len(ghost_ips)
    for g in ghost_ips:
        g.status = 'free'
        
    # 2. Temukan Perangkat yang punya IP, tapi di IPAM tidak diakui/milik orang lain
    devices = db.query(Device).all()
    count_devices = 0
    for d in devices:
        if d.ip_address:
            ip_entry = db.query(IpPool).filter(IpPool.ip_address == d.ip_address).first()
            if not ip_entry or ip_entry.device_id != d.id:
                d.ip_address = ""
                count_devices += 1
                
    db.commit()
    return {"message": f"Berhasil memulihkan {count_ips} IP siluman ke status free, dan membersihkan {count_devices} perangkat yang mencantumkan IP siluman!"}

@router.get("/fix-seksi-data")
def fix_seksi_data(db: Session = Depends(get_db)):
    return {"message": "Already fixed"}

@router.get("/devices", response_class=HTMLResponse)
def list_devices(
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    q: Optional[str] = None,
    status: Optional[str] = None,
    seksi: Optional[str] = None,
    page: int = 1
):
    limit = 1000
    offset = (page - 1) * limit
    
    query = db.query(Device).outerjoin(User, Device.user_id == User.id)
    
    if q and q.strip():
        search_str = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Device.hostname.ilike(search_str),
                Device.ip_address.ilike(search_str),
                Device.mac_address.ilike(search_str),
                Device.device_type.ilike(search_str),
                Device.seksi.ilike(search_str),
                User.name.ilike(search_str),
                User.nip_pendek.ilike(search_str),
                User.nip.ilike(search_str)
            )
        )
    if status:
        query = query.filter(Device.status == status)
    if seksi:
        query = query.filter(Device.seksi == seksi)
        
    total = query.count()
    devices = query.order_by(Device.last_seen.desc()).offset(offset).limit(limit).all()
    
    total_pages = (total + limit - 1) // limit
    
    from models.setting import Setting
    import json
    seksi_setting = db.query(Setting).filter(Setting.key == "seksi_ranges").first()
    if seksi_setting and seksi_setting.value:
        seksi_data = json.loads(seksi_setting.value)
        seksi_list = list(seksi_data.keys())
    else:
        seksi_list = [
            'Subbagian Umum dan Kepatuhan Internal', 'Seksi Pelayanan', 
            'Seksi Penjaminan Kualitas Data', 'Seksi Pemeriksaan, Penilaian, dan Penagihan',
            'Seksi Pengawasan I', 'Seksi Pengawasan II', 'Seksi Pengawasan III',
            'Seksi Pengawasan IV', 'Seksi Pengawasan V', 'Seksi Pengawasan VI',
            'Fungsional Pemeriksa', 'Kepala Kantor', 'Administrator',
            'Printer', 'Server', 'Jaringan'
        ]

    return templates.TemplateResponse(
        request=request, 
        name="devices/list.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "devices",
            "devices": devices,
            "q": q or "",
            "status": status or "",
            "seksi": seksi or "",
            "page": page,
            "total_pages": total_pages,
            "seksi_list": seksi_list
        }
    )

def get_ip_seksi_maps(db: Session):
    all_ips = db.query(IpPool).all()
    ip_seksi_map = {item.ip_address: item.seksi for item in all_ips if item.seksi}
    seksi_ip_map = {}
    for item in all_ips:
        if item.seksi:
            if item.seksi not in seksi_ip_map:
                seksi_ip_map[item.seksi] = []
            seksi_ip_map[item.seksi].append(item.ip_address)
    return ip_seksi_map, seksi_ip_map

@router.get("/devices/create", response_class=HTMLResponse)
def create_device_form(request: Request, ip: Optional[str] = None, seksi: Optional[str] = None, source: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    users = db.query(User).order_by(User.name.asc()).all()
    users_map = {u.id: u.name for u in users}
    ip_seksi_map, seksi_ip_map = get_ip_seksi_maps(db)
    return templates.TemplateResponse(
        request=request, 
        name="devices/form.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "devices",
            "device": None,
            "prefill_ip": ip,
            "prefill_seksi": seksi,
            "source": source,
            "users": users,
            "users_map": users_map,
            "ip_seksi_map": ip_seksi_map,
            "seksi_ip_map": seksi_ip_map
        }
    )

@router.post("/devices/create", response_class=HTMLResponse)
def create_device(
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_admin),
    hostname: str = Form(...),
    ip_address: str = Form(...),
    mac_address: str = Form(...),
    device_type: str = Form(...),
    brand: Optional[str] = Form(""),
    model: Optional[str] = Form(""),
    seksi: str = Form(...),
    snmp_community: Optional[str] = Form("public"),
    source: Optional[str] = Form(None)
):
    error = None
    mac_address = normalize_mac(mac_address)
    
    # Simple Validation
    if ip_address:
        exists = db.query(Device).filter(Device.ip_address == ip_address).first()
        if exists:
            error = f"IP Address {ip_address} sudah terdaftar pada perangkat {exists.hostname}."
            
    if mac_address and not error:
        exists = db.query(Device).filter(func.upper(Device.mac_address) == mac_address).first()
        if exists:
            error = f"MAC Address {mac_address} sudah terdaftar pada perangkat {exists.hostname}."

    if error:
        ip_seksi_map, seksi_ip_map = get_ip_seksi_maps(db)
        return templates.TemplateResponse(
            request=request, 
            name="devices/form.html", 
            context={
                "request": request, 
                "current_user": current_user, 
                "active_menu": "devices",
                "device": None,
                "error": error,
                "ip_seksi_map": ip_seksi_map,
                "seksi_ip_map": seksi_ip_map,
                "form_data": {
                    "hostname": hostname, "ip_address": ip_address, "mac_address": mac_address,
                    "device_type": device_type, "brand": brand, "model": model, "seksi": seksi,
                    "snmp_community": snmp_community
                }
            }
        )

    new_device = Device(
        hostname=hostname,
        ip_address=ip_address,
        mac_address=mac_address,
        device_type=device_type,
        brand=brand,
        model=model,
        seksi=seksi,
        snmp_community=snmp_community,
        status="unknown",
        last_seen=None
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    
    # Update IP Pool if IP provided
    if ip_address:
        ip_entry = db.query(IpPool).filter(IpPool.ip_address == ip_address).first()
        if ip_entry:
            ip_entry.status = "used"
            ip_entry.device_id = new_device.id
            ip_entry.reserved_for = None
            db.commit()

    msg = f"Perangkat {hostname} berhasil ditambahkan!"
    url = f"/ipam?msg={quote(msg)}" if source == 'ipam' else f"/devices?msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)

@router.get("/devices/{id}/edit", response_class=HTMLResponse)
def edit_device_form(id: int, request: Request, source: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        return RedirectResponse(url="/devices", status_code=303)
        
    history = db.query(DeviceHistory).filter(DeviceHistory.device_id == id).order_by(DeviceHistory.changed_at.desc()).all()
    users = db.query(User).order_by(User.name.asc()).all()
    users_map = {u.id: u.name for u in users}
    ip_seksi_map, seksi_ip_map = get_ip_seksi_maps(db)
        
    return templates.TemplateResponse(
        request=request, 
        name="devices/form.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "devices",
            "device": device,
            "history": history,
            "users": users,
            "users_map": users_map,
            "source": source,
            "ip_seksi_map": ip_seksi_map,
            "seksi_ip_map": seksi_ip_map
        }
    )

@router.post("/devices/{id}/edit", response_class=HTMLResponse)
def edit_device(
    id: int,
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_admin),
    hostname: str = Form(...),
    ip_address: str = Form(...),
    mac_address: str = Form(...),
    device_type: str = Form(...),
    brand: Optional[str] = Form(""),
    model: Optional[str] = Form(""),
    seksi: str = Form(...),
    snmp_community: Optional[str] = Form("public"),
    source: Optional[str] = Form(None)
):
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        return RedirectResponse(url="/devices", status_code=303)
        
    error = None
    mac_address = normalize_mac(mac_address)
    
    # Validation
    if ip_address and ip_address != device.ip_address:
        exists = db.query(Device).filter(Device.ip_address == ip_address).first()
        if exists:
            error = f"IP Address {ip_address} sudah terdaftar."
            
    if mac_address and mac_address != normalize_mac(device.mac_address) and not error:
        exists = db.query(Device).filter(func.upper(Device.mac_address) == mac_address).first()
        if exists:
            error = f"MAC Address {mac_address} sudah terdaftar."

    if error:
        history = db.query(DeviceHistory).filter(DeviceHistory.device_id == id).order_by(DeviceHistory.changed_at.desc()).all()
        ip_seksi_map, seksi_ip_map = get_ip_seksi_maps(db)
        return templates.TemplateResponse(
            request=request, 
            name="devices/form.html", 
            context={
                "request": request, 
                "current_user": current_user, 
                "active_menu": "devices",
                "device": device,
                "history": history,
                "error": error,
                "ip_seksi_map": ip_seksi_map,
                "seksi_ip_map": seksi_ip_map
            }
        )

    old_ip = device.ip_address

    device.hostname = hostname
    device.ip_address = ip_address
    device.mac_address = mac_address
    device.device_type = device_type
    device.brand = brand
    device.model = model
    device.seksi = seksi
    device.snmp_community = snmp_community
    
    db.commit()
    
    # Update IP Pool logic
    if old_ip != ip_address:
        if old_ip:
            old_ip_entry = db.query(IpPool).filter(IpPool.ip_address == old_ip).first()
            if old_ip_entry:
                old_ip_entry.status = "free"
                old_ip_entry.device_id = None
        if ip_address:
            new_ip_entry = db.query(IpPool).filter(IpPool.ip_address == ip_address).first()
            if new_ip_entry:
                new_ip_entry.status = "used"
                new_ip_entry.device_id = device.id
                new_ip_entry.reserved_for = None
        db.commit()

    msg = f"Perangkat {hostname} berhasil diperbarui!"
    url = f"/ipam?msg={quote(msg)}" if source == 'ipam' else f"/devices?msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)

@router.post("/devices/{id}/delete")
def delete_device(id: int, source: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    device = db.query(Device).filter(Device.id == id).first()
    if device:
        if device.ip_address:
            ip_entry = db.query(IpPool).filter(IpPool.ip_address == device.ip_address).first()
            if ip_entry:
                ip_entry.status = "free"
                ip_entry.device_id = None
        db.delete(device)
        db.commit()
    msg = "Perangkat berhasil dihapus!"
    url = f"/ipam?msg={quote(msg)}" if source == 'ipam' else f"/devices?msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)

@router.post("/devices/import")
def import_devices(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    import csv
    import io
    import openpyxl

    if not file.filename:
        msg = "File tidak ditemukan."
        return RedirectResponse(url=f"/devices?msg={quote(msg)}", status_code=303)
        
    filename = file.filename.lower()
    contents = file.file.read()
    
    rows_data = []
    
    if filename.endswith(".csv"):
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = contents.decode("latin-1")
            
        reader = csv.reader(io.StringIO(text))
        header = None
        for r in reader:
            if not r or not any(r):
                continue
            if header is None:
                header = [c.strip().lower() for c in r]
                continue
            row_dict = {}
            for i, val in enumerate(r):
                if i < len(header):
                    row_dict[header[i]] = val.strip()
            rows_data.append(row_dict)
            
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        wb = openpyxl.load_workbook(filename=io.BytesIO(contents), data_only=True)
        sheet = wb.active
        header = None
        for row in sheet.iter_rows(values_only=True):
            if not row or not any(row):
                continue
            if header is None:
                header = [str(c).strip().lower() if c is not None else "" for c in row]
                continue
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(header):
                    row_dict[header[i]] = str(val).strip() if val is not None else ""
            rows_data.append(row_dict)
    else:
        msg = "Format file tidak didukung. Harap unggah file .csv atau .xlsx"
        return RedirectResponse(url=f"/devices?msg={quote(msg)}", status_code=303)
        
    imported_count = 0
    duplicate_count = 0
    failed_count = 0
    
    for r in rows_data:
        hostname = r.get("hostname") or r.get("nama perangkat") or r.get("nama") or ""
        ip_address = r.get("ip address") or r.get("ip_address") or r.get("ip") or ""
        mac_raw = r.get("mac address") or r.get("mac_address") or r.get("mac") or ""
        mac_address = normalize_mac(mac_raw)
        device_type = r.get("tipe perangkat") or r.get("device_type") or r.get("tipe") or "PC"
        brand = r.get("brand") or r.get("merk") or ""
        model = r.get("model") or ""
        seksi = r.get("seksi") or ""
        
        if not hostname or not ip_address:
            failed_count += 1
            continue
            
        existing_ip = db.query(Device).filter(Device.ip_address == ip_address).first()
        existing_mac = db.query(Device).filter(func.upper(Device.mac_address) == mac_address).first() if mac_address else None
        
        if existing_ip or existing_mac:
            duplicate_count += 1
            continue
            
        new_dev = Device(
            hostname=hostname,
            ip_address=ip_address,
            mac_address=mac_address or None,
            device_type=device_type,
            brand=brand,
            model=model,
            seksi=seksi,
            status="online"
        )
        db.add(new_dev)
        db.flush()
        
        ip_entry = db.query(IpPool).filter(IpPool.ip_address == ip_address).first()
        if ip_entry:
            ip_entry.status = "used"
            ip_entry.device_id = new_dev.id
            ip_entry.reserved_for = None
            
        imported_count += 1
        
    db.commit()
    
    msg = f"Import Selesai: {imported_count} berhasil, {duplicate_count} duplikat dilewati, {failed_count} tidak lengkap."
    return RedirectResponse(url=f"/devices?msg={quote(msg)}", status_code=303)

@router.get("/devices/export")
def export_devices_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    seksi: Optional[str] = None,
    status: Optional[str] = None
):
    import csv
    import io
    import socket
    import struct
    from datetime import datetime
    from fastapi.responses import Response
    from sqlalchemy.orm import joinedload
    from models.ip_pool import IpPool
    from models.unknown_device import UnknownDevice
    from models.device_spec import DeviceSpec

    query = db.query(IpPool)
    if seksi and seksi.strip() and seksi != "-- Semua Seksi --" and seksi != "Semua Seksi":
        query = query.filter(IpPool.seksi == seksi.strip())

    all_ips = query.all()

    try:
        all_ips = sorted(all_ips, key=lambda x: struct.unpack("!L", socket.inet_aton(x.ip_address))[0])
    except Exception:
        pass

    devices = {d.id: d for d in db.query(Device).options(joinedload(Device.user)).all()}
    device_specs = {s.device_id: s for s in db.query(DeviceSpec).all()}
    unknowns = {u.ip_address: u for u in db.query(UnknownDevice).all()}

    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM for Microsoft Excel
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "No", "IP Address", "Seksi Alokasi", "Status IPAM", "Status Device",
        "Hostname", "MAC Address", "Tipe / Brand Perangkat",
        "Pemilik / Pegawai", "Terakhir Dilihat", "CPU", "RAM Total", "Storage Total", "Sistem Operasi", "Catatan"
    ])

    st_clean = status.strip().lower() if (status and status.strip() and status != "-- Semua Status --" and status != "Semua Status") else None

    row_num = 1
    for ip in all_ips:
        dev = devices.get(ip.device_id) if ip.device_id else None
        unk = unknowns.get(ip.ip_address)
        spec = device_specs.get(dev.id) if dev else None

        eff_status = ip.status or "free"
        if ip.status == 'used' and dev and dev.seksi and dev.seksi != ip.seksi:
            eff_status = "salah_seksi"

        dev_status = dev.status if dev and dev.status else ("online" if unk else "-")

        if st_clean:
            if st_clean != eff_status.lower() and st_clean != dev_status.lower():
                continue

        hostname = dev.hostname if dev and dev.hostname else "-"
        mac = dev.mac_address if dev and dev.mac_address else (unk.mac_address if unk and unk.mac_address else "-")
        brand = dev.brand if dev and dev.brand else (unk.vendor if unk and unk.vendor else "-")
        dev_type = dev.device_type if dev and dev.device_type else brand
        owner = dev.user.name if dev and dev.user and dev.user.name else "-"

        last_seen = "-"
        if dev and dev.last_seen:
            last_seen = dev.last_seen.strftime('%Y-%m-%d %H:%M:%S')
        elif unk and unk.last_seen:
            last_seen = unk.last_seen.strftime('%Y-%m-%d %H:%M:%S')

        cpu = f"{spec.cpu_model} ({spec.cpu_brand})" if spec and spec.cpu_model else "-"
        ram = spec.ram_total if spec and spec.ram_total else "-"
        storage = spec.storage_capacity if spec and spec.storage_capacity else "-"
        os_ver = spec.os_version if spec and spec.os_version else "-"
        notes = ip.reserved_for or ip.notes or "-"

        writer.writerow([
            row_num,
            ip.ip_address,
            ip.seksi,
            eff_status.upper() if eff_status != "salah_seksi" else "SALAH SEKSI",
            dev_status,
            hostname,
            mac,
            dev_type,
            owner,
            last_seen,
            cpu,
            ram,
            storage,
            os_ver,
            notes
        ])
        row_num += 1

    csv_content = output.getvalue()
    filename = f"export_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content.encode('utf-8'),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )

@router.post("/devices/{id}/assign")
def assign_device_user(
    id: int,
    user_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        return RedirectResponse(url="/devices", status_code=303)
        
    old_user_id = device.user_id
    
    if old_user_id != user_id or notes:
        new_seksi = None
        if user_id:
            new_user = db.query(User).filter(User.id == user_id).first()
            if new_user:
                new_seksi = new_user.seksi
                device.seksi = new_seksi

        history_entry = DeviceHistory(
            device_id=device.id,
            from_user_id=old_user_id,
            to_user_id=user_id,
            changed_at=datetime.now(),
            notes=notes or "Perubahan pemilik perangkat",
            seksi=new_seksi
        )
        db.add(history_entry)
        
    device.user_id = user_id
    db.commit()
    
    msg = "Pemilik perangkat berhasil diperbarui!"
    return RedirectResponse(url=f"/devices/{id}?msg={quote(msg)}", status_code=303)

@router.post("/devices/history/{history_id}/delete")
def delete_device_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    entry = db.query(DeviceHistory).filter(DeviceHistory.id == history_id).first()
    device_id = entry.device_id if entry else None
    if entry:
        db.delete(entry)
        db.commit()
        msg = "Riwayat kepemilikan berhasil dihapus!"
        url = f"/devices/{device_id}?msg={quote(msg)}" if device_id else "/devices"
        return RedirectResponse(url=url, status_code=303)
    return RedirectResponse(url="/devices", status_code=303)

@router.get("/devices/{id}", response_class=HTMLResponse)
def detail_device(
    id: int, 
    request: Request, 
    source: Optional[str] = None, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        return RedirectResponse(url="/devices", status_code=303)
        
    history = db.query(DeviceHistory).filter(DeviceHistory.device_id == id).order_by(DeviceHistory.changed_at.desc()).all()
    spec = db.query(DeviceSpec).filter(DeviceSpec.device_id == id).first()
    users = db.query(User).order_by(User.name.asc()).all()
    users_map = {u.id: u.name for u in users}
    
    if source == "topology":
        back_url = "/topology"
    elif source == "ipam":
        back_url = "/ipam"
    elif source == "employees":
        back_url = "/employees"
    else:
        back_url = "/devices"
    
    return templates.TemplateResponse(
        request=request, 
        name="devices/detail.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": source or "devices",
            "device": device,
            "spec": spec,
            "history": history,
            "users": users,
            "users_map": users_map,
            "source": source,
            "back_url": back_url
        }
    )

class RegisterSpecs(BaseModel):
    cpu_brand: Optional[str] = None
    cpu_model: Optional[str] = None
    ram_total: Optional[str] = None
    ram_type: Optional[str] = None
    ram_brand: Optional[str] = None
    storage_capacity: Optional[str] = None
    storage_type: Optional[str] = None
    storage_brand: Optional[str] = None
    os_version: Optional[str] = None

class RegisterPayload(BaseModel):
    hostname: str
    mac_address: str
    ip_address: Optional[str] = None
    device_type: Optional[str] = "PC"
    seksi: Optional[str] = None
    pegawai_id: Optional[int] = None
    nip_pendek: Optional[str] = None
    specs: Optional[RegisterSpecs] = None

@router.post("/api/v1/devices/register")
def register_device(payload: RegisterPayload, x_script_token: str = Header(None), db: Session = Depends(get_db)):
    if x_script_token != SCRIPT_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Script Token")

    # Lookup user by nip_pendek if provided
    matched_user = None
    if payload.nip_pendek:
        matched_user = db.query(User).filter(User.nip_pendek == payload.nip_pendek).first()

    norm_mac = normalize_mac(payload.mac_address)
    device = db.query(Device).filter(func.upper(Device.mac_address) == norm_mac).first() if norm_mac else None
    
    assigned_user_id = matched_user.id if matched_user else None
    assigned_seksi = matched_user.seksi if (matched_user and matched_user.seksi) else payload.seksi

    if not device:
        # Create new device
        device = Device(
            hostname=payload.hostname,
            mac_address=norm_mac or payload.mac_address,
            ip_address=payload.ip_address,
            device_type=payload.device_type,
            user_id=assigned_user_id,
            seksi=assigned_seksi,
            status="online",
            last_seen=datetime.now(),
            created_at=datetime.now()
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        
        if payload.ip_address:
            new_pool = db.query(IpPool).filter(IpPool.ip_address == payload.ip_address).first()
            if new_pool:
                new_pool.status = "used"
                new_pool.device_id = device.id
                db.commit()
        
        if device.user_id:
            history = DeviceHistory(
                device_id=device.id,
                from_user_id=device.user_id,
                to_user_id=device.user_id,
                changed_at=datetime.now(),
                notes="Registered via script",
                seksi=device.seksi
            )
            db.add(history)
            db.commit()
    else:
        # Update existing
        device.hostname = payload.hostname
        if payload.device_type:
            device.device_type = payload.device_type
            
        if payload.ip_address and device.ip_address != payload.ip_address:
            old_ip = device.ip_address
            device.ip_address = payload.ip_address
            
            if old_ip:
                old_pool = db.query(IpPool).filter(IpPool.ip_address == old_ip).first()
                if old_pool:
                    old_pool.status = "free"
                    old_pool.device_id = None
                    
            new_pool = db.query(IpPool).filter(IpPool.ip_address == payload.ip_address).first()
            if new_pool:
                new_pool.status = "used"
                new_pool.device_id = device.id
        if assigned_user_id:
            device.user_id = assigned_user_id
        if assigned_seksi:
            device.seksi = assigned_seksi
        device.status = "online"
        device.last_seen = datetime.now()
        db.commit()
        
        if device.user_id:
            history = DeviceHistory(
                device_id=device.id,
                from_user_id=device.user_id,
                to_user_id=device.user_id,
                changed_at=datetime.now(),
                notes="Updated via script",
                seksi=device.seksi
            )
            db.add(history)
            db.commit()

    # Update specs
    if payload.specs:
        spec = db.query(DeviceSpec).filter(DeviceSpec.device_id == device.id).first()
        if not spec:
            spec = DeviceSpec(device_id=device.id)
            db.add(spec)
        spec.cpu_brand = payload.specs.cpu_brand
        spec.cpu_model = payload.specs.cpu_model
        spec.ram_total = payload.specs.ram_total
        spec.ram_type = payload.specs.ram_type
        spec.ram_brand = payload.specs.ram_brand
        spec.storage_capacity = payload.specs.storage_capacity
        spec.storage_type = payload.specs.storage_type
        spec.storage_brand = payload.specs.storage_brand
        spec.os_version = payload.specs.os_version
        spec.collected_at = datetime.now()
        db.commit()

    # Update IP Pool if applicable
    if payload.ip_address:
        ip_entry = db.query(IpPool).filter(IpPool.ip_address == payload.ip_address).first()
        if ip_entry:
            ip_entry.status = "used"
            ip_entry.device_id = device.id
            ip_entry.hostname = device.hostname
            db.commit()

    return {"message": "Device registered successfully", "device_id": device.id}

@router.get("/api/v1/devices/{id}/snmp")
async def get_device_snmp(id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Perangkat tidak ditemukan")
        
    if device.device_type not in ["Switch", "Jaringan"] or not device.snmp_community:
        raise HTTPException(status_code=400, detail="Perangkat tidak mendukung SNMP atau community string belum diatur")
        
    if not device.ip_address:
        raise HTTPException(status_code=400, detail="IP Address belum diatur")
        
    from services.snmp_service import get_snmp_data
    
    # Run async function
    snmp_result = await get_snmp_data(device.ip_address, device.snmp_community)
    
    if snmp_result.get('error'):
        return {"success": False, "error": snmp_result['error']}
        
    return {
        "success": True,
        "data": {
            "sys_desc": snmp_result.get('sys_desc'),
            "uptime_str": snmp_result.get('uptime_str'),
            "ports_up": snmp_result.get('ports_up'),
            "ports_down": snmp_result.get('ports_down')
        }
    }
