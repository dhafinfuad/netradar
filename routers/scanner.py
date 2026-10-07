from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.unknown_device import UnknownDevice
from dependencies import require_admin
from fastapi.templating import Jinja2Templates
from urllib.parse import quote

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/scanner", response_class=HTMLResponse)
def scanner_index(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin), msg: str = None, q: str = None, sort: str = "last_seen_desc"):
    # Fetch pending unknown devices
    query = db.query(UnknownDevice).filter(UnknownDevice.status == "pending")
    
    if q:
        query = query.filter(
            (UnknownDevice.ip_address.contains(q)) |
            (UnknownDevice.mac_address.contains(q))
        )
        
    if sort == "ip_asc":
        query = query.order_by(UnknownDevice.ip_address.asc())
    elif sort == "ip_desc":
        query = query.order_by(UnknownDevice.ip_address.desc())
    elif sort == "mac_asc":
        query = query.order_by(UnknownDevice.mac_address.asc())
    elif sort == "mac_desc":
        query = query.order_by(UnknownDevice.mac_address.desc())
    elif sort == "first_seen_asc":
        query = query.order_by(UnknownDevice.first_seen.asc())
    elif sort == "first_seen_desc":
        query = query.order_by(UnknownDevice.first_seen.desc())
    elif sort == "last_seen_asc":
        query = query.order_by(UnknownDevice.last_seen.asc())
    else:
        query = query.order_by(UnknownDevice.last_seen.desc())
        
    unknowns = query.all()
    
    return templates.TemplateResponse(
        request=request,
        name="scanner/index.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "scanner",
            "unknowns": unknowns,
            "msg": msg,
            "q": q or "",
            "sort": sort
        }
    )

@router.post("/scanner/{id}/ignore")
def ignore_device(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    device = db.query(UnknownDevice).filter(UnknownDevice.id == id).first()
    if device:
        device.status = "ignored"
        db.commit()
        msg = f"IP {device.ip_address} berhasil diabaikan."
    else:
        msg = "Perangkat tidak ditemukan."
    
    return RedirectResponse(url=f"/scanner?msg={quote(msg)}", status_code=303)
