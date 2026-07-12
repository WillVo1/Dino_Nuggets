# Tryton Fleet — Control-Plane Webapp (M3)

"+ New Task" → plain-language task → auto-dispatched to an idle fleet VM →
live screenshot tile + streaming agent feed → DB-verified ✓.

## Architecture

```
frontend (React/Vite/Tailwind, :5173)
   │  /api/* + /ws  (vite proxy)
backend (FastAPI, :8000)
   ├─ dispatcher: FIFO queue → idle worker → hai create_session (inline agent,
   │              Environment_Desktop(session_id=<vm bridge>), max_steps=200)
   ├─ watcher:    get_session_changes long-poll (404-tolerant) → SQLite + WS
   ├─ verify:     task-specific SQL over `gcloud ssh` on trytond-server
   ├─ pool:       workers.json + /opt/agent/session_id read over `gcloud ssh`
   └─ screenshot proxy: adds the bearer token <img> tags can't send
```

Key platform facts baked in (see ../DESIGN.md §11 M0/M1 findings):
- No iframe live view (X-Frame-Options: DENY) → tiles render observation-event
  screenshot URLs.
- Concurrent trajectory cap (3/key): sessions can sit `queued` — surfaced as
  "waiting for slot", not an error.
- Fresh sessions can transiently 404 → the watcher polls through errors.

## Run

Backend (needs `gcloud` authed and `.env` with HAI_API_KEY):

    cd backend
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    cp .env.example .env   # fill in HAI_API_KEY
    .venv/bin/uvicorn app.main:app --port 8000

Frontend:

    cd frontend
    npm install
    npm run dev            # http://localhost:5173

## Operational notes

- Workers are declared in `backend/workers.json`; hit POST /api/workers/refresh
  after a VM (re)registers its bridge.
- `src/components/vendor/` holds ToolSteps/ThinkingIndicator lifted from
  Ourguide-B2B per the design; dark-mode CSS vars are set in `index.css`.
