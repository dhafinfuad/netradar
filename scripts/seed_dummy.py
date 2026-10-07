import os
import sys
import random
from datetime import datetime, timedelta

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine, Base
from models.user import User
from models.device import Device
from models.ip_pool import IpPool
from models.notification import Notification

def seed():
    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if there is already data
    if db.query(Device).count() > 0:
        print("Data already exists. Skipping dummy seed.")
        return

    print("Seeding dummy data...")

    seksi_list = [
        'Subbagian Umum dan Kepatuhan Internal',
        'Seksi Pelayanan',
        'Seksi Penjaminan Kualitas Data',
        'Seksi Pemeriksaan, Penilaian, dan Penagihan',
        'Seksi Pengawasan I',
        'Seksi Pengawasan II',
        'Seksi Pengawasan III',
        'Seksi Pengawasan IV',
        'Seksi Pengawasan V',
        'Seksi Pengawasan VI',
        'Fungsional Pemeriksa',
        'Kepala Kantor',
        'Administrator'
    ]
    device_types = ["PC", "Laptop", "Printer", "Server", "Switch"]
    
    devices = []
    
    # 1. Create Devices
    for i in range(1, 51):
        status = random.choices(["online", "offline", "unknown"], weights=[70, 20, 10])[0]
        dev_type = random.choice(device_types)
        
        last_seen = datetime.utcnow()
        if status == "offline":
            last_seen = datetime.utcnow() - timedelta(minutes=random.randint(5, 600))
        
        device = Device(
            hostname=f"DEV-{dev_type.upper()}-{i:03d}",
            ip_address=f"192.168.1.{i+10}",
            mac_address=f"00:1A:2B:3C:4D:{i:02X}",
            device_type=dev_type,
            brand="Generic",
            model="Model-X",
            status=status,
            last_seen=last_seen,
            seksi=random.choice(seksi_list)
        )
        db.add(device)
        devices.append(device)
        
    db.commit()
    print(f"Created {len(devices)} devices.")

    # 2. Create IP Pool
    ip_pools = []
    for seksi in seksi_list:
        # Assign 30 IPs per seksi
        subnet = seksi_list.index(seksi) + 1
        for i in range(1, 31):
            ip = f"192.168.{subnet}.{i}"
            # Randomly mark some as used
            status = random.choices(["used", "free"], weights=[40, 60])[0]
            
            ip_pool = IpPool(
                seksi=seksi,
                ip_address=ip,
                status=status
            )
            db.add(ip_pool)
            ip_pools.append(ip_pool)
    
    db.commit()
    print(f"Created {len(ip_pools)} IP pool entries.")

    # 3. Create Notifications
    offline_devices = [d for d in devices if d.status == "offline"]
    for dev in offline_devices[:5]:
        notif = Notification(
            type="offline",
            message=f"Perangkat {dev.hostname} ({dev.ip_address}) terdeteksi offline sejak {dev.last_seen.strftime('%Y-%m-%d %H:%M')}",
            is_read=False
        )
        db.add(notif)
    
    db.commit()
    print("Created dummy notifications.")
    print("Seed complete!")
    db.close()

if __name__ == "__main__":
    seed()
