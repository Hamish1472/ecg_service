import os
import tempfile
from dotenv import load_dotenv

load_dotenv()


# ========================
# API / Service Credentials
# ========================
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# CLIENT_ID = os.getenv("CLIENT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# QT_USERNAME = os.getenv("QT_USERNAME")
# QT_PASSWORD = os.getenv("QT_PASSWORD")

# SPREADSHEET_ID = "1KuPDV7I_mW65-wXugX9b7paA1T6BCqn7prkN67KG--Y"
# SHEET_NAME = "ECG_Consent"
# FOLDER_ID = "1omD_So7E-hTouZl37zXj-GBtl8Ni-_KE"

# ========================
# Paths / Folders
# ========================
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # points to src/ecg_service
DATA_DIR = os.path.join(BASE_DIR, "data")
AUTH_DIR = os.path.join(BASE_DIR, "auth")
CLUBS_CONFIG_PATH = os.path.join(AUTH_DIR, "club_credentials.csv")
TEMP_DIR_OBJ = tempfile.TemporaryDirectory()
TEMP_DIR = TEMP_DIR_OBJ.name

os.makedirs(DATA_DIR, exist_ok=True)

SEEN_IDS_FILE = os.path.join(DATA_DIR, "seen_ids.json")
PASSWORD_DB = os.path.join(DATA_DIR, "passwords.db")


# ========================
# Email / SMTP
# ========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMS_SENDER_ID = "Cardiologic"
SEVEN_ZIP_PATH = "7z"  # Or full path e.g., "C:/Program Files/7-Zip/7z.exe"


# ========================
# API Endpoints
# ========================
# HOSTNAME = "https://fr-qtm-api.qtmedical.com"
def get_endpoints(hostname: str) -> dict:
    return {
        "OAUTH_URL": f"{hostname}/oauth/token",
        "STUDIES_URL": f"{hostname}/api/v1/studies",
        "STUDY_STATUS_URL": f"{hostname}/api/v1/study/status/{{sid}}",
        "PDF_URL": f"{hostname}/api/v1/study/pdf/{{sid}}",
        "CSV_URL": f"{hostname}/api/v1/patient-information-entities/import",
    }


# ========================
# Service Settings
# ========================
POLL_INTERVAL = 60  # in seconds


# ========================
# Helper Functions
# ========================
