from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def load_project_env() -> Path:
    env_path = BASE_DIR / ".env"
    load_dotenv(env_path, override=False)

    env_local = BASE_DIR / ".env.local"
    if env_local.exists():
        load_dotenv(env_local, override=True)

    return env_path
