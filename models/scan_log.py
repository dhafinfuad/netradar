from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from database import Base
import datetime

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False, index=True)
    is_online = Column(Boolean, nullable=False)
    scanned_at = Column(DateTime, default=datetime.datetime.utcnow)
    response_time_ms = Column(Float, nullable=True)
