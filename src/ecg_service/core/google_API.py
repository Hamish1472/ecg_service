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

from ecg_service.config import DATA_DIR, AUTH_DIR
from ecg_service.utils import logging_config
from ecg_service.core.patient_creation import upload_csv
from ecg_service.core.token_manager import TokenManager
from ecg_service.core.clubs import all_club_configs


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


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
    """Authenticate with Google APIs (shared creds)."""
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

    return creds


def get_sheet_and_drive(creds, spreadsheet_id, sheet_name):
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return sheet, drive_service


def clean_drive_folder(drive_service, folder_id, days_old=30):
    """Delete files older than days_old in Google Drive folder."""
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
    """Fetch Google Sheet data and sync to local CSV."""
    sheet_rows = sheet.get_all_values()
    csv_rows = load_csv(csv_file)

    if not csv_rows and sheet_rows:
        csv_rows = [sheet_rows[0]]
        save_csv(csv_file, csv_rows)

    updated_rows = [sheet_rows[0]] + sheet_rows[1:]
    if updated_rows != csv_rows:
        save_csv(csv_file, updated_rows)
    return updated_rows


def delete_old_rows(sheet, days_old=30):
    """Delete Sheet rows older than days_old."""
    rows = sheet.get_all_values()
    if not rows or "Added Time" not in rows[0]:
        return

    idx = rows[0].index("Added Time")
    now = datetime.datetime.now()
    to_delete = []
    for i, row in enumerate(rows[1:], start=2):
        try:
            if not row[idx]:
                continue
            added = datetime.datetime.strptime(row[idx], "%d/%m/%Y %H:%M:%S")
            if (now - added).days > days_old:
                to_delete.append(i)
        except Exception as e:
            logging.warning(f"Row {i}: invalid date - {e}")

    for i in sorted(to_delete, reverse=True):
        try:
            sheet.delete_rows(i)
            logging.info(f"Deleted old row {i}")
        except Exception as e:
            logging.error(f"Failed deleting row {i}: {e}")


# @with_token_refresh
# def safe_upload_csv(access_token, hostname, csv_path):
#     return upload_csv(access_token, hostname, csv_path)


def run_google_sync(stop_event, log_queue):
    """Main loop: sync each club's sheet to CSV and upload."""
    logging_config.setup_logging(log_queue)
    creds = authenticate()
    os.makedirs(DATA_DIR, exist_ok=True)
    logging.info("Google Sheets multi-club sync started...")

    try:
        while not stop_event.is_set():
            clubs = all_club_configs()
            for club_name, club_config in clubs.items():
                try:
                    sheet, drive = get_sheet_and_drive(
                        creds, club_config["spreadsheet_id"], club_config["sheet_name"]
                    )
                    csv_path = os.path.join(DATA_DIR, f"{club_name}.csv")
                    delete_old_rows(sheet)
                    clean_drive_folder(drive, club_config["folder_id"])
                    sync_sheet(sheet, csv_path)

                    token_manager = TokenManager(club_name)
                    access_token = token_manager.get_token()

                    upload_csv(access_token, club_config["hostname"], csv_path)
                except Exception as e:
                    logging.error(f"{club_name}: sync error {e}")
            stop_event.wait(5)
    except KeyboardInterrupt:
        logging.info("Google Sheets sync stopped gracefully.")
