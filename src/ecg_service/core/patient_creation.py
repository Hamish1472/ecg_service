import os
import requests
from ecg_service.utils import csv_utils
from ecg_service.config import DATA_DIR, CSV_URL, CSV_PATH


def upload_csv(access_token):
    """Upload formatted patient CSV to the API using the provided access token."""

    patient_list = os.path.join(DATA_DIR, "output.csv")
    csv_utils.format_consent_csv(CSV_PATH, patient_list)

    with open(patient_list, "rb") as f:
        files = {"file": ("output.csv", f, "text/csv")}
        response = requests.post(
            CSV_URL, headers={"Authorization": access_token}, files=files, timeout=10
        )
        response.raise_for_status()
    return response.json()
