import os
import json
import logging
import requests
from ecg_service.config import (
    get_endpoints,
    TEMP_DIR,
    DATA_DIR,
)


def fetch_all_studies(hostname, access_token):
    offset, limit = 0, 1000
    all_studies = []
    while True:
        response = requests.get(
            get_endpoints(hostname)["STUDIES_URL"],
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


def download_pdf(hostname, access_token, sid, email):
    response = requests.get(
        get_endpoints(hostname)["PDF_URL"].format(sid=sid),
        headers={"Authorization": access_token},
    )
    response.raise_for_status()
    os.makedirs(TEMP_DIR, exist_ok=True)
    file_path = os.path.join(TEMP_DIR, f"{email}.pdf")
    with open(file_path, "wb") as f:
        f.write(response.content)
    logging.info(f"Downloaded report {sid}")


def _club_seen_ids_path(club_name: str) -> str:
    """Return the path to the seen IDs file for a specific club."""
    return os.path.join(DATA_DIR, f"seen_ids_{club_name.lower()}.json")


def load_seen_ids(club_name: str):
    """Load the set of seen study IDs for a specific club."""
    seen_path = _club_seen_ids_path(club_name)
    if os.path.exists(seen_path):
        try:
            with open(seen_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logging.warning(f"Failed to load seen IDs for {club_name}: {e}")
    return set()


def save_seen_ids(club_name: str, seen_ids):
    """Save the set of seen study IDs for a specific club."""
    seen_path = _club_seen_ids_path(club_name)
    try:
        os.makedirs(os.path.dirname(seen_path), exist_ok=True)
        with open(seen_path, "w", encoding="utf-8") as f:
            json.dump(list(seen_ids), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Failed to save seen IDs for {club_name}: {e}")
