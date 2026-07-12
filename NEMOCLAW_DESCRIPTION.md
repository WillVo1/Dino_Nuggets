# NemoClaw — How It Works in WorkFleet

## What NemoClaw Does

NemoClaw is a **security sandbox layer** that wraps every task dispatched through WorkFleet. It sits between the user submitting a task and the agent executing it on a remote VM — sanitizing prompts before they're sent, and auditing agent actions after they complete.

```
User submits task in the webapp
       │
       ▼
  ┌─────────────┐
  │ NemoClaw    │  1. PRE-FLIGHT: scan prompt for secrets/tokens/keys
  │ pre-flight  │     → strip sensitive data ([REDACTED])
  │ check       │     → stamp a SandboxManifest (allowed paths, sandbox ID)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ hai bridge  │  2. DISPATCH: agent drives the desktop on the VM
  │ (AGP cloud)│     → NemoClaw stays passive during execution
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ NemoClaw    │  3. POST-FLIGHT: scan every agent action for violations
  │ post-flight │     → file writes outside allowed paths?
  │ audit       │     → flagged shell commands? (curl, wget, sudo, ssh)
  └──────┬──────┘     → sensitive data in agent output?
         │
         ▼
    Verification + Done
```

## The Two Hooks

### Pre-flight (`nemoclaw.pre_flight_check`)
Runs **before** the prompt is sent to the agent:
- Scans for API keys, bearer tokens, private key blocks in the prompt text
- Replaces sensitive patterns with `[REDACTED]`
- Creates a `SandboxManifest` with:
  - `sandbox_id` — deterministic hash (task ID + timestamp)
  - `allowed_paths` — `/tmp/`, `/home/agent/`, `/opt/agent/`
  - `sanitized` — whether the prompt was modified
  - `violations` — list of findings

### Post-flight (`nemoclaw.post_flight_audit`)
Runs **after** the agent session completes:
- Scans every tool-use event from the session:
  - **File writes** — checks if paths are within `allowed_paths`
  - **Shell commands** — flags `curl`, `wget`, `scp`, `ssh`, `sudo`, `chmod 777`, etc.
  - **Agent output** — checks for leaked credentials in text responses
- Produces an audit summary with `clean: true/false` and violation list
- Emits a status feed event visible in the webapp UI

## Modes

| Mode | Env Var | Behavior |
|---|---|---|
| **Passive** (default) | `NEMOCLAW_ACTIVE` not set | Logs and stamps manifests, never blocks. Existing flow unchanged. |
| **Active** | `NEMOCLAW_ACTIVE=true` | Enforces sanitization (modifies prompts) and surfaces violations as warnings in the feed. |

Passive mode is safe for production — it's observability-only. Active mode adds enforcement.

## Where It Lives in the Code

```
web/backend/app/
├── nemoclaw.py      ← NemoClawSandbox class + SandboxManifest dataclass
├── dispatcher.py    ← wired in: pre_flight before _launch, post_flight after _watch
├── config.py        ← nemoclaw_active setting (env var)
└── main.py          ← exposed in /api/config for the frontend badge

web/frontend/src/
├── hooks/useFleet.ts    ← nemoclawActive state from API
├── components/Sidebar.tsx ← green "NemoClaw" badge when active
└── lib/api.ts           ← typed config response
```

## UI

When NemoClaw is active, a green **NemoClaw** badge appears in the sidebar next to the Workfleet logo. During task execution, the feed shows status events like:
- `"NemoClaw sandbox: nc-a1b2c3d4e5f6"` — pre-flight manifest stamped
- `"NemoClaw audit: 2 violation(s) flagged"` — post-flight findings (if any)

## Demo Talking Points

- "Every task dispatched to a fleet VM passes through NemoClaw, which sanitizes the prompt to prevent credential leakage and audits agent actions for policy violations."
- "In passive mode it's observability — it logs everything without blocking. In active mode it enforces the sandbox policy."
- "The pre-flight check strips API keys, tokens, and private keys from prompts before they're sent to the agent."
- "The post-flight audit scans every file write, shell command, and text output for violations — file writes outside the workspace, flagged commands like curl/ssh/sudo, and leaked credentials."
