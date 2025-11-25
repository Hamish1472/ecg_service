import os
import typing
import tempfile
from dotenv import load_dotenv

load_dotenv()


# ========================
# API / Service Credentials
# ========================
VONAGE_API_KEY: str = typing.cast(str, os.getenv("VONAGE_API_KEY"))
VONAGE_API_SECRET: str = typing.cast(str, os.getenv("VONAGE_API_SECRET"))

EMAIL_SENDER: str = typing.cast(str, os.getenv("EMAIL_SENDER"))
EMAIL_PASSWORD: str = typing.cast(str, os.getenv("EMAIL_PASSWORD"))

# ========================
# Paths / Folders
# ========================
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # points to src/ecg_service
DATA_DIR = os.path.join(BASE_DIR, "data")
AUTH_DIR = os.path.join(BASE_DIR, "auth")
CLUBS_CONFIG_PATH = os.path.join(AUTH_DIR, "club_credentials.csv")
# TEMP_DIR_OBJ = tempfile.TemporaryDirectory()
# TEMP_DIR = TEMP_DIR_OBJ.name
TEMP_DIR = os.path.join(BASE_DIR, "tmp")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUTH_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

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
