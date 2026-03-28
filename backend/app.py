from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from actions.executor import ActionExecutor
from backend.groq_service import GroqService
from backend.models import (
    AdminUserUpdateRequest,
    ChatRequest,
    DevicePermissionRequest,
    GoogleAuthRequest,
    LearnCommandRequest,
    PromptUpdateRequest,
    VoiceSettingsRequest,
    VoiceTrainRequest,
    VoiceVerifyRequest,
)
from backend.supabase_service import SupabaseService
from core.assistant import AssistantService
from core.command_learning import CommandLearningService
from core.config_store import ConfigStore
from core.history import HistoryStore
from core.user_store import UserStore
from utils.logger import get_logger
from voice.service import VoiceDependencyError, VoiceService, VoiceValidationError

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    load_dotenv()
    config_store = ConfigStore(BASE_DIR)
    history_store = HistoryStore(BASE_DIR / "data")
    user_store = UserStore(BASE_DIR / "data", config_store)
    supabase = SupabaseService()
    groq_service = GroqService()
    voice_service = VoiceService(config_store, BASE_DIR)
    action_executor = ActionExecutor(config_store)
    command_service = CommandLearningService(config_store)
    assistant = AssistantService(
        config_store=config_store,
        history_store=history_store,
        user_store=user_store,
        supabase_service=supabase,
        command_service=command_service,
        action_executor=action_executor,
        voice_service=voice_service,
        groq_service=groq_service,
    )
    settings = config_store.load_settings()
    logger = get_logger()
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    app = FastAPI(title="Vijay AI Platform", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get("allowed_origins", ["http://127.0.0.1:8000"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend" / "static"), name="static")
    templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))

    def guest_user() -> dict[str, Any]:
        return {
            "id": "guest",
            "email": "",
            "name": "Guest",
            "role": "guest",
            "provider": "none",
            "system_prompt": settings.get("default_user_system_prompt", ""),
            "device_access_enabled": False,
            "device_access_configured": False,
            "authenticated": False,
        }

    def extract_token(authorization: str | None) -> str:
        if authorization and authorization.lower().startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        return ""

    def resolve_user(authorization: str | None) -> dict[str, Any]:
        token = extract_token(authorization)
        if token:
            user = user_store.get_user_by_session(token)
            if user:
                return {**user, "authenticated": True, "session_token": token}
        return guest_user()

    def require_user(authorization: str | None) -> dict[str, Any]:
        user = resolve_user(authorization)
        if not user.get("authenticated"):
            raise HTTPException(status_code=401, detail="Please sign in with Google first.")
        return user

    def require_admin(authorization: str | None) -> dict[str, Any]:
        user = require_user(authorization)
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required.")
        return user

    def sync_user_to_supabase(user: dict[str, Any]) -> None:
        if not supabase.logging_ready():
            return
        try:
            supabase.upsert_user_profile(user)
        except Exception:
            logger.exception("Supabase user sync failed")

    def build_user_payload(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "picture": user.get("picture", ""),
            "role": user.get("role", "user"),
            "provider": user.get("provider", "google"),
            "system_prompt": user.get("system_prompt", ""),
            "device_access_enabled": user.get("device_access_enabled", False),
            "device_access_configured": user.get("device_access_configured", False),
        }

    async def read_audio_bytes(request: Request) -> bytes:
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"}:
            raise HTTPException(
                status_code=415,
                detail="Vijay expects WAV audio from the browser recorder for voice lock.",
            )
        audio_bytes = await request.body()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="No audio was uploaded.")
        return audio_bytes

    def voice_http_error(exc: Exception) -> HTTPException:
        if isinstance(exc, VoiceDependencyError):
            return HTTPException(status_code=503, detail=str(exc))
        if isinstance(exc, VoiceValidationError):
            return HTTPException(status_code=400, detail=str(exc))
        return HTTPException(status_code=500, detail="Voice processing failed.")

    def verify_google_credential(credential: str) -> dict[str, Any]:
        if not google_client_id:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_CLIENT_ID is missing. Add it to .env before using Google sign-in.",
            )
        try:
            payload = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                google_client_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Google credential verification failed.") from exc
        if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
            raise HTTPException(status_code=401, detail="Invalid Google issuer.")
        if not payload.get("email_verified"):
            raise HTTPException(status_code=403, detail="Google email is not verified.")
        return payload

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"app_name": settings.get("app_name", "Vijay")},
        )

    @app.get("/api/public-config")
    async def public_config() -> dict[str, Any]:
        return {
            "app_name": settings.get("app_name", "Vijay"),
            "admin_email": settings.get("admin_email", "harkarshaurya@gmail.com"),
            "google_client_id": google_client_id,
            "google_enabled": bool(google_client_id) and settings.get("google_sign_in_enabled", True),
            "groq_model": groq_service.model,
        }

    @app.get("/api/status")
    async def status(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = resolve_user(authorization)
        return {
            "app_name": settings.get("app_name", "Vijay"),
            "dry_run": settings.get("dry_run", True),
            "google_ready": bool(google_client_id),
            "groq_ready": groq_service.is_configured(),
            "supabase_ready": supabase.is_configured(),
            "logging_ready": supabase.logging_ready(),
            "voice": voice_service.status(user["id"] if user.get("authenticated") else None),
            "user": build_user_payload(user) if user.get("authenticated") else None,
        }

    @app.post("/api/auth/google")
    async def google_sign_in(payload: GoogleAuthRequest) -> dict[str, Any]:
        google_payload = verify_google_credential(payload.credential)
        user = user_store.upsert_google_user(
            email=str(google_payload["email"]),
            google_sub=str(google_payload["sub"]),
            name=str(google_payload.get("name") or google_payload["email"].split("@")[0]),
            picture=str(google_payload.get("picture") or ""),
        )
        sync_user_to_supabase(user)
        session_token = user_store.create_session(user["id"])
        redirect_hash = "admin" if user.get("role") == "admin" else "assistant"
        return {
            "message": "Signed in with Google.",
            "data": {
                "session_token": session_token,
                "user": build_user_payload(user),
                "redirect_hash": redirect_hash,
            },
        }

    @app.get("/api/auth/session")
    async def session(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = require_user(authorization)
        return {"message": "Session loaded.", "data": {"user": build_user_payload(user)}}

    @app.post("/api/auth/logout")
    async def logout(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        token = extract_token(authorization)
        if token:
            user_store.clear_session(token)
        return {"message": "Session cleared.", "data": {}}

    @app.get("/api/history")
    async def history(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = require_user(authorization)
        local_history = history_store.fetch_history(user["id"])
        remote_history: dict[str, Any] = {}
        if supabase.logging_ready():
            try:
                remote_history = supabase.fetch_history(user["id"])
            except Exception:
                logger.exception("Remote history fetch failed")
        return {
            "message": "History loaded.",
            "data": {
                "user": build_user_payload(user),
                "local": local_history,
                "remote": remote_history,
            },
        }

    @app.get("/api/commands")
    async def commands() -> dict[str, Any]:
        return {"message": "Commands loaded.", "data": config_store.load_commands()}

    @app.post("/api/commands/learn")
    async def learn_command(
        payload: LearnCommandRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        try:
            learned = command_service.learn_from_text(payload.instruction)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        assistant.log_action(
            user_id=user["id"],
            action_type="command_learned",
            details=learned,
        )
        return {"message": "Command saved.", "data": learned}

    @app.post("/api/voice/train")
    async def train_voice(
        payload: VoiceTrainRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        result = voice_service.train_voice(user["id"], payload.sample_reference)
        assistant.log_action(user_id=user["id"], action_type="voice_training_requested", details=result)
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/train/audio")
    async def train_voice_audio(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        audio_bytes = await read_audio_bytes(request)
        try:
            result = voice_service.train_voice_from_audio(user["id"], audio_bytes)
        except Exception as exc:
            raise voice_http_error(exc) from exc
        assistant.log_action(
            user_id=user["id"],
            action_type="voice_training",
            details={
                "duration_seconds": result["duration_seconds"],
                "transcript": result["transcript"],
                "language": result["language"],
                "similarity_threshold": result["similarity_threshold"],
            },
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/verify")
    async def verify_voice(
        payload: VoiceVerifyRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        result = voice_service.verify_voice(user["id"], payload.sample_reference)
        assistant.log_action(
            user_id=user["id"],
            action_type="voice_verification_requested",
            details=result,
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/verify/audio")
    async def verify_voice_audio(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        audio_bytes = await read_audio_bytes(request)
        try:
            result = voice_service.verify_voice_from_audio(user["id"], audio_bytes)
        except Exception as exc:
            raise voice_http_error(exc) from exc
        assistant.log_action(
            user_id=user["id"],
            action_type="voice_verification",
            details={
                "authorized": result["authorized"],
                "similarity": result["similarity"],
                "threshold": result["threshold"],
            },
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/settings")
    async def update_voice_settings(
        payload: VoiceSettingsRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        result = voice_service.update_similarity_threshold(payload.similarity_threshold)
        assistant.log_action(
            user_id=user["id"],
            action_type="voice_settings_updated",
            details={"similarity_threshold": result["similarity_threshold"]},
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/command")
    async def voice_command(
        request: Request,
        confirm: bool = False,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        audio_bytes = await read_audio_bytes(request)
        try:
            verification = voice_service.verify_voice_from_audio(
                user["id"],
                audio_bytes,
                transcribe_on_success=True,
            )
        except Exception as exc:
            raise voice_http_error(exc) from exc

        assistant.log_action(
            user_id=user["id"],
            action_type="voice_verification",
            details={
                "authorized": verification["authorized"],
                "similarity": verification["similarity"],
                "threshold": verification["threshold"],
            },
        )

        if not verification["authorized"]:
            return {"message": verification["message"], "data": {"voice": verification}}

        transcript = str(verification.get("transcript", "")).strip()
        if not transcript:
            return {
                "message": "Authorized user verified, but Vijay could not detect a spoken command. Try again.",
                "data": {"voice": verification},
            }

        assistant.log_action(
            user_id=user["id"],
            action_type="voice_command_received",
            details={
                "transcript": transcript,
                "language": verification.get("language", ""),
            },
        )
        response = assistant.handle_message(
            user_profile=user,
            message=transcript,
            confirm=confirm,
        )
        return {
            "message": response["response"],
            "data": {
                **response,
                "transcript": transcript,
                "voice": verification,
            },
        }

    @app.post("/api/me/system-prompt")
    async def update_my_prompt(
        payload: PromptUpdateRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        updated = user_store.update_user(user["id"], prompt=payload.prompt)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found.")
        sync_user_to_supabase(updated)
        assistant.log_action(updated["id"], "system_prompt_updated", {"scope": "self"})
        return {"message": "Your Vijay system prompt was updated.", "data": {"user": build_user_payload(updated)}}

    @app.post("/api/me/device-permission")
    async def update_my_device_permission(
        payload: DevicePermissionRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        updated = user_store.update_user(
            user["id"],
            device_access_enabled=payload.enabled,
            device_access_configured=True,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found.")
        sync_user_to_supabase(updated)
        assistant.log_action(
            updated["id"],
            "device_permission_updated",
            {"enabled": payload.enabled, "scope": "self"},
        )
        return {
            "message": "Local device permission updated.",
            "data": {"user": build_user_payload(updated)},
        }

    @app.post("/api/chat")
    async def chat(
        payload: ChatRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = require_user(authorization)
        response = assistant.handle_message(
            user_profile=user,
            message=payload.message,
            confirm=payload.confirm,
        )
        return {"message": "Response generated.", "data": response}

    @app.get("/api/admin/overview")
    async def admin_overview(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        require_admin(authorization)
        users = user_store.list_users()
        all_history = history_store.fetch_all_history(limit=200)
        summaries = []
        for item in users:
            user_conversations = [
                entry for entry in all_history["conversations"] if entry["user_id"] == item["id"]
            ]
            user_actions = [entry for entry in all_history["actions"] if entry["user_id"] == item["id"]]
            summaries.append(
                {
                    **build_user_payload(item),
                    "conversation_count": len(user_conversations),
                    "action_count": len(user_actions),
                }
            )

        remote = {}
        if supabase.logging_ready():
            try:
                remote = {
                    "users": supabase.fetch_all_users(limit=200),
                    "conversations": supabase.fetch_all_conversations(limit=50),
                    "actions": supabase.fetch_all_actions(limit=50),
                }
            except Exception:
                logger.exception("Admin remote overview fetch failed")

        return {
            "message": "Admin overview loaded.",
            "data": {
                "users": summaries,
                "local_recent": all_history,
                "remote": remote,
            },
        }

    @app.get("/api/admin/users/{user_id}")
    async def admin_user_detail(
        user_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        require_admin(authorization)
        user = user_store.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        remote_history: dict[str, Any] = {}
        if supabase.logging_ready():
            try:
                remote_history = supabase.fetch_history(user_id)
            except Exception:
                logger.exception("Admin remote user history fetch failed")
        return {
            "message": "Admin user detail loaded.",
            "data": {
                "user": build_user_payload(user),
                "local": history_store.fetch_history(user_id, limit=50),
                "remote": remote_history,
            },
        }

    @app.post("/api/admin/users/{user_id}")
    async def admin_update_user(
        user_id: str,
        payload: AdminUserUpdateRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        admin = require_admin(authorization)
        updated = user_store.update_user(
            user_id,
            prompt=payload.prompt,
            device_access_enabled=payload.device_access_enabled,
            device_access_configured=(
                payload.device_access_enabled is not None
            ),
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found.")
        sync_user_to_supabase(updated)
        assistant.log_action(
            admin["id"],
            "admin_user_updated",
            {
                "target_user_id": user_id,
                "prompt_updated": payload.prompt is not None,
                "device_access_enabled": payload.device_access_enabled,
            },
        )
        return {
            "message": "Admin user settings updated.",
            "data": {"user": build_user_payload(updated)},
        }

    return app
