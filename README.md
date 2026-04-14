# CloudTripwire — Multi-Cloud Honeytokens & Auto-Incident Response

Plant decoy credentials, objects, and links across **AWS & Azure**.  
When anything touches them, **auto-revoke access**, capture a **forensic evidence bundle**, and publish a full **incident timeline** to a dashboard.

> **Status:** Full AWS pipeline live — honeytoken planted, CloudTrail detecting, Lambda auto-responding in under 30 seconds. Azure side in progress.

---

## Why

A decoy IAM key or S3 object should *never* be accessed legitimately.  
Any touch is a guaranteed true-positive — no tuning, no baseline noise.  
CloudTripwire turns that signal into automated containment and a reproducible IR artifact, end-to-end in under 90 seconds.

---

## What's built

| Layer | Stack | Status |
|---|---|---|
| Incident API | FastAPI · SQLite · Pydantic | ✅ Live |
| Dashboard UI | React · Vite · TailwindCSS · Recharts | ✅ Live |
| AWS canaries | IAM honeytoken · S3 canary bucket · CloudTrail | ✅ Live |
| AWS detection | EventBridge rules · CloudTrail event patterns | ✅ Live |
| AWS auto-IR | Lambda · IAM key disable · severity engine · MITRE mapping | ✅ Live |
| IaC | Terraform (full AWS stack) | ✅ Live |
| Azure canaries + detection | Storage · Sentinel analytics | In progress |
| Azure auto-IR | Logic Apps · Microsoft Graph | In progress |
| Evidence bundler | CloudTrail ZIP per incident | In progress |

---

## Architecture

```
Decoy IAM key / S3 canary object (AWS)
        │
        ▼
   CloudTrail  (logs every API call, even failed ones)
        │
        ▼
   EventBridge  (pattern-matches on honeytoken username / bucket)
        │
        ▼
   Lambda — isolate_and_log.py
        │  • extracts identity, IP, user agent
        │  • determines severity (Critical / High / Medium)
        │  • maps to MITRE ATT&CK technique
        │  • disables IAM key via UpdateAccessKey
        │  • POSTs structured incident to dashboard
        ▼
   FastAPI  →  SQLite
        │
        ▼
   React Dashboard  (auto-refreshes every 15 s)
```

**Honeytoken types**

| Type | AWS | Azure |
|---|---|---|
| Object canary | S3 object with access logging | Blob Storage with diagnostic logs |
| Credential | IAM access key (no permissions) | App Registration secret |
| Beacon link | Pre-signed URL logged on fetch | SAS URL logged on fetch |

**Auto-IR actions**

| Provider | Trigger | Actions |
|---|---|---|
| AWS | EventBridge rule on CloudTrail `GetObject` / `AssumeRole` | Disable IAM key · isolate Security Group · EBS snapshot · capture CloudTrail window |
| Azure | Sentinel analytic rule on Storage / sign-in logs | Disable Service Principal · revoke refresh tokens · collect Storage access logs |

---

## Repo structure

```
cloudtripwire/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── core/               # Config, utilities, ID generation
│   │   ├── routers/            # incidents, metrics, evidence, health
│   │   ├── models.py           # SQLAlchemy ORM
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── database.py         # SQLite engine + session
│   │   └── main.py             # App factory, CORS, router registration
│   ├── seed.data.py            # Seed sample incidents for demo
│   └── requirements.txt
│
├── frontend/                   # React dashboard
│   ├── src/
│   │   ├── api/                # Axios client + mock data
│   │   ├── components/         # MetricCard, Charts, IncidentTable, IncidentDetail, Layout
│   │   ├── pages/              # Dashboard, IncidentsPage, IncidentDetailPage
│   │   ├── styles/             # TailwindCSS + global.css
│   │   └── utils/              # formatters (timestamp, status colors, truncation)
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── honeytokens/                # Honeytoken deployment + testing
│   ├── deploy_honeytokens.py   # Creates IAM user, S3 canary, CloudTrail, EventBridge
│   ├── test_trigger.py         # Simulates attacker using decoy credentials
│   └── config.json             # AWS account config (no secrets)
│
├── response/
│   └── aws_lambda/
│       ├── isolate_and_log.py  # Lambda handler — disable key, determine severity, POST incident
│       ├── deploy_lambda.py    # Packages and deploys the Lambda function
│       └── update_dashboard_url.py  # Updates Lambda env var when ngrok URL changes
│
├── terraform/                  # IaC — full AWS stack
│   ├── aws.tf                  # IAM user, S3 canary, CloudTrail, EventBridge, Lambda, IAM roles
│   └── variables.tf
│
└── docs/
    ├── mitre-mapping.md        # Full ATT&CK coverage + severity decision tree
    └── demo-guide.md           # Pre-demo checklist + 60-second script + interview Q&A
```

