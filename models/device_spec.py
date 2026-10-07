from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base
import datetime

class DeviceSpec(Base):
    __tablename__ = "device_specs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    cpu_brand = Column(String(100), nullable=True)
    cpu_model = Column(String(255), nullable=True)
    ram_total = Column(String(50), nullable=True)
    ram_type = Column(String(50), nullable=True)
    ram_brand = Column(String(100), nullable=True)
    storage_capacity = Column(String(50), nullable=True)
    storage_type = Column(String(50), nullable=True)
    storage_brand = Column(String(100), nullable=True)
    os_version = Column(String(255), nullable=True)
    collected_at = Column(DateTime, default=datetime.datetime.now)
