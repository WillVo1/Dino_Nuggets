# Parallel Computer-Use Fleet for Tryton — Design

> A control-plane webapp on your Mac that spins up and drives a small fleet of
> cloud VMs, each running the **native Tryton desktop client** driven by
> **H Company's `hai` / Holo3** computer-use agent — so multiple ERP tasks run
> **in parallel** against **one** Tryton server, **without** taking over your Mac.

Status: design. Author-facing planning doc. Last updated 2026-07-11.

---

## 1. The problem

Running a computer-use agent locally means it **takes over your whole desktop**.
H Company's own docs confirm this and recommend a dedicated machine:

- The agent "controls your whole desktop" — real mouse, keyboard, screen.
- **One Python process serves one local desktop session at a time; starting a new
  session cancels the previous one.**

So today you can run **one** Tryton automation at a time and **can't use your Mac
while it runs**. Both halves of that limitation are real and documented. This
project's entire purpose is to add the **isolation layer** that removes it:
give each agent its **own** desktop, elsewhere, so many run at once and your Mac
stays free.

---

## 2. Current state (what exists today)

Local, single-instance setup under `tryton/`:

| Thing | Value |
|---|---|
| Tryton server | `trytond` 8.0, **PostgreSQL** (`postgresql://eshaankrishngulati@/`), db `tryton` |
| Web/API bind | `localhost:8000` ⚠️ (loopback only) |
| Desktop client | macOS (`tryton-client.dmg`), also `/Applications/Tryton.app` |
| Login | `admin` / `admin`, company **"Dunder Mifflin"** |
| Task suite | `tasks/01_create_sale.md` … `04_attach_document.md` (written for the **macOS** file dialog) |
| Sample docs | `sample_docs/acme_contract.txt` (attach), `internal_notes.txt` (decoy) |
| Compute-use tool | `hai` CLI / `hai-agents` SDK + **Holo3** model (H Company cloud) |

Two facts from the current setup drive the design:

1. **PostgreSQL is already in use** → concurrent clients are supported out of the
   box (SQLite would have serialized writes and blocked the fleet). ✅
2. **The server listens on `localhost`** → unreachable from cloud VMs. Must be
   re-bound behind a private network (see §6.2). ⚠️

---

## 3. The core insight

`hai` isn't magic about "your" machine — **it drives whatever desktop the runtime
process is attached to.** `host: user_device` means "the real desktop of the
machine the bridge runs on." One bridge → one desktop → one session.

Therefore:

> **Parallelism = N independent desktops, each with its own `hai` bridge.**
> Put each bridge on its own VM and the "one session at a time" limit becomes a
> *per-VM* fact, not a global bottleneck. N VMs = N parallel sessions.

A second insight that shapes everything: **the "brain" already runs in H Company's
cloud.** `hai run`, `hai sessions status/watch/cancel`, `hai --json …` are
authenticated API calls to `agp.hcompany.ai`. Only the **bridge/runtime** (the
hands and eyes) must live next to the desktop. So the orchestrator can fire and
monitor *every* task centrally from one place — it just needs each VM's
`session_id`.

---

## 4. The constraint chain (why the shape is what it is)

Each decision below forced the next; recorded so we don't relitigate:

1. **Fleet must not touch the Mac's real desktop** → each agent needs its own
   isolated desktop.
2. **Isolation on the Mac doesn't scale** → M5, arm64, **16 GB RAM**. Full VMs
   cost ~4–8 GB each → ~2–3 max. Only containers pack densely, but that's Linux.
3. **`hai` Linux runtime is not shipped** → reported that the managed
   `hai-agent-runtime` download **is not published for Linux** (bring-your-own
   binary; X11 only, no Wayland). So Linux containers on the Mac are blocked today.
4. **Windows runtime won't run on the M5** → `hai` runtime is **Windows x86_64**;
   the M5 is ARM → only Windows-on-ARM, needing x64 emulation. Risky, and full VMs
   still cap at ~2–3 on 16 GB.
5. **Move the fleet off the Mac → GCP** → removes both the RAM ceiling and the ARM
   problem. GCP instances are x86_64, so the **Windows `hai` runtime runs
   natively**.
6. **Small fleet now → Windows Server VMs on GCP** → the `hai` runtime works out of
   the box; no reverse-engineering. Linux containers remain the *future* cost/scale
   optimization (see §10) once the Linux runtime is obtained or Holo3 is self-hosted.

**Net:** small fleet of **GCP Windows Server VMs**, each running the **native
Tryton Windows client + `hai` runtime**, all pointed at **one shared `trytond`**,
orchestrated by a **webapp on the Mac**, with a **Tailscale + SMB** path for files.

---

## 5. Target architecture

```
                         YOUR MAC (stays free)
   ┌──────────────────────────────────────────────────────────────┐
   │  Control-plane webapp                                          │
   │   • holds HAI_API_KEY                                          │
   │   • provisions / tears down VMs (gcloud)                       │
   │   • fires tasks:  hai run --agent local-desktop \             │
   │                     -o '…session_id=<VM's id>' "<task>"        │
   │   • monitors:     hai --json sessions status/watch <id>        │
   │   • UI: one embedded "live view URL" pane per VM  = tabs       │
   │                                                                │
   │  trytond 8.0 (PostgreSQL, db=tryton)  ← ONE shared server      │
   │   • re-bound to a Tailscale-reachable address (not localhost)  │
   │                                                                │
   │  SMB share of  tryton/sample_docs/  (via Tailscale, private)   │
   └───────────────┬──────────────────────────┬───────────────────┘
                   │ Tailscale (WireGuard,     │ hai control API
                   │ encrypted, private)       │ (agp.hcompany.ai)
                   ▼                           ▼
   ┌─────────────────────────┐   …   ┌─────────────────────────┐
   │ GCP Windows VM #1        │       │ GCP Windows VM #N        │
   │  • Tryton Windows client │       │  • Tryton Windows client │
   │    → trytond over Tailscl│       │    → trytond over Tailscl│
   │  • hai runtime (bridge)  │       │  • hai runtime (bridge)  │
   │    → drives THIS desktop │       │    → drives THIS desktop │
   │    → session_id = …      │       │    → session_id = …      │
   │  • Z:\ = Mac SMB share   │       │  • Z:\ = Mac SMB share   │
   └─────────────────────────┘       └─────────────────────────┘
        (the model / "brain" for every session runs in H Company's cloud)
```

Three planes:

- **Control plane** (Mac webapp) — orchestrates, monitors, displays.
- **Data plane** (one `trytond` + PostgreSQL) — the shared source of truth; all
  ERP state, including attachments, lives here.
- **Execution plane** (GCP Windows VMs) — disposable desktops; each an isolated
  pair of {Tryton client, `hai` bridge}.

---

## 6. Components in detail

### 6.1 Control-plane webapp (on the Mac)

The "application" you open. Thin wrapper over `gcloud` + the `hai` API. Holds one
table:

| vm | gcp_instance | tailscale_ip | session_id | live_view_url | status | current_task |
|----|-----|-----|-----|-----|-----|-----|

Responsibilities:

- **Provision / destroy** VMs (`gcloud compute instances create/delete`, ideally
  from a prebuilt image — §6.3).
- **Bind a session**: tell a VM to start its `hai` bridge and capture the printed
  `session_id` (and `live_view_url`).
- **Dispatch tasks** centrally — because `session_id` is passed per-run via `-o`,
  you likely register **one** `local-desktop` agent and target N bridges by id:
  ```
  hai run --agent local-desktop \
    -o 'agent.environments[kind=desktop].session_id=<VM_SESSION_ID>' \
    "$(cat tasks/04_attach_document.windows.md)"
  ```
- **Monitor** with `hai --json sessions status|watch <id>`.
- **Display**: embed each session's **live view URL** in an iframe → your
  TabCube-style tabs, no custom VNC needed.

UI shell: a plain web app (React/whatever) is enough since everything is an API
call. Electron/Tauri only if you later want deep OS integration.

