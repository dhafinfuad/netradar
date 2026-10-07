from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models.device import Device
from models.ip_pool import IpPool
from services.ping_service import run_ping_scan
from dependencies import require_admin
import datetime

router = APIRouter()

@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    ip_pools = db.query(IpPool).all()

    device_list = []
    for d in devices:
        device_list.append({
            "id": d.id,
            "hostname": d.hostname,
            "ip_address": d.ip_address,
            "status": d.status,
            "last_seen": d.last_seen.strftime('%Y-%m-%d %H:%M:%S') if d.last_seen else None,
            "seksi": d.seksi
        })

    ip_pool_list = []
    for p in ip_pools:
        ip_pool_list.append({
            "id": p.id,
            "ip_address": p.ip_address,
            "seksi": p.seksi,
            "status": p.status,
            "reserved_for": p.reserved_for
        })

    return {
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "devices": device_list,
        "ip_pools": ip_pool_list
    }

@router.post("/status/scan")
async def trigger_manual_scan(background_tasks: BackgroundTasks, current_user = Depends(require_admin)):
    background_tasks.add_task(run_ping_scan)
    return {"message": "Pemindaian Ping Jaringan dimulai di latar belakang!"}

from fastapi import Request
from fastapi.responses import StreamingResponse
import asyncio
import json

@router.get("/sse/status")
async def sse_status(request: Request, db: Session = Depends(get_db)):
    """SSE endpoint for real-time dashboard updates."""
    async def event_stream():
        while True:
            if await request.is_disconnected():
                break
                
            # Re-fetch counts
            total_devices = db.query(Device).count()
            online = db.query(Device).filter(Device.status == "online").count()
            offline = db.query(Device).filter(Device.status == "offline").count()
            unregistered = db.query(IpPool).filter(IpPool.status == "unregistered").count()
            
            # Count IP Pools usage for progress bars
            from sqlalchemy import func, case
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
                    
            # Get recent alerts (down devices)
            down_devices = db.query(Device).filter(Device.status == "offline").order_by(Device.last_seen.desc()).limit(5).all()
            recent_alerts = [{"name": d.hostname, "ip": d.ip_address} for d in down_devices]

            data = {
                "stats": {
                    "total_devices": total_devices,
                    "online": online,
                    "offline": offline,
                    "unregistered": unregistered,
                    "unknown": unregistered
                },
                "progress_seksi": progress_seksi,
                "recent_alerts": recent_alerts
            }
            
            try:
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.CancelledError:
                break
                
            await asyncio.sleep(5) # Push update every 5 seconds for responsive dashboard

    return StreamingResponse(event_stream(), media_type="text/event-stream")
