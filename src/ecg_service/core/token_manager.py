import json
import logging
import os
import time
from multiprocessing import Lock
from functools import wraps
import requests

from ecg_service.core.tokens import get_access_token
from ecg_service.config import AUTH_DIR, get_endpoints
from ecg_service.core.clubs import load_club_config


class TokenManager:
    """
    Per-club token lifecycle manager.
    Handles caching, expiry, persistence, and safe refresh.
    Each club has its own token file: DATA_DIR/access_token_<club>.json
    """

    _global_lock = Lock()  # optional safety across processes

    def __init__(self, club_name: str):
        self.club_name = club_name
        self.club_config = load_club_config(club_name)
        self.endpoints = get_endpoints(self.club_config["hostname"])
        self.club_config.update(self.endpoints)

        self._token = None
        self._expiry = 0
        self._token_type = "Bearer"
        self._lock = Lock()
        self._cache_path = os.path.join(AUTH_DIR, f"access_token_{club_name}.json")

    # ----------------------------
    # Public API
    # ----------------------------
    def get_token(self):
        """Return a valid access token (refresh if needed)."""
        with self._lock:
            if self._token and time.time() < self._expiry:
                return f"{self._token_type} {self._token}"

            if self._load_from_disk() and time.time() < self._expiry:
                return f"{self._token_type} {self._token}"

            return self._refresh_locked()

    def refresh_token(self):
        """Force refresh regardless of cache."""
        with self._lock:
            return self._refresh_locked()

    # ----------------------------
    # Internal
    # ----------------------------
    def _refresh_locked(self):
        """Fetch and cache a new token."""
        logging.info(f"[{self.club_name}] Fetching new access token...")

        # Pass full club configuration as expected by tokens.py
        response = get_access_token(self.club_config, return_full=True)

        self._token = response["access_token"]
        self._token_type = response.get("token_type", "Bearer")
        self._expiry = time.time() + response.get("expires_in", 3600)
        self._save_to_disk()
        return f"{self._token_type} {self._token}"

    def _save_to_disk(self):
        """Save token data for persistence."""
        try:
            data = {
                "access_token": self._token,
                "token_type": self._token_type,
                "expiry": self._expiry,
            }
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
            with open(self._cache_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logging.warning(f"[{self.club_name}] Failed to save token cache: {e}")

    def _load_from_disk(self):
        """Load cached token if available."""
        try:
            if not os.path.exists(self._cache_path):
                return False
            with open(self._cache_path, "r") as f:
                data = json.load(f)
            self._token = data.get("access_token")
            self._token_type = data.get("token_type", "Bearer")
            self._expiry = data.get("expiry", 0)
            return True
        except Exception as e:
            logging.warning(f"[{self.club_name}] Failed to load token cache: {e}")
            return False


# ----------------------------
# Decorator for token reuse
# ----------------------------
def with_token_refresh(func):
    """
    Decorator for API calls needing a valid token.
    Expects first argument to be club_name.
    Automatically refreshes and retries on 401.
    """

    @wraps(func)
    def wrapper(club_name, *args, **kwargs):
        manager = TokenManager(club_name)
        token = manager.get_token()

        try:
            return func(token, club_name, *args, **kwargs)

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logging.info(f"[{club_name}] Token expired. Refreshing...")
                token = manager.refresh_token()
                return func(token, club_name, *args, **kwargs)
            raise

        except Exception as e:
            logging.error(f"[{club_name}] API call failed: {e}")
            raise

    return wrapper
