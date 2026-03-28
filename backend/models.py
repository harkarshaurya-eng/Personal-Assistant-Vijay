from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    confirm: bool = False


class LearnCommandRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=4000)


class VoiceTrainRequest(BaseModel):
    sample_reference: str | None = Field(default=None, max_length=500)


class VoiceVerifyRequest(BaseModel):
    sample_reference: str | None = Field(default=None, max_length=500)


class ApiMessage(BaseModel):
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
