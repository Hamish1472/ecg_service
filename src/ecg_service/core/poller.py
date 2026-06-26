import logging
import os
import time
from threading import Event

from ecg_service.core import ecg_send
from ecg_service.config import EMAIL_SENDER, POLL_INTERVAL, DATA_DIR, TEMP_DIR
from ecg_service.core.token_manager import TokenManager
from ecg_service.core.studies import (
    fetch_all_studies,
    download_pdf,
    load_seen_ids,
    save_seen_ids,
)
from ecg_service.core.clubs import all_club_configs
from ecg_service.utils import email_utils, logging_config

# Backoff configuration
_BACKOFF_BASE = 10  # seconds for first failure
_BACKOFF_FACTOR = 2  # multiplier per consecutive failure
_BACKOFF_MAX = 300  # cap at 5 minutes


def run_poller(stop_event: Event, log_queue):
    """
    Polls each club's API for new completed ECG studies and triggers
    PDF download + encryption + email/SMS dispatch via ecg_send.
    """
    logging_config.setup_logging(log_queue)
    logging.info("ECG Poller started...")
    error_count = 0

    # try:
    while not stop_event.is_set():
        try:
            clubs = all_club_configs()
            # logging.info(f"Loaded {len(clubs)} club configurations")

            for club_name, club_config in clubs.items():
                if stop_event.is_set():
                    break
                csv_path = os.path.join(DATA_DIR, f"{club_name}.csv")
                # logging.info(f"Polling for club: {club_name}")

                # Maintain a separate seen file per club
                seen_ids = load_seen_ids(club_name)

                token_manager = TokenManager(club_name)
                access_token = token_manager.get_token()

                studies = fetch_all_studies(club_config["hostname"], access_token)

                new_reports = [
                    s
                    for s in studies.get("studies", [])
                    if s.get("sid")
                    and s.get("status") in [5, 6]
                    and s.get("sid") not in seen_ids
                ]

                if not new_reports:
                    # logging.info(f"[{club_name}] No new reports.")
                    continue

                logging.info(f"[{club_name}] {len(new_reports)} new reports found.")

                for study in new_reports:
                    if stop_event.is_set():
                        break

                    sid = study["sid"]
                    email = study.get("patient_ie_mrn")
                    # try:
                    #     download_pdf(club_config["hostname"], access_token, sid, email)
                    #     ecg_send.process_club_pdfs(
                    #         club_name, csv_path, stop_event
                    #     )  # process PDFs, send email/SMS
                    #     seen_ids.add(sid)
                    #     save_seen_ids(club_name, seen_ids)
                    #     logging.info(f"[{club_name}] Completed study {sid}")
                    # except Exception as e:
                    #     logging.exception(
                    #         f"[{club_name}] Failed processing study {sid}: {e}"
                    #     )
                    try:
                        download_pdf(
                            club_config["hostname"], club_name, access_token, sid, email
                        )
                        success = ecg_send.process_club_pdfs(
                            club_name, csv_path, stop_event
                        )
                        if success:
                            seen_ids.add(sid)
                            save_seen_ids(club_name, seen_ids)
                            logging.info(f"[{club_name}] Completed study {sid}")
                        else:
                            logging.warning(
                                f"[{club_name}] Partial failure for study {sid}, will retry"
                            )
                    except Exception as e:
                        logging.exception(
                            f"[{club_name}] Failed processing study {sid}: {e}"
                        )
                for f in os.listdir(TEMP_DIR):
                    if f.endswith(".sent"):
                        try:
                            os.remove(os.path.join(TEMP_DIR, f))
                        except:
                            logging.error(
                                f"Failed to remove temp file: {os.path.join(TEMP_DIR, f)}"
                            )

            # Reset error counter on successful loop
            error_count = 0
            # logging.info(f"Sleeping for {POLL_INTERVAL}s...")
            stop_event.wait(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("ECG Poller stopped gracefully.")

        except Exception as e:
            error_count += 1
            wait = min(
                _BACKOFF_BASE * (_BACKOFF_FACTOR ** (error_count - 1)), _BACKOFF_MAX
            )
            logging.exception(f"Polling error: {e}")
            logging.warning(f"Consecutive failure #{error_count}. Retrying in {wait}s.")
            stop_event.wait(wait)
            if error_count == 5:
                email_utils.send_email(
                    EMAIL_SENDER,
                    f"PDF Pipeline Failure - {club_name}",
                    f"Polling error:\n{type(e).__name__}: {e}",
                )
