from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db
from models.user import User
from services.auth_service import SECRET_KEY, ALGORITHM

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        # Pengecualian untuk request dari browser agar di-redirect ke halaman login
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    # Jika token diawali dengan 'Bearer ', hapus
    if token.startswith("Bearer "):
        token = token[7:]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": "/"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Blokir akses jika akun tidak aktif meskipun token masih valid
    if getattr(user, 'is_aktif', 1) != 1:
        if "text/html" in request.headers.get("accept", ""):
            from fastapi.responses import RedirectResponse as _Redirect
            from urllib.parse import quote
            response = _Redirect(url="/?msg=" + quote("Akun Anda telah dinonaktifkan. Hubungi administrator."))
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                headers={
                    "Location": "/?msg=" + quote("Akun Anda telah dinonaktifkan. Hubungi administrator."),
                    "Set-Cookie": "access_token=; Max-Age=0; Path=/; HttpOnly",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif",
        )

    return user

async def require_admin(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        from urllib.parse import quote
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/dashboard?msg=" + quote("Akses Ditolak: Anda tidak memiliki izin Administrator.")},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required",
        )
    return current_user
