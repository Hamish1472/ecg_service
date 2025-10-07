import os
import shutil
import logging
import datetime
import time
from ecg_service.config import (
    TEMP_DIR,
    CSV_PATH,
    EMAIL_SENDER,
    SMS_SENDER_ID,
    PASSWORD_DB,
)
from ecg_service.utils import csv_utils, email_utils, encryption_utils, sms_utils


def process_pdf(filename: str):
    """Encrypt, zip, and send a single PDF."""
    pdf_path = os.path.join(TEMP_DIR, filename)
    email_address = os.path.splitext(filename)[0]
    archive_name = f"{email_address}.7z"
    archive_path = os.path.join(TEMP_DIR, archive_name)
    password = encryption_utils.generate_password()

    # Wait until the file exists
    wait_seconds = 0
    while not os.path.exists(CSV_PATH):
        if wait_seconds >= 30:  # optional max wait
            logging.warning(
                f"{CSV_PATH} not found after {wait_seconds}s, continuing anyway."
            )
            break
        logging.info(f"{CSV_PATH} not found yet, waiting 1s...")
        time.sleep(1)
        wait_seconds += 1

    # Get phone number from today's CSV first
    phone_number = csv_utils.get_phone_number_from_email(CSV_PATH, email_address)

    # Compress PDF and store password
    encryption_utils.compress_pdf(pdf_path, archive_path, password)
    encryption_utils.store_password(PASSWORD_DB, archive_name, password)

    # Zip for email attachment
    zip_name = f"{email_address}.zip"
    zip_path = os.path.join(TEMP_DIR, zip_name)
    encryption_utils.zip_archive(archive_path, zip_path)

    # Prepare email body
    base_body = (
        "Please find your encrypted PDF archive attached.\n"
        "To access the PDF please follow these steps:\n"
        "    - Download and install 7zip from https://www.7-zip.org/download.html\n"
        "    - Open the .zip attachment, click 'Extract all'\n"
        "    - In the extracted folder, right-click on the .7z file → 7-zip → Open Archive\n"
        "    - Enter the password sent via SMS\n"
        "    - Double-click to open the PDF\n"
    )
    password_info = (
        "Phone number not found. Please contact us for the password."
        if phone_number == "Not found"
        else "Password sent to provided contact number."
    )

    full_body = base_body + password_info

    # Send email
    email_utils.send_email(email_address, "Encrypted PDF Archive", full_body, zip_path)
    logging.info(f"Email sent to {email_address} with encrypted PDF")

    # Send SMS if phone exists
    if phone_number != "Not found":
        sms_utils.send_sms(phone_number, password, SMS_SENDER_ID)
        logging.info(f"SMS sent to {phone_number}")


def clear_folder(path: str, retries: int = 10, delay: float = 0.5) -> None:
    """Remove all contents of a folder while keeping the folder itself."""
    for attempt in range(retries):
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    os.unlink(full_path)
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
            return
        except PermissionError:
            logging.warning(
                "Attempt %d failed: contents locked. Retrying...", attempt + 1
            )
            time.sleep(delay)
    logging.error("Failed to clear folder %s after %d attempts", path, retries)


def main():
    """Process all PDFs in TEMP folder."""
    os.makedirs(TEMP_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(TEMP_DIR) if f.endswith(".pdf")]
    for filename in pdf_files:
        try:
            process_pdf(filename)
        except Exception as e:
            logging.exception(f"Failed processing PDF {filename}: {e}")
            email_utils.send_email(
                EMAIL_SENDER,
                "Failed PDF Pipeline",
                f"The pipeline failed for PDF: {filename} with exception:\n\n{e}",
            )

    if os.path.exists(TEMP_DIR):
        clear_folder(TEMP_DIR)
