import os
import logging
import shutil
import datetime
from threading import Event
from ecg_service.config import (
    TEMP_DIR,
    # TEMP_DIR_OBJ,
    EMAIL_SENDER,
    SMS_SENDER_ID,
    PASSWORD_DB,
)
from ecg_service.utils import csv_utils, email_utils, encryption_utils, sms_utils


def process_pdf(filename: str, csv_path: str, stop_event: Event):
    """Encrypt, zip, and send a single PDF using club CSV."""
    pdf_path = os.path.join(TEMP_DIR, filename)
    # output_path = os.path.join(TEMP_DIR, "encrypted_" + filename)
    email = os.path.splitext(filename)[0].rsplit("_", 1)[0]

    password = encryption_utils.generate_password()

    wait = 0
    while not os.path.exists(csv_path) and wait < 30:
        stop_event.wait(1)
        wait += 1

    phone = csv_utils.get_col_from_email("Phone",csv_path, email)

    if not phone:
        try:
            os.remove(pdf_path)
        except OSError as e:
            logging.error(f"Failed to remove: {pdf_path}: {e}")
        return

    encryption_utils.encrypt_pdf(pdf_path, password)
    encryption_utils.store_password(PASSWORD_DB, filename, password, phone)

    body = f"""Dear {csv_utils.get_col_from_email("Name",csv_path, email)},

Please find attached the ECG report from your recent test. The password has been sent via text to your provided contact number.

If the “Summary” section states that the ECG is abnormal or recommends further investigation, you must contact your GP and share the attached PDF report with them. Alternatively, you may choose to seek further assessment through a private medical provider.

Please note that an ECG is a screening tool and does not rule out all heart conditions.

If you experience symptoms such as chest pain, unusual shortness of breath, dizziness, palpitations, or loss of consciousness at any time, you should seek medical attention regardless of the ECG result.

If you have any questions, please contact us at office@cardiologic.co.uk or 01845 523132.

Kind regards,
The CardioLogic Team"""

    # full_body = base_body + password_info

    email_utils.send_email(email, "ECG Report - Encrypted PDF", body, pdf_path)
    logging.info(f"Email sent to {email}")

    if phone:
        sms_utils.send_sms(phone, filename, password, SMS_SENDER_ID)
        logging.info(f"SMS sent to {phone}")

    # with open("C:\\Users\\Hamish\\Documents\\Cardiologic\\Send_Log.txt", "a") as f:
    #     f.write(f"\n{str(datetime.datetime.now())} - {email} - {phone}")

    os.rename(pdf_path, pdf_path.replace("pdf", "sent"))


# def process_club_pdfs(club_name: str, csv_path: str, stop_event: Event):
#     """Process all PDFs in TEMP_DIR for one club."""
#     # logging.info(f"Processing PDFs for {club_name}")

#     for f in os.listdir(TEMP_DIR):
#         #     if f.endswith(".sent"):
#         #         try:
#         #             os.remove(os.path.join(TEMP_DIR, f))
#         #         except:
#         #             logging.error(
#         #                 f"Failed to remove temp file: {os.path.join(TEMP_DIR, f)}"
#         #             )
#         if not f.endswith(".pdf"):
#             continue
#         # print(f)
#         try:
#             process_pdf(f, csv_path, stop_event)
#             # os.remove(f)
#         except Exception as e:
#             logging.exception(f"{club_name}: PDF error {f}: {e}")
#             email_utils.send_email(
#                 EMAIL_SENDER,
#                 f"PDF Pipeline Failure - {club_name}",
#                 f"Error processing {f}:\n{e}",
#             )

#     # TEMP_DIR_OBJ.cleanup()

def process_club_pdfs(club_name: str, csv_path: str, stop_event: Event) -> bool:
    """Process all PDFs in TEMP_DIR for one club. Returns True if all succeeded."""
    all_succeeded = True
    for f in os.listdir(TEMP_DIR):
        if not f.endswith(".pdf"):
            continue
        try:
            process_pdf(f, csv_path, stop_event)
        except Exception as e:
            all_succeeded = False
            logging.exception(f"{club_name}: PDF error {f}: {e}")
    return all_succeeded