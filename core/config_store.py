from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, file_name: str, default: dict[str, Any]) -> dict[str, Any]:
        path = self.config_dir / file_name
        if not path.exists():
            self._write_json(file_name, default)
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, file_name: str, payload: dict[str, Any]) -> None:
        path = self.config_dir / file_name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_settings(self) -> dict[str, Any]:
        defaults = {
            "app_name": "Vijay",
            "admin_email": "harkarshaurya@gmail.com",
            "host": "127.0.0.1",
            "port": 8000,
            "dry_run": True,
            "google_sign_in_enabled": True,
            "base_system_prompt": (
                "You are Vijay, a secure local-first AI assistant. "
                "Be helpful, calm, and operationally precise. "
                "Never claim you completed an action unless the automation context says it happened. "
                "Prefer safe automation, explain when device permission is missing, "
                "and keep responses useful for non-technical users."
            ),
            "default_user_system_prompt": (
                "Tailor your tone to the user, stay concise, and prioritize practical help."
            ),
            "allowed_origins": [
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            ],
            "allowed_app_aliases": {
                "android studio": "C:\\Program Files\\Android\\Android Studio\\bin\\studio64.exe",
                "claude code": "claude",
                "vs code": "code",
                "chatgpt": "https://chatgpt.com",
                "youtube": "https://www.youtube.com",
            },
            "search_engine": "https://www.google.com/search?q={query}",
        }
        current = self._read_json("settings.json", defaults)
        merged = {**defaults, **current}
        merged["allowed_app_aliases"] = {
            **defaults["allowed_app_aliases"],
            **current.get("allowed_app_aliases", {}),
        }
        env_admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        if env_admin_email:
            merged["admin_email"] = env_admin_email
        if merged != current:
            self._write_json("settings.json", merged)
        return merged

    def load_commands(self) -> dict[str, Any]:
        return self._read_json("commands.json", {"commands": []})

    def save_commands(self, payload: dict[str, Any]) -> None:
        self._write_json("commands.json", payload)

    def load_voice(self) -> dict[str, Any]:
        defaults = {
            "mode": "scaffold",
            "lock_enabled": False,
            "similarity_threshold": 0.8,
            "authorized_profiles": {},
        }
        current = self._read_json("voice.json", defaults)
        merged = {**defaults, **current}
        if merged != current:
            self._write_json("voice.json", merged)
        return merged

    def save_voice(self, payload: dict[str, Any]) -> None:
        self._write_json("voice.json", payload)
