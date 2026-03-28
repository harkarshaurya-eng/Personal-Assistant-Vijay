from __future__ import annotations

import importlib.util
import io
import math
import os
import sys
import uuid
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config_store import ConfigStore


class VoiceDependencyError(RuntimeError):
    """Raised when optional voice-model dependencies are unavailable."""


class VoiceValidationError(ValueError):
    """Raised when the uploaded voice sample cannot be used safely."""


class VoiceService:
    def __init__(self, config_store: ConfigStore, base_dir: Path | None = None) -> None:
        self.config_store = config_store
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.voice_data_dir = self.base_dir / "data" / "voice"
        self.models_dir = self.base_dir / "data" / "models"
        self.voice_data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._whisper_model: Any | None = None
        self._speaker_encoder: Any | None = None

    def status(self, user_id: str | None = None) -> dict[str, Any]:
        voice = self.config_store.load_voice()
        dependencies = self.dependency_status()
        profile = None
        if user_id:
            profile = voice.get("authorized_profiles", {}).get(user_id)
        return {
            "mode": voice.get("mode", "browser_wav"),
            "lock_enabled": voice.get("lock_enabled", False),
            "profile_count": len(voice.get("authorized_profiles", {})),
            "similarity_threshold": voice.get("similarity_threshold", 0.8),
            "dependencies_ready": dependencies["ready"],
            "stt_ready": dependencies["stt_ready"],
            "speaker_ready": dependencies["speaker_ready"],
            "dependency_message": dependencies["message"],
            "user_has_profile": bool(profile),
            "user_trained_at": profile.get("trained_at") if profile else None,
        }

    def dependency_status(self) -> dict[str, Any]:
        missing: list[str] = []
        if importlib.util.find_spec("torch") is None:
            missing.append("torch")
        if importlib.util.find_spec("faster_whisper") is None:
            missing.append("faster-whisper")
        if importlib.util.find_spec("speechbrain") is None:
            missing.append("speechbrain")

        if missing:
            if sys.version_info >= (3, 14):
                return {
                    "ready": False,
                    "stt_ready": False,
                    "speaker_ready": False,
                    "message": (
                        "This Vijay environment is running Python "
                        f"{sys.version_info.major}.{sys.version_info.minor}. "
                        "Real voice lock currently needs Python 3.11 or 3.12. "
                        "Recreate .venv with `py -3.12 -m venv .venv` or `py -3.11 -m venv .venv`, "
                        "then run install.bat again."
                    ),
                }

            packages = ", ".join(missing)
            return {
                "ready": False,
                "stt_ready": "faster-whisper" not in missing,
                "speaker_ready": "speechbrain" not in missing and "torch" not in missing,
                "message": (
                    "Install the real voice lock dependencies first: "
                    f"{packages}. After installation, the first voice run will download the local models."
                ),
            }

        return {
            "ready": True,
            "stt_ready": True,
            "speaker_ready": True,
            "message": "Voice models are available. The first training run may still download local model files.",
        }

    def update_similarity_threshold(self, threshold: float) -> dict[str, Any]:
        voice = self.config_store.load_voice()
        bounded = max(0.5, min(0.99, round(float(threshold), 2)))
        voice["similarity_threshold"] = bounded
        self.config_store.save_voice(voice)
        return {
            "message": f"Voice similarity threshold saved at {bounded:.2f}.",
            "similarity_threshold": bounded,
        }

    def train_voice(self, user_id: str, sample_reference: str | None = None) -> dict[str, Any]:
        return {
            "message": (
                "Voice enrollment now requires a real microphone recording from the Vijay web UI. "
                "Use Start Enrollment and Stop Enrollment in the Voice Training panel."
            ),
            "voice_mode": "browser_wav",
            "lock_enabled": bool(self.config_store.load_voice().get("lock_enabled", False)),
            "sample_reference": sample_reference,
            "user_id": user_id,
        }

    def train_voice_from_audio(self, user_id: str, audio_bytes: bytes) -> dict[str, Any]:
        self._require_dependencies()
        wav_info = self._prepare_audio(audio_bytes)
        voice = self.config_store.load_voice()
        min_seconds = float(voice.get("min_training_seconds", 3.0))
        if wav_info["duration_seconds"] < min_seconds:
            raise VoiceValidationError(
                f"Record at least {min_seconds:.0f} seconds for enrollment so Vijay can learn your voice cleanly."
            )

        sample_path = self._write_sample(user_id, "enrollment", audio_bytes)
        transcript = self._transcribe(sample_path)
        if not transcript["text"]:
            raise VoiceValidationError(
                "Vijay could not hear spoken words in that recording. Try again in a quieter room."
            )

        embedding = self._encode_embedding(wav_info["samples"])
        voice.setdefault("authorized_profiles", {})
        voice["authorized_profiles"][user_id] = {
            "embedding": embedding,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "sample_rate": wav_info["sample_rate"],
            "duration_seconds": round(wav_info["duration_seconds"], 2),
            "transcript": transcript["text"],
            "language": transcript["language"],
            "enrollment_path": self._relative_path(sample_path),
        }
        voice["lock_enabled"] = True
        voice["mode"] = "browser_wav"
        self.config_store.save_voice(voice)
        return {
            "message": "Voice profile trained successfully. Vijay will now verify your voice before running voice commands.",
            "voice_mode": voice["mode"],
            "lock_enabled": True,
            "duration_seconds": round(wav_info["duration_seconds"], 2),
            "transcript": transcript["text"],
            "language": transcript["language"],
            "similarity_threshold": voice.get("similarity_threshold", 0.8),
        }

    def verify_voice(self, user_id: str, sample_reference: str | None = None) -> dict[str, Any]:
        return {
            "authorized": False,
            "message": (
                "Voice verification now expects a real microphone recording. "
                "Use the secure voice command recorder in the Vijay web UI."
            ),
            "sample_reference": sample_reference,
            "user_id": user_id,
        }

    def verify_voice_from_audio(
        self,
        user_id: str,
        audio_bytes: bytes,
        *,
        transcribe_on_success: bool = False,
    ) -> dict[str, Any]:
        self._require_dependencies()
        voice = self.config_store.load_voice()
        profile = voice.get("authorized_profiles", {}).get(user_id)
        if not profile:
            return {
                "authorized": False,
                "message": "No trained voice profile was found for this user. Train your voice first.",
                "similarity": 0.0,
                "threshold": voice.get("similarity_threshold", 0.8),
                "transcript": "",
            }

        wav_info = self._prepare_audio(audio_bytes)
        min_seconds = float(voice.get("min_command_seconds", 1.5))
        if wav_info["duration_seconds"] < min_seconds:
            raise VoiceValidationError(
                f"Record at least {min_seconds:.1f} seconds so Vijay has enough audio to verify the speaker."
            )

        embedding = self._encode_embedding(wav_info["samples"])
        stored_embedding = [float(value) for value in profile.get("embedding", [])]
        if not stored_embedding:
            raise VoiceValidationError("The saved voice profile is incomplete. Retrain the voice profile once.")

        similarity = self._cosine_similarity(stored_embedding, embedding)
        threshold = float(profile.get("similarity_threshold", voice.get("similarity_threshold", 0.8)))
        authorized = similarity >= threshold
        transcript = {"text": "", "language": ""}
        sample_path: Path | None = None
        if authorized:
            sample_path = self._write_sample(user_id, "command", audio_bytes)
            if transcribe_on_success:
                transcript = self._transcribe(sample_path)

        return {
            "authorized": authorized,
            "message": (
                "Authorized user verified."
                if authorized
                else "Unauthorized user detected. Access denied."
            ),
            "similarity": round(similarity, 4),
            "threshold": round(threshold, 2),
            "duration_seconds": round(wav_info["duration_seconds"], 2),
            "transcript": transcript["text"],
            "language": transcript["language"],
            "sample_path": self._relative_path(sample_path) if sample_path else "",
        }

    def _require_dependencies(self) -> tuple[Any, Any, Any]:
        if sys.version_info >= (3, 14):
            raise VoiceDependencyError(
                "Real voice lock currently needs Python 3.11 or 3.12. "
                f"This Vijay environment is running Python {sys.version_info.major}.{sys.version_info.minor}. "
                "Recreate .venv with `py -3.12 -m venv .venv` or `py -3.11 -m venv .venv`, then reinstall."
            )

        try:
            import torch
        except Exception as exc:  # pragma: no cover - import path is environment specific
            raise VoiceDependencyError(
                "Torch is not installed. Run pip install -r requirements.txt to enable Vijay voice lock."
            ) from exc

        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - import path is environment specific
            raise VoiceDependencyError(
                "faster-whisper is not installed. Run pip install -r requirements.txt to enable Vijay voice transcription."
            ) from exc

        try:
            from speechbrain.inference.classifiers import EncoderClassifier
        except Exception:
            try:
                from speechbrain.inference.speaker import EncoderClassifier
            except Exception as exc:  # pragma: no cover - import path is environment specific
                raise VoiceDependencyError(
                    "SpeechBrain is not installed. Run pip install -r requirements.txt to enable speaker verification."
                ) from exc

        return torch, WhisperModel, EncoderClassifier

    def _load_whisper_model(self) -> Any:
        if self._whisper_model is not None:
            return self._whisper_model

        _, whisper_model_class, _ = self._require_dependencies()
        model_name = os.getenv("VOICE_STT_MODEL", "base.en").strip() or "base.en"
        compute_type = os.getenv("VOICE_STT_COMPUTE_TYPE", "int8").strip() or "int8"
        download_root = str(self.models_dir / "faster_whisper")
        try:
            self._whisper_model = whisper_model_class(
                model_name,
                device="cpu",
                compute_type=compute_type,
                download_root=download_root,
            )
        except Exception:
            if compute_type == "float32":
                raise
            self._whisper_model = whisper_model_class(
                model_name,
                device="cpu",
                compute_type="float32",
                download_root=download_root,
            )
        return self._whisper_model

    def _load_speaker_encoder(self) -> Any:
        if self._speaker_encoder is not None:
            return self._speaker_encoder

        _, _, encoder_class = self._require_dependencies()
        self._speaker_encoder = encoder_class.from_hparams(
            source=os.getenv("VOICE_SPEAKER_MODEL", "speechbrain/spkrec-ecapa-voxceleb"),
            savedir=str(self.models_dir / "speechbrain_ecapa"),
            run_opts={"device": "cpu"},
        )
        return self._speaker_encoder

    def _prepare_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        if not audio_bytes:
            raise VoiceValidationError("No audio data was received. Record your voice and try again.")

        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as handle:
                channels = handle.getnchannels()
                sample_width = handle.getsampwidth()
                sample_rate = handle.getframerate()
                frame_count = handle.getnframes()
                raw_frames = handle.readframes(frame_count)
        except wave.Error as exc:
            raise VoiceValidationError("Vijay only accepts WAV audio from the browser recorder.") from exc

        if frame_count <= 0:
            raise VoiceValidationError("The recording was empty. Try again.")

        if sample_width != 2:
            raise VoiceValidationError(
                "Vijay expects 16-bit WAV audio from the browser recorder. Record directly in Vijay and try again."
            )

        samples = array("h")
        samples.frombytes(raw_frames)
        if channels > 1:
            mono_samples = array("h")
            for index in range(0, len(samples), channels):
                frame = samples[index : index + channels]
                mono_samples.append(int(sum(frame) / len(frame)))
            samples = mono_samples

        target_sample_rate = 16000
        if sample_rate != target_sample_rate:
            samples = self._resample_samples(samples, sample_rate, target_sample_rate)
            sample_rate = target_sample_rate

        if len(samples) < 8000:
            raise VoiceValidationError("The recording is too short. Record at least a couple of spoken words.")

        return {
            "samples": [float(sample) / 32768.0 for sample in samples],
            "sample_rate": sample_rate,
            "duration_seconds": len(samples) / sample_rate,
        }

    def _encode_embedding(self, samples: list[float]) -> list[float]:
        torch, _, _ = self._require_dependencies()
        encoder = self._load_speaker_encoder()
        waveform = torch.tensor(samples, dtype=torch.float32).unsqueeze(0)
        embeddings = encoder.encode_batch(waveform)
        vector = embeddings.squeeze().detach().cpu().tolist()
        return [round(float(value), 8) for value in vector]

    def _transcribe(self, sample_path: Path) -> dict[str, str]:
        model = self._load_whisper_model()
        segments, info = model.transcribe(
            str(sample_path),
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        language = getattr(info, "language", "") or ""
        return {"text": text, "language": language}

    def _write_sample(self, user_id: str, sample_kind: str, audio_bytes: bytes) -> Path:
        user_dir = self.voice_data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_path = user_dir / f"{sample_kind}-{timestamp}-{uuid.uuid4().hex[:8]}.wav"
        file_path.write_bytes(audio_bytes)
        return file_path

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)

    def _resample_samples(
        self,
        samples: array,
        source_rate: int,
        target_rate: int,
    ) -> array:
        if source_rate == target_rate:
            return samples
        if len(samples) < 2:
            return array("h", samples)

        target_length = max(1, int(round(len(samples) * target_rate / source_rate)))
        if target_length == 1:
            return array("h", [samples[0]])

        position_scale = (len(samples) - 1) / (target_length - 1)
        resampled = array("h")
        for target_index in range(target_length):
            position = target_index * position_scale
            left_index = int(position)
            right_index = min(left_index + 1, len(samples) - 1)
            fraction = position - left_index
            interpolated = (
                samples[left_index] * (1 - fraction) + samples[right_index] * fraction
            )
            clipped = max(-32768, min(32767, int(round(interpolated))))
            resampled.append(clipped)
        return resampled

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            raise VoiceValidationError("The stored voice profile and the new recording are incompatible. Retrain the profile once.")

        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            raise VoiceValidationError("The voice embedding could not be normalized. Record a clearer sample and try again.")
        return numerator / (left_norm * right_norm)
