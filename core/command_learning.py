from __future__ import annotations

import re
from typing import Any

from core.config_store import ConfigStore
from utils.security import normalize_text

LEARN_PATTERN = re.compile(r"^when i say\s+(.+?)\s*(?:->|-|:)\s*(.+)$", re.IGNORECASE)


class CommandLearningService:
    def __init__(self, config_store: ConfigStore) -> None:
        self.config_store = config_store

    def learn_from_text(self, instruction: str) -> dict[str, Any]:
        match = LEARN_PATTERN.match(instruction.strip())
        if not match:
            raise ValueError("Use the format: When I say <trigger> - <actions>")
        trigger = normalize_text(match.group(1))
        steps = self._parse_steps(match.group(2))
        commands = self.config_store.load_commands()
        existing = next(
            (item for item in commands["commands"] if item["trigger"] == trigger),
            None,
        )
        if existing:
            existing["steps"] = steps
        else:
            commands["commands"].append({"trigger": trigger, "steps": steps})
        self.config_store.save_commands(commands)
        return {"trigger": trigger, "steps": steps}

    def _parse_steps(self, raw_actions: str) -> list[str]:
        text = raw_actions.strip()
        if text.lower().startswith("open "):
            remainder = text[5:]
            parts = re.split(r",|\band\b", remainder, flags=re.IGNORECASE)
            return [f"open {normalize_text(part)}" for part in parts if part.strip()]
        return [normalize_text(part) for part in re.split(r",|\band\b", text) if part.strip()]

    def find_command(self, message: str) -> dict[str, Any] | None:
        normalized = normalize_text(message)
        commands = self.config_store.load_commands()["commands"]
        return next((item for item in commands if item["trigger"] == normalized), None)

