"""Environment-driven configuration for the test framework.

Every knob has a working local default, so ``pytest`` runs with no setup at
all; CI and Docker override them through environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    """Read a boolean env var, accepting the usual truthy spellings."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    """Resolved settings for one test run."""

    base_url: str
    api_url: str
    timeout: float
    headless: bool
    slow_mo: int
    db_path: Path
    browser_channel: str | None

    @classmethod
    def from_env(cls) -> "Config":
        """Build a config from the current environment."""
        base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        return cls(
            base_url=base_url,
            api_url=os.getenv("API_URL", f"{base_url}/api").rstrip("/"),
            timeout=float(os.getenv("TIMEOUT", "10")),
            headless=_bool("HEADLESS", True),
            slow_mo=int(os.getenv("SLOW_MO", "0")),
            db_path=Path(os.getenv("DB_PATH", str(REPO_ROOT / "commission.db"))).resolve(),
            browser_channel=os.getenv("BROWSER_CHANNEL") or None,
        )


config = Config.from_env()
