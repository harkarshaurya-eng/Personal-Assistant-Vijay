from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class HistoryStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "local_store.json"
        self.lock = Lock()
        if not self.file_path.exists():
            self.file_path.write_text(
                json.dumps({"conversations": [], "actions": []}, indent=2),
                encoding="utf-8",
            )

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_conversation(self, record: dict[str, Any]) -> None:
        with self.lock:
            payload = self._load()
            payload["conversations"].append(record)
            self._save(payload)

    def save_action(self, record: dict[str, Any]) -> None:
        with self.lock:
            payload = self._load()
            payload["actions"].append(record)
            self._save(payload)

    def fetch_history(self, user_id: str, limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        with self.lock:
            payload = self._load()
        conversations = [item for item in payload["conversations"] if item["user_id"] == user_id]
        actions = [item for item in payload["actions"] if item["user_id"] == user_id]
        return {
            "conversations": list(reversed(conversations[-limit:])),
            "actions": list(reversed(actions[-limit:])),
        }

