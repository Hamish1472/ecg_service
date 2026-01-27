import os
import subprocess
import shutil
import secrets
import string
import sqlite3
from datetime import datetime

from ecg_service.config import PASSWORD_DB


def generate_password(length: int = 16) -> str:
    # base alphabet without ambiguous characters:
    # e.g. omit: l, I, 1, O, 0, o
    ambiguous = {"l", "I", "1", "O", "0", "o"}
    alphabet = "".join(
        ch for ch in (string.ascii_letters + string.digits) if ch not in ambiguous
    )
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


def encrypt_pdf(input_path, password):
    pdf_dir = os.path.dirname(input_path)
    input = os.path.basename(input_path)
    # output = os.path.basename(output_path)
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
    subprocess.run(cmd, check=True, cwd=pdf_dir)


if __name__ == "__main__":
    directory = (
        "C:\\Users\\Hamish\\Documents\\Programming\\Python\\ecg_service\\_misc\\input"
    )
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        password = generate_password()
        encrypt_pdf(path, password)
        store_password(PASSWORD_DB, name, password)

# def compress_pdf(pdf_path, archive_path, password):
#     pdf_dir = os.path.dirname(pdf_path)
#     pdf_file = os.path.basename(pdf_path)
#     cmd = [
#         SEVEN_ZIP_PATH,
#         "a",
#         "-t7z",
#         archive_path,
#         pdf_file,
#         f"-p{password}",
#         "-mhe=on",
#     ]
#     subprocess.run(cmd, check=True, cwd=pdf_dir)


# def zip_archive(archive_path, zip_path):
#     shutil.make_archive(
#         zip_path.replace(".zip", ""),
#         "zip",
#         root_dir=os.path.dirname(archive_path),
#         base_dir=os.path.basename(archive_path),
#     )
