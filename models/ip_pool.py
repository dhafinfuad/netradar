from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from database import Base
import datetime

class IpPool(Base):
    __tablename__ = "ip_pool"

    id = Column(Integer, primary_key=True, index=True)
    seksi = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(50), default="free")
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    reserved_for = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
