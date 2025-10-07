import os
import csv
import time
import datetime
import logging
import pickle
import gspread
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ecg_service.config import BASE_DIR, DATA_DIR, CSV_PATH
from ecg_service.utils import logging_config
from ecg_service.core.patient_creation import upload_csv
from ecg_service.core.token_manager import with_token_refresh

logging_config.setup_logging()

# --- Config ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_ID = "1KuPDV7I_mW65-wXugX9b7paA1T6BCqn7prkN67KG--Y"
SHEET_NAME = "Sheet1"
FOLDER_ID = "1PvBhOF2a1f8Vz4xf6Jc_T5sj8uOY11Xi"


AUTH_DIR = os.path.join(BASE_DIR, "auth")


def load_csv(csv_file):
    if os.path.exists(csv_file):
        with open(csv_file, "r", encoding="utf-8") as f:
            return list(csv.reader(f))
    return []


def save_csv(csv_file, rows):
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def authenticate():
    """Authenticate with Google APIs using credentials in ecg_service/auth/"""
    creds = None
    token_path = os.path.join(AUTH_DIR, "token.pickle")
    creds_path = os.path.join(AUTH_DIR, "credentials.json")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token_file:
            pickle.dump(creds, token_file)

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return sheet, drive_service


def clean_drive_folder(drive_service, folder_id, days_old=30):
    """Delete files older than days_old in Google Drive folder"""
    try:
        cutoff_date = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days_old)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        query = f"'{folder_id}' in parents and modifiedTime < '{cutoff_date}' and trashed = false"
        results = (
            drive_service.files()
            .list(q=query, spaces="drive", fields="files(id, name, modifiedTime)")
            .execute()
        )

        for file in results.get("files", []):
            try:
                drive_service.files().delete(fileId=file["id"]).execute()
                logging.info(
                    f"Deleted Drive file '{file['name']}' (modified {file['modifiedTime']})"
                )
            except HttpError as e:
                logging.error(f"Failed to delete Drive file {file['name']}: {e}")
    except Exception as e:
        logging.error(f"Drive cleanup error: {e}")


def sync_sheet(sheet, csv_file):
    """Fetch Google Sheet data and sync to local CSV"""
    sheet_rows = sheet.get_all_values()
    csv_rows = load_csv(csv_file)

    # Initialize CSV if empty
    if not csv_rows and sheet_rows:
        csv_rows = [sheet_rows[0]]
        save_csv(csv_file, csv_rows)

    updated_rows = [sheet_rows[0]]
    for row in sheet_rows[1:]:
        updated_rows.append(row)

    if updated_rows != csv_rows:
        save_csv(csv_file, updated_rows)
        csv_rows = updated_rows

    return csv_rows


def delete_old_rows(sheet, days_old=30):
    """Delete Google Sheet rows older than days_old based on 'Added Time' column"""
    sheet_rows = sheet.get_all_values()
    if not sheet_rows or "Added Time" not in sheet_rows[0]:
        return

    added_idx = sheet_rows[0].index("Added Time")
    now = datetime.datetime.now()
    rows_to_delete = []

    for i, row in enumerate(sheet_rows[1:], start=2):  # 1-based indexing
        try:
            added_time_str = row[added_idx]
            if not added_time_str:
                continue
            added_time = datetime.datetime.strptime(added_time_str, "%d/%m/%Y %H:%M:%S")
            if (now - added_time).days > days_old:
                rows_to_delete.append(i)
        except Exception as e:
            logging.warning(f"Failed to parse date in row {i}: {e}")

    # Delete from bottom up
    for row_index in sorted(rows_to_delete, reverse=True):
        try:
            sheet.delete_rows(row_index)
            logging.info(f"Deleted row {row_index} (older than {days_old} days)")
        except Exception as e:
            logging.error(f"Failed to delete row {row_index}: {e}")


@with_token_refresh
def safe_upload_csv(access_token):
    return upload_csv(access_token)


def run_google_sync(stop_event):
    sheet, drive_service = authenticate()
    os.makedirs(DATA_DIR, exist_ok=True)

    logging.info("Google Sheets sync started...")

    while not stop_event.is_set():
        try:
            delete_old_rows(sheet)
            clean_drive_folder(drive_service, FOLDER_ID)
            sync_sheet(sheet, CSV_PATH)
            safe_upload_csv()
            time.sleep(2)

        except Exception as e:
            logging.error(f"Google Sheets sync error: {e}")
            time.sleep(10)

    logging.info("Google Sheets sync stopped gracefully.")
