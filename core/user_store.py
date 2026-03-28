from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from core.config_store import ConfigStore


class UserStore:
    def __init__(self, data_dir: Path, config_store: ConfigStore) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "user_store.json"
        self.lock = Lock()
        self.config_store = config_store
        if not self.file_path.exists():
            self.file_path.write_text(
                json.dumps({"users": [], "sessions": {}}, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict[str, Any]:
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _admin_email(self) -> str:
        settings = self.config_store.load_settings()
        return str(settings.get("admin_email", "harkarshaurya@gmail.com")).strip().lower()

    def _default_prompt(self) -> str:
        settings = self.config_store.load_settings()
        return str(settings.get("default_user_system_prompt", "")).strip()

    def upsert_google_user(
        self,
        email: str,
        google_sub: str,
        name: str | None = None,
        picture: str | None = None,
    ) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            payload = self._load()
            existing = next(
                (
                    user
                    for user in payload["users"]
                    if user["email"] == normalized_email or user.get("google_sub") == google_sub
                ),
                None,
            )
            role = "admin" if normalized_email == self._admin_email() else "user"
            if existing:
                existing.update(
                    {
                        "email": normalized_email,
                        "google_sub": google_sub,
                        "name": name or existing.get("name") or normalized_email.split("@")[0],
                        "picture": picture or existing.get("picture", ""),
                        "provider": "google",
                        "role": role,
                        "last_login_at": now,
                    }
                )
                user = existing
            else:
                user = {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"google:{google_sub}")),
                    "email": normalized_email,
                    "name": name or normalized_email.split("@")[0],
                    "picture": picture or "",
                    "provider": "google",
                    "role": role,
                    "google_sub": google_sub,
                    "system_prompt": self._default_prompt(),
                    "device_access_enabled": False,
                    "device_access_configured": False,
                    "created_at": now,
                    "last_login_at": now,
                }
                payload["users"].append(user)
            self._save(payload)
        return user

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            payload = self._load()
            payload["sessions"][token] = {
                "user_id": user_id,
                "created_at": now,
            }
            self._save(payload)
        return token

    def clear_session(self, token: str) -> None:
        with self.lock:
            payload = self._load()
            payload["sessions"].pop(token, None)
            self._save(payload)

    def get_user_by_session(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        with self.lock:
            payload = self._load()
            session = payload["sessions"].get(token)
            if not session:
                return None
            return next((user for user in payload["users"] if user["id"] == session["user_id"]), None)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.lock:
            payload = self._load()
            return next((user for user in payload["users"] if user["id"] == user_id), None)

    def update_user(
        self,
        user_id: str,
        *,
        prompt: str | None = None,
        device_access_enabled: bool | None = None,
        device_access_configured: bool | None = None,
    ) -> dict[str, Any] | None:
        with self.lock:
            payload = self._load()
            user = next((item for item in payload["users"] if item["id"] == user_id), None)
            if not user:
                return None
            if prompt is not None:
                user["system_prompt"] = prompt.strip()
            if device_access_enabled is not None:
                user["device_access_enabled"] = device_access_enabled
            if device_access_configured is not None:
                user["device_access_configured"] = device_access_configured
            self._save(payload)
            return user

    def list_users(self) -> list[dict[str, Any]]:
        with self.lock:
            payload = self._load()
            return sorted(
                payload["users"],
                key=lambda item: (
                    item.get("role") != "admin",
                    item.get("email", ""),
                ),
            )

