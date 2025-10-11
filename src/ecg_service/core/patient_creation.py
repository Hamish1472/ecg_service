import requests
from ecg_service.utils import csv_utils
from ecg_service.config import get_endpoints


def upload_csv(access_token, hostname, csv_path):
    """Upload formatted CSV to the club API endpoint."""
    formatted_csv = csv_path.replace(".csv", "_formatted.csv")
    csv_utils.format_consent_csv(csv_path, formatted_csv)

    with open(formatted_csv, "rb") as f:
        files = {"file": ("patients.csv", f, "text/csv")}
        headers = {"Authorization": access_token}
        response = requests.post(
            get_endpoints(hostname)["CSV_URL"], headers=headers, files=files, timeout=15
        )
        response.raise_for_status()
    return response.json()
