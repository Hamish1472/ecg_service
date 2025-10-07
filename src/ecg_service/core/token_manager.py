import json
import logging
import os
import time
from multiprocessing import Lock
from functools import wraps
import requests
from ecg_service.core.tokens import get_access_token
from ecg_service.config import DATA_DIR

TOKEN_CACHE_PATH = os.path.join(DATA_DIR, "access_token.json")


class TokenManager:
    """
    Centralised manager for access token lifecycle.
    Handles caching, expiry, persistence and safe refresh.
    """

    _token = None
    _expiry = 0
    _token_type = "Bearer"
    _lock = Lock()

    @classmethod
    def get_token(cls):
        """Return a valid token, refreshing or loading if required."""
        with cls._lock:
            if cls._token and time.time() < cls._expiry:
                return f"{cls._token_type} {cls._token}"
            if cls._load_from_disk():
                if time.time() < cls._expiry:
                    return f"{cls._token_type} {cls._token}"
            return cls._refresh_locked()

    @classmethod
    def refresh_token(cls):
        """Force refresh, e.g. after HTTP 401."""
        with cls._lock:
            return cls._refresh_locked()

    @classmethod
    def _refresh_locked(cls):
        """Fetch new token and cache it."""
        logging.info("Fetching new access token from API...")
        response = get_access_token(return_full=True)
        cls._token = response["access_token"]
        cls._token_type = response.get("token_type", "Bearer")
        cls._expiry = time.time() + response.get("expires_in", 3600)
        cls._save_to_disk()
        return f"{cls._token_type} {cls._token}"

    @classmethod
    def _save_to_disk(cls):
        """Persist token details for use by other processes."""
        try:
            data = {
                "access_token": cls._token,
                "token_type": cls._token_type,
                "expiry": cls._expiry,
            }
            os.makedirs(os.path.dirname(TOKEN_CACHE_PATH), exist_ok=True)
            with open(TOKEN_CACHE_PATH, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logging.warning(f"Failed to save token cache: {e}")

    @classmethod
    def _load_from_disk(cls):
        """Load cached token if available."""
        try:
            if not os.path.exists(TOKEN_CACHE_PATH):
                return False
            with open(TOKEN_CACHE_PATH, "r") as f:
                data = json.load(f)
            cls._token = data.get("access_token")
            cls._token_type = data.get("token_type", "Bearer")
            cls._expiry = data.get("expiry", 0)
            return True
        except Exception as e:
            logging.warning(f"Failed to load token cache: {e}")
            return False


def with_token_refresh(func):
    """
    Decorator to ensure any API function always has a valid token.
    Retries once automatically if a 401 is returned.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        token = TokenManager.get_token()
        try:
            return func(token, *args, **kwargs)
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logging.info("Access token expired, refreshing and retrying...")
                token = TokenManager.refresh_token()
                return func(token, *args, **kwargs)
            raise
        except Exception as e:
            logging.error(e)

    return wrapper
