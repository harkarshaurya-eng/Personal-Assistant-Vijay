from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from actions.executor import ActionExecutor
from backend.supabase_service import SupabaseService
from core.command_learning import CommandLearningService
from core.config_store import ConfigStore
from core.history import HistoryStore
from utils.logger import get_logger
from utils.security import normalize_text
from voice.service import VoiceService


class AssistantService:
    def __init__(
        self,
        config_store: ConfigStore,
        history_store: HistoryStore,
        supabase_service: SupabaseService,
        command_service: CommandLearningService,
        action_executor: ActionExecutor,
        voice_service: VoiceService,
    ) -> None:
        self.config_store = config_store
        self.history_store = history_store
        self.supabase_service = supabase_service
        self.command_service = command_service
        self.action_executor = action_executor
        self.voice_service = voice_service
        self.logger = get_logger()

    def handle_message(
        self,
        user_id: str,
        user_email: str,
        message: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        normalized = normalize_text(message)
        if normalized == "train voice":
            result = self.voice_service.train_voice(user_id, "manual-ui-trigger")
            reply = result["message"]
            actions = [result]
            self.log_action(user_id, "voice_training", result)
        elif normalized.startswith("when i say "):
            learned = self.command_service.learn_from_text(message)
            reply = f'Saved command "{learned["trigger"]}".'
            actions = [{"type": "command_learned", **learned}]
            self.log_action(user_id, "command_learned", learned)
        else:
            learned_command = self.command_service.find_command(message)
            if learned_command:
                execution = self.action_executor.execute_steps(
                    learned_command["steps"],
                    confirm=confirm,
                )
                reply = execution["summary"]
                actions = execution["actions"]
                for action in actions:
                    self.log_action(user_id, "command_executed", action)
                response = {
                    "response": reply,
                    "actions": actions,
                    "needs_confirmation": execution["needs_confirmation"],
                    "command_saved": False,
                }
                self.log_conversation(user_id, user_email, message, reply)
                return response

            execution = self.action_executor.execute_steps([message], confirm=confirm)
            reply = execution["summary"]
            actions = execution["actions"]
            for action in actions:
                self.log_action(user_id, "direct_action", action)

        self.log_conversation(user_id, user_email, message, reply)
        return {
            "response": reply,
            "actions": actions,
            "needs_confirmation": any(
                action.get("status") == "confirmation_required" for action in actions
            ),
            "command_saved": normalized.startswith("when i say "),
        }

    def log_conversation(
        self,
        user_id: str,
        user_email: str,
        message: str,
        response: str,
    ) -> None:
        record = {
            "user_id": user_id,
            "email": user_email,
            "message": message,
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.history_store.save_conversation(record)
        try:
            self.supabase_service.log_conversation(record)
        except Exception:
            self.logger.exception("Supabase conversation log failed")

    def log_action(self, user_id: str, action_type: str, details: dict[str, Any]) -> None:
        record = {
            "user_id": user_id,
            "action_type": action_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.history_store.save_action(record)
        try:
            self.supabase_service.log_action(record)
        except Exception:
            self.logger.exception("Supabase action log failed")
