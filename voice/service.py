from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from core.config_store import ConfigStore


class VoiceService:
    def __init__(self, config_store: ConfigStore) -> None:
        self.config_store = config_store

    def status(self) -> dict[str, Any]:
        voice = self.config_store.load_voice()
        return {
            "mode": voice.get("mode", "scaffold"),
            "lock_enabled": voice.get("lock_enabled", False),
            "profile_count": len(voice.get("authorized_profiles", {})),
            "similarity_threshold": voice.get("similarity_threshold", 0.8),
        }

    def train_voice(self, user_id: str, sample_reference: str | None = None) -> dict[str, Any]:
        voice = self.config_store.load_voice()
        reference = sample_reference or "default-sample"
        embedding_hash = hashlib.sha256(f"{user_id}:{reference}".encode("utf-8")).hexdigest()
        voice.setdefault("authorized_profiles", {})
        voice["authorized_profiles"][user_id] = {
            "embedding_hash": embedding_hash,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        voice["lock_enabled"] = True
        self.config_store.save_voice(voice)
        return {
            "message": "Voice profile scaffold saved locally. Replace scaffold mode with real embeddings in phase 2.",
            "voice_mode": voice.get("mode", "scaffold"),
            "lock_enabled": True,
        }

    def verify_voice(self, user_id: str, sample_reference: str | None = None) -> dict[str, Any]:
        voice = self.config_store.load_voice()
        profile = voice.get("authorized_profiles", {}).get(user_id)
        if not profile:
            return {
                "authorized": False,
                "message": "No trained voice profile was found for this user.",
            }
        reference = sample_reference or "default-sample"
        sample_hash = hashlib.sha256(f"{user_id}:{reference}".encode("utf-8")).hexdigest()
        authorized = sample_hash == profile.get("embedding_hash")
        return {
            "authorized": authorized,
            "message": (
                "Authorized user verified."
                if authorized
                else "Unauthorized user detected. Access denied."
            ),
        }
