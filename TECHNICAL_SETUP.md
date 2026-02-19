# Daily Scheduler — Technical Setup Guide

This guide covers everything needed to unlock the two optional features:
**Voice Monkey announcements** and **Cloudflare R2 cloud sync**.

The app runs fine without either of these. This is for someone who wants the
full experience and has a basic comfort level with command-line tools.

---

## Prerequisites (both features)

- Python 3.x installed, with `pip`
- Install the one Python dependency if you haven't already:
  ```
  pip install requests
  ```

---

## Part 1 — Secrets File

Both features (Voice Monkey and Cloudflare sync) are configured through a
single JSON file that lives **outside the project folder** on your machine.
This keeps credentials out of the repo entirely.

### Where to put it

The app checks the following locations in order and uses the first one it finds:

```
D:\secrets\daily-scheduler-secrets.json   ← checked first
C:\secrets\daily-scheduler-secrets.json   ← checked second
~\secrets\daily-scheduler-secrets.json    ← fallback (your home folder)
```

Create whichever folder makes sense for your machine (D:\secrets\ if you have
a D: drive, C:\secrets\ otherwise) and put the file there.

### File format

A template is included in the repo at `secrets/daily-scheduler-secrets.json.example`.
Copy it to your secrets location and fill in your values:

```json
{
  "voice_monkey_api_url": "https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE_GROUP",
  "cloudflare_worker_url": "https://scheduler-sync-worker.your-subdomain.workers.dev"
}
```

You only need to fill in the keys for the features you're actually using.
The app gracefully ignores blank or missing values — it just runs without
that feature enabled.

---

## Part 2 — Voice Monkey (Alexa Announcements)

Voice Monkey is a third-party service that lets you send text-to-speech
announcements to Alexa devices over the internet via a simple API call.

> **Honest heads-up:** The current TTS voice that Voice Monkey uses sounds
> a bit like a robotic doorbell operated by a confused monkey. It works, it
> chimes and announces the phase, but don't expect it to sound natural. The
> Local Chime option (no setup required) is arguably more pleasant if you
> just want an audio cue.

### Step 1 — Create a Voice Monkey account

Go to: https://voicemonkey.io

Sign up for a free account. The free tier is sufficient.

### Step 2 — Set up a Monkey (device group)

In the Voice Monkey dashboard:
1. Click **Monkeys** → **Add Monkey**
2. Give it a name (e.g., "everything" to hit all your Alexas)
3. Follow the in-app steps to link it to your Alexa account via the Alexa app

The "device" name you set here is what goes in the API URL.

### Step 3 — Get your API token

In the Voice Monkey dashboard:
1. Go to **Account** or **API**
2. Copy your API token (long alphanumeric string)

### Step 4 — Build your API URL

The URL format is:
```
https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE_NAME
```

Replace `YOUR_TOKEN` with your token and `YOUR_DEVICE_NAME` with the monkey
name you created in Step 2.

### Step 5 — Add it to your secrets file

```json
{
  "voice_monkey_api_url": "https://api-v2.voicemonkey.io/announcement?token=abc123...&device=everything"
}
```

### Step 6 — Switch the app to Voice Monkey mode

In the app, use the radio buttons in the top-left of the timer bar:
- **Local Chime** = plays a Windows system beep then speaks the announcement aloud via Windows built-in TTS (default, no setup needed, Windows only)
- **Voice Monkey** = sends announcements to your Alexa devices

Your selection is saved automatically.

### What gets announced

- Start of Planning phase
- 5 minutes remaining (in any work block or break)
- 2 minutes remaining (in any work block or break)
- End of each block / start of the next phase
- End of day after Block 8

---

## Part 3 — Cloudflare R2 Cloud Sync (Home dataset only)

This syncs your Home task data to a Cloudflare R2 bucket so multiple machines
share the same tasks. The Work dataset is always local-only regardless of this
setting.

Cloudflare's free tier covers this completely — typical usage is a few
kilobytes of JSON per day, nowhere near any limits.

**Free tier limits for reference:**
- R2: 10 GB storage, 10M uploads/month, 10M downloads/month
- Workers: 100,000 requests/day

### Step 1 — Create a Cloudflare account

Go to: https://cloudflare.com and sign up (free).

### Step 2 — Install Node.js and Wrangler

You need Node.js to deploy the Worker. Get it at https://nodejs.org if you
don't have it.

