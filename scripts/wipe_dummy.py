import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.device_history import DeviceHistory
from models.notification import Notification
from models.ip_pool import IpPool
from models.device import Device

def wipe():
    db = SessionLocal()
    db.query(DeviceHistory).delete()
    db.query(Notification).delete()
    db.query(IpPool).delete()
    db.query(Device).delete()
    db.commit()
    print("Old dummy data wiped.")
    db.close()

if __name__ == "__main__":
    wipe()