### 6.2 The Tryton server (shared) — the one required change

Keep **one** `trytond`; every client connects to it, so all ERP state (and the
`ir_attachment` rows) is shared automatically. Two adjustments:

1. **Reachability (required).** It currently binds `localhost:8000`. Cloud VMs
   can't reach that. Put the Mac on the Tailscale network and bind the web
   listener to the Tailscale interface (or `0.0.0.0:8000` *while firewalled to the
   tailnet only*). VMs then connect to `http://<mac-tailscale-ip>:8000`.
   - Alternative: host `trytond` itself on a small GCP VM so the DB is cloud-side
     and low-latency to the fleet; the Mac connects in like any other client.
     Cleaner if latency or Mac uptime becomes an issue.
2. **Concurrency (recommended).** For >2–3 parallel clients, run under
   **`trytond-gunicorn`/gunicorn with `--workers ≥ fleet size`** (+ `trytond-worker`
   if the task queue is used). Rule of thumb: workers ≥ parallel agents, else
   requests queue and agents stall even though PostgreSQL could keep up.

PostgreSQL is already in place, so no DB migration needed. ✅

### 6.3 The VM fleet (GCP Windows) — golden image

Build **one** image, clone it N times. Contents:

- Windows Server (x86_64) — hai runtime is native here.
- **Tryton Windows desktop client** (GTK app, `.exe` installer) — a real desktop
  window, exactly what `hai` drives. Pre-configured to connect to
  `http://<mac-tailscale-ip>:8000`, db `tryton`, and to auto-login `admin` (or a
  per-agent user — see §8).
- **`hai` runtime + SDK** (`pip install "hai-agents[cli,desktop]"`), `HAI_API_KEY`
  injected via GCP instance metadata / secret, **not** baked into the image.
- **Tailscale** (auth via an ephemeral/reusable auth key) → joins your tailnet on
  boot, mounts the Mac's SMB share as `Z:\`.
- **Startup script** that: joins Tailscale → mounts `Z:\` → launches Tryton client
  → starts the `hai` bridge → registers its `session_id` back to the webapp
  (small HTTP callback, or the webapp reads it via `hai sessions list --json`).

Golden-image discipline matters: each VM must be **stateless and disposable** —
all durable state lives in the Tryton DB, so a VM can be destroyed and recreated
freely.

### 6.4 `hai` / Holo3 integration

- **Brain in cloud, bridge on VM.** The Holo3 agent loop runs in H Company's
  cloud; each VM only runs the bridge that executes actions on its desktop and
  streams screenshots up.
- **One agent, many bridges.** Register the `local-desktop` agent once; distinguish
  VMs by `session_id` at run time via the `-o` override.
- **Endpoint.** SDK defaults to EU (`agp.eu.hcompany.ai`); set
  `HAI_BASE_URL=https://agp.hcompany.ai` for US if needed.
- **Kill-switch.** Use `--no-kill-switch` (the double-Esc listener can misfire) or
  drive via the SDK, which auto-bridges.
- **Cost model.** N parallel sessions = **N× Holo3 usage** and N× rate-limit
  consumption. Budget accordingly (see §10).

### 6.5 File access — how the agent actually reaches a document

**The agent has no special file API for this — it uses the GUI like a human.**
Attaching a document = driving **Tryton's attach dialog + the Windows file-open
dialog**. So two independent things must both be true:

