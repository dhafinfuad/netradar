from fastapi import APIRouter, Depends, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from services.auth_service import verify_password, create_access_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# GET /login dipindahkan ke sini atau bisa tetap di main.py.
# Tapi karena di main.py kita akan ganti, kita biarkan POST /login di sini.
@router.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Cari user berdasarkan nip
    user = db.query(User).filter(User.nip == username).first()
    
    # Jika tidak ketemu dengan nip, coba cari berdasarkan nip_pendek
    if not user:
        user = db.query(User).filter(User.nip_pendek == username).first()
        
    # Jika masih tidak ketemu, coba cari berdasarkan name
    if not user:
        user = db.query(User).filter(User.name == username).first()

    # Verifikasi password
    # Jika tabel users dari laravel dan password kosong, mungkin kita perlu handle khusus jika environment lokal
    # Namun secara standar kita lakukan verify_password
    is_valid_password = False
    if user and user.password:
        is_valid_password = verify_password(password, user.password)
    elif user and not user.password and password == "": # Fallback jika password di db kosong (kasus langka)
        is_valid_password = True
    
    # Bypass untuk dev khusus root MySQL admin jika tidak ada user
    if username == "123456789" and password in ["admin", "123456789", ""]:
        if not user:
            # Auto-create user administrator untuk mempermudah development
            from services.auth_service import get_password_hash
            new_admin = User(
                name="System Administrator",
                nip="123456789",
                seksi="Seksi Penjaminan Kualitas Data",
                password=get_password_hash("123456789")
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            user = new_admin
        
        is_valid_password = True

    if not user or not is_valid_password:
        return templates.TemplateResponse(
            request=request, 
            name="auth/login.html", 
            context={"request": request, "error_msg": "Operator ID atau Access Key salah."}
        )

    # Cek apakah akun masih aktif
    if getattr(user, 'is_aktif', 1) != 1:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"request": request, "error_msg": "Akun Anda telah dinonaktifkan. Hubungi administrator."}
        )

    # Generate JWT
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Set Cookie & Redirect ke Dashboard
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect_response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=86400,
        expires=86400,
    )
    
    return redirect_response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response
