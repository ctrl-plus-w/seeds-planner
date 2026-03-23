import sys
from pathlib import Path

from dotenv import dotenv_values

BASE_URL = "https://permapeople.org/api"
REQUEST_DELAY = 0.5
PAGE_SIZE = 100

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict[str, str]:
    env = dotenv_values(PROJECT_ROOT / ".env")
    key_id = env.get("PERMAPEOPLE_ID")
    key_secret = env.get("PERMAPEOPLE_KEY")
    if not key_id or not key_secret:
        print(
            "Error: PERMAPEOPLE_ID and PERMAPEOPLE_KEY must be set in .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return {"id": key_id, "key": key_secret}
