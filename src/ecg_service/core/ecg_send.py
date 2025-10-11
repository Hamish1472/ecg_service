import os
import logging
import time
from ecg_service.config import (
    TEMP_DIR,
    TEMP_DIR_OBJ,
    EMAIL_SENDER,
    SMS_SENDER_ID,
    PASSWORD_DB,
)
from ecg_service.utils import csv_utils, email_utils, encryption_utils, sms_utils


def process_pdf(filename: str, csv_path: str):
    """Encrypt, zip, and send a single PDF using club CSV."""
    pdf_path = os.path.join(TEMP_DIR, filename)
    email = os.path.splitext(filename)[0]
    archive = f"{email}.7z"
    archive_path = os.path.join(TEMP_DIR, archive)
    password = encryption_utils.generate_password()

    wait = 0
    while not os.path.exists(csv_path) and wait < 30:
        time.sleep(1)
        wait += 1

    phone = csv_utils.get_phone_number_from_email(csv_path, email)
    encryption_utils.compress_pdf(pdf_path, archive_path, password)
    encryption_utils.store_password(PASSWORD_DB, archive, password)

    zip_name = f"{email}.zip"
    zip_path = os.path.join(TEMP_DIR, zip_name)
    encryption_utils.zip_archive(archive_path, zip_path)

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
        if phone == "Not found"
        else "Password sent to provided contact number."
    )

    full_body = base_body + password_info

    email_utils.send_email(email, "Encrypted PDF Archive", full_body, zip_path)
    logging.info(f"Email sent to {email}")

    if phone != "Not found":
        sms_utils.send_sms(phone, password, SMS_SENDER_ID)
        logging.info(f"SMS sent to {phone}")


def process_club_pdfs(club_name: str, csv_path: str):
    """Process all PDFs in TEMP_DIR for one club."""
    logging.info(f"Processing PDFs for {club_name}")

    for f in os.listdir(TEMP_DIR):
        if not f.endswith(".pdf"):
            continue
        try:
            process_pdf(f, csv_path)
        except Exception as e:
            logging.exception(f"{club_name}: PDF error {f}: {e}")
            email_utils.send_email(
                EMAIL_SENDER,
                f"PDF Pipeline Failure - {club_name}",
                f"Error processing {f}:\n{e}",
            )

    TEMP_DIR_OBJ.cleanup()
