import os
import subprocess
import shutil
import secrets
import string
import sqlite3
from datetime import datetime
from ecg_service.config import SEVEN_ZIP_PATH


def generate_password(length=16):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def store_password(db_path, filename, password):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS passwords (
            filename TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """
    )
    c.execute(
        """
        INSERT OR REPLACE INTO passwords (filename, password, timestamp)
        VALUES (?, ?, ?)
    """,
        (filename, password, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def compress_pdf(pdf_path, archive_path, password):
    pdf_dir = os.path.dirname(pdf_path)
    pdf_file = os.path.basename(pdf_path)
    cmd = [
        SEVEN_ZIP_PATH,
        "a",
        "-t7z",
        archive_path,
        pdf_file,
        f"-p{password}",
        "-mhe=on",
    ]
    subprocess.run(cmd, check=True, cwd=pdf_dir)


def zip_archive(archive_path, zip_path):
    shutil.make_archive(
        zip_path.replace(".zip", ""),
        "zip",
        root_dir=os.path.dirname(archive_path),
        base_dir=os.path.basename(archive_path),
    )
