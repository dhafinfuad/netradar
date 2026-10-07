from sqlalchemy import Column, Integer, String, DateTime, SmallInteger
from sqlalchemy.dialects.mysql import BIGINT
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    nip_pendek = Column(String(50), nullable=True)
    nip = Column(String(50), nullable=True)
    jabatan = Column(String(255), nullable=True)
    seksi = Column(String(255), nullable=True)
    tim = Column(String(255), nullable=True)
    target_kegiatan = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String(255), nullable=False)
    remember_token = Column(String(100), nullable=True)
    is_aktif = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    @property
    def is_admin(self):
        # Admin is NIP 123456789 OR from these two specific seksi
        if self.nip == '123456789':
            return True
        if self.seksi in ['Seksi Penjaminan Kualitas Data', 'Subbagian Umum dan Kepatuhan Internal']:
            return True
        return False
