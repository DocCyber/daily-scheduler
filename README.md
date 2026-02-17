# Daily Scheduler

Daily task scheduler GUI with 9 time blocks (Planning + 8 main blocks) for organizing your day.

## Features
- **Timer System**: Auto-advancing timer for full 8-hour workday with breaks
  - Planning: 20 min → 15 min break → 8 work blocks (45 min each) with breaks
  - 30-minute lunch break between Block 5 and 6
  - Visual indicators showing active block
  - Pause/resume, skip, reset, and end day controls
- **House-Wide Announcements**: Voice Monkey integration for Alexa announcements
  - Announces phase transitions to all speakers throughout house
  - Works when away from desk or outside
  - More reliable than Alexa timers (no batching)
- **Planning Block**: 20-minute planning section at top
- **8 Main Blocks**: 45-minute work blocks in grid layout
- **Task Queue**: Scrollable list for incomplete tasks that need rescheduling
- **Task Management**: Add, edit, complete, and delete tasks
- **Persistence**: Auto-saves every 30 seconds to local JSON files
- **Daily Reset**: "Start New Day" button to log completed tasks and move incomplete ones to queue
- **Statistics**: Tracks completed tasks, incomplete tasks, and daily completion rates

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/DocCyber/daily-scheduler.git
   cd daily-scheduler
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your secrets file (optional, for announcements and cloud sync):
   - Copy `secrets/daily-scheduler-secrets.json.example` to `D:\secrets\daily-scheduler-secrets.json`
   - Fill in your Voice Monkey API URL and Cloudflare Worker URL
   - App works fully without this - announcements and sync will just be disabled
   - See **Secrets Setup** section below for details

4. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Timer Controls
1. **Start**: Begin the timer from Planning phase (20 minutes)
2. **Pause**: Temporarily stop the timer (can resume later)
3. **Skip**: Advance to next phase immediately
4. **Reset**: Return to Planning phase and reset timer
5. **End Day**: Stop timer and disable announcements (useful when leaving early)

The timer auto-advances through the full schedule:
```
Planning (20 min) → Break (15 min) → Block 1 (45 min) → Break (15 min) → ...
... → Block 5 (45 min) → Lunch (30 min) → Block 6 (45 min) → ... → Block 8 (45 min)
```

### Task Management
1. **Add Tasks**: Click "+ Add Task" buttons in any block to add new tasks
2. **Complete Tasks**: Check the checkbox when a task is done
3. **Mark Block Complete**: Use "Block Complete" checkbox when entire block is finished
4. **Queue Tasks**: Incomplete tasks from previous day appear in queue at bottom
5. **Move from Queue**: Click "→1" through "→8" buttons to move queued tasks to specific blocks
6. **Start New Day**: Click "Start New Day" to reset all blocks, timer, and move incomplete tasks to queue
7. **Save**: Click "Save" button or wait 30 seconds for auto-save

## Secrets Setup

API credentials are kept **completely separate** from the project folder so you can safely copy, share, or thumb-drive the project without leaking tokens.

**Create your secrets file** by copying the example from the repo:
```
secrets/daily-scheduler-secrets.json.example  →  D:\secrets\daily-scheduler-secrets.json
```

Fill in your actual values:
```json
{
  "voice_monkey_api_url": "https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE",
  "cloudflare_worker_url": "https://scheduler-sync-worker.your-subdomain.workers.dev"
}
```

**Where the app looks** (first one found wins):
1. `D:\secrets\daily-scheduler-secrets.json`
2. `C:\secrets\daily-scheduler-secrets.json`
3. `~\secrets\daily-scheduler-secrets.json`

**If no secrets file is found**: App runs normally - timer, tasks, and all UI work fine. Announcements are silenced and cloud sync is disabled.

| Secrets File | Announcements | Cloud Sync | Timer & Tasks |
|---|---|---|---|
| Found | ✅ | ✅ | ✅ |
| Not found | ⚠️ Silent | ⚠️ Disabled | ✅ Full |

## Data Storage

All data is stored locally in the `data/` directory:
- `tasks.json` - Current day's tasks and queue
- `timer_state.json` - Current timer position (for pause/resume)
- `config.json` - Timer preferences only (no secrets)
- `completed_log.json` - Log of all completed tasks with timestamps
- `incomplete_history.json` - History of tasks moved to queue
- `daily_stats.json` - Daily completion statistics

