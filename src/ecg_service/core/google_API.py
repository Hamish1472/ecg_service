import os
import csv
import sqlite3
import logging
import socket
import pickle
import gspread
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from ecg_service.config import DATA_DIR, AUTH_DIR, PASSWORD_DB
from ecg_service.utils import logging_config
from ecg_service.core.patient_creation import upload_csv
from ecg_service.core.token_manager import TokenManager
from ecg_service.core.clubs import all_club_configs

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_last_db_mtime = None


def is_network_available(host="oauth2.googleapis.com", port=443, timeout=3):
    """Cheap connectivity/DNS check before hammering every club in the loop."""
    try:
        socket.getaddrinfo(host, port)
        return True
    except socket.gaierror:
        return False


def sync_db_to_sheet(sheet, db_path):
    global _last_db_mtime

    try:
        current_mtime = os.path.getmtime(db_path)
        if _last_db_mtime == current_mtime:
            return  # no changes

        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT filename, password, phone_number, timestamp, club_name FROM passwords"
        ).fetchall()
        con.close()

    except Exception as e:
        logging.error(f"Failed to read database: {e}")
        return

    try:
        new_values = [
            ["Filename", "Password", "Phone", "Timestamp", "Club Name"],
            *[list(row) for row in rows],
        ]
        sheet.update(range_name="A1", values=new_values)

        _last_db_mtime = current_mtime

    except Exception as e:
        logging.error(f"Failed to write to sheet: {e}")


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


def get_cached_sheet_and_drive(cache, creds, club_name, spreadsheet_id, sheet_name):
    """Return a cached (sheet, drive) handle for a club, opening it only once.

    This handle is a reference (spreadsheet ID + worksheet ID/title), not a
    snapshot of cell data — sheet.get_all_values() still issues a fresh API
    call every time it's invoked. Caching only skips the repeated
    open_by_key()/.worksheet() lookup calls, not the actual data read.
    """
    if club_name not in cache:
        cache[club_name] = get_sheet_and_drive(creds, spreadsheet_id, sheet_name)
    return cache[club_name]


# def clean_drive_folder(drive_service, folder_id, days_old=30):
#     """Delete files older than days_old in Google Drive folder."""
#     try:
#         cutoff_date = (
#             datetime.datetime.now(datetime.timezone.utc)
#             - datetime.timedelta(days=days_old)
#         ).strftime("%Y-%m-%dT%H:%M:%SZ")

#         query = f"'{folder_id}' in parents and modifiedTime < '{cutoff_date}' and trashed = false"
#         results = (
#             drive_service.files()
#             .list(q=query, spaces="drive", fields="files(id, name, modifiedTime)")
#             .execute()
#         )

#         for file in results.get("files", []):
#             try:
#                 drive_service.files().delete(fileId=file["id"]).execute()
#                 logging.info(
#                     f"Deleted Drive file '{file['name']}' (modified {file['modifiedTime']})"
#                 )
#             except HttpError as e:
#                 logging.error(f"Failed to delete Drive file {file['name']}: {e}")
#     except Exception as e:
#         logging.error(f"Drive cleanup error: {e}")


def sync_sheet(sheet, csv_file):
    """Fetch Google Sheet data and sync to local CSV.

    Returns:
        tuple[list, bool]: (rows now on disk, True if the CSV file was
        created or its contents changed on this call).
    """
    sheet_rows = sheet.get_all_values()
    csv_rows = load_csv(csv_file)

    if not csv_rows and sheet_rows:
        csv_rows = [sheet_rows[0]]
        save_csv(csv_file, csv_rows)

    updated_rows = [sheet_rows[0]] + sheet_rows[1:]
    changed = updated_rows != csv_rows
    if changed:
        save_csv(csv_file, updated_rows)
    return updated_rows, changed


# def delete_old_rows(sheet, days_old=60):
#     """Delete Sheet rows older than days_old."""
#     rows = sheet.get_all_values()
#     if not rows or "Added Time" not in rows[0]:
#         return

#     idx = rows[0].index("Added Time")
#     now = datetime.datetime.now()
#     to_delete = []
#     for i, row in enumerate(rows[1:], start=2):
#         try:
#             if not row[idx]:
#                 continue
#             added = datetime.datetime.strptime(row[idx], "%d/%m/%Y %H:%M:%S")
#             if (now - added).days > days_old:
#                 to_delete.append(i)
#         except Exception as e:
#             logging.warning(f"Row {i}: invalid date - {e}")

