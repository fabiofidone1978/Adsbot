"""
API keys and role helpers for Adsbot

- Loads ADMIN and USER API keys from environment variables
- Provides `get_role(api_key)` helper returning 'admin', 'user', or None

SECURITY: Do NOT commit secrets into the repository. Store keys in a secret manager
or environment variables. If a key was exposed (e.g. pasted in chat), rotate it
immediately in your provider dashboard.
"""

import os
from typing import Set, Optional

# Optional: load variables from a local `.env` when present (development convenience).
# We import `load_dotenv` if available, but do not require it at runtime.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # dotenv not installed or .env not present — environment variables will be read from OS env
    pass


def _load_keys_from_env(var_name: str) -> Set[str]:
    raw = os.getenv(var_name, "")
    if not raw:
        return set()
    return set(k.strip() for k in raw.split(",") if k.strip())


# Environment variable names (configurable)
ADMIN_ENV = "ADMIN_API_KEYS"  # comma-separated admin keys
USER_ENV = "USER_API_KEYS"    # comma-separated normal user keys

# Load at import time; functions read these sets
ADMIN_KEYS: Set[str] = _load_keys_from_env(ADMIN_ENV)
USER_KEYS: Set[str] = _load_keys_from_env(USER_ENV)


def reload_keys() -> None:
    """Reload keys from environment (call after changing env vars at runtime).
    Useful for long running processes that update env vars via external means.
    """
    global ADMIN_KEYS, USER_KEYS
    ADMIN_KEYS = _load_keys_from_env(ADMIN_ENV)
    USER_KEYS = _load_keys_from_env(USER_ENV)


def get_role(api_key: str) -> Optional[str]:
    """Return role for given api_key.

    Returns:
      - 'admin' for admin keys
      - 'user' for normal keys
      - None if key unknown
    """
    if not api_key:
        return None
    if api_key in ADMIN_KEYS:
        return "admin"
    if api_key in USER_KEYS:
        return "user"
    return None


def is_admin(api_key: str) -> bool:
    return get_role(api_key) == "admin"


def is_user(api_key: str) -> bool:
    return get_role(api_key) == "user"
