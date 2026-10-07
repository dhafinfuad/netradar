from database import SessionLocal
from models.user import User

def capitalize_names():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        updated = 0
        for u in users:
            if u.name:
                new_name = u.name.title()
                if u.name != new_name:
                    u.name = new_name
                    updated += 1
        db.commit()
        print(f"Berhasil mengubah {updated} nama pegawai menjadi Capitalized (Title Case).")
    except Exception as e:
        db.rollback()
        print(f"Error updating user names: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    capitalize_names()
