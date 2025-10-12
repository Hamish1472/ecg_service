import logging
import sys
from multiprocessing import Process, Event
from time import sleep

from ecg_service.core.poller import run_poller
from ecg_service.core.google_API import run_google_sync
from ecg_service.utils import logging_config
from ecg_service.config import TEMP_DIR_OBJ


def supervise(name: str, target, stop_event, log_queue, restart_delay: int = 5):
    """
    Supervises a subprocess, restarting it if it exits unexpectedly.
    """
    while not stop_event.is_set():
        proc = Process(target=target, args=(stop_event, log_queue), name=name)
        proc.start()
        logging.info(f"{name} started with PID {proc.pid}")
        proc.join()

        if stop_event.is_set():
            logging.info(f"{name} received stop signal, exiting supervisor loop.")
            break

        if proc.exitcode != 0:
            logging.warning(
                f"{name} exited with code {proc.exitcode}. Restarting in {restart_delay}s."
            )
            sleep(restart_delay)
        else:
            logging.info(f"{name} exited cleanly. Restarting in {restart_delay}s.")
            sleep(restart_delay)


def main():
    logging_config.start_listener()
    log_queue = logging_config.get_queue()
    logging_config.setup_logging(log_queue)
    logging.info("#" * 80)
    logging.info("ECG Report Service starting up...")

    stop_event = Event()

    google_supervisor = Process(
        target=supervise,
        args=("GoogleSync", run_google_sync, stop_event, log_queue),
        name="GoogleSupervisor",
    )

    poller_supervisor = Process(
        target=supervise,
        args=("ECGPoller", run_poller, stop_event, log_queue),
        name="PollerSupervisor",
    )
    google_supervisor.start()
    poller_supervisor.start()

    try:
        google_supervisor.join()
        poller_supervisor.join()

    except KeyboardInterrupt:
        logging.info("Service stopping... sending stop signals to supervisors.")
        stop_event.set()
        google_supervisor.join()
        poller_supervisor.join()
        logging.info("All processes terminated cleanly.")
        sys.exit(0)

    except Exception as e:
        logging.exception(f"Unexpected fatal error: {e}")
        stop_event.set()
        google_supervisor.join()
        poller_supervisor.join()
        sys.exit(1)

    finally:
        TEMP_DIR_OBJ.cleanup()
        logging.info("Temporary directories cleaned.")
        logging.info("Shutdown complete.")
        logging_config.stop_listener()


if __name__ == "__main__":
    main()
