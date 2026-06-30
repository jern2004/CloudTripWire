"""
deploy_azure.py
───────────────
Sets up the CloudTripwire Azure honeytoken detection stack.

What it creates:
  1. Resource Group        — container for all CloudTripwire resources
  2. Storage Account       — holds the canary blob files
  3. Blob container        — 'honeytokens' container with tempting fake files
  4. Log Analytics Workspace — where storage access logs are sent
  5. App Registration      — the honeytoken credential (zero permissions)
  6. Diagnostic Settings   — routes storage logs to Log Analytics

Usage:
    python azure/deploy_azure.py
"""

import subprocess
import json
import sys
import os
import time
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

SUBSCRIPTION_ID  = "74e54a67-30b7-4f94-83da-1d5925e36484"
RESOURCE_GROUP   = "cloudtripwire-rg"
LOCATION         = "australiaeast"
STORAGE_ACCOUNT  = "cloudtripwirecanary"   # must be globally unique, lowercase, 3-24 chars
CONTAINER_NAME   = "honeytokens"
WORKSPACE_NAME   = "cloudtripwire-logs"
APP_NAME         = "cloudtripwire-honeytoken"

CONFIG_PATH = Path(__file__).parent.parent / "azure" / "config.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd, capture=True, check=True):
    """Run an az CLI command and return parsed JSON output."""
    # Inject --subscription into az commands that support it
    if isinstance(cmd, list) and cmd[0] == "az" and "--subscription" not in cmd:
        # Only add for resource-level commands, not ad/account commands
        skip_cmds = {"ad", "account", "login"}
        if len(cmd) > 1 and cmd[1] not in skip_cmds:
            cmd = cmd + ["--subscription", SUBSCRIPTION_ID]
    print(f"  → {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=capture, text=True
    )
    if check and result.returncode != 0:
        print(f"\n❌ Command failed:\n{result.stderr}")
        sys.exit(1)
    if capture and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()
    return None


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  CloudTripwire — Azure Honeytoken Setup")
    print("=" * 60)

    # ── 1. Resource Group ──────────────────────────────────────────────────────
    section("1. Resource Group")
    run(["az", "group", "create",
         "--name", RESOURCE_GROUP,
         "--location", LOCATION])
    print(f"✅ Resource group '{RESOURCE_GROUP}' ready")

    # ── 2. Storage Account ─────────────────────────────────────────────────────
    section("2. Storage Account (canary)")
    storage = run(["az", "storage", "account", "create",
                   "--name", STORAGE_ACCOUNT,
                   "--resource-group", RESOURCE_GROUP,
                   "--location", LOCATION,
                   "--sku", "Standard_LRS",
                   "--kind", "StorageV2",
                   "--allow-blob-public-access", "false"])
    storage_id = storage["id"]
    print(f"✅ Storage account '{STORAGE_ACCOUNT}' created")

    # Get connection string for uploading blobs
    conn = run(["az", "storage", "account", "show-connection-string",
                "--name", STORAGE_ACCOUNT,
                "--resource-group", RESOURCE_GROUP,
                "--query", "connectionString",
                "--output", "tsv"])

    # ── 3. Blob container + canary files ───────────────────────────────────────
    section("3. Blob container + canary files")
    run(["az", "storage", "container", "create",
         "--name", CONTAINER_NAME,
         "--connection-string", conn])
    print(f"✅ Container '{CONTAINER_NAME}' created")

    # Upload tempting fake files
    canary_files = {
        "aws-backup-creds.txt": "AWS_ACCESS_KEY_ID=FAKEKEYDONOTUSE\nAWS_SECRET_ACCESS_KEY=FAKESECRETDONOTUSE",
        "employee-salaries-2025.csv": "name,salary\nJohn Doe,95000\nJane Smith,102000",
        "db-dump-prod.sql": "-- Production database backup\n-- Date: 2025-10-01\n-- DO NOT SHARE",
    }

    import tempfile
    for filename, content in canary_files.items():
        with tempfile.NamedTemporaryFile(mode='w', suffix=filename, delete=False) as f:
            f.write(content)
            tmp_path = f.name
        run(["az", "storage", "blob", "upload",
             "--container-name", CONTAINER_NAME,
             "--name", filename,
             "--file", tmp_path,
             "--connection-string", conn,
             "--overwrite"])
        os.unlink(tmp_path)
        print(f"  ✅ Uploaded {filename}")

    # ── 4. Log Analytics Workspace ─────────────────────────────────────────────
    section("4. Log Analytics Workspace")
    workspace = run(["az", "monitor", "log-analytics", "workspace", "create",
                     "--resource-group", RESOURCE_GROUP,
                     "--workspace-name", WORKSPACE_NAME,
                     "--location", LOCATION,
                     "--retention-time", "30"])
    workspace_id    = workspace["id"]
    workspace_cid   = workspace["customerId"]
    print(f"✅ Log Analytics workspace '{WORKSPACE_NAME}' created")

    # ── 5. Diagnostic Settings — route storage logs to workspace ──────────────
    section("5. Diagnostic Settings (storage → Log Analytics)")

    # Diagnostic settings must be on the blob service sub-resource
    blob_resource_id = f"{storage_id}/blobServices/default"

    run(["az", "monitor", "diagnostic-settings", "create",
         "--name", "cloudtripwire-diag",
         "--resource", blob_resource_id,
         "--workspace", workspace_id,
         "--logs", '[{"category":"StorageRead","enabled":true},{"category":"StorageWrite","enabled":true}]',
         "--metrics", '[{"category":"Transaction","enabled":false}]'])
    print("✅ Diagnostic settings configured — blob reads will flow to Log Analytics")

    # ── 6. SAS token honeytoken credential ────────────────────────────────────
    section("6. SAS token (honeytoken credential)")

    # Generate a SAS token for the canary container — this IS the honeytoken.
    # An attacker who finds this token and uses it to access the blob will be
    # logged in Storage diagnostics and trigger our detection rule.
    from datetime import datetime, timedelta, timezone
    expiry = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%MZ")

    sas = run(["az", "storage", "container", "generate-sas",
               "--name", CONTAINER_NAME,
               "--account-name", STORAGE_ACCOUNT,
               "--permissions", "rl",
               "--expiry", expiry,
               "--output", "tsv",
               "--connection-string", conn])

    honeytoken_url = (
        f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/"
        f"{CONTAINER_NAME}/aws-backup-creds.txt?{sas}"
    )
    print(f"✅ SAS token generated (valid 1 year)")
    print(f"   Any use of this URL will be logged and trigger detection")

    # ── 7. Save config ─────────────────────────────────────────────────────────
    section("7. Saving config")
    config = {
        "azure": {
            "subscription_id": SUBSCRIPTION_ID,
            "resource_group":  RESOURCE_GROUP,
            "location":        LOCATION,
            "storage": {
                "account_name":     STORAGE_ACCOUNT,
                "container_name":   CONTAINER_NAME,
                "resource_id":      storage_id,
                "blob_resource_id": blob_resource_id,
                "connection_string": conn,
            },
            "log_analytics": {
                "workspace_name": WORKSPACE_NAME,
                "workspace_id":   workspace_id,
                "customer_id":    workspace_cid,
            },
            "honeytoken_sas": {
                "url":    honeytoken_url,
                "expiry": expiry,
                "note":   "Plant this URL in a fake .env file or config — any access triggers detection",
            }
        }
    }

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Config saved to {CONFIG_PATH}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅ Azure setup complete!")
    print("=" * 60)
    print(f"""
  Resource Group:    {RESOURCE_GROUP}
  Storage Account:   {STORAGE_ACCOUNT}
  Canary container:  {CONTAINER_NAME}  (3 tempting files uploaded)
  Log Analytics:     {WORKSPACE_NAME}
  Honeytoken SAS URL saved to azure/config.json

  Next step:
    python azure/deploy_sentinel.py
    (sets up the Sentinel detection rule and Logic App response)
""")


if __name__ == "__main__":
    main()
