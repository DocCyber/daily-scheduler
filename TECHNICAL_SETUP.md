# Daily Scheduler — Technical Setup & Architecture

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [File Structure](#file-structure)
3. [Component Details](#component-details)
4. [Data Files](#data-files)
5. [Timer System](#timer-system)
6. [Task Model & Features](#task-model--features)
7. [Dataset System (Home / Work)](#dataset-system-home--work)
8. [Cloud Sync](#cloud-sync)
9. [Prerequisites & Installation](#prerequisites--installation)
10. [Secrets File Setup](#secrets-file-setup)
11. [Voice Monkey Setup](#voice-monkey-setup)
12. [Cloudflare R2 Sync Setup](#cloudflare-r2-sync-setup)
13. [Troubleshooting](#troubleshooting)
14. [Quick Reference](#quick-reference)

---

## Architecture Overview

Desktop app built on Python + Tkinter. No web server, no database — everything is
plain JSON files on disk. Two optional cloud features (Alexa announcements via Voice
Monkey, multi-machine sync via Cloudflare R2) layer on top without being required.

```
┌─────────────────────────────────────────────────────┐
│                     main.py                         │
│              (entry point, boots MainWindow)        │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  MainWindow (tk.Tk)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  TimerBar   │  │ PlanningBlock│  │ TaskBlock  │  │
│  │  (timer UI  │  │  (planning   │  │ ×8 (work   │  │
│  │  controls)  │  │   phase)     │  │  blocks)   │  │
│  └──────┬──────┘  └──────────────┘  └────────────┘  │
│         │                            ┌────────────┐  │
│         │                            │ TaskQueue  │  │
│         │                            │(incomplete)│  │
│         │                            └────────────┘  │
└─────────┼───────────────────────────────────────────┘
          │
┌─────────▼──────────┐    ┌──────────────────────────┐
│   TimerManager     │    │      DataManager          │
│  (countdown loop,  │◄───┤  (load/save JSON, cloud   │
│   phase advance,   │    │   sync, secrets, config)  │
│   announcements)   │    └──────────┬───────────────┘
└────────────────────┘               │
                           ┌─────────▼──────────────┐
                           │    CloudflareSync       │
                           │  (upload/download R2    │
                           │   via Worker HTTP API)  │
                           └────────────────────────┘
```

**Announcement flow:**

```
TimerManager ──► VoiceMonkeyClient  ──► voicemonkey.io API ──► Alexa
             └─► LocalChimeClient   ──► Windows Beep + pyttsx3 / SAPI TTS
```

Mode is toggled at runtime via radio buttons in the timer bar and persisted in `config.json`.

---

## File Structure

```
sceduler/
├── main.py                          # Entry point
├── requirements.txt                 # pip: requests>=2.31.0
├── TECHNICAL_SETUP.md               # This file
├── user_manual.txt                  # End-user guide
├── .gitignore
├── Git-Pull.bat / git-push.bat      # Convenience git scripts
│
├── secrets/
│   └── daily-scheduler-secrets.json.example   # Template — DO NOT commit real values
│
├── data/                            # Home dataset (git-ignored)
│   ├── tasks.json                   # Planning + 8 blocks + queue
│   ├── timer_state.json             # Current timer phase & countdown
│   ├── recurring.json               # Recurring task templates
│   ├── config.json                  # App preferences + active_dataset
│   ├── completed_log.json           # Historical completed tasks
│   ├── incomplete_history.json      # Historical incomplete tasks
│   └── daily_stats.json             # Per-day completion stats
│
├── data-work/                       # Work dataset (same structure, always local)
│
├── src/
│   ├── data_manager.py              # All persistence, secrets loading, cloud sync
│   ├── timer_manager.py             # Countdown logic, phase transitions, announcements
│   │
│   ├── models/
│   │   ├── timer_state.py           # TimerState dataclass + SCHEDULE constant
│   │   ├── task.py                  # Task dataclass
│   │   ├── block.py                 # Block container (name + list of Tasks)
│   │   └── recurring_task.py        # RecurringTask dataclass
│   │
│   ├── ui/
│   │   ├── main_window.py           # Root window, layout, dataset switching, new-day logic
│   │   ├── timer_bar.py             # Timer display, play/pause/skip/reset controls
│   │   ├── planning_block.py        # Planning phase block UI
│   │   ├── task_block.py            # Numbered work block UI (×8)
│   │   ├── task_item.py             # Single task row widget
│   │   ├── task_queue.py            # Incomplete task queue panel
│   │   └── recurring_dialog.py      # Recurring task management dialog
│   │
│   └── integrations/
│       ├── voice_monkey.py          # VoiceMonkeyClient (HTTP POST to voicemonkey.io)
│       ├── local_chime.py           # LocalChimeClient (Windows beep + SAPI TTS)
│       └── cloudflare_sync.py       # CloudflareSync (upload/download via Worker)
│
└── scheduler-sync-worker/           # Cloudflare Worker (JavaScript)
    ├── src/index.js                 # Worker handler — REST API over R2 bucket
    ├── wrangler.toml                # Worker config (R2 binding: SCHEDULER_DATA)
    └── package.json
```

---

## Component Details

### `main.py`
Boots `MainWindow` and calls `mainloop()`. Three lines of real code.

---

### `MainWindow` (`src/ui/main_window.py`)
The root `tk.Tk` window. Owns the full application lifecycle.

**On startup:**
1. Reads `active_dataset` from `data/config.json` (defaults to `"home"`)
2. Creates `DataManager` pointed at the correct data directory
3. Creates `TimerManager` (loads persisted timer state)
4. Builds the widget tree
5. Warns if Voice Monkey isn't configured
6. Schedules a 1-second-delayed cloud download (home dataset only)

**Layout** — all inside a scrollable canvas:
- Row 0: `TimerBar` (full width)
- Row 1: `PlanningBlock` (full width)
- Rows 2+: 8 `TaskBlock` widgets in a responsive grid (1–4 columns, adjusts on resize)
- Bottom: `TaskQueue` (full width)
- Outside scroll: bottom button bar (Start New Day, Save, ☁ Sync Now, Recurring, Exit)

**Responsive columns:** Uses hysteresis thresholds against a fixed block width of 280px.
Adds a column when there's 20% extra space; removes one when under by 20px buffer.

**Key callbacks:**
- `on_timer_state_changed()` — fired every second by `TimerManager`; updates `TimerBar` and block highlight
- `on_data_changed()` — fired by any task edit; triggers immediate silent save
- `switch_dataset()` — tears down and rebuilds `DataManager` + `TimerManager` in-place; reloads all task widgets

**Block highlight:** Only the currently active phase block gets a colored border.
Tracking uses `_highlighted_phase` (previous) and `_prev_timer_phase` to avoid
re-rendering every tick.

**High-priority escalation:** On every block transition, incomplete high-priority
tasks from the outgoing block are automatically moved to the next block (or to the
queue if it was Block 8).

**Auto-save:** Every 30 seconds via `after()`, plus immediately on any task change.

---

### `TimerBar` (`src/ui/timer_bar.py`)
Green/blue/orange header bar. Contains:
- Announcement mode radio buttons (Voice Monkey / Local Chime)
- Dataset radio buttons (Home / Work) — triggers `switch_dataset()` in MainWindow
- Phase label + MM:SS countdown + progress bar
- **▶ Start** — enabled only before the timer has been started for the first time
- **⏸ Pause / ▶ Continue** — toggles between pause and resume once a session is in progress
- **⏭ Skip** — jumps immediately to the next phase
- **↺ Reset** — resets to Planning phase (not started)
- **■ End Day** — stops timer cleanly, prevents further announcements

Button state logic (three states):
| State | Start btn | Pause/Continue btn |
|---|---|---|
| Never started (`is_running=False`, `paused_at=None`) | Enabled | Disabled, "⏸ Pause" |
| Running | Disabled | Enabled, "⏸ Pause" |
| Paused (`is_running=False`, `paused_at` set) | Disabled | Enabled, "▶ Continue" |

---

### `TimerManager` (`src/timer_manager.py`)
Owns the countdown loop. No UI dependencies beyond the `root_window.after()` hook
and the `on_state_change_callback`.

**State persistence:** Saves `timer_state.json` on every tick and every state change.

**Startup safety:** If the saved state has `is_running=True` (app was closed while
running), it is immediately flipped to `is_running=False` with `paused_at` set. The
user must explicitly click Continue to resume. This prevents the start button from
appearing to do nothing.

**Tick loop:** `_tick()` is scheduled via `root_window.after(1000, self._tick)`.
On phase completion, `_advance_phase()` sets up the new phase state and calls
`_tick()` directly (not via `after()`) to start the fresh loop without a 1-second gap.

---

### `DataManager` (`src/data_manager.py`)
Single class that owns all file I/O.

**Secrets loading:** On init, tries three paths in order:
```
D:\secrets\daily-scheduler-secrets.json
C:\secrets\daily-scheduler-secrets.json
~\secrets\daily-scheduler-secrets.json
```
Secrets are injected into the live config dict at runtime and **stripped back out**
before writing `config.json` — they never land in the repo.

**Config:** `data/config.json` stores preferences only (announcement mode, sync
settings, active_dataset). Secrets are never written here.

**`active_dataset`** is always read from and written to `data/config.json` regardless
of which dataset is currently active.

---

### `CloudflareSync` (`src/integrations/cloudflare_sync.py`)
HTTP client that talks to the deployed Cloudflare Worker.

- **`sync()`** — upload all → download all
- **`download_all()`** — used on startup (download only)
- **`tasks.json` merge** — completed-state-wins: cloud structure is authoritative for
  task order and new tasks; if a task exists in both and is completed locally but not
  in the cloud, it stays completed. Local-only tasks (not in cloud) are appended so
  nothing is lost.
- Work dataset: `CloudflareSync.enabled` is forced to `False` — never syncs.

---

### Cloudflare Worker (`scheduler-sync-worker/src/index.js`)
Thin REST proxy over an R2 bucket. Three endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API info / health check |
| `GET` | `/list` | List all files in bucket |
| `POST` | `/upload` | Upload `{filename, content}` — whitelist enforced |
| `GET` | `/download/:filename` | Download file by name |

Allowed filenames: `config.json`, `tasks.json`, `timer_state.json`,
`completed_log.json`, `incomplete_history.json`, `daily_stats.json`.

R2 binding name: `SCHEDULER_DATA` (configured in `wrangler.toml`).

---

## Data Files

### `tasks.json`
```json
{
  "planning": { "name": "Planning", "tasks": [...] },
  "blocks":   [ { "name": "Block 1", "tasks": [...] }, ... ],
  "queue":    [ ... ]
}
```

### `timer_state.json`
```json
{
  "current_phase": "Block 2",
  "phase_type": "work",
  "phase_index": 4,
  "time_remaining_seconds": 1843,
  "is_running": false,
  "started_at": "2026-04-04T09:15:00.000000",
  "paused_at": "2026-04-04T09:45:12.000000"
}
```

### `recurring.json`
Array of `RecurringTask` objects. Managed through the Recurring dialog.
Never overwritten by cloud sync (machine-local by design).

### `config.json`
```json
{
  "timer": {
    "auto_advance": true,
    "enable_announcements": true,
    "warning_at_minutes": [5, 2],
    "announcement_mode": "voice_monkey"
  },
  "cloudflare_sync": {
    "enabled": true,
    "auto_sync_on_startup": true
  },
  "active_dataset": "home"
}
```

---

## Timer System

### Daily Schedule (17 phases, ~8 hours)

| Index | Phase | Type | Duration |
|---|---|---|---|
| 0 | Planning | work | 20 min |
| 1 | Break | break | 15 min |
| 2 | Block 1 | work | 45 min |
| 3 | Break | break | 15 min |
| 4 | Block 2 | work | 45 min |
| 5 | Break | break | 15 min |
| 6 | Block 3 | work | 45 min |
| 7 | Break | break | 15 min |
| 8 | Block 4 | work | 45 min |
| 9 | Break | break | 15 min |
| 10 | Block 5 | work | 45 min |
| 11 | Break (Lunch) | break | **30 min** |
| 12 | Block 6 | work | 45 min |
| 13 | Break | break | 15 min |
| 14 | Block 7 | work | 45 min |
| 15 | Break | break | 15 min |
| 16 | Block 8 | work | 45 min |

### Announcements

| Trigger | Message |
|---|---|
| Start (Planning) | "Starting planning phase. 20 minutes to organize your day." |
| Start (Block N) | "Starting Block N. Time to focus." |
| Start (Break) | "Starting X minute break." |
| 5 min remaining (work) | "5 minutes remaining in [phase]" |
| 2 min remaining (work) | "2 minutes remaining in [phase]" |
| 5 min remaining (break) | "Break ending in 5 minutes" |
| 2 min remaining (break) | "Break ending in 2 minutes" |
| Phase transition | "[Previous] ended. Begin [next]." |
| End of day | "Block 8 complete. Your work day is finished!" |

Warning thresholds are configurable: `timer.warning_at_minutes` in `config.json`.

---

## Task Model & Features

### Task fields

| Field | Type | Description |
|---|---|---|
| `text` | str | Task description |
| `completed` | bool | Done state |
| `created_at` | ISO str | Auto-set on creation |
| `completed_at` | ISO str | Set when marked done |
| `times_queued` | int | How many times moved to queue across days |
| `is_recurring` | bool | Created from a recurring template |
| `is_high_priority` | bool | Auto-escalates on block transition |
| `blocks_escalated` | int | Count of times auto-moved to next block |

### High-priority escalation
When a block's timer phase ends, any incomplete high-priority tasks are
automatically moved to the next block. If it was Block 8, they go to the queue.
`blocks_escalated` increments each time. Regular tasks are left in place — only
high-priority ones move.

### Recurring tasks
Stored as templates in `recurring.json`. Applied on "Start New Day".

| Schedule type | Behaviour |
|---|---|
| `daily` | Applied every day |
| `day_of_week` | Applied on specified weekdays (0=Mon, 6=Sun) |
| `day_of_month` | Applied on specified days of the month |

Idempotent: `last_applied_date` is checked — templates already applied today are
skipped. Recurring tasks that were incomplete at day-end are silently discarded
(not queued) — they'll be re-created fresh the next morning.

### New Day flow
1. Completed tasks → `completed_log.json`
2. Incomplete non-recurring tasks → `queue` (and `incomplete_history.json`)
3. Incomplete recurring tasks → silently discarded
4. All blocks cleared
5. Recurring templates applied to fresh blocks
6. Timer reset to Planning (not started)

---

## Dataset System (Home / Work)

Two fully independent datasets stored in separate directories:

| Dataset | Directory | Cloud sync |
|---|---|---|
| Home | `data/` | Yes (if configured) |
| Work | `data-work/` | Never — always local |

The active dataset is persisted in `data/config.json` as `active_dataset`.
Switching datasets via the radio buttons in the timer bar:
1. Saves current data
2. Cancels the running timer tick
3. Rebuilds `DataManager` and `TimerManager` for the new directory
4. Reloads all task widgets
5. Shows/hides the Sync button
6. Updates the window title: `Daily Scheduler [Home]` / `Daily Scheduler [Work]`

---

## Cloud Sync

Sync is one-directional per operation:

```
Local disk ──upload──► Cloudflare Worker ──PUT──► R2 bucket
Local disk ◄─download─ Cloudflare Worker ◄─GET─── R2 bucket
```

**Full sync** (`☁ Sync Now` button): upload all → download all.
**Startup**: download only (no upload on startup).

### tasks.json merge logic (on download)
Cloud structure is the base. Local completed state is preserved:
- If a task text matches in both local and cloud, and it's completed locally → stays completed
- Tasks in local but not in cloud → appended (not lost)
- Tasks in cloud but not in local → included as-is

All other files (timer state, logs, config, stats) are plain overwrites — cloud wins.

### Synced files
`config.json`, `tasks.json`, `timer_state.json`, `completed_log.json`,
`incomplete_history.json`, `daily_stats.json`

`recurring.json` is **never synced** — recurring templates are machine-local.

---

## Prerequisites & Installation

```
pip install requests
```

That's the only Python dependency. The app uses Python's standard library
(tkinter, json, pathlib, dataclasses, datetime) for everything else.

Python 3.8+ required (dataclasses, walrus not used but f-strings and typing are).

---

## Secrets File Setup

Both Voice Monkey and Cloudflare sync are configured through a single JSON file
that lives **outside the project folder**. This keeps credentials out of the repo.

### Locations checked (in order)

```
D:\secrets\daily-scheduler-secrets.json   ← checked first
C:\secrets\daily-scheduler-secrets.json   ← checked second
~\secrets\daily-scheduler-secrets.json    ← fallback (home folder)
```

Create the folder (`D:\secrets\` if you have a D: drive, `C:\secrets\` otherwise)
and put the file there. A template is at `secrets/daily-scheduler-secrets.json.example`.

### Format

```json
{
  "voice_monkey_api_url": "https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE",
  "cloudflare_worker_url": "https://scheduler-sync-worker.your-subdomain.workers.dev"
}
```

You only need the keys for the features you're using. Missing or blank values are
silently ignored — the app runs without those features.

Secrets are loaded at startup, injected into the live config dict, and never written
to `config.json` or committed to git.

---

## Voice Monkey Setup

Voice Monkey sends text-to-speech announcements to Alexa devices over the internet.

> **Heads-up on audio quality:** The TTS voice Voice Monkey uses is functional but
> robotic. Local Chime (no setup, Windows only) plays a system beep + Windows SAPI
> speech and is arguably more pleasant as a simple audio cue.

### Step 1 — Create account
Go to https://voicemonkey.io and sign up (free tier is sufficient).

### Step 2 — Create a Monkey (device group)
Dashboard → **Monkeys** → **Add Monkey** → name it (e.g., "everything") → link to
your Alexa account via the Alexa app.

### Step 3 — Get your API token
Dashboard → **Account** / **API** → copy token.

### Step 4 — Build URL and add to secrets
```
https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE_NAME
```

Add to secrets file as `voice_monkey_api_url`.

### Step 5 — Switch mode in app
Timer bar radio buttons → **Voice Monkey**. Selection saves automatically.

---

## Cloudflare R2 Sync Setup

Syncs Home task data across machines via Cloudflare R2 (object storage) + a
Cloudflare Worker (HTTP proxy). Free tier covers typical usage entirely.

**Free tier limits:** R2: 10 GB storage, 10M requests/month. Workers: 100K req/day.

### Step 1 — Create Cloudflare account
https://cloudflare.com (free).

### Step 2 — Install Node.js and Wrangler
Node.js: https://nodejs.org

```
npm install -g wrangler
wrangler --version
```

### Step 3 — Authenticate
```
wrangler login
```

### Step 4 — Create R2 bucket
```
wrangler r2 bucket create scheduler-data
wrangler r2 bucket list    # verify it appears
```

### Step 5 — Deploy the Worker
```
cd scheduler-sync-worker
npm install
npx wrangler deploy
```

Output will include your Worker URL:
```
https://scheduler-sync-worker.YOUR-SUBDOMAIN.workers.dev
```

Visit that URL in a browser — you should get a JSON response listing the API endpoints.

### Step 6 — Add Worker URL to secrets file
```json
{
  "cloudflare_worker_url": "https://scheduler-sync-worker.YOUR-SUBDOMAIN.workers.dev"
}
```

### Step 7 — Verify config.json
```json
{
  "cloudflare_sync": {
    "enabled": true,
    "auto_sync_on_startup": true
  }
}
```

`auto_sync_on_startup: true` downloads cloud data 1 second after launch.
Set to `false` to sync manually only.

### Step 8 — Test
1. Launch app → click **☁ Sync Now**
2. Console should show:
   ```
   [Sync] ═══ Starting full sync ═══
   [Sync] ✓ Uploaded tasks.json
   ...
   [Sync] ═══ Sync complete ✓ ═══
   ```
3. Confirm in Cloudflare dashboard → R2 → `scheduler-data` bucket

### Additional machines
1. Install Python + `pip install requests`
2. Clone/copy the repo
3. Create secrets file at `D:\secrets\` or `C:\secrets\` with the same Worker URL
4. Run — tasks download automatically on startup

### Disabling sync temporarily
Set `"enabled": false` in `cloudflare_sync` section of `data/config.json`.

### Security note
The Worker URL is unauthenticated. Anyone who knows it can read or write your task
data. For personal use across your own machines this is fine. If you ever need to
restrict access, add an API key header check to `scheduler-sync-worker/src/index.js`.

---

## Troubleshooting

**Start button does nothing**
- The timer state was saved as `is_running=True` from a previous session. Fixed in
  current code — on startup, any running state is reset to paused. If you see this,
  delete `data/timer_state.json` and restart.

**Pause button doesn't resume**
- Fixed in current code — the Pause button is now a toggle. If you're on an old
  version, click **▶ Start** to resume from a paused state.

**Announcements don't work**
- Console on launch will say which secrets file was loaded, or "No secrets file found"
- Check the file path exactly (filename, folder, drive letter)
- Validate the JSON (no trailing commas)
- Confirm the radio button is set to the mode you expect

**☁ Sync Now is greyed out**
- `cloudflare_worker_url` is missing or blank in secrets file
- Restart after editing the secrets file — it only loads at startup
- Work dataset never shows Sync Now (by design)

**Sync fails**
- Visit your Worker URL in a browser — if no response, Worker isn't deployed
- Re-run `npx wrangler deploy` from `scheduler-sync-worker/`
- Check auth: `wrangler whoami`

**"not in cloud (skipping)" on first sync**
- Normal. First sync uploads everything; subsequent syncs will find the files.

**Worker deploy fails — auth errors**
```
wrangler logout
wrangler login
```

**Worker deploy fails — binding errors**
Check `scheduler-sync-worker/wrangler.toml` contains:
```toml
[[r2_buckets]]
binding = "SCHEDULER_DATA"
bucket_name = "scheduler-data"
```

---

## Quick Reference

### Features and requirements

| Feature | Requires | Where to configure |
|---|---|---|
| Local Chime | Nothing (Windows only) | Radio button in timer bar |
| Voice Monkey | voicemonkey.io account + Alexa | Secrets file |
| Cloud Sync | Cloudflare account + Node.js | Secrets file |

### Secrets file locations (checked in order)
1. `D:\secrets\daily-scheduler-secrets.json`
2. `C:\secrets\daily-scheduler-secrets.json`
3. `~\secrets\daily-scheduler-secrets.json`

### Key data directories
| Path | Purpose | Synced |
|---|---|---|
| `data/` | Home dataset | Yes |
| `data-work/` | Work dataset | Never |

### Worker API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Health check / API info |
| GET | `/list` | List files in R2 bucket |
| POST | `/upload` | Upload `{filename, content}` |
| GET | `/download/:filename` | Download file |