#     for i in sorted(to_delete, reverse=True):
#         try:
#             sheet.delete_rows(i)
#             logging.info(f"Deleted old row {i}")
#         except Exception as e:
#             logging.error(f"Failed deleting row {i}: {e}")


# @with_token_refresh
# def safe_upload_csv(access_token, hostname, csv_path):
#     return upload_csv(access_token, hostname, csv_path)


def run_google_sync(stop_event, log_queue):
    """Main loop: sync each club's sheet to CSV and upload."""
    logging_config.setup_logging(log_queue)
    creds = authenticate()
    os.makedirs(DATA_DIR, exist_ok=True)
    logging.info("Google Sheets multi-club sync started...")

    pdf_client = gspread.authorize(creds)
    pdf_sheet = pdf_client.open_by_key(
        "19oyQseaulZmVEnHuj-iqNChSSazRO_GxyrOZEcPo9KY"
    ).worksheet("Sheet1")

    base_delay = 30
    max_delay = 300
    consecutive_failures = 0
    sheet_cache = {}  # club_name -> (sheet, drive), persists across cycles
    stop_event.wait(2)
    try:
        while not stop_event.is_set():
            if not is_network_available():
                consecutive_failures += 1
                delay = min(base_delay * (2**consecutive_failures), max_delay)
                logging.warning(
                    f"Network unavailable (DNS check failed). "
                    f"Skipping sync cycle #{consecutive_failures}. Retrying in {delay}s."
                )
                stop_event.wait(delay)
                continue

            cycle_had_error = False
            clubs = all_club_configs()
            for club_name, club_config in clubs.items():
                stop_event.wait(1.25)
                csv_path = None
                csv_changed = False
                try:
                    sheet, drive = get_cached_sheet_and_drive(
                        sheet_cache,
                        creds,
                        club_name,
                        club_config["spreadsheet_id"],
                        club_config["sheet_name"],
                    )
                    csv_path = os.path.join(DATA_DIR, f"{club_name}.csv")
                    _, csv_changed = sync_sheet(sheet, csv_path)
                except (SpreadsheetNotFound, WorksheetNotFound) as e:
                    # the cached reference genuinely no longer points anywhere valid
                    sheet_cache.pop(club_name, None)
                    cycle_had_error = True
                    logging.error(
                        f"[{club_name}] Sheet reference invalid, will reopen next cycle: {e}"
                    )
                except APIError as e:
                    cycle_had_error = True
                    status = getattr(e.response, "status_code", None)
                    if status == 429:
                        logging.warning(f"[{club_name}] Rate limited (429): {e}")
                    else:
                        # unknown API error — evict to be safe in case the handle is stale
                        sheet_cache.pop(club_name, None)
                        logging.error(f"[{club_name}] Google API error: {e}")
                except Exception as e:
                    cycle_had_error = True
                    sheet_id = club_config["spreadsheet_id"]
                    sheet_name = club_config["sheet_name"]
                    logging.error(
                        f"[{club_name}] Google CSV sync error: {e} --- for sheet_id: {sheet_id}, sheet_name: {sheet_name}"
                    )

                if not csv_changed:
                    continue
                try:
                    if csv_path:
                        token_manager = TokenManager(club_name)
                        access_token = token_manager.get_token()
                        upload_csv(
                            access_token, club_config["hostname"], csv_path, club_name
                        )
                except Exception as e:
                    cycle_had_error = True
                    logging.error(f"[{club_name}]: QT sync error {e}")

            try:
                sync_db_to_sheet(pdf_sheet, PASSWORD_DB)
            except Exception as e:
                cycle_had_error = True
                logging.error(f"Failed to write to PDF sheet: {e}")

            if cycle_had_error:
                consecutive_failures += 1
                delay = min(base_delay * (2**consecutive_failures), max_delay)
                logging.warning(
                    f"Sync cycle had errors (#{consecutive_failures} in a row). "
                    f"Backing off to {delay}s before next attempt."
                )
            else:
                consecutive_failures = 0
                delay = base_delay

            stop_event.wait(delay)
    except KeyboardInterrupt:
        logging.info("Google Sheets sync stopped gracefully.")
