"""
test_trigger.py (Azure)
────────────────────────
Simulates an attacker who found the Azure honeytoken SAS URL and is
trying to access the canary blob container.

What it does:
  1. Reads the honeytoken SAS URL from azure/config.json
  2. Uses it to list blobs (like an attacker doing reconnaissance)
  3. Downloads the canary file (like an attacker exfiltrating data)

This access gets logged by Storage diagnostics → flows to Log Analytics
→ Sentinel analytic rule fires → Logic App POSTs incident to dashboard.

Note: Sentinel runs on a 5-minute schedule so the incident appears
      within 5 minutes of running this script.

Usage:
    python azure/test_trigger.py
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

if not CONFIG_PATH.exists():
    print("❌ azure/config.json not found — run deploy_azure.py first")
    exit(1)

with open(CONFIG_PATH) as f:
    config = json.load(f)

honeytoken = config["azure"]["honeytoken_sas"]
sas_url    = honeytoken["url"]

# The SAS URL points to a specific blob — extract the base + SAS token
# to also simulate listing the container
base_url   = sas_url.split("?")[0]
sas_token  = sas_url.split("?")[1]
account_url = base_url.rsplit("/", 2)[0]  # https://account.blob.core.windows.net
container   = config["azure"]["storage"]["container_name"]

print("=" * 60)
print("  CloudTripwire — Azure Honeytoken Trigger (Attacker Sim)")
print("=" * 60)
print()
print("Simulating: attacker found SAS URL in leaked .env file")
print()

# ── 1. List blobs (reconnaissance) ────────────────────────────────────────────
list_url = f"{account_url}/{container}?restype=container&comp=list&{sas_token}"
print(f"[1] Listing blobs in canary container...")
try:
    req = urllib.request.Request(list_url, headers={"User-Agent": "python-requests/2.31.0"})
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode()
        # Parse blob names from XML response
        import re
        names = re.findall(r"<Name>(.*?)</Name>", body)
        print(f"    ✅ Listed {len(names)} blobs: {names}")
except urllib.error.HTTPError as e:
    print(f"    ❌ {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"    ❌ {e}")

print()

# ── 2. Download canary file (exfiltration) ─────────────────────────────────────
print(f"[2] Downloading aws-backup-creds.txt...")
try:
    req = urllib.request.Request(sas_url, headers={"User-Agent": "python-requests/2.31.0"})
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        print(f"    ✅ Downloaded file content:")
        for line in content.strip().splitlines():
            print(f"       {line}")
except urllib.error.HTTPError as e:
    print(f"    ❌ {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"    ❌ {e}")

print()

# ── 3. Trigger Logic App directly (instant dashboard update) ──────────────────
logic_app_url = config["azure"]["logic_app"]["trigger_url"]

print(f"[3] Triggering Logic App response...")
import socket
source_ip = socket.gethostbyname(socket.gethostname())

payload = {
    "AlertDisplayName": "CloudTripwire - Canary Blob Accessed",
    "CallerIpAddress":  source_ip,
    "OperationName":    "GetBlob",
    "UserAgentHeader":  "python-requests/2.31.0",
    "TimeGenerated":    __import__("datetime").datetime.utcnow().isoformat() + "Z",
}

try:
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        logic_app_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"    ✅ Logic App triggered (HTTP {resp.status})")
        print(f"    ✅ Incident POSTed to dashboard")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"    ❌ Logic App error {e.code}: {body[:200]}")
except Exception as e:
    print(f"    ❌ {e}")

print()
print("=" * 60)
print("  ✅ Attacker simulation complete")
print("=" * 60)
print("""
  Check your dashboard at http://localhost:5173
  An Azure incident should have appeared now.

  (Storage logs also flow to Sentinel in the background —
   the Sentinel rule will fire within 5 minutes independently)
""")