Then install Wrangler (Cloudflare's CLI tool):
```
npm install -g wrangler
```

Verify:
```
wrangler --version
```

### Step 3 — Log in to Cloudflare via Wrangler

```
wrangler login
```

This opens a browser window to authorize Wrangler with your account.

### Step 4 — Create the R2 bucket

```
wrangler r2 bucket create scheduler-data
```

Verify it exists:
```
wrangler r2 bucket list
```

You should see `scheduler-data` in the list.

### Step 5 — Deploy the Cloudflare Worker

The Worker code is already written and included in the repo under
`scheduler-sync-worker/`. Just deploy it:

```
cd scheduler-sync-worker
npm install
npx wrangler deploy
```

After deployment you'll see output like:
```
Published scheduler-sync-worker (X.XX sec)
  https://scheduler-sync-worker.YOUR-SUBDOMAIN.workers.dev
```

**Copy that URL** — you need it for the next step.

You can test the Worker is live by visiting that URL in a browser. You should
see a JSON response describing the API endpoints.

### Step 6 — Add the Worker URL to your secrets file

```json
{
  "cloudflare_worker_url": "https://scheduler-sync-worker.YOUR-SUBDOMAIN.workers.dev"
}
```

### Step 7 — Enable sync in config.json

Open `data/config.json` and make sure this section is present:

```json
{
  "cloudflare_sync": {
    "enabled": true,
    "auto_sync_on_startup": true
  }
}
```

`auto_sync_on_startup: true` means the app pulls the latest cloud data every
time it launches. Set it to `false` if you prefer to sync manually only.

### Step 8 — Test it

1. Launch the app
2. Click **☁ Sync Now** in the bottom toolbar
3. Watch the console — you should see:
   ```
   [Sync] ═══ Starting full sync ═══
   [Sync] ✓ Uploaded tasks.json
   [Sync] ✓ Uploaded timer_state.json
   ...
   [Sync] ═══ Sync complete ✓ ═══
   ```
4. Confirm in the Cloudflare dashboard: Dashboard → R2 → scheduler-data bucket
   → your JSON files should be listed there

### Setting up a second machine

On each additional machine:
1. Install Python + `pip install requests`
2. Create the secrets file at `D:\secrets\` or `C:\secrets\` with the same
   Worker URL (and Voice Monkey URL if you want announcements there too)
3. Run the app — it will pull your tasks automatically on startup

### How sync works

- **On startup**: app downloads latest data from R2 (if auto_sync_on_startup is true)
- **Sync Now button**: uploads all local files to R2, then downloads from R2
- **Task conflict resolution**: if the same task exists on both machines and
  one of them has it marked completed, completed wins — it won't un-complete
- **Work dataset**: never synced, always local-only

### Disabling sync temporarily

Set `"enabled": false` in the `cloudflare_sync` section of `data/config.json`.
The Sync Now button will disappear from the UI.

### Security note

The Worker URL is unauthenticated — anyone who knows the URL can read or write
your task data. For personal use between your own machines this is fine. If you
ever share the Worker URL or make it public, consider adding an API key to the
Worker (not covered here).

---

## Troubleshooting

**App starts but announcements don't work**
- Check the console output on launch — it prints which secrets file it loaded,
  or says "No secrets file found" if it couldn't find one
- Confirm the file path is exactly right (filename, folder, drive letter)
- Make sure the JSON in the secrets file is valid (no trailing commas, etc.)
- In the app, confirm the radio button is set to Voice Monkey, not Local Chime

**Sync Now button is greyed out**
- The Worker URL is missing or blank in the secrets file
- Restart the app after editing the secrets file — it only reads on launch

**Sync fails with an error**
- Visit your Worker URL in a browser — if it doesn't respond, the Worker isn't
  deployed or has an error
- Re-run `npx wrangler deploy` from the `scheduler-sync-worker/` folder
- Check you're logged in: `wrangler whoami`

**"file not in cloud (skipping)" messages on first sync**
- This is normal. The first sync uploads everything. Subsequent syncs will find
  the files. Not an error.

**Worker deploy fails with auth errors**
```
wrangler logout
wrangler login
```

**Worker deploy fails with binding errors**
Check `scheduler-sync-worker/wrangler.toml` — it should contain:
```toml
[[r2_buckets]]
binding = "SCHEDULER_DATA"
bucket_name = "scheduler-data"
```

---

## Quick Reference

| Feature | Requires | Where to configure |
|---|---|---|
| Local Chime | Nothing | Radio button in timer bar |
| Voice Monkey | voicemonkey.io account + Alexa | Secrets file |
| Cloud Sync | Cloudflare account + Node.js | Secrets file + data/config.json |

**Secrets file locations checked (in order):**
1. `D:\secrets\daily-scheduler-secrets.json`
2. `C:\secrets\daily-scheduler-secrets.json`
3. `~\secrets\daily-scheduler-secrets.json`
