import logging
import os
import datetime
import time
from ecg_service.core import ecg_send
from ecg_service.config import POLL_INTERVAL, DATA_DIR
from ecg_service.core.tokens import get_access_token
from ecg_service.core.studies import (
    fetch_all_studies,
    download_pdf,
    load_seen_ids,
    save_seen_ids,
)
from ecg_service.utils import logging_config, cleanup

logging_config.setup_logging()


def run_poller(stop_event):
    logging.info("ECG Poller started...")
    seen_ids = load_seen_ids()
    error_count = 0

    while not stop_event.is_set():
        try:
            access_token = f"Bearer {get_access_token()}"
            studies = fetch_all_studies(access_token)

            new_reports = [
                s
                for s in studies["studies"]
                if s.get("sid")
                and s.get("status") in [3, 4, 5, 6]
                and s.get("sid") not in seen_ids
            ]

            if new_reports:
                logging.info(f"{len(new_reports)} new reports detected")
                for study in new_reports:
                    if stop_event.is_set():
                        break
                    sid = study["sid"]
                    email = study["patient_ie_mrn"]
                    download_pdf(access_token, sid, email)
                    ecg_send.main()  # handles compression/email/SMS
                    seen_ids.add(sid)
                    save_seen_ids(seen_ids)
            else:
                logging.info("No new reports found.")

            cleanup.cleanup_old_csvs(DATA_DIR, 30)

            error_count = 0
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            logging.error(f"Polling error: {e}")
            error_count += 1
            if error_count >= 5:
                logging.error("Multiple polling failures, pausing before retry")
                time.sleep(10)
            else:
                time.sleep(1)

    logging.info("ECG Poller stopped gracefully.")
