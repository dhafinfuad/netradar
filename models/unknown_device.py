from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class UnknownDevice(Base):
    __tablename__ = "unknown_devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False, index=True)
    mac_address = Column(String(50), nullable=True, unique=True, index=True)
    vendor = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")  # pending, ignored, resolved
    first_seen = Column(DateTime, default=datetime.datetime.now)
    last_seen = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