---

## Quick start — dashboard only

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# API: http://127.0.0.1:8000
# Swagger docs: http://127.0.0.1:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:5173
```

The UI ships with a **Mock Data** toggle — it works fully without the backend or any cloud infra.  
Flip to **Live API** once the backend is running.

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/metrics` | Incident counts (total, active, AWS, Azure) |
| `GET` | `/api/incidents` | List incidents (`?limit=&status=&cloud=`) |
| `GET` | `/api/incident/{id}` | Single incident detail |
| `PATCH` | `/api/incident/{id}` | Update status (e.g. mark resolved) |
| `POST` | `/api/incidents` | Ingest new incident (called by playbooks) |
| `GET` | `/api/incidents/timeseries` | Daily counts for charts (`?days=7`) |
| `GET` | `/api/evidence/{id}` | Evidence bundle links for an incident |
| `GET` | `/health` | Health check |

---

## Incident data model

```json
{
  "id": "inc-001",
  "cloud": "AWS",
  "principal": "arn:aws:iam::123456789012:user/honeypot-user",
  "trigger_type": "S3 Access",
  "timestamp": "2025-10-27T14:23:45Z",
  "status": "Active",
  "severity": "High",
  "region": "us-east-1",
  "ip_address": "203.45.67.89",
  "resource_arn": "arn:aws:s3:::honeypot-bucket/sensitive.zip",
  "user_agent": "aws-cli/2.13.5 Python/3.11.4",
  "response_actions": [
    { "action": "Credential Revoked", "timestamp": "...", "status": "Success" },
    { "action": "Security Team Notified", "timestamp": "...", "status": "Success" }
  ],
  "timeline": [
    { "event": "Honeytoken Triggered", "timestamp": "..." },
    { "event": "Automated Response Initiated", "timestamp": "..." },
    { "event": "Evidence Saved", "timestamp": "..." }
  ],
  "evidence": {
    "cloudtrail_log": "s3://evidence/inc-001-cloudtrail.json",
    "vpc_flow_logs": "s3://evidence/inc-001-vpc-flow.log",
    "iam_snapshot": "s3://evidence/inc-001-iam-snapshot.json"
  },
  "threat_indicators": {
    "is_vpn": false,
    "is_tor": false,
    "is_known_attacker": true,
    "geo_location": "Singapore"
  }
}
```

---

## MITRE ATT&CK coverage

| Technique | ID | Honeytoken trigger |
|---|---|---|
| Unsecured Credentials | T1552.001 | Decoy IAM key / App secret used |
| Exfiltration to Cloud Storage | T1567.002 | Decoy S3 / Blob object accessed |
| Cloud Service Discovery | T1526 | ListBuckets · GetBlobServiceProperties |
| Valid Accounts: Cloud Accounts | T1078.004 | Honeytoken principal authenticated |
| Data from Cloud Storage | T1530 | GetObject on canary file |

---

## Safety

- All honeytokens deployed in **isolated AWS test accounts and Azure trial tenants** — no production access.
- Decoy IAM keys carry **zero IAM permissions** (they trigger on authentication, not authorisation).
- All secrets are **immediately revokable** and rotated after each demo run.
- Terraform state is stored locally; no credentials are committed.

---

## Roadmap

- [x] FastAPI incident API (CRUD, metrics, evidence, health)
- [x] React dashboard (metric cards, line/bar charts, incident table, detail page, all-incidents page)
- [x] AWS honeytoken IAM user + S3 canary bucket with tempting files
- [x] CloudTrail multi-region trail with S3 data events
- [x] EventBridge detection rules (IAM key use + S3 canary access)
- [x] Lambda auto-IR: disable key, severity engine, MITRE mapping, POST to dashboard
- [x] Terraform IaC for full AWS stack (reproducible with `terraform apply`)
- [x] Attacker simulation script (`honeytokens/test_trigger.py`)
- [x] MITRE ATT&CK tagging on every ingest
- [ ] Azure Blob canary + Sentinel analytic rule
- [ ] Logic App IR playbook (disable SP → revoke sessions → collect logs)
- [ ] Evidence bundler (ZIP per incident with CloudTrail window + flow logs)
- [ ] Terraform Azure module

---

## Target metrics

| Metric | Target |
|---|---|
| Detection latency | < 60 s from honeytoken touch |
| Automated containment | < 90 s end-to-end |
| Evidence completeness | CloudTrail + flow logs + IAM snapshot per incident |
| False positive rate | 0 — any access to a decoy is definitionally malicious |