1. **The file must physically exist at a path on the VM.** Two delivery methods:
   - **Tailscale + SMB mount (default).** The Mac shares `tryton/sample_docs/`;
     it appears inside each VM as `Z:\`. Files are "just there" at
     `Z:\acme_contract.txt`. Persistent, reusable for any future file task.
   - **Per-task push (minimal).** The webapp `gcloud compute scp`s just the one
     file to `C:\staging\` right before the task. Less always-on surface; good if
     you'd rather not keep a share mounted.
2. **The agent must navigate to that path** — so **put the exact path in the task
   prompt** (`"Attach Z:\acme_contract.txt to the Acme Corp sale"`). Never let it
   guess the location.

**Why this stays simple for Tryton:** attachments are uploaded **into the server
DB** (`ir_attachment`) — confirmed by your own task 04 verification
(`SELECT name, resource FROM ir_attachment`). So the file is only needed on the
**one** VM doing the attach, **only at that moment**; afterward it's in the DB and
visible to every client. You do **not** need your whole filesystem mounted on
every VM.

**Safety of Tailscale + SMB:** SMB is dangerous *on the public internet*; over
Tailscale it isn't. Tailscale is a **WireGuard mesh VPN** — traffic is end-to-end
encrypted, the share is only reachable inside your **private, authenticated
tailnet**, and it's never bound to a public IP. Hygiene: share **only**
`sample_docs/` (not `$HOME`), restrict with **tailnet ACLs**, require SMB
credentials (no guest), enable via *System Settings → General → Sharing → File
Sharing*.

**Task adaptation:** `tasks/04_attach_document.md` is written for the **macOS**
dialog and a Mac path (`Cmd+Shift+G`, `/Users/.../sample_docs/`). For the fleet it
needs a Windows variant: the **Windows** open dialog, path `Z:\acme_contract.txt`,
and the same decoy-avoidance / success criteria. Keep the excellent cross-task UI
notes from `tasks/README.md` in the prompts — they're exactly the hints Holo3
benefits from.

---

## 7. Key flows

### 7.1 Provision & register a VM
1. Webapp: `gcloud compute instances create vm-3 --image tryton-agent-img …`.
2. VM boot script: join Tailscale → mount `Z:\` → launch Tryton client (auto-login
   to `<mac-tailscale-ip>:8000`) → start `hai` bridge.
3. Bridge prints `session_id` + `live_view_url`; webapp records them (callback or
   `hai sessions list --json`).
4. Webapp shows a new tab (embedded live view). VM is now "ready".

### 7.2 Run a task end-to-end (attach a document to a sale)
1. Ensure the file is reachable: it already is at `Z:\acme_contract.txt` (mounted)
   — or push it to `C:\staging\`.
2. Webapp fires:
   ```
   hai run --agent local-desktop \
     -o 'agent.environments[kind=desktop].session_id=<VM3_SESSION>' \
     "In the Tryton client, open the Acme Corp sale, click the paperclip
      (Attachments), Add, and in the Windows file dialog select
      Z:\acme_contract.txt (NOT internal_notes.txt). Confirm one attachment."
   ```
3. Holo3 (cloud) drives VM3's desktop: opens the sale → paperclip → Add → file
   dialog → picks the file → Open. Tryton uploads it into `ir_attachment`.
4. Webapp watches `hai --json sessions watch <id>` → marks task done.
5. Verify: `psql -d tryton -tA -c "SELECT name, resource FROM ir_attachment …"`.

### 7.3 Monitor & teardown
- Live status: `hai --json sessions status <id>`; live pixels: embedded live view.
- Stop a task: `hai sessions cancel <id>`.
- Recycle a VM: destroy + recreate from the golden image (state is in the DB, so
  this is safe and cheap).

---

## 8. Concurrency & correctness

Tryton is multi-user by design; parallel clients are normal. Watch three things:

- **DB backend:** PostgreSQL ✅ (already set). No SQLite lock problem.
- **Workers:** run `trytond` under gunicorn with `workers ≥ fleet size` (§6.2),
  or agents will serialize waiting on the server.
- **Same-record conflicts:** Tryton uses **optimistic concurrency** — two agents
  editing the *same* record → *"This record has been modified…"*. Mitigate by
  **partitioning work** (agent A: sales, agent B: products, …) and/or giving each
  agent **its own Tryton user login** (also cleaner audit + avoids stale-session
  "company required" errors noted in `tasks/README.md`).

---

## 9. Security

- **Network:** all Mac↔VM traffic (Tryton API + SMB) rides **Tailscale/WireGuard**
  — encrypted, private, no public exposure. Lock down with tailnet ACLs.
- **File share:** expose only `sample_docs/`, credentialed, no guest access.
- **Secrets:** `HAI_API_KEY` and Tailscale auth keys via GCP instance metadata /
  Secret Manager — never baked into the golden image or committed.
- **Blast radius:** VMs are disposable and hold no durable secrets/state; the Mac
  never runs an agent, so your primary environment is never driven.

---

## 10. Cost & scaling

**Now (small fleet, Windows on GCP):**
- Cost = (N Windows VMs incl. Windows license) + (N× Holo3 usage). Windows VMs are
  heavy — one desktop per VM — so this is the pricey-but-simple path. Fine for 2–8.

**Later (scale/cheaper — Linux containers):**
- One Linux VM hosts many containers (each Xvfb + Tryton GTK client + bridge) →
  5–10× denser, no Windows license. Blocked today only by the **Linux `hai`
  runtime**. Two ways to unblock:
  1. **Get the Linux `hai-agent-runtime`** from H Company (they have Linux code
     paths; the binary just isn't in the public managed channel). Put it on `PATH`.
  2. **Self-host / call Holo3 directly** (OpenAI-compatible endpoint) and run your
     own X11 executor (`xdotool`/`ydotool` + screenshots), reimplementing the
     screenshot→model→action loop. Most work, but fully under your control and
     infinitely scalable.
- Recommendation: **prove the concept on Windows/GCP, then port the golden image
  to a Linux container** once (1) or (2) lands.

---

## 11. Assumptions to verify (explicit unknowns)

| # | Assumption | Confidence | How to verify |
|---|---|---|---|
| A | Windows x86_64 `hai` runtime runs on a GCP Windows VM | High (native x86_64) | Boot one VM, `hai whoami`, `hai local desktop`, run a trivial task |
| B | Linux `hai-agent-runtime` is **not** publicly shipped | Medium (search-reported) | Ask H Company; try `hai local desktop` in an Ubuntu+Xvfb container |
| C | One registered agent can target N bridges via `-o session_id` | Medium (from `-o` example) | Start 2 bridges, run against each by id |
| D | Live view URL is embeddable in an iframe (no X-Frame-Options block) | Medium | Load a session's live view URL in an iframe |
| E | Tryton Windows client can auto-login + connect over Tailscale | High | Manual connect from one VM to `<mac-tailscale-ip>:8000` |
| F | gunicorn worker count needed for target concurrency | — | Load test with the fleet |

Item **A** is the single load-bearing unknown for the current plan — verify first.

---

## 12. Build milestones

- **M0 — Verify the runtime (½ day).** One GCP Windows VM: install `hai`,
  `hai whoami`, `hai local desktop`, run "open Notepad, type hi". Confirms A.
- **M1 — One VM, end-to-end, manual (1 day).** Same VM: install Tryton Windows
  client, connect to the Mac's `trytond` over Tailscale (fix the `localhost` bind
  first), mount `Z:\`, and run the **Windows-adapted task 04** by hand via
  `hai run`. Confirms E + the file path.
- **M2 — Golden image + 2–3 VMs in parallel (1–2 days).** Bake the image;
  script provisioning; run task 01 on VM-A and task 04 on VM-B **simultaneously**;
  observe no interference in Tryton. Confirms concurrency + C.
- **M3 — Webapp control plane (2–3 days).** The table, provision/destroy,
  dispatch, `--json` monitoring, embedded live-view tabs. Confirms D.
- **M4 — Polish.** Per-agent Tryton users, gunicorn workers tuned, teardown/recycle,
  cost dashboard.
- **(Later) M5 — Linux container port** once the Linux runtime path (§10) is
  unblocked.

---

## 13. Immediate next step

**Do M0 before anything else** — the whole Windows-on-GCP plan rests on assumption
A. In parallel, **email H Company for the Linux `hai-agent-runtime` binary**, since
that single answer decides whether the cheap Linux-container future (§10) is open.

Also queue two small, independent fixes that M1 needs:
1. Re-bind `trytond` off `localhost` onto the tailnet (§6.2).
2. Write `tasks/04_attach_document.windows.md` (Windows dialog + `Z:\` path).
