import os
import logging
import csv
import json
from ecg_service.config import CLUBS_CONFIG_PATH, TEMP_DIR_OBJ

from threading import Lock

CACHE_FILE = os.path.join(TEMP_DIR_OBJ.name, "seen_clubs.json")
_cache_lock = Lock()


def _load_seen():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try:
            return set(json.load(f))
        except Exception:
            return set()


def _save_seen(seen):
    with _cache_lock:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(seen), f)


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
                "hostname": hostname,
                "spreadsheet_id": row.get("spreadsheet_id", "").strip(),
                "sheet_name": row.get("sheet_name", "").strip(),
                "folder_id": row.get("folder_id", "").strip(),
                "client_id": row.get("client_id", "").strip(),
                "client_secret": row.get("client_secret", "").strip(),
                "username": row.get("username", "").strip(),
                "password": row.get("password", "").strip(),
            }

    seen = _load_seen()
    new_clubs = set(clubs.keys()) - seen
    if new_clubs:
        logging.info(
            f"New club configurations detected: {', '.join(sorted(new_clubs))}"
        )
        seen.update(new_clubs)
        _save_seen(seen)
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
