import requests
import logging
from ecg_service.config import get_endpoints


def get_access_token(club_config: dict, return_full=False):
    payload = {
        "grant_type": "password",
        "client_id": club_config["client_id"],
        "client_secret": club_config["client_secret"],
        "username": club_config["username"],
        "password": club_config["password"],
    }
    response = requests.post(
        get_endpoints(club_config["hostname"])["OAUTH_URL"], data=payload
    )
    if response.status_code != 200:
        logging.info(f"QT API | status={response.status_code}")
    response.raise_for_status()
    data = response.json()
    return data if return_full else data["access_token"]
