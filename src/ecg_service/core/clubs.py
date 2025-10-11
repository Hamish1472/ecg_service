import os
import logging
import csv
from ecg_service.config import CLUBS_CONFIG_PATH

# Track already seen clubs across calls
_PREVIOUSLY_LOADED_CLUBS = set()


def all_club_configs() -> dict:
    """
    Load all club configurations from the central CSV file.

    Returns:
        dict[str, dict]: { club_name: {hostname, spreadsheet_id, folder_id, ...} }
    """
    global _PREVIOUSLY_LOADED_CLUBS

    clubs = {}
    if not os.path.exists(CLUBS_CONFIG_PATH):
        logging.warning(f"Club config file not found: {CLUBS_CONFIG_PATH}")
        return clubs

    with open(CLUBS_CONFIG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            club_name = row.get("club_name", "").strip()
            if not club_name:
                continue

            hostname = row.get("hostname", "").strip()

            clubs[club_name] = {
                "club_name": club_name,
                "spreadsheet_id": row.get("spreadsheet_id", "").strip(),
                "sheet_name": row.get("sheet_name", "").strip(),
                "folder_id": row.get("folder_id", "").strip(),
                "hostname": hostname,
                "client_id": row.get("client_id", "").strip(),
                "client_secret": row.get("client_secret", "").strip(),
                "username": row.get("username", "").strip(),
                "password": row.get("password", "").strip(),
            }

    new_clubs = set(clubs.keys()) - _PREVIOUSLY_LOADED_CLUBS
    if new_clubs:
        logging.info(
            f"New club configurations detected: {', '.join(sorted(new_clubs))}"
        )
        _PREVIOUSLY_LOADED_CLUBS.update(new_clubs)

    return clubs


def load_club_config(club_name: str) -> dict:
    """
    Return configuration for a specific club.
    """
    clubs = all_club_configs()
    club = clubs.get(club_name)
    if not club:
        raise ValueError(f"Club configuration for '{club_name}' not found")
    return club
