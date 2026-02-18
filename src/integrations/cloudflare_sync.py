"""Cloudflare R2 sync client for syncing data across machines."""
import json
import requests
from pathlib import Path
from typing import Dict


class CloudflareSync:
    """Client for syncing JSON files to/from Cloudflare R2 via Worker."""

    def __init__(self, worker_url: str, data_dir: Path, enabled: bool = True):
        """
        Initialize Cloudflare sync client.

        Args:
            worker_url: URL of deployed Cloudflare Worker (from config)
            data_dir: Path to local data directory
            enabled: Whether syncing is enabled
        """
        self.worker_url = worker_url.rstrip('/')
        self.data_dir = data_dir
        self.enabled = enabled

        # Files to sync (order matters for dependencies)
        self.sync_files = [
            "config.json",
            "tasks.json",
            "timer_state.json",
            "completed_log.json",
            "incomplete_history.json",
            "daily_stats.json"
        ]

    def upload_file(self, filename: str) -> bool:
        """Upload single file to R2."""
        if not self.enabled:
            return True

        file_path = self.data_dir / filename
        if not file_path.exists():
            print(f"[Sync] Skipping {filename} (doesn't exist locally)")
            return True

        try:
            content = file_path.read_text()
            response = requests.post(
                f"{self.worker_url}/upload",
                json={"filename": filename, "content": content},
                timeout=10
            )

            if response.status_code == 200:
                print(f"[Sync] ✓ Uploaded {filename}")
                return True
            else:
                print(f"[Sync] ✗ Upload failed for {filename}: {response.status_code}")
                return False

        except Exception as e:
            print(f"[Sync] Error uploading {filename}: {e}")
            return False

    def download_file(self, filename: str) -> bool:
        """Download single file from R2."""
        if not self.enabled:
            return True

        try:
            response = requests.get(
                f"{self.worker_url}/download/{filename}",
                timeout=10
            )

            if response.status_code == 200:
                file_path = self.data_dir / filename

                if filename == "tasks.json":
                    # Completed-state-wins merge: preserve local completions
                    local_json = file_path.read_text() if file_path.exists() else None
                    cloud_json = response.text
                    if local_json:
                        try:
                            merged = self._merge_tasks(local_json, cloud_json)
                            file_path.write_text(merged)
                            print(f"[Sync] ✓ Downloaded {filename} (with completion merge)")
                        except Exception as merge_err:
                            # If merge fails, fall back to plain overwrite
                            print(f"[Sync] Merge failed ({merge_err}), using cloud version")
                            file_path.write_text(cloud_json)
                    else:
                        file_path.write_text(cloud_json)
                        print(f"[Sync] ✓ Downloaded {filename}")
                else:
                    file_path.write_text(response.text)
                    print(f"[Sync] ✓ Downloaded {filename}")

                return True
            elif response.status_code == 404:
                print(f"[Sync] ⊘ {filename} not in cloud (skipping)")
                return True
            else:
                print(f"[Sync] ✗ Download failed for {filename}: {response.status_code}")
                return False

        except Exception as e:
            print(f"[Sync] Error downloading {filename}: {e}")
            return False

    def _merge_tasks(self, local_json: str, cloud_json: str) -> str:
        """Merge local and cloud tasks.json with completed-state-wins logic.

        Cloud structure wins (task order, new tasks from cloud appear).
        But if a task exists in both local and cloud (matched by text),
        completed=True if EITHER version has it done.
        """
        local = json.loads(local_json)
        cloud = json.loads(cloud_json)

        # Merge planning tasks
        cloud["planning"]["tasks"] = self._merge_task_list(
            local.get("planning", {}).get("tasks", []),
            cloud["planning"]["tasks"]
        )

        # Merge each block's tasks
        local_blocks = local.get("blocks", [])
        for i, block in enumerate(cloud.get("blocks", [])):
            local_block_tasks = local_blocks[i].get("tasks", []) if i < len(local_blocks) else []
            block["tasks"] = self._merge_task_list(local_block_tasks, block["tasks"])

        # Merge queue
        cloud["queue"] = self._merge_task_list(
            local.get("queue", []),
            cloud.get("queue", [])
        )

        return json.dumps(cloud, indent=2)

    def _merge_task_list(self, local_tasks: list, cloud_tasks: list) -> list:
        """Merge two task lists: cloud is the base, local completed state wins.

        Tasks are matched by text. If a task is marked completed on local
        but not on cloud, it stays completed in the merged result.
        Local-only tasks (not present in cloud) are appended so nothing is lost.
        """
        # Build lookup from local: text → task dict
        local_by_text = {t["text"]: t for t in local_tasks if t.get("text")}

        merged = []
        seen_texts = set()

        for task in cloud_tasks:
            text = task.get("text", "")
            seen_texts.add(text)
            if text in local_by_text:
                local_task = local_by_text[text]
                # completed-state-wins: once done, stays done
                if local_task.get("completed") and not task.get("completed"):
                    task = dict(task)  # don't mutate original
                    task["completed"] = True
                    task["completed_at"] = local_task.get("completed_at")
            merged.append(task)

        # Append any local tasks that don't exist in cloud (would otherwise be lost)
        for task in local_tasks:
            text = task.get("text", "")
            if text and text not in seen_texts:
                merged.append(task)
                print(f"[Sync] Preserved local-only task: '{text[:40]}'")

        return merged

    def upload_all(self) -> Dict[str, int]:
        """Upload all data files to R2."""
        print("[Sync] Starting upload...")
        results = {"success": 0, "failed": 0, "skipped": 0}

        for filename in self.sync_files:
            if self.upload_file(filename):
                results["success"] += 1
            else:
                results["failed"] += 1

        print(f"[Sync] Upload complete: {results['success']} succeeded, {results['failed']} failed")
        return results

    def download_all(self) -> Dict[str, int]:
        """Download all data files from R2."""
        if not self.worker_url:
            print("[Sync] No worker URL configured - skipping download")
            return {"success": 0, "failed": 0, "skipped": len(self.sync_files)}

        print("[Sync] Starting download...")
        results = {"success": 0, "failed": 0, "skipped": 0}

        for filename in self.sync_files:
            if self.download_file(filename):
                results["success"] += 1
            else:
                results["failed"] += 1

        print(f"[Sync] Download complete: {results['success']} succeeded, {results['failed']} failed")
        return results

    def sync(self) -> bool:
        """
        Full sync: upload local changes, then download cloud updates.
        Returns True if successful.
        """
        if not self.enabled:
            print("[Sync] Syncing is disabled")
            return True

        if not self.worker_url:
            print("[Sync] No worker URL configured - add cloudflare_worker_url to your secrets file")
            return False

        print("[Sync] ═══ Starting full sync ═══")

        # Upload first (push local changes)
        upload_results = self.upload_all()

        # Then download (pull cloud updates)
        download_results = self.download_all()

        success = (upload_results["failed"] == 0 and download_results["failed"] == 0)

        if success:
            print("[Sync] ═══ Sync complete ✓ ═══")
        else:
            print("[Sync] ═══ Sync completed with errors ✗ ═══")

        return success

    def test_connection(self) -> bool:
        """Test connection to Worker."""
        try:
            response = requests.get(f"{self.worker_url}/list", timeout=5)
            return response.status_code == 200
        except:
            return False
