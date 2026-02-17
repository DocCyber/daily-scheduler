# Cloudflare R2 Sync Setup Guide

This guide walks you through setting up cloud sync for the Daily Scheduler using Cloudflare R2 and Workers.

## Overview

The sync system consists of three components:
1. **R2 Bucket** - Stores your JSON data files in the cloud
2. **Cloudflare Worker** - Provides HTTP endpoints for upload/download
3. **Python Sync Client** - Integrates sync into the scheduler app

## Prerequisites

- Cloudflare account (free tier works fine)
- Node.js and npm installed (for deploying the Worker)
- Wrangler CLI (Cloudflare's command-line tool)

## Step 1: Install Wrangler

```bash
npm install -g wrangler
```

Verify installation:
```bash
wrangler --version
```

## Step 2: Login to Cloudflare

```bash
wrangler login
```

This will open a browser window to authorize Wrangler with your Cloudflare account.

## Step 3: R2 Bucket (Already Created)

The R2 bucket `scheduler-data` has already been created for you. You can verify it exists:

```bash
wrangler r2 bucket list
```

You should see `scheduler-data` in the list.

## Step 4: Deploy the Cloudflare Worker

Navigate to the worker directory and deploy:

```bash
cd scheduler-sync-worker
npm install
npx wrangler deploy
```

After deployment, you'll see output like:
```
Published scheduler-sync-worker (X.XX sec)
  https://scheduler-sync-worker.your-subdomain.workers.dev
```

**IMPORTANT**: Copy this URL - you'll need it for configuration!

## Step 5: Test the Worker

Test that the Worker is running:

```bash
curl https://scheduler-sync-worker.your-subdomain.workers.dev/
```

You should see JSON output with API documentation:
```json
{
  "service": "Daily Scheduler Sync API",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

## Step 6: Configure the Scheduler App

Credentials are stored in your **secrets file** (not in the project folder).

Edit `D:\secrets\daily-scheduler-secrets.json` (create it if it doesn't exist - copy from `secrets/daily-scheduler-secrets.json.example`):

```json
{
  "voice_monkey_api_url": "https://api-v2.voicemonkey.io/announcement?token=YOUR_TOKEN&device=YOUR_DEVICE",
  "cloudflare_worker_url": "https://scheduler-sync-worker.your-subdomain.workers.dev"
}
```

Replace `your-subdomain.workers.dev` with your actual Worker URL from Step 4.

Then enable sync in `data/config.json`:

```json
{
  "cloudflare_sync": {
    "enabled": true,
    "auto_sync_on_startup": true
  }
}
```

Note: The Worker URL goes in the **secrets file**, not config.json.

## Step 7: Test the Sync

1. Run the scheduler app:
   ```bash
   python main.py
   ```

2. Add some tasks to your scheduler

3. Click the **"☁ Sync Now"** button in the bottom toolbar

4. Check the console output - you should see:
   ```
   [Sync] ═══ Starting full sync ═══
   [Sync] Starting upload...
   [Sync] ✓ Uploaded tasks.json
   [Sync] ✓ Uploaded timer_state.json
   ...
   [Sync] ═══ Sync complete ✓ ═══
   ```

5. Verify files in R2 bucket (via Cloudflare dashboard):
   - Go to Cloudflare Dashboard → R2
   - Click on `scheduler-data` bucket
   - You should see your JSON files listed

## Step 8: Test Cross-Machine Sync

To test syncing between machines:

1. **On Machine A**:
   - Add some tasks
   - Click "Sync Now"
   - Verify success message

2. **On Machine B**:
   - Make sure `config.json` has the same Worker URL
   - Set `enabled: true` in cloudflare_sync section
   - Start the app
   - Tasks from Machine A should automatically download on startup!

3. **Alternative**: Manually trigger download:
   - Click "Sync Now" on Machine B
   - Tasks will be downloaded

## How Sync Works

### Automatic Sync (Startup)
- When you start the app with `auto_sync_on_startup: true`
- The app automatically downloads latest data from cloud
- Your local files are updated with cloud versions

### Manual Sync ("Sync Now" Button)
1. **Upload Phase**: Pushes all local JSON files to R2 bucket
2. **Download Phase**: Pulls all JSON files from R2 bucket
3. **Conflict Resolution**: Cloud version overwrites local (last-write-wins)

### Files Synced
- `config.json` - Settings and configuration
- `tasks.json` - Current tasks and queue
- `timer_state.json` - Timer position
- `completed_log.json` - History of completed tasks
- `incomplete_history.json` - History of queued tasks
- `daily_stats.json` - Daily completion statistics

## Troubleshooting

### "Sync Failed" Error
- **Check internet connection**: Sync requires active internet
- **Verify Worker URL**: Make sure the URL in config.json is correct
- **Check Worker status**: Visit the Worker URL in your browser - should see JSON response
- **Console logs**: Look for detailed error messages in the terminal

### Worker Deploy Fails
```bash
# If you see authentication errors:
wrangler logout
wrangler login

# If you see binding errors, verify wrangler.toml:
cat scheduler-sync-worker/wrangler.toml
# Should have:
# [[r2_buckets]]
# binding = "SCHEDULER_DATA"
# bucket_name = "scheduler-data"
```

### Files Not Syncing
1. Check that sync is enabled in `config.json`
2. Verify Worker deployment: `wrangler deployments list`
3. Test Worker endpoint manually:
   ```bash
   curl https://your-worker-url.workers.dev/list
   ```
4. Check R2 bucket contents in Cloudflare Dashboard

### "Download Failed" Messages
- Usually means the file doesn't exist in cloud yet
- This is normal for first sync - files will be created on first upload
- Check console for "⊘ filename not in cloud (skipping)" - this is OK

## Advanced Configuration

### Disable Auto-Sync on Startup
In `config.json`:
```json
{
  "cloudflare_sync": {
    "auto_sync_on_startup": false
  }
}
```

Now you must manually click "Sync Now" to sync.

### Temporarily Disable Sync
In `config.json`:
```json
{
  "cloudflare_sync": {
    "enabled": false
  }
}
```

The "Sync Now" button will disappear from the UI.

## Cost

Cloudflare R2 Free Tier:
- **10 GB storage** (way more than needed - typical usage is ~5-10 KB)
- **10 million Class A operations/month** (uploads)
- **10 million Class B operations/month** (downloads)
- **No egress fees** (unlike AWS S3!)

Workers Free Tier:
- **100,000 requests/day**
- **10ms CPU time per request**

**Bottom Line**: This sync solution is **completely free** for typical usage!

## Security Notes

1. **Worker URL is public** - anyone with the URL can access your data
2. **Future enhancement**: Add authentication/API keys to Worker
3. **Files are not encrypted** - don't store sensitive information
4. **CORS enabled** - Worker accepts requests from any origin

For production use, consider:
- Adding authentication to the Worker
- Using environment variables for API keys
- Encrypting sensitive data before upload

## Support

If you encounter issues:
1. Check console output for detailed error messages
2. Verify Worker is responding: visit URL in browser
3. Check R2 bucket in Cloudflare Dashboard
4. Review Wrangler deployment logs: `wrangler tail scheduler-sync-worker`

## Next Steps

Once sync is working:
- Configure it on all your machines
- Use "Sync Now" before switching machines
- Enjoy seamless task continuity across devices!

---

**Pro Tip**: Always sync before ending your work session to ensure your tasks are backed up to the cloud!