**Note**: The `data/` directory is machine-specific and NOT synced to GitHub. Secrets are stored separately in `D:\secrets\` (never in the project folder).

### Syncing Data Across Machines

If you use multiple computers in your house and want to share task data, here are your options:

**Option 1: Cloudflare R2 Sync (Recommended - Built-in)**

The app includes built-in cloud sync using Cloudflare R2 object storage:

**Features:**
- ☁️ One-click sync via "Sync Now" button
- 🔄 Auto-download latest data on app startup
- 💰 Completely free (Cloudflare R2 free tier)
- 🌍 Works from anywhere with internet
- 🚀 No egress fees (unlike AWS S3)

**Quick Setup:**
1. Install Wrangler CLI: `npm install -g wrangler`
2. Login to Cloudflare: `wrangler login`
3. Deploy Worker: `cd scheduler-sync-worker && npx wrangler deploy`
4. Copy the Worker URL from deployment output
5. Edit `data/config.json`:
   ```json
   {
     "cloudflare_sync": {
       "enabled": true,
       "worker_url": "https://scheduler-sync-worker.your-subdomain.workers.dev"
     }
   }
   ```
6. Click "☁ Sync Now" button to sync!

**See CLOUDFLARE_SYNC_SETUP.md for detailed setup instructions.**

---

**Option 2: Cloud Storage Sync (Symbolic Links)**
- Move the `data/` folder to a cloud-synced location:
  - **Dropbox**: `C:\Users\YourName\Dropbox\daily-scheduler-data`
  - **OneDrive**: `C:\Users\YourName\OneDrive\daily-scheduler-data`
  - **Google Drive**: Use Google Drive Desktop to sync a folder
- Create a symbolic link from the app to the cloud folder:
  ```bash
  # Windows (run as Administrator)
  mklink /D "D:\Users\Phoenix\Desktop\work\sceduler\data" "C:\Users\Phoenix\Dropbox\daily-scheduler-data"
  ```
- **Pros**: Works automatically, no code changes needed
- **Cons**: Potential conflicts if running on two machines simultaneously

**Option 3: Network Share (Home Network)**
- Create a shared folder on one machine (e.g., NAS, always-on PC)
- Mount it on all machines and symlink the `data/` folder to it
- **Pros**: Fast, local network, no cloud service needed
- **Cons**: Requires network share setup, must be on same network

**Option 4: Git-Based Sync**
- Initialize git in the `data/` folder and push to a private GitHub repo
- Pull/push data before/after each session
- Add automation with git hooks
- **Pros**: Version history, conflict resolution, works anywhere
- **Cons**: Manual sync required, more complex

**Recommended**: Option 1 (Cloudflare R2) provides the best balance of convenience, reliability, and cost (free!).

## Project Structure

```
daily-scheduler/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── src/
│   ├── data_manager.py        # JSON I/O and data persistence
│   ├── timer_manager.py       # Timer countdown and state machine
│   ├── models/
│   │   ├── task.py           # Task data class
│   │   ├── block.py          # Block data class
│   │   └── timer_state.py    # Timer state and schedule
│   ├── integrations/
│   │   └── voice_monkey.py   # Voice Monkey API client
│   └── ui/
│       ├── main_window.py    # Main application window
│       ├── timer_bar.py      # Timer display and controls
│       ├── planning_block.py # Planning section widget
│       ├── task_block.py     # Task block widget
│       ├── task_item.py      # Individual task row
│       └── task_queue.py     # Queue widget
└── data/                      # Local data (git-ignored)
    ├── config.json           # Voice Monkey configuration
    ├── timer_state.json      # Current timer state
    └── tasks.json            # Current tasks
```

## Known Issues

### Voice Monkey Announcements
**Status**: Needs troubleshooting

The Voice Monkey integration is currently triggering presence/doorbell announcements ("someone is at the everything") instead of TTS text-to-speech announcements. This appears to be an issue with how the API endpoint is being called or the device configuration.

**Temporary Workaround**: Disable announcements by setting `enable_announcements: false` in `data/config.json` to prevent the dogs (and spouse) from going crazy while this is being investigated.

**To Disable Announcements**:
```json
{
  "timer": {
    "enable_announcements": false
  }
}
```

The timer will still work normally, just without the house-wide audio announcements.

## License

Open source - use as you wish!
