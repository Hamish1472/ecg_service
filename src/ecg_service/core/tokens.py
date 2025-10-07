import requests
import logging
from ecg_service.config import (
    OAUTH_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    QT_USERNAME,
    QT_PASSWORD,
)


def get_access_token(return_full=False):
    payload = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": QT_USERNAME,
        "password": QT_PASSWORD,
    }

    response = requests.post(OAUTH_URL, data=payload)
    if response.status_code != 200:
        logging.info(f"QT API | status={response.status_code}")
    response.raise_for_status()

    data = response.json()
    return data if return_full else data["access_token"]


# def refresh_access_token(refresh_token):
#     response = requests.get(
#         OAUTH_URL,
#         data={
#             "grant_type": "refresh_token",
#             "refresh_token": refresh_token,
#             "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET,
#         },
#     )
#     response.raise_for_status()
#     return response.json()["access_token"]
