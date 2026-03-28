from __future__ import annotations

import subprocess
import webbrowser
from urllib.parse import quote_plus

from core.config_store import ConfigStore
from utils.logger import get_logger
from utils.security import is_risky_text, normalize_text


class ActionExecutor:
    def __init__(self, config_store: ConfigStore) -> None:
        self.config_store = config_store
        self.logger = get_logger()

    def can_handle_step(self, step: str) -> bool:
        normalized = normalize_text(step)
        return normalized.startswith("search web for ") or normalized.startswith("open ")

    def execute_steps(
        self,
        steps: list[str],
        confirm: bool = False,
        device_access_enabled: bool = False,
    ) -> dict[str, object]:
        settings = self.config_store.load_settings()
        actions: list[dict[str, object]] = []
        needs_confirmation = False

        if not device_access_enabled:
            blocked_actions = [
                {
                    "step": step,
                    "status": "blocked",
                    "reason": "Device access is disabled. The user must allow local automation during setup.",
                }
                for step in steps
            ]
            return {
                "summary": "Device automation is disabled for this user.",
                "actions": blocked_actions,
                "needs_confirmation": False,
            }

        for step in steps:
            normalized = normalize_text(step)
            if is_risky_text(normalized) and not confirm:
                needs_confirmation = True
                actions.append(
                    {
                        "step": step,
                        "status": "confirmation_required",
                        "reason": "Risky text detected.",
                    }
                )
                continue

            result = self._run_step(normalized, settings)
            actions.append(result)

        if needs_confirmation:
            return {
                "summary": "One or more actions need confirmation before Vijay will run them.",
                "actions": actions,
                "needs_confirmation": True,
            }

        success_count = len([item for item in actions if item["status"] in {"simulated", "executed"}])
        return {
            "summary": f"Processed {success_count} action(s).",
            "actions": actions,
            "needs_confirmation": False,
        }

    def _run_step(self, step: str, settings: dict[str, object]) -> dict[str, object]:
        if step.startswith("search web for "):
            query = step.replace("search web for ", "", 1).strip()
            url = str(settings["search_engine"]).format(query=quote_plus(query))
            return self._open_url(step, url, settings)

        if step.startswith("open "):
            target = step.replace("open ", "", 1).strip()
            aliases = settings.get("allowed_app_aliases", {})
            if isinstance(aliases, dict) and target in aliases:
                mapped = str(aliases[target])
                if mapped.startswith("http://") or mapped.startswith("https://"):
                    return self._open_url(step, mapped, settings)
                return self._launch_app(step, mapped, settings)
            if target.startswith("http://") or target.startswith("https://"):
                return self._open_url(step, target, settings)
            return {
                "step": step,
                "status": "blocked",
                "reason": f'Add "{target}" to config/settings.json before using it.',
            }

        return {
            "step": step,
            "status": "simulated",
            "reason": "No direct action matched. Vijay kept this as an assistant note.",
        }

    def _open_url(self, step: str, url: str, settings: dict[str, object]) -> dict[str, object]:
        if settings.get("dry_run", True):
            return {"step": step, "status": "simulated", "target": url}
        webbrowser.open(url)
        return {"step": step, "status": "executed", "target": url}

    def _launch_app(self, step: str, command: str, settings: dict[str, object]) -> dict[str, object]:
        if settings.get("dry_run", True):
            return {"step": step, "status": "simulated", "target": command}
        subprocess.Popen(command, shell=True)
        return {"step": step, "status": "executed", "target": command}
