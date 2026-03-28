from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from actions.executor import ActionExecutor
from backend.groq_service import GroqService
from backend.supabase_service import SupabaseService
from core.command_learning import CommandLearningService
from core.config_store import ConfigStore
from core.history import HistoryStore
from core.user_store import UserStore
from utils.logger import get_logger
from utils.security import normalize_text
from voice.service import VoiceService


class AssistantService:
    def __init__(
        self,
        config_store: ConfigStore,
        history_store: HistoryStore,
        user_store: UserStore,
        supabase_service: SupabaseService,
        command_service: CommandLearningService,
        action_executor: ActionExecutor,
        voice_service: VoiceService,
        groq_service: GroqService,
    ) -> None:
        self.config_store = config_store
        self.history_store = history_store
        self.user_store = user_store
        self.supabase_service = supabase_service
        self.command_service = command_service
        self.action_executor = action_executor
        self.voice_service = voice_service
        self.groq_service = groq_service
        self.logger = get_logger()

    def handle_message(
        self,
        user_profile: dict[str, Any],
        message: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        user_id = user_profile["id"]
        user_email = user_profile["email"]
        normalized = normalize_text(message)
        actions: list[dict[str, Any]] = []
        needs_confirmation = False
        action_summary: str | None = None

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
            can_execute_directly = self.action_executor.can_handle_step(message)
            if learned_command or can_execute_directly:
                steps = learned_command["steps"] if learned_command else [message]
                execution = self.action_executor.execute_steps(
                    steps,
                    confirm=confirm,
                    device_access_enabled=bool(user_profile.get("device_access_enabled")),
                )
                action_summary = execution["summary"]
                reply = action_summary
                actions = execution["actions"]
                needs_confirmation = bool(execution["needs_confirmation"])
                for action in actions:
                    self.log_action(
                        user_id,
                        "command_executed" if learned_command else "direct_action",
                        action,
                    )

            groq_reply = None
            try:
                groq_reply = self.groq_service.generate_reply(
                    settings=self.config_store.load_settings(),
                    user_profile=user_profile,
                    user_message=message,
                    history=self.history_store.fetch_recent_conversations(user_id, limit=6),
                    action_summary=action_summary,
                    actions=actions,
                )
            except Exception:
                self.logger.exception("Groq response generation failed")

            if groq_reply:
                reply = groq_reply["content"]
                self.log_action(
                    user_id,
                    "llm_response_generated",
                    {
                        "provider": groq_reply["provider"],
                        "model": groq_reply["model"],
                    },
                )
            elif not actions:
                reply = (
                    "Groq is not configured yet. Add a GROQ_API_KEY to enable Vijay's AI chat, "
                    "or ask me to save commands and local automations."
                )

        self.log_conversation(user_id, user_email, message, reply)
        return {
            "response": reply,
            "actions": actions,
            "needs_confirmation": needs_confirmation or any(
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
