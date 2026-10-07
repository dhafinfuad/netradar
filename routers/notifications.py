from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.notification import Notification
from dependencies import get_current_user
from fastapi.templating import Jinja2Templates
from urllib.parse import quote

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/notifications", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    type: Optional[str] = None,
    read_status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    limit = 15
    offset = (page - 1) * limit

    query = db.query(Notification)
    if type:
        query = query.filter(Notification.type == type)
    if read_status == 'unread':
        query = query.filter(Notification.is_read == False)
    elif read_status == 'read':
        query = query.filter(Notification.is_read == True)

    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    # Statistics
    stats = {
        "total": db.query(Notification).count(),
        "unread": db.query(Notification).filter(Notification.is_read == False).count(),
        "conflicts": db.query(Notification).filter(Notification.type == 'ip_conflict').count()
    }

    return templates.TemplateResponse(
        request=request,
        name="notifications/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_menu": "notifications",
            "notifications": notifications,
            "stats": stats,
            "type": type or "",
            "read_status": read_status or "",
            "page": page,
            "total_pages": total_pages
        }
    )

@router.post("/notifications/clear-all")
def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db.query(Notification).delete()
    db.commit()
    msg = "Seluruh riwayat notifikasi berhasil dihapus!"
    return RedirectResponse(url=f"/notifications?msg={quote(msg)}", status_code=303)

@router.get("/api/v1/notifications/dropdown", response_class=HTMLResponse)
def get_dropdown_notifications(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    notifs = db.query(Notification).filter(Notification.is_read == False).order_by(Notification.created_at.desc()).limit(5).all()
    
    html = ""
    if not notifs:
        return "<div class='p-4 text-center text-sm text-gray-400'>Belum ada notifikasi baru.</div>"
        
    for n in notifs:
        icon = "info"
        icon_bg = "bg-blue-500/15 text-blue-400 border-blue-500/30"
        if n.type == 'device_offline':
            icon = "router"
            icon_bg = "bg-red-500/15 text-red-400 border-red-500/30"
        elif n.type == 'ip_conflict':
            icon = "warning"
            icon_bg = "bg-amber-500/15 text-amber-400 border-amber-500/30"
            
        html += f"""
        <div class="px-4 py-3 hover:bg-white/5 cursor-pointer transition-colors" onclick="window.location.href='/notifications'">
            <div class="flex items-start gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center border {icon_bg} mt-0.5">
                    <span class="material-symbols-outlined text-[18px]">{icon}</span>
                </div>
                <div class="min-w-0 flex-1">
                    <p class="text-xs sm:text-sm text-gray-200 dark:text-gray-100 font-medium leading-snug break-words">{n.message}</p>
                    <p class="text-[11px] text-gray-400 dark:text-gray-400 mt-1 flex items-center gap-1 font-mono">
                        <span class="material-symbols-outlined text-[12px]">schedule</span>
                        {n.created_at.strftime('%Y-%m-%d %H:%M')}
                    </p>
                </div>
            </div>
        </div>
        """
    return html

@router.api_route("/api/v1/notifications/mark-all-read", methods=["GET", "POST"])
def mark_all_read(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db.query(Notification).filter(Notification.is_read == False).update({"is_read": True})
    db.commit()
    if request.method == "GET":
        referer = request.headers.get("referer", "/notifications")
        return RedirectResponse(url=referer, status_code=303)
    return {"status": "ok"}

@router.get("/api/v1/notifications/unread-count")
def get_unread_count(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    count = db.query(Notification).filter(Notification.is_read == False).count()
    return {"count": count}
