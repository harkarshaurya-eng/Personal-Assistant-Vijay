from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from actions.executor import ActionExecutor
from backend.models import (
    AuthRequest,
    ChatRequest,
    LearnCommandRequest,
    VoiceTrainRequest,
    VoiceVerifyRequest,
)
from backend.supabase_service import SupabaseService
from core.assistant import AssistantService
from core.command_learning import CommandLearningService
from core.config_store import ConfigStore
from core.history import HistoryStore
from utils.logger import get_logger
from voice.service import VoiceService

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    config_store = ConfigStore(BASE_DIR)
    history_store = HistoryStore(BASE_DIR / "data")
    supabase = SupabaseService()
    voice_service = VoiceService(config_store)
    action_executor = ActionExecutor(config_store)
    command_service = CommandLearningService(config_store)
    assistant = AssistantService(
        config_store=config_store,
        history_store=history_store,
        supabase_service=supabase,
        command_service=command_service,
        action_executor=action_executor,
        voice_service=voice_service,
    )
    settings = config_store.load_settings()
    logger = get_logger()

    app = FastAPI(title="Vijay AI Platform", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get("allowed_origins", ["http://127.0.0.1:8000"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend" / "static"), name="static")
    templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))

    def resolve_user(authorization: str | None) -> dict[str, Any]:
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            user = supabase.get_user_from_token(token)
            if user:
                return {"user_id": user["id"], "email": user["email"], "authenticated": True}
        return {
            "user_id": "local-dev-user",
            "email": "local@vijay.dev",
            "authenticated": False,
        }

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "app_name": settings.get("app_name", "Vijay")},
        )

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return {
            "app_name": settings.get("app_name", "Vijay"),
            "dry_run": settings.get("dry_run", True),
            "supabase_ready": supabase.is_configured(),
            "logging_ready": supabase.logging_ready(),
            "voice": voice_service.status(),
        }

    @app.post("/api/auth/signup")
    async def signup(payload: AuthRequest) -> dict[str, Any]:
        if not supabase.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Supabase keys are missing. Add them to .env before using signup.",
            )
        try:
            result = supabase.signup(payload.email, payload.password)
        except Exception as exc:
            logger.exception("Signup failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "message": "Signup completed. Check your email if confirmation is enabled.",
            "data": result,
        }

    @app.post("/api/auth/login")
    async def login(payload: AuthRequest) -> dict[str, Any]:
        if not supabase.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Supabase keys are missing. Add them to .env before using login.",
            )
        try:
            result = supabase.login(payload.email, payload.password)
        except Exception as exc:
            logger.exception("Login failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"message": "Login successful.", "data": result}

    @app.get("/api/history")
    async def history(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        user = resolve_user(authorization)
        local_history = history_store.fetch_history(user["user_id"])
        remote_history: dict[str, Any] = {}
        if user["authenticated"] and supabase.logging_ready():
            try:
                remote_history = supabase.fetch_history(user["user_id"])
            except Exception:
                logger.exception("Remote history fetch failed")
        return {
            "message": "History loaded.",
            "data": {
                "user": user,
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
        user = resolve_user(authorization)
        try:
            learned = command_service.learn_from_text(payload.instruction)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        assistant.log_action(
            user_id=user["user_id"],
            action_type="command_learned",
            details=learned,
        )
        return {"message": "Command saved.", "data": learned}

    @app.post("/api/voice/train")
    async def train_voice(
        payload: VoiceTrainRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = resolve_user(authorization)
        result = voice_service.train_voice(user["user_id"], payload.sample_reference)
        assistant.log_action(
            user_id=user["user_id"],
            action_type="voice_training",
            details=result,
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/voice/verify")
    async def verify_voice(
        payload: VoiceVerifyRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = resolve_user(authorization)
        result = voice_service.verify_voice(user["user_id"], payload.sample_reference)
        assistant.log_action(
            user_id=user["user_id"],
            action_type="voice_verification",
            details=result,
        )
        return {"message": result["message"], "data": result}

    @app.post("/api/chat")
    async def chat(
        payload: ChatRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        user = resolve_user(authorization)
        response = assistant.handle_message(
            user_id=user["user_id"],
            user_email=user["email"],
            message=payload.message,
            confirm=payload.confirm,
        )
        return {"message": "Response generated.", "data": response}

    return app
