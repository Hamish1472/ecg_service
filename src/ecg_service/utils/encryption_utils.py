import os
import subprocess
import shutil
import secrets
import string
import sqlite3
import logging
from datetime import datetime
from ecg_service.config import DATA_DIR
from ecg_service.config import PASSWORD_DB


def generate_password(length: int = 16) -> str:
    # base alphabet without ambiguous characters:
    # e.g. omit: l, I, 1, O, 0, o
    ambiguous = {"l", "I", "1", "O", "0", "o"}
    alphabet = "".join(
        ch for ch in (string.ascii_letters + string.digits) if ch not in ambiguous
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def store_password(db_path, filename, password, phone_number, club_name):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            filename TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            phone_number TEXT,
            club_name TEXT
        )
    """)
    c.execute(
        """
        INSERT OR REPLACE INTO passwords (filename, password, timestamp, phone_number, club_name)
        VALUES (?, ?, ?, ?, ?)
    """,
        (filename, password, datetime.now().isoformat(), phone_number, club_name),
    )
    conn.commit()
    conn.close()


def encrypt_pdf(input_path, password):
    pdf_dir = os.path.dirname(input_path)
    input = os.path.basename(input_path)

    cmd = [
        "qpdf",
        "--encrypt",
        password,
        password,
        "256",
        "--",
        input,
        "--replace-input",
    ]
    result = subprocess.run(cmd, cwd=pdf_dir, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(
            "qpdf failed (exit %s) on %s\nstdout: %s\nstderr: %s",
            result.returncode,
            input,
            result.stdout,
            result.stderr,
        )
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
