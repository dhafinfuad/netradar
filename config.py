import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/db_aplikasi")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_in_production")
SCRIPT_API_TOKEN = os.getenv("SCRIPT_API_TOKEN", "token_script_ipradar_2026")
PING_INTERVAL_MINUTES = int(os.getenv("PING_INTERVAL_MINUTES", "3"))
