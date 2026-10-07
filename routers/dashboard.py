import zipfile
import io
import os
from config import SCRIPT_API_TOKEN
from fastapi.responses import Response
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from database import get_db
from models.user import User
from models.device import Device
from models.ip_pool import IpPool
from dependencies import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_dashboard_stats(db: Session):
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    offline_devices = db.query(Device).filter(Device.status == "offline").count()
    unregistered_ips = db.query(IpPool).filter(IpPool.status == "unregistered").count()

    # Progress Seksi (IP Usage)
    seksi_stats = db.query(
        IpPool.seksi,
        func.count(IpPool.id).label('total'),
        func.sum(case((IpPool.status == 'used', 1), else_=0)).label('used')
    ).group_by(IpPool.seksi).all()

    progress_seksi = {}
    for seksi, total, used in seksi_stats:
        if seksi and total > 0:
            used = used or 0
            progress_seksi[seksi] = int((used / total) * 100)
            
    # Recent Alerts (Offline devices)
    recent_offline = db.query(Device)\
        .filter(Device.status == "offline")\
        .order_by(Device.last_seen.desc())\
        .limit(5).all()
        
    recent_alerts = [
        {"name": dev.hostname, "ip": dev.ip_address or "N/A"}
        for dev in recent_offline
    ]

    return {
        "stats": {
            "total_devices": total_devices,
            "online": online_devices,
            "offline": offline_devices,
            "unregistered": unregistered_ips,
            "unknown": unregistered_ips
        },
        "progress_seksi": progress_seksi,
        "recent_alerts": recent_alerts
    }

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = get_dashboard_stats(db)
    
    return templates.TemplateResponse(
        request=request, 
        name="dashboard/index.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "dashboard", 
            "stats": data["stats"], 
            "recent_alerts": data["recent_alerts"], 
            "progress_seksi": data["progress_seksi"]
        }
    )

@router.get("/api/v1/dashboard/stats")
def dashboard_stats_api(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = get_dashboard_stats(db)
    return JSONResponse(content=data)

@router.get("/docs/script-guide", response_class=HTMLResponse)
def script_guide_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        request=request, 
        name="docs/script_guide.html", 
        context={
            "request": request, 
            "current_user": current_user, 
            "active_menu": "docs"
        }
    )


@router.get("/downloads/ipradar-agent-windows.zip")
def download_dynamic_agent_zip(request: Request, current_user: User = Depends(get_current_user)):
    """
    Downloads the agent zip file but dynamically injects the current SCRIPT_API_TOKEN
    and the SERVER_URL into the PowerShell script before serving it.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_path = os.path.join(BASE_DIR, 'static', 'downloads', 'ipradar-agent-windows.zip')
    
    if not os.path.exists(zip_path):
        return Response(status_code=404, content=f"Original zip file not found on server at {zip_path}")
        
    try:
        with open(zip_path, 'rb') as f:
            zip_bytes = f.read()
            
        in_memory_zip = io.BytesIO(zip_bytes)
        new_zip_buffer = io.BytesIO()
        
        # Get the base URL from the request (e.g., http://1panel-netradar.test)
        # We strip trailing slashes to avoid double slashes in the endpoint path
        base_url = str(request.base_url).rstrip("/")
        
        with zipfile.ZipFile(in_memory_zip, 'r') as zin:
            with zipfile.ZipFile(new_zip_buffer, 'w') as zout:
                zout.comment = zin.comment
                for item in zin.infolist():
                    content = zin.read(item.filename)
                    if item.filename.endswith('IPRadar_Installer.ps1'):
                        content_str = content.decode('utf-8', errors='ignore')
                        
                        # Replace Token
                        content_str = content_str.replace('token_script_ipradar_2026', SCRIPT_API_TOKEN)
                        
                        # Replace Hardcoded Server URL
                        content_str = content_str.replace('https://netradar.multiapp.my.id', base_url)
                        
                        content = content_str.encode('utf-8')
                    zout.writestr(item, content)
                    
        headers = {
            'Content-Disposition': 'attachment; filename="ipradar-agent-windows.zip"'
        }
        
        return Response(content=new_zip_buffer.getvalue(), media_type="application/zip", headers=headers)
        
    except Exception as e:
        return Response(status_code=500, content=f"Failed to generate dynamic zip: {str(e)}")


