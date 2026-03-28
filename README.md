# Vijay

Vijay is a local-first AI assistant platform scaffold designed for voice-enabled personal automation, authenticated chat, safe command learning, and Supabase-backed history storage.

This starter repository already includes:

- A Python `FastAPI` backend served by `python main.py`
- A lightweight web UI for signup, login, chat, history, and command training
- Local-safe command execution with dry-run mode enabled by default
- Supabase integration points for auth plus conversation/action logging
- Config-driven project structure for commands, settings, and voice data
- Beginner-friendly Windows bootstrap via `install.bat`

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

### Option A: One-click install on Windows

1. Double-click `install.bat`
2. Wait for the virtual environment and dependencies to install
3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Option B: Manual install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

## Current Starter Features

- Signup and login API routes prepared for Supabase email/password auth
- Chat interface with local conversation history
- Command-learning flow for instructions like:
  - `When I say open my setup - open Android Studio, Claude Code, YouTube and ChatGPT`
- Command execution engine with:
  - safe validation
  - dry-run mode
  - confirmation gate for risky text
- Voice subsystem scaffold with local profile storage hooks
- Logging to local files and optional Supabase tables

## Required Configuration

Create a `.env` file from `.env.example` and add:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Notes:

- `SUPABASE_ANON_KEY` is used for user auth calls.
- `SUPABASE_SERVICE_ROLE_KEY` is recommended for secure server-side logging into the `users`, `conversations`, and `actions` tables.
- Keep the service role key on the backend only. Never expose it in frontend JavaScript.

## Supabase Setup

1. Create a new Supabase project.
2. Open the SQL editor.
3. Run the SQL from [`config/supabase_schema.sql`](/C:/Users/Admin/Desktop/Vijay/config/supabase_schema.sql).
4. Open Project Settings -> API.
5. Copy the project URL, anon key, and service role key into `.env`.
6. In Authentication -> Providers, ensure Email auth is enabled.
7. In Authentication -> URL configuration, add your local callback or local site URL if you enable email confirmation flows.

## How To Run Locally

```powershell
python main.py
```

Then visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

## How To Train Voice

The repository includes the voice training flow scaffold and local profile config under [`config/voice.json`](/C:/Users/Admin/Desktop/Vijay/config/voice.json).

Starter workflow:

1. Open the Vijay UI
2. Use the Voice Training panel
3. Trigger a training save
4. Confirm that voice lock is enabled in the status panel

The current starter implementation stores a local profile placeholder so the rest of the app can be built around it. The next phase should replace this with:

- Whisper or Faster-Whisper for transcription
- Speaker embedding extraction
- Similarity matching against the authorized embedding

## How To Add Commands

Use the training input in the UI or send a chat message such as:

```text
When I say open my setup - open Android Studio, Claude Code, YouTube and ChatGPT
```

The command will be saved into [`config/commands.json`](/C:/Users/Admin/Desktop/Vijay/config/commands.json).

To keep execution safe:

- Only allow known app aliases from [`config/settings.json`](/C:/Users/Admin/Desktop/Vijay/config/settings.json)
- Keep `dry_run` enabled until you are happy with the mappings
- Require confirmation for risky instructions

## Packaging Roadmap

### Package as an executable

1. Install PyInstaller in the app environment.
2. Build:

```powershell
pyinstaller --onefile --name Vijay main.py
```

3. Copy the `config/` and `frontend/` folders next to the executable or include them in the spec file.

### Improve desktop UX

Recommended next step:

- Wrap the local web UI with Tauri or Electron only if you need a native shell.
- Keep FastAPI as the backend service layer.

## Deployment Roadmap

### Local user install

1. Download repository or packaged release
2. Run `install.bat`
3. Add Supabase keys to `.env`
4. Open the local UI
5. Train voice
6. Add allowed apps and custom commands

### Backend deployment

1. Keep Vijay local-first for desktop automation.
2. Deploy the FastAPI server to Railway, Render, Fly.io, or a VPS only if you separate automation from desktop execution.
3. Store secrets in the deployment platform secret manager.
4. Restrict CORS to trusted origins.
5. Keep desktop-only actions disabled in cloud deployments.

## Implementation Phases

### Phase 1: Starter foundation

- Repo scaffold
- Web UI
- Local config and logging
- Supabase auth and history integration hooks

### Phase 2: Real voice pipeline

- Microphone capture
- Whisper transcription
- Speaker verification embeddings
- Voice lock enforcement

### Phase 3: Rich automation

- File operations with confirmation policies
- Multi-step workflow planner
- App launch templates
- Browser and system action plugins

### Phase 4: Hardening and packaging

- Test coverage
- Background service mode
- PyInstaller build
- GitHub Actions for release automation

## Security Notes

- Vijay blocks text that looks like destructive shell activity.
- Risky actions require explicit confirmation before execution.
- App launches are restricted to configured aliases.
- Keep secrets in `.env`, never in source control.

