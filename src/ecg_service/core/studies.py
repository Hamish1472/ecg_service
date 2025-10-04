import os
import json
import logging
import requests
from ecg_service.config import (
    STUDIES_URL,
    PDF_URL,
    TEMP_DIR,
    SEEN_IDS_FILE,
)


def fetch_all_studies(access_token):
    offset, limit = 0, 1000
    all_studies = []
    while True:
        response = requests.get(
            STUDIES_URL,
            headers={"Authorization": access_token},
            params={
                "order_by": "studies.recorded_at",
                "order_by_direction": "DESC",
                "offset": offset,
                "limit": limit,
            },
        )
        response.raise_for_status()
        data = response.json()
        all_studies.extend(data["studies"])

        if data["current_page"] == data["last_page"]:
            break
        offset += limit
    return {"studies": all_studies}


def download_pdf(access_token, sid, email):
    response = requests.get(
        PDF_URL.format(sid=sid),
        headers={"Authorization": access_token},
    )
    response.raise_for_status()
    os.makedirs(TEMP_DIR, exist_ok=True)
    file_path = os.path.join(TEMP_DIR, f"{email}.pdf")
    with open(file_path, "wb") as f:
        f.write(response.content)
    logging.info(f"Downloaded report {sid}")


def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(seen_ids), f)
