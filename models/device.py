from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=True, index=True)
    mac_address = Column(String(50), nullable=True, unique=True, index=True)
    device_type = Column(String(50), nullable=False)
    brand = Column(String(100), nullable=True)
    model = Column(String(255), nullable=True)
    status = Column(String(50), default="unknown")
    last_seen = Column(DateTime, nullable=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey("users.id"), nullable=True)
    seksi = Column(String(255), nullable=True)
    topology_x = Column(Float, nullable=True)
    topology_y = Column(Float, nullable=True)
    snmp_community = Column(String(100), nullable=True, default="public")
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User")
