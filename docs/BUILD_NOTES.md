# CloudTripwire — Build Notes

*Personal reference for picking this project back up. Assumes general CS/software engineering background (APIs, databases, cloud computing as a concept) but not familiarity with AWS/Azure's specific products or this codebase's internals.*

---

## 1. What this project is

It's an intrusion-detection system built around **honeytokens**: fake credentials and fake files planted specifically as bait, with no legitimate use. Because nothing real should ever reference them, any access is unambiguous evidence of an attacker — there's no false-positive problem to tune away, unlike anomaly/ML-based detection (e.g. AWS GuardDuty).

The system closes the loop automatically:

```
bait touched → cloud provider logs the event → a rule matches the log entry
→ a serverless function runs → disables the compromised credential
→ POSTs a structured incident to a REST API → shows up on a live dashboard
```

This is implemented **twice, independently** — once using AWS-native services, once using Azure-native services — and both implementations report into the same backend/dashboard via a shared JSON schema. That shared contract is what makes "multi-cloud" a real claim rather than two disconnected demos.

---

## 2. Architecture

| Layer | AWS implementation | Azure implementation |
|---|---|---|
| Bait | IAM user with zero permissions + an S3 bucket with decoy files | A SAS token (time-limited access credential) + a Blob Storage container with decoy files |
| Logging | CloudTrail (logs every API call, including denied ones) | Storage diagnostic logs → Log Analytics workspace |
| Detection rule | EventBridge (pattern-matches on CloudTrail events) | Microsoft Sentinel analytic rule, written in KQL (Kusto Query Language), polls every 5 min |
| Response | AWS Lambda function | Azure Logic App (a low-code workflow/automation service) |

Both response layers do the same conceptual job: identify the actor, decide severity, disable the credential, and `POST` a JSON incident to the backend's `/api/incidents` endpoint. The AWS Lambda has real multi-signal severity logic (see §5); the Azure Logic App currently just hardcodes `severity: "High"` — a known asymmetry, not an oversight I've fixed yet.

The backend is a small **FastAPI + SQLAlchemy + SQLite** service. The frontend is **React + Vite**, polling the backend every 15s (no websockets — deliberate simplicity, not a limitation I hit).

---

## 3. Repo layout

```
backend/            FastAPI service — the dashboard's data layer and REST API
frontend/            React/Vite dashboard
honeytokens/         AWS bait provisioning (boto3) + an attack-simulation script
response/aws_lambda/ The Lambda handler (detection→response logic) + its deploy scripts
azure/                Azure bait provisioning + Sentinel/Logic App setup + attack simulator
terraform/            IaC version of the AWS side only (no Azure module yet)
docs/                 This file, plus a recruiter-facing overview, demo scripts, and a MITRE ATT&CK writeup
```

**Backend internals worth remembering:**
- One SQLAlchemy model, `Incident`. Structured fields (cloud, principal, severity, etc.) are plain columns; `response_actions`, `timeline`, `threat_indicators`, `evidence` are JSON columns rather than normalized tables — a deliberate simplicity tradeoff for an event-log-shaped record that's always read/written as a whole.
- Pydantic schemas validate the API boundary (`IncidentCreate`, `IncidentUpdate`).
- `POST /api/incidents` and `PATCH /api/incident/{id}` optionally require an `X-API-Key` header (see §7) — everything else is read-only and unauthenticated.
- `get_timeseries()` buckets incidents by day using string-slicing on the ISO timestamp (`ts[:10]`) instead of a SQL `GROUP BY` with `strftime` — done deliberately to sidestep SQLite date-format quirks.

**Frontend internals worth remembering:**
- Three routes: dashboard, full incident list, incident detail.
- A Mock Data / Live API toggle exists on every page — mock data is hardcoded in `api/incidentAPI.js` and needs no backend at all.
- `baseURL` and the API key header are read from Vite env vars (`VITE_API_BASE_URL`, `VITE_API_KEY`) rather than hardcoded, so the frontend can point at a different backend without a code change.

---

## 4. How to run it

### Dashboard only, no cloud account needed

```powershell
# Terminal 1
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8080

# Terminal 2
cd frontend
npm run dev
```
Open `http://localhost:5173`. Toggle to Live API to hit the real backend (starts empty). To populate it without a real cloud trigger:
```powershell
cd backend
$env:API_BASE_URL="http://127.0.0.1:8080/api"
python seed.data.py
```

