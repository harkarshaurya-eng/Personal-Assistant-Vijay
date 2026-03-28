from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseService:
    def __init__(self) -> None:
        load_dotenv()
        self.url = os.getenv("SUPABASE_URL", "").strip()
        self.anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.client = self._create_client(self.anon_key)
        self.service_client = self._create_client(self.service_role_key)
        self.runtime_disabled = False

    def _create_client(self, key: str) -> Client | None:
        if not self.url or not key:
            return None
        return create_client(self.url, key)

    def is_configured(self) -> bool:
        return self.client is not None and not self.runtime_disabled

    def logging_ready(self) -> bool:
        return self.service_client is not None and not self.runtime_disabled

    def _disable_runtime(self) -> None:
        self.runtime_disabled = True

    def signup(self, email: str, password: str) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("Supabase is not configured.")
        response = self.client.auth.sign_up({"email": email, "password": password})
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if user:
            try:
                self.ensure_user_profile(str(user.id), email)
            except Exception:
                pass
        return {
            "user_id": str(user.id) if user else None,
            "email": getattr(user, "email", email) if user else email,
            "access_token": getattr(session, "access_token", None) if session else None,
            "refresh_token": getattr(session, "refresh_token", None) if session else None,
        }

    def login(self, email: str, password: str) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("Supabase is not configured.")
        response = self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if user:
            try:
                self.ensure_user_profile(str(user.id), getattr(user, "email", email))
            except Exception:
                pass
        return {
            "user_id": str(user.id) if user else None,
            "email": getattr(user, "email", email) if user else email,
            "access_token": getattr(session, "access_token", None) if session else None,
            "refresh_token": getattr(session, "refresh_token", None) if session else None,
        }

    def get_user_from_token(self, access_token: str) -> dict[str, Any] | None:
        if not self.client or not access_token:
            return None
        try:
            response = self.client.auth.get_user(access_token)
            user = getattr(response, "user", None)
        except Exception:
            self._disable_runtime()
            return None
        if not user:
            return None
        return {"id": str(user.id), "email": user.email}

    def ensure_user_profile(self, user_id: str, email: str) -> None:
        self.upsert_user_profile({"id": user_id, "email": email})

    def upsert_user_profile(self, profile: dict[str, Any]) -> None:
        client = self.service_client
        if not client:
            return
        payload = {
            "id": profile["id"],
            "email": profile["email"],
            "name": profile.get("name"),
            "picture_url": profile.get("picture"),
            "provider": profile.get("provider", "google"),
            "role": profile.get("role", "user"),
            "google_sub": profile.get("google_sub"),
            "system_prompt": profile.get("system_prompt", ""),
            "device_access_enabled": profile.get("device_access_enabled", False),
            "device_access_configured": profile.get("device_access_configured", False),
            "created_at": profile.get("created_at"),
            "last_login_at": profile.get("last_login_at"),
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        try:
            client.table("users").upsert(payload).execute()
        except Exception:
            self._disable_runtime()

    def log_conversation(self, record: dict[str, Any]) -> None:
        client = self.service_client
        if not client:
            return
        payload = {
            "user_id": record["user_id"],
            "message": record["message"],
            "response": record["response"],
            "timestamp": record["timestamp"],
        }
        try:
            client.table("conversations").insert(payload).execute()
        except Exception:
            self._disable_runtime()

    def log_action(self, record: dict[str, Any]) -> None:
        client = self.service_client
        if not client:
            return
        try:
            client.table("actions").insert(record).execute()
        except Exception:
            self._disable_runtime()

    def fetch_history(self, user_id: str, limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        client = self.service_client
        if not client:
            return {"conversations": [], "actions": []}
        try:
            conversations = (
                client.table("conversations")
                .select("*")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            actions = (
                client.table("actions")
                .select("*")
                .eq("user_id", user_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception:
            self._disable_runtime()
            return {"conversations": [], "actions": []}

        return {
            "conversations": list(getattr(conversations, "data", []) or []),
            "actions": list(getattr(actions, "data", []) or []),
        }

    def fetch_all_users(self, limit: int = 200) -> list[dict[str, Any]]:
        client = self.service_client
        if not client:
            return []
        try:
            response = (
                client.table("users")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception:
            self._disable_runtime()
            return []
        return list(getattr(response, "data", []) or [])

    def fetch_all_conversations(
        self,
        *,
        limit: int = 200,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self.service_client
        if not client:
            return []
        query = client.table("conversations").select("*").order("timestamp", desc=True).limit(limit)
        if user_id:
            query = query.eq("user_id", user_id)
        try:
            response = query.execute()
        except Exception:
            self._disable_runtime()
            return []
        return list(getattr(response, "data", []) or [])

    def fetch_all_actions(
        self,
        *,
        limit: int = 200,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self.service_client
        if not client:
            return []
        query = client.table("actions").select("*").order("timestamp", desc=True).limit(limit)
        if user_id:
            query = query.eq("user_id", user_id)
        try:
            response = query.execute()
        except Exception:
            self._disable_runtime()
            return []
        return list(getattr(response, "data", []) or [])
