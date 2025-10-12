import os
import logging
import logging.handlers
import multiprocessing

_log_queue = None
_listener = None


def start_listener():
    global _log_queue, _listener
    if _listener is not None:
        return  # already running

    os.makedirs("logs", exist_ok=True)
    log_filename = "logs/core.log"

    log_format = "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_filename,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    _log_queue = multiprocessing.Queue(-1)
    _listener = logging.handlers.QueueListener(
        _log_queue, file_handler, console_handler, respect_handler_level=True
    )
    _listener.start()


def stop_listener():
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None


def get_queue():
    global _log_queue
    return _log_queue


def setup_logging(log_queue=None):
    """
    Configure logging for worker processes.

    If log_queue is provided, attach a QueueHandler so logs
    go through the main process QueueListener. Otherwise,
    fallback to basic console logging.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any existing handlers
    if root.hasHandlers():
        root.handlers.clear()

    if log_queue is not None:
        # Attach QueueHandler to send logs to main process listener
        queue_handler = logging.handlers.QueueHandler(log_queue)
        root.addHandler(queue_handler)
    else:
        # Fallback if no queue is provided (e.g., worker started before listener)
        formatter = logging.Formatter(
            "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
