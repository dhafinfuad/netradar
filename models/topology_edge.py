from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from database import Base
import datetime

class TopologyEdge(Base):
    __tablename__ = "topology_edges"

    id = Column(Integer, primary_key=True, index=True)
    from_device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    to_device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    label = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
