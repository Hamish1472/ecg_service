import logging
import os
import shutil
from multiprocessing import Process, Event
from ecg_service.core.poller import run_poller
from ecg_service.core.google_API import run_google_sync
from ecg_service.utils.logging_config import setup_logging
from ecg_service.config import TEMP_DIR


def cleanup_temp():
    """Remove TEMP directory safely."""
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
            logging.info(f"Cleaned up TEMP directory: {TEMP_DIR}")
        except Exception as e:
            logging.warning(f"Failed to remove TEMP directory {TEMP_DIR}: {e}")


def main():
    setup_logging()
    logging.info("#" * 80)
    logging.info("ECG Report Service starting up...")

    stop_event = Event()  # signal to stop child processes

    google_proc = Process(target=run_google_sync, args=(stop_event,), name="GoogleSync")
    poller_proc = Process(target=run_poller, args=(stop_event,), name="ECGPoller")

    google_proc.start()
    poller_proc.start()

    try:
        google_proc.join()
        poller_proc.join()

    except KeyboardInterrupt:
        logging.info("Service stopping... sending stop signals to child processes.")
        stop_event.set()
        google_proc.join()
        poller_proc.join()
        logging.info("All processes terminated cleanly.")

    except Exception as e:
        logging.exception(f"Unexpected fatal error: {e}")
        stop_event.set()
        google_proc.join()
        poller_proc.join()

    finally:
        cleanup_temp()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    main()
