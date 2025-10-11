import logging
from multiprocessing import Process, Event
from ecg_service.core.poller import run_poller
from ecg_service.core.google_API import run_google_sync
from ecg_service.utils.logging_config import setup_logging
from ecg_service.config import TEMP_DIR_OBJ


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
        # cleanup_temp()
        TEMP_DIR_OBJ.cleanup()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    main()
