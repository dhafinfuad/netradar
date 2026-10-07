from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # Naikan dari default 5 — cukup untuk request user + scan bersamaan
    max_overflow=20,     # Koneksi tambahan jika pool habis (total max = 30)
    pool_timeout=30,     # Timeout menunggu koneksi dari pool (detik); cegah hang tanpa batas
    pool_recycle=1800,   # Recycle koneksi tiap 30 menit — cegah MySQL "gone away" error
    pool_pre_ping=True,  # Test koneksi sebelum dipakai — cegah stale/mati diam-diam
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
