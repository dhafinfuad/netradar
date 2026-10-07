from fastapi import APIRouter, Depends, Request, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.user import User
from models.device import Device
from models.topology_edge import TopologyEdge
from dependencies import get_current_user, require_admin
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/topology", response_class=HTMLResponse)
def topology_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    devices = db.query(Device).order_by(Device.hostname.asc()).all()
    edges = db.query(TopologyEdge).all()
    return templates.TemplateResponse(
        request=request,
        name="topology/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_menu": "topology",
            "devices": devices,
            "edges": edges
        }
    )

@router.get("/api/v1/topology/data")
def get_topology_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    devices = db.query(Device).all()
    edges = db.query(TopologyEdge).all()

    nodes_data = []
    for d in devices:
        dtype = (d.device_type or "PC").upper()
        if "ROUTER" in dtype or "GATEWAY" in dtype or "JARINGAN" in dtype or "NETWORK" in dtype:
            shape = "hexagon"
        elif "SWITCH" in dtype or "HUB" in dtype:
            shape = "box"
        elif "SERVER" in dtype:
            shape = "database"
        elif "PRINTER" in dtype:
            shape = "square"
        else:
            shape = "ellipse"

        status_val = (d.status or "unknown").lower()
        if status_val == "online":
            status_dot = '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#10B981;margin-right:6px;vertical-align:middle;box-shadow:0 0 6px #10B981;"></span>'
            status_label = "Online"
        elif status_val == "offline":
            status_dot = '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#EF4444;margin-right:6px;vertical-align:middle;box-shadow:0 0 6px #EF4444;"></span>'
            status_label = "Offline"
        else:
            status_dot = '<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#6B7280;margin-right:6px;vertical-align:middle;"></span>'
            status_label = status_val.capitalize()

        ip_str = d.ip_address or ''
        hostname_str = d.hostname or 'Unknown'
        if ip_str and '.' in ip_str:
            short_ip = '.' + ip_str.split('.')[-1]
            label_text = f"[{short_ip}] {hostname_str}"
        else:
            label_text = hostname_str

        node_item = {
            "id": d.id,
            "label": label_text,
            "title": (
                f"<b>{d.hostname}</b><br>"
                f"IP: {d.ip_address or '-'}<br>"
                f"Tipe: {d.device_type}<br>"
                f"Seksi: {d.seksi or '-'}<br>"
                f"Status: {status_dot}{status_label}"
            ),
            "group": d.device_type or "Unknown",
            "status": d.status or "unknown",
            "shape": shape
        }
        if d.topology_x is not None:
            node_item["x"] = float(d.topology_x)
        if d.topology_y is not None:
            node_item["y"] = float(d.topology_y)

        nodes_data.append(node_item)

    edges_data = []
    for e in edges:
        edges_data.append({
            "id": e.id,
            "from": e.from_device_id,
            "to": e.to_device_id,
            "label": e.label or ""
        })

    return JSONResponse(content={"nodes": nodes_data, "edges": edges_data})

@router.put("/api/v1/topology/nodes/{id}/position")
def update_node_position(
    id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    x = body.get("x")
    y = body.get("y")
    
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.topology_x = float(x) if x is not None else None
    device.topology_y = float(y) if y is not None else None
    db.commit()
    return {"status": "success", "id": id, "x": x, "y": y}

@router.post("/api/v1/topology/edges")
def create_edge(
    from_device_id: int = Form(...),
    to_device_id: int = Form(...),
    label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    if from_device_id == to_device_id:
        msg = "Node awal dan node tujuan tidak boleh sama."
        return RedirectResponse(url=f"/topology?msg={quote(msg)}", status_code=303)
        
    existing = db.query(TopologyEdge).filter(
        ((TopologyEdge.from_device_id == from_device_id) & (TopologyEdge.to_device_id == to_device_id)) |
        ((TopologyEdge.from_device_id == to_device_id) & (TopologyEdge.to_device_id == from_device_id))
    ).first()
    
    if existing:
        msg = "Koneksi antar perangkat ini sudah ada."
        return RedirectResponse(url=f"/topology?msg={quote(msg)}", status_code=303)

    edge = TopologyEdge(
        from_device_id=from_device_id,
        to_device_id=to_device_id,
        label=label
    )
    db.add(edge)
    db.commit()
    
    msg = "Koneksi jaringan berhasil ditambahkan!"
    return RedirectResponse(url=f"/topology?msg={quote(msg)}", status_code=303)

@router.post("/api/v1/topology/edges/{id}/delete")
def delete_edge_post(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    edge = db.query(TopologyEdge).filter(TopologyEdge.id == id).first()
    if edge:
        db.delete(edge)
        db.commit()
        msg = "Koneksi jaringan berhasil dihapus!"
        return RedirectResponse(url=f"/topology?msg={quote(msg)}", status_code=303)
    return RedirectResponse(url="/topology", status_code=303)

@router.delete("/api/v1/topology/edges/{id}")
def delete_edge(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    edge = db.query(TopologyEdge).filter(TopologyEdge.id == id).first()
    if edge:
        db.delete(edge)
        db.commit()
        return {"status": "success", "message": "Koneksi berhasil dihapus"}
    raise HTTPException(status_code=404, detail="Koneksi tidak ditemukan")
