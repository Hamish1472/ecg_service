import logging
import os
import time
from threading import Event

from ecg_service.core import ecg_send
from ecg_service.config import POLL_INTERVAL, DATA_DIR
from ecg_service.core.token_manager import TokenManager
from ecg_service.core.studies import (
    fetch_all_studies,
    download_pdf,
    load_seen_ids,
    save_seen_ids,
)
from ecg_service.core.clubs import all_club_configs
from ecg_service.utils import logging_config


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
            logging.info(f"Loaded {len(clubs)} club configurations")

            for club_name, club_config in clubs.items():
                if stop_event.is_set():
                    break
                csv_path = os.path.join(DATA_DIR, f"{club_name}.csv")
                logging.info(f"Polling for club: {club_name}")

                # Maintain a separate seen file per club
                seen_ids = load_seen_ids(club_name)

                token_manager = TokenManager(club_name)
                access_token = token_manager.get_token()

                studies = fetch_all_studies(club_config["hostname"], access_token)

                new_reports = [
                    s
                    for s in studies.get("studies", [])
                    if s.get("sid")
                    and s.get("status") in [3, 4, 5, 6]
                    and s.get("sid") not in seen_ids
                ]

                if not new_reports:
                    logging.info(f"[{club_name}] No new reports.")
                    continue

                logging.info(f"[{club_name}] {len(new_reports)} new reports found.")

                for study in new_reports:
                    if stop_event.is_set():
                        break

                    sid = study["sid"]
                    email = study.get("patient_ie_mrn")
                    try:
                        download_pdf(
                            club_config["hostname"], access_token, sid, email
                        )
                        ecg_send.process_club_pdfs(
                            club_name, csv_path, stop_event
                        )  # process PDFs, send email/SMS
                        seen_ids.add(sid)
                        save_seen_ids(club_name, seen_ids)
                        logging.info(f"[{club_name}] Completed study {sid}")
                    except Exception as e:
                        logging.exception(
                            f"[{club_name}] Failed processing study {sid}: {e}"
                        )

            # Reset error counter on successful loop
            error_count = 0
            logging.info(f"Sleeping for {POLL_INTERVAL}s...")
            stop_event.wait(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("ECG Poller stopped gracefully.")

        except Exception as e:
            logging.exception(f"Polling error: {e}")
            error_count += 1
            if error_count >= 5:
                logging.error("Multiple polling failures, pausing before retry")
                stop_event.wait(10)
            else:
                stop_event.wait(1)