*(Port 8080, not the usual 8000 — Windows has 8000 reserved on this machine via Hyper-V/WSL's dynamic port exclusions. `frontend/.env`, `seed.data.py`, and the CSP in `index.html` are all already configured to handle a non-default port — see §6 if this ever needs re-diagnosing.)*

### Full AWS pipeline (provisions real, billable AWS resources)

Order matters — each step reads output from the previous one:

```powershell
python honeytokens\deploy_honeytokens.py          # decoy IAM user, S3 bucket, CloudTrail, EventBridge rules
python response\aws_lambda\deploy_lambda.py        # deploys the response Lambda, wires it to the EventBridge rules
ngrok http 8080                                     # exposes the local backend so AWS can reach it
python response\aws_lambda\update_dashboard_url.py https://xxxx.ngrok-free.dev
python honeytokens\test_trigger.py                  # simulates an attacker using the leaked credential
```
Alternative to the first two steps: `terraform apply` in `terraform/` provisions the same AWS resources declaratively. `terraform destroy` tears it down cleanly; there's no equivalent teardown for the manual script path.

### Full Azure pipeline (provisions real, billable Azure resources)

```powershell
python azure\deploy_azure.py       # Storage account + canary blob container + Log Analytics workspace + SAS token
python azure\deploy_sentinel.py    # enables Sentinel, creates the KQL analytic rule, deploys the Logic App
python azure\test_trigger.py       # simulates an attacker; also pokes the Logic App directly for an instant demo
```

---

## 5. Severity scoring (AWS side only)

Lives in `determine_severity()` in `response/aws_lambda/isolate_and_log.py`. Evaluated top-to-bottom, first match wins:

1. Source IP falls in a private range (`10.x`, `172.16–31.x`, `192.168.x`, `127.x`) → **Critical** — implies the attacker is already inside the network, not just using a leaked external credential
2. Event is `CreateUser` / `CreateAccessKey` / `AttachUserPolicy` / `AssumeRole` → **Critical** — persistence or privilege-escalation attempt
3. `ConsoleLogin` without MFA → **Critical** — credential stuffing / stolen password
4. `GetObject` / `GetSecretValue` / `Scan` / `Query` → **High** — active data exfiltration
5. `RunInstances` / `InvokeFunction` → **High** — compute/resource abuse (e.g. cryptomining)
6. Anything else → **Medium** — reconnaissance/enumeration

Each event is also mapped to a real **MITRE ATT&CK** technique ID (e.g. `T1530` for data exfiltration) via a lookup table — MITRE ATT&CK being the industry-standard taxonomy for attacker tactics/techniques, used so incidents speak a vocabulary other security tooling/analysts recognize.

---

## 6. Environment-specific gotchas (this machine)

- Port 8000 is inside a Windows-reserved range here (`netsh interface ipv4 show excludedportrange protocol=tcp` to check) — hence port 8080 throughout.
- `index.html` has a CSP (`Content-Security-Policy`) meta tag restricting which origins the frontend's JS is allowed to make network requests to (`connect-src`). It used to hardcode port 8000 explicitly, which silently blocked requests to any other port with no useful error beyond a generic "Network Error" — now set to `http://127.0.0.1:*`/`http://localhost:*` so this won't recur if the port changes again.
- `frontend/.env` created via PowerShell's `Set-Content -Encoding utf8` gets a UTF-8 BOM (byte-order mark) prepended — Windows PowerShell 5.1 has no built-in way to write BOM-less UTF-8 with that cmdlet. A BOM stuck onto the first env var name makes Vite fail to recognize it, silently falling back to defaults. If `.env` files ever seem to be "ignored," check for a BOM (`[System.IO.File]::ReadAllBytes(path)`, first 3 bytes `239,187,191` = BOM present) before assuming anything else is wrong.

---

## 7. Optional API key auth

`POST /api/incidents` and `PATCH /api/incident/{id}` support an `X-API-Key` header, checked against `INCIDENT_API_KEY`. Unset by default (fine for local dev); should be set before exposing the backend publicly via ngrok, since otherwise anyone with the URL can inject or tamper with incidents. If set, the same value needs to also be set in three other places, or the pipeline breaks silently:
- `frontend/.env` → `VITE_API_KEY`
- `honeytokens/config.json` → `dashboard.api_key` (read by the Lambda deploy scripts)
- a `DASHBOARD_API_KEY` env var before running `azure/deploy_sentinel.py`

---

## 8. Things to be careful about

- The real AWS account ID and Azure subscription ID are committed in plaintext (`honeytokens/config.json`, `terraform/variables.tf`, `azure/deploy_azure.py`). Not directly exploitable, but worth scrubbing before making the repo public.
- `honeytoken_keys.txt` and `azure/config.json` (the files holding actual live credentials) are correctly gitignored — don't change that.
- Running the AWS pipeline for real disables the honeytoken IAM key every time (that's the intended behavior) — it needs to be recreated before the next demo (`aws iam create-access-key`).
- ngrok's free tier issues a new URL every session — the most common reason the dashboard silently stops receiving incidents.

---

## 9. What's unfinished

- **Evidence bundling**: the API endpoint exists but just echoes back placeholder URLs; there's no code that actually packages a CloudTrail time-window into a downloadable forensic bundle.
- **Azure Terraform module**: doesn't exist; Azure provisioning is still imperative Python/CLI scripts only.
- **Azure severity scoring**: always hardcoded `High`, no multi-signal logic like the AWS side.
- **No AWS teardown for the manual (non-Terraform) path**: cleanup after a manual deploy means deleting resources by hand.
- **Never live-tested from this machine**: no AWS/Azure CLI or credentials are configured here, so while the code is written and reviewed, it hasn't been run end-to-end against a real account from this environment. Worth doing before fully trusting either pipeline.

---

## 10. Cheat sheet

```powershell
# Start everything
cd backend; uvicorn app.main:app --reload --port 8080
cd frontend; npm run dev
ngrok http 8080

# After ngrok issues a new URL
python response\aws_lambda\update_dashboard_url.py <new-ngrok-url>

# Re-arm the AWS honeytoken key after it's been auto-disabled
aws iam list-access-keys --user-name honeytoken-user
aws iam delete-access-key --user-name honeytoken-user --access-key-id <old-id>
aws iam create-access-key --user-name honeytoken-user

# Populate the dashboard without a real cloud trigger
cd backend; python seed.data.py

# Real triggers
python honeytokens\test_trigger.py     # AWS
python azure\test_trigger.py           # Azure
```

---

## 11. Related docs

- **`PROJECT_OVERVIEW.md`** — recruiter/newcomer-facing writeup, no assumed background at all
- **`HOW_TO_DEMO.md`** — a demo script, quick (mock/seeded data) and full (real trigger) versions
- **`demo-guide.md`** — deeper version with interview Q&A prep
- **`mitre-mapping.md`** — full MITRE ATT&CK technique-by-technique breakdown
