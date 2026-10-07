from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI(title="IP Radar")

from routers import auth, dashboard, devices, ipam, notifications, employees, topology, settings, scanner
from routers.api import status as status_api
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.ping_service import run_ping_scan
from config import PING_INTERVAL_MINUTES

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(devices.router)
app.include_router(ipam.router)
app.include_router(employees.router)
app.include_router(status_api.router, prefix="/api/v1")
app.include_router(notifications.router)
app.include_router(topology.router)
app.include_router(settings.router)
app.include_router(scanner.router)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(
        run_ping_scan,
        'interval',
        minutes=PING_INTERVAL_MINUTES,
        id='ping_scan_job',
        replace_existing=True,
        max_instances=1,       # Hanya 1 siklus scan berjalan sekaligus; cegah resource doubling
        misfire_grace_time=60  # Toleransi 60 detik jika scheduler sempat terlambat
    )
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

from fastapi import Request, Depends
from fastapi.responses import HTMLResponse, Response

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_probe():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="auth/login.html", context={"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth/login.html", context={"request": request})



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
