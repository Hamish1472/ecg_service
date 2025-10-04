import os
import logging


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    log_filename = "logs/core.log"

    # Get log level from environment or default to INFO
    log_level = os.getenv("LOGLEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Define a consistent format including process name
    log_format = "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"

    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_filename, mode="a", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logging.info("#" * 80)
