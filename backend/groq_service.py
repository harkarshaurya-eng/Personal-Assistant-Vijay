from __future__ import annotations

import os
from typing import Any

import httpx

from utils.env_loader import load_project_env


class GroqService:
    def __init__(self) -> None:
        load_project_env()
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_reply(
        self,
        *,
        settings: dict[str, Any],
        user_profile: dict[str, Any],
        user_message: str,
        history: list[dict[str, Any]],
        action_summary: str | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if not self.api_key:
            return None

        system_parts = [
            str(settings.get("base_system_prompt", "")).strip(),
            f"Assistant name: {settings.get('app_name', 'Vijay')}.",
            f"Current user email: {user_profile.get('email', 'unknown')}.",
            (
                "The current user is the global admin and can audit every Vijay user."
                if user_profile.get("role") == "admin"
                else "This is a standard Vijay user."
            ),
            (
                "Local device control is enabled for this user."
                if user_profile.get("device_access_enabled")
                else "Local device control is disabled until the user grants permission."
            ),
        ]
        user_prompt = str(user_profile.get("system_prompt", "")).strip()
        if user_prompt:
            system_parts.append(f"User-specific system prompt: {user_prompt}")
        if action_summary:
            system_parts.append(f"Automation context: {action_summary}")
        if actions:
            system_parts.append(f"Latest automation actions: {actions}")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "\n".join(part for part in system_parts if part)}
        ]

        for item in history[-6:]:
            if item.get("message"):
                messages.append({"role": "user", "content": str(item["message"])})
            if item.get("response"):
                messages.append({"role": "assistant", "content": str(item["response"])})

        messages.append({"role": "user", "content": user_message})

        response = httpx.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.4,
                "messages": messages,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return {
            "content": content,
            "provider": "groq",
            "model": self.model,
        }
