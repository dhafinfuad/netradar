from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from database import get_db
from models.user import User
from models.device import Device
from models.device_history import DeviceHistory
from dependencies import get_current_user, require_admin
from fastapi.templating import Jinja2Templates
from datetime import datetime
from urllib.parse import quote

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/employees", response_class=HTMLResponse)
def list_employees(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = None,
    seksi: Optional[str] = None,
    page: int = 1
):
    limit = 1000
    offset = (page - 1) * limit

    query = db.query(User)

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                User.name.like(search),
                User.nip.like(search),
                User.nip_pendek.like(search),
                User.jabatan.like(search)
            )
        )

    if seksi:
        query = query.filter(User.seksi == seksi)

    total = query.count()
    employees = query.order_by(User.name.asc()).offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    # Count devices per employee
    emp_ids = [e.id for e in employees]
    device_counts = {}
    if emp_ids:
        counts = db.query(Device.user_id, func.count(Device.id)).filter(Device.user_id.in_(emp_ids)).group_by(Device.user_id).all()
        device_counts = {u_id: count for u_id, count in counts}

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
            'Fungsional Pemeriksa', 'Kepala Kantor', 'Administrator'
        ]

    jabatan_list = [
        'Pelaksana',
        'AR',
        'Supervisor',
        'FPP',
        'Juru Sita',
        'Kepala Kantor',
        'Kepala Seksi',
        'Penilai',
        'Penyuluh',
        'Administrator'
    ]

    return templates.TemplateResponse(
        request=request,
        name="employees/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_menu": "employees",
            "employees": employees,
            "device_counts": device_counts,
            "q": q or "",
            "seksi": seksi or "",
            "seksi_list": seksi_list,
            "jabatan_list": jabatan_list,
            "page": page,
            "total_pages": total_pages,
            "total_employees": total
        }
    )

@router.post("/employees/create")
def create_employee(
    name: str = Form(...),
    nip_pendek: Optional[str] = Form(None),
    nip: Optional[str] = Form(None),
    seksi: Optional[str] = Form(None),
    jabatan: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    formatted_name = name.strip().title() if name else ""
    now = datetime.utcnow()
    new_user = User(
        name=formatted_name,
        nip_pendek=nip_pendek or "",
        nip=nip or "",
        seksi=seksi or "",
        jabatan=jabatan or "",
        tim="",
        target_kegiatan=0,
        created_at=now,
        updated_at=now,
        password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW"
    )
    db.add(new_user)
    db.commit()
    msg = f"Pegawai {formatted_name} berhasil ditambahkan!"
    return RedirectResponse(url=f"/employees?msg={quote(msg)}", status_code=303)

@router.post("/employees/update")
def update_employee(
    employee_id: int = Form(...),
    name: str = Form(...),
    nip_pendek: Optional[str] = Form(None),
    nip: Optional[str] = Form(None),
    seksi: Optional[str] = Form(None),
    jabatan: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    employee = db.query(User).filter(User.id == employee_id).first()
    if employee:
        formatted_name = name.strip().title() if name else ""
        employee.name = formatted_name
        employee.nip_pendek = nip_pendek or ""
        employee.nip = nip or ""
        employee.seksi = seksi or ""
        employee.jabatan = jabatan or ""
        employee.updated_at = datetime.utcnow()
        if employee.target_kegiatan is None or employee.target_kegiatan == "":
            employee.target_kegiatan = 0
        if employee.tim is None:
            employee.tim = ""
        db.commit()
        msg = f"Data pegawai {formatted_name} berhasil diperbarui!"
        return RedirectResponse(url=f"/employees?msg={quote(msg)}", status_code=303)
    return RedirectResponse(url="/employees", status_code=303)

@router.post("/employees/delete")
def delete_employee(
    employee_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    employee = db.query(User).filter(User.id == employee_id).first()
    if employee:
        # First, detach any devices this user holds to avoid FK constraints
        devices = db.query(Device).filter(Device.user_id == employee_id).all()
        for device in devices:
            device.user_id = None
        
        name = employee.name
        db.delete(employee)
        db.commit()
        msg = f"Pegawai {name} berhasil dihapus!"
        return RedirectResponse(url=f"/employees?msg={quote(msg)}", status_code=303)
    return RedirectResponse(url="/employees", status_code=303)

@router.get("/employees/{id}", response_class=HTMLResponse)
def detail_employee(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(User).filter(User.id == id).first()
    if not employee:
        return RedirectResponse(url="/employees", status_code=303)

    # Fetch devices currently owned by employee
    devices = db.query(Device).filter(Device.user_id == id).order_by(Device.hostname.asc()).all()

    # Fetch ownership history
    history = db.query(DeviceHistory).filter(
        or_(DeviceHistory.from_user_id == id, DeviceHistory.to_user_id == id)
    ).order_by(DeviceHistory.changed_at.desc()).all()

    history_devices = {}
    h_device_ids = [h.device_id for h in history if h.device_id]
    if h_device_ids:
        h_devs = db.query(Device).filter(Device.id.in_(h_device_ids)).all()
        history_devices = {d.id: d for d in h_devs}

    return templates.TemplateResponse(
        request=request,
        name="employees/detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_menu": "employees",
            "employee": employee,
            "devices": devices,
            "history": history,
            "history_devices": history_devices
        }
    )
