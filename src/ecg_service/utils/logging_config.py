import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    log_filename = "logs/core.log"

    log_level = os.getenv("LOGLEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    log_format = "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"

    file_handler = TimedRotatingFileHandler(
        log_filename,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )

    file_handler.setFormatter(logging.Formatter(log_format))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[file_handler, console_handler],
    )
