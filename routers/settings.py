import os
import json
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.setting import Setting
from models.scan_log import ScanLog
from dependencies import require_admin
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
import config

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def set_key_in_env(env_path, key, value):
    """Utility to update or add a key in .env file."""
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write(f"{key}={value}\n")
        return

    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    key_found = False
    with open(env_path, 'w') as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                key_found = True
            else:
                f.write(line)
        if not key_found:
            f.write(f"{key}={value}\n")

@router.get("/admin/settings", response_class=HTMLResponse)
def settings_index(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_admin), msg: str = None):
    # Get seksi configuration
    seksi_setting = db.query(Setting).filter(Setting.key == "seksi_ranges").first()
    seksi_ranges = json.loads(seksi_setting.value) if seksi_setting and seksi_setting.value else {}
    
    # Get scan logs
    scan_logs = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).limit(50).all()

    # Get distinct seksi from users
    seksi_list_query = db.query(User.seksi).filter(User.seksi != None, User.seksi != "").distinct().all()
    seksi_list = sorted([s[0] for s in seksi_list_query])
    
    return templates.TemplateResponse(
        request=request,
        name="settings/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_menu": "settings",
            "msg": msg,
            "ping_interval": config.PING_INTERVAL_MINUTES,
            "script_token": config.SCRIPT_API_TOKEN,
            "seksi_ranges": seksi_ranges,
            "scan_logs": scan_logs,
            "seksi_list": seksi_list
        }
    )

@router.post("/admin/settings/env")
def update_env_settings(
    request: Request,
    ping_interval: int = Form(...),
    script_token: str = Form(...),
    current_user: User = Depends(require_admin)
):
    env_path = os.path.join(os.getcwd(), ".env")
    
    # Update .env
    set_key_in_env(env_path, "PING_INTERVAL_MINUTES", str(ping_interval))
    set_key_in_env(env_path, "SCRIPT_API_TOKEN", script_token)
    
    # Update in memory
    config.PING_INTERVAL_MINUTES = ping_interval
    config.SCRIPT_API_TOKEN = script_token
    os.environ["PING_INTERVAL_MINUTES"] = str(ping_interval)
    os.environ["SCRIPT_API_TOKEN"] = script_token
    
    # Catatan: Perubahan ping_interval membutuhkan restart scheduler/server untuk berlaku efektif,
    # tetapi karena kita menyimpan ke .env, akan efektif pada startup berikutnya.
    
    msg = "Pengaturan Umum berhasil diperbarui. (Catatan: Interval Ping mungkin memerlukan restart server agar aktif)"
    return RedirectResponse(url=f"/admin/settings?msg={quote(msg)}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/settings/seksi/save")
async def save_seksi_settings_json(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # We will send JSON from frontend for easier mapping
    data = await request.json()
    
    seksi_setting = db.query(Setting).filter(Setting.key == "seksi_ranges").first()
    if not seksi_setting:
        seksi_setting = Setting(key="seksi_ranges")
        db.add(seksi_setting)
        
    seksi_setting.value = json.dumps(data)
    db.commit()

    # --- Sync IpPool Logic ---
    import ipaddress
    from models.ip_pool import IpPool
    
    target_ips_by_seksi = {}
    all_target_ips = set()
    
    for seksi, range_str in data.items():
        try:
            parts = [ip.strip() for ip in range_str.split('-')]
            if len(parts) == 2:
                start = int(ipaddress.IPv4Address(parts[0]))
                end = int(ipaddress.IPv4Address(parts[1]))
                if end - start <= 2000: # reasonable limit
                    ips = [str(ipaddress.IPv4Address(ip)) for ip in range(start, end + 1)]
                    target_ips_by_seksi[seksi] = ips
                    all_target_ips.update(ips)
        except Exception:
            continue
            
    existing_pools = db.query(IpPool).all()
    existing_ip_map = {p.ip_address: p for p in existing_pools}
    
    # 1. Re-categorize orphaned IPs
    for p in existing_pools:
        if p.ip_address not in all_target_ips:
            if p.seksi != "Tanpa Seksi":
                p.seksi = "Tanpa Seksi"
                
    # 2. Add or update valid IPs
    for seksi, ips in target_ips_by_seksi.items():
        for ip in ips:
            if ip in existing_ip_map:
                if existing_ip_map[ip].seksi != seksi:
                    existing_ip_map[ip].seksi = seksi
            else:
                new_entry = IpPool(seksi=seksi, ip_address=ip, status="free")
                db.add(new_entry)
                
    db.commit()
    # -------------------------
    
    return {"status": "success", "message": "Konfigurasi Seksi berhasil disimpan!"}
