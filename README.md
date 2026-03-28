# Vijay

Vijay is a local-first AI assistant platform with:

- Google sign-in
- Groq `llama-3.3-70b-versatile` chat responses
- Per-user customizable system prompts
- Admin dashboard access for `harkarshaurya@gmail.com`
- Local device-permission onboarding before automation
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
3. Open the URL shown in the terminal

### Manual start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

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
```

Notes:

- `GOOGLE_CLIENT_ID` is required for the new Google sign-in flow.
- `GROQ_API_KEY` is required for Vijay’s AI chat replies.
- `SUPABASE_SERVICE_ROLE_KEY` is used server-side only for backend logging and admin reads.
- `ADMIN_EMAIL` defaults to `harkarshaurya@gmail.com`.

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
   - customize your personal Vijay prompt if you want
   - chat and teach commands
4. If you sign in as `harkarshaurya@gmail.com`:
   - Vijay opens the admin dashboard
   - you can inspect every user
   - you can edit any user’s prompt
   - you can enable or disable device access per user

## Local Device Permission

Before Vijay performs local automation, the user must explicitly allow device access.

If device access is disabled:

- Vijay will still chat
- Vijay will still save prompts and commands
- Vijay will block local automation with a clear message

## Voice Training

The current build still uses the voice-training scaffold in [`voice/service.py`](/C:/Users/Admin/Desktop/Vijay/voice/service.py). It stores a local placeholder profile so the auth/admin layers are ready for the real microphone-based voice lock phase.

Current config file:

- [`config/voice.json`](/C:/Users/Admin/Desktop/Vijay/config/voice.json)

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
6. Start using Vijay

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
5. Use Vijay

