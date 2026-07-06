"""Application configuration loaded from CLI args, env, and ~/.openlink/settings.json."""

import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

OPENLINK_DIR = Path.home() / ".openlink"
SETTINGS_FILE = OPENLINK_DIR / "settings.json"


def load_or_create_token() -> str:
    """Load existing token or generate a new 64-hex-char token."""
    OPENLINK_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data.get("token"), str) and data["token"]:
                return data["token"]
        except (json.JSONDecodeError, OSError):
            pass

    token = secrets.token_hex(32)
    settings = {"token": token, "created_at": datetime.now().isoformat()}
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return token


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENLINK_",
        case_sensitive=False,
    )

    root_dir: str = Field(default_factory=os.getcwd)
    port: int = 39527
    timeout: int = 60  # seconds
    token: str = ""

    def model_post_init(self, __context):
        if not self.token:
            self.token = load_or_create_token()
