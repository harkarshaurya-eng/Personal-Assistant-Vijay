# Vijay

Vijay is a local-first AI assistant platform with:

- Google sign-in
- Groq `llama-3.3-70b-versatile` chat responses
- Per-user customizable system prompts
- Admin dashboard access for `harkarshaurya@gmail.com`
- Local device-permission onboarding before automation
- Real browser-microphone voice enrollment and speaker verification
- Safe command learning, conversation history, and action logging

The current build serves a lightweight web UI from the Python backend, stores runtime state locally, and syncs users, conversations, and actions to Supabase when backend credentials are configured.

## What Changed In This Build

- Replaced the old password-first UI with Google Identity Services sign-in
- Added local session handling and admin role detection
- Added per-user Vijay system prompts
- Added an admin dashboard to inspect users and update prompts or device permissions
- Added Groq integration for Vijay replies
- Added setup-time device permission gating for local automation
- Added auto-fallback to a free local port if `8000` is busy
- Replaced the voice scaffold with real WAV recording, Faster-Whisper transcription, and SpeechBrain speaker verification

## Project Structure

```text
ai-vijay/
  backend/
  frontend/
  core/
  voice/
  actions/
  config/
  data/
  utils/
  main.py
  requirements.txt
  README.md
  install.bat
```

## Quick Start

### Windows one-click start

1. Double-click `install.bat`
2. Wait for the environment and dependencies to install
3. The voice dependencies are larger and may take a few extra minutes on the first install
4. Open the URL shown in the terminal

### Manual start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Voice compatibility:

- the local voice stack is currently validated for Python `3.11` and `3.12`
- `install.bat` now prefers those versions automatically when they are available through the Windows `py` launcher
- if you already created `.venv` with Python `3.14`, delete `.venv` and run `install.bat` again before testing voice lock

## Environment Variables

Set these in `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GOOGLE_CLIENT_ID=your-google-web-client-id
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
ADMIN_EMAIL=harkarshaurya@gmail.com
VOICE_STT_MODEL=base.en
VOICE_STT_COMPUTE_TYPE=int8
VOICE_SPEAKER_MODEL=speechbrain/spkrec-ecapa-voxceleb
```

Notes:

- `GOOGLE_CLIENT_ID` is required for the new Google sign-in flow.
- `GROQ_API_KEY` is required for Vijay’s AI chat replies.
- `SUPABASE_SERVICE_ROLE_KEY` is used server-side only for backend logging and admin reads.
- `ADMIN_EMAIL` defaults to `harkarshaurya@gmail.com`.
- `VOICE_STT_MODEL`, `VOICE_STT_COMPUTE_TYPE`, and `VOICE_SPEAKER_MODEL` are optional voice-tuning overrides.

## Google Sign-In Setup

1. Open the Google Cloud Console.
2. Create or choose a project.
3. Open `APIs & Services -> Credentials`.
4. Create an OAuth client ID for a web application.
5. Add local origins such as:
   - `http://127.0.0.1:8000`
   - `http://localhost:8000`
6. Copy the client ID into `.env` as `GOOGLE_CLIENT_ID`.
7. Start Vijay and click the Google sign-in button.

Admin behavior:

- If the signed-in email is `harkarshaurya@gmail.com`, Vijay opens the admin dashboard automatically.

## Groq Setup

1. Create a Groq account and generate an API key.
2. Put the key in `.env` as `GROQ_API_KEY`.
3. Keep the default model:

```env
GROQ_MODEL=llama-3.3-70b-versatile
```

4. Restart Vijay.

Each user gets their own customizable system prompt. Vijay merges:

- the global base system prompt from [`config/settings.json`](/C:/Users/Admin/Desktop/Vijay/config/settings.json)
- the user’s personal prompt from their profile
- automation context from the current action request

## Supabase Setup

1. Create a Supabase project.
2. Open the SQL editor.
3. Run [`config/supabase_schema.sql`](/C:/Users/Admin/Desktop/Vijay/config/supabase_schema.sql).
4. Copy the project URL, anon key, and service role key into `.env`.
5. Restart Vijay.

What Supabase stores in this build:

- user profiles
- user prompts
- device-permission state
- conversation logs
- action logs

If Supabase is unreachable, Vijay falls back to local mode without crashing.

## User Setup Flow

1. Launch Vijay.
2. Sign in with Google.
3. If you are a normal user:
   - choose whether Vijay may control the local device
   - record one enrollment sample in the Voice Training panel
   - customize your personal Vijay prompt if you want
   - chat, speak secure voice commands, and teach commands
4. If you sign in as `harkarshaurya@gmail.com`:
   - Vijay opens the admin dashboard
   - you can inspect every user
   - you can edit any user’s prompt
   - you can enable or disable device access per user

## Local Device Permission

Before Vijay performs local automation, the user must explicitly allow device access.

If device access is disabled:

- Vijay will still chat
- Vijay will still verify the user’s voice and transcribe what they said
- Vijay will still save prompts and commands
- Vijay will block local automation with a clear message

Browser note:

- the first time a user records audio, the browser will separately ask for microphone permission

## Voice Training And Voice Lock

Vijay now uses real microphone audio from the browser UI.

How enrollment works:

1. Sign in with Google.
2. In the Voice Training panel, keep the default threshold or adjust it.
3. Click `Start Enrollment`.
4. Allow microphone access in the browser if prompted.
5. Speak naturally for 4 to 8 seconds.
6. Click `Stop Enrollment`.
7. Vijay stores a local speaker embedding and enables voice lock.

How secure voice commands work:

1. Click `Start Voice Command`.
2. Speak your command.
3. Click `Stop Voice Command`.
4. Vijay compares the new speaker embedding to the enrolled profile.
5. If the similarity score is below the threshold, Vijay returns:

```text
Unauthorized user detected. Access denied.
```

6. If the voice is authorized, Vijay transcribes the command with Faster-Whisper and runs it through the normal assistant pipeline.

What is stored locally:

- speaker embeddings and thresholds in [`config/voice.json`](/C:/Users/Admin/Desktop/Vijay/config/voice.json)
- recorded WAV samples in `data/voice/`
- downloaded voice models in `data/models/`

Important:

- the first enrollment or command run may take longer because the local Whisper and SpeechBrain models are downloaded
- voice automation still respects the same per-user device-permission gate used by text commands
- for local voice lock, use a Vijay virtualenv created with Python `3.11` or `3.12`

## Command Learning

Example:

```text
When I say open my setup - open Android Studio, Claude Code, YouTube and ChatGPT
```

Saved commands live in:

- [`config/commands.json`](/C:/Users/Admin/Desktop/Vijay/config/commands.json)

## Admin Dashboard

The admin dashboard lets the admin:

- view all registered users
- inspect local and backend-backed activity
- edit per-user Vijay prompts
- toggle device access for any user

This build gives the admin control over the configuration and visibility of every user’s Vijay assistant. Actual local device automation still respects the per-user permission gate on that machine.

## Security Notes

- Do not keep real secrets in `.env.example`
- Keep real keys only in `.env`
- Rotate exposed service-role keys immediately if they were ever committed or shared
- Vijay blocks obviously risky automation text unless confirmation is supplied
- Local device automation is permission-gated

## Packaging Roadmap

### Package as an executable

1. Install PyInstaller in the Vijay environment.
2. Build:

```powershell
pyinstaller --onefile --name Vijay main.py
```

3. Include `config/`, `frontend/`, and `.env` handling in the packaged release.

### Better desktop UX

Recommended next phase:

- keep FastAPI as the local backend
- optionally wrap the UI in Tauri or Electron

## Deployment Roadmap

### Local user install

1. Download the repo or packaged release
2. Run `install.bat`
3. Add Google, Groq, and Supabase keys to `.env`
4. Sign in with Google
5. Choose local device permission
6. Record a voice enrollment sample
7. Start using Vijay

### Shared deployment

1. Host the FastAPI service on a VPS, Railway, Render, or Fly.io
2. Keep secrets in the platform secret store
3. Restrict allowed origins
4. Keep local-only automation gated behind the desktop user permission flow
5. Consider splitting cloud management from desktop execution for stronger security

## GitHub Publish Steps

To connect this local repo to your `Vijay The Assistant` GitHub repository:

```powershell
git remote add origin <your-github-repo-url>
git push -u origin main
```

If you want a branch-and-PR workflow:

```powershell
git checkout -b codex/google-groq-admin-dashboard
git push -u origin codex/google-groq-admin-dashboard
```

## Step-by-Step Implementation Roadmap

### 1. Create the Supabase project

1. Create the project
2. Run the SQL schema
3. Add the URL and keys to `.env`
4. Restart Vijay

### 2. Configure Google auth

1. Create a Google OAuth web client
2. Add local origins
3. Put the client ID in `.env`
4. Restart Vijay

### 3. Configure Groq

1. Generate a Groq API key
2. Add `GROQ_API_KEY` to `.env`
3. Restart Vijay

### 4. Run the backend and frontend

The frontend is served by the backend in this repo, so one command runs both:

```powershell
python main.py
```

### 5. Package the app

1. Install PyInstaller
2. Build the executable
3. Bundle static files and config
4. Test on a clean Windows machine

### 6. Deploy

1. Push the repo to GitHub
2. Add CI or release automation
3. Host the backend if you want centralized admin access
4. Keep desktop automation local where possible

### 7. User installation flow

1. Install Vijay
2. Configure `.env`
3. Sign in with Google
4. Choose device permission
5. Train voice lock
6. Use Vijay

## Real Voice Lock And Jarvis Permission Steps

If you want to understand or extend the implementation, follow this order:

1. Browser microphone capture
   - Vijay records raw audio in the web UI with `getUserMedia` and Web Audio
   - the UI encodes the captured PCM stream into a WAV blob before upload

2. Enrollment endpoint
   - the browser posts the WAV file to `/api/voice/train/audio`
   - [`voice/service.py`](/C:/Users/Admin/Desktop/Vijay/voice/service.py) normalizes the audio to mono 16 kHz
   - SpeechBrain creates the speaker embedding
   - Faster-Whisper transcribes the sample for operator feedback
   - Vijay stores the embedding locally in [`config/voice.json`](/C:/Users/Admin/Desktop/Vijay/config/voice.json)

3. Verification endpoint
   - the browser posts command audio to `/api/voice/command`
   - Vijay computes a new speaker embedding
   - cosine similarity is compared against the configured threshold
   - unauthorized speakers are blocked before transcription and automation

4. Voice command execution
   - authorized audio is transcribed with Faster-Whisper
   - the transcript is passed into the same assistant path as text chat
   - command learning, history, Groq replies, and admin visibility all stay unified

5. Jarvis-style device permission
   - every user must opt into local device control during onboarding
   - if that permission is off, Vijay can still chat and transcribe but it will refuse local automation
   - this enforcement happens in [`actions/executor.py`](/C:/Users/Admin/Desktop/Vijay/actions/executor.py)

6. Local storage and safety
   - embeddings and thresholds live in local config
   - raw WAV samples stay on the machine in `data/voice/`
   - risky commands still require confirmation before execution
