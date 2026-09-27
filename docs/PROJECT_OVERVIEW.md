# CloudTripwire — Project Documentation

*A plain-English walkthrough of what this project is, how it works, and why each piece exists — written for recruiters, hiring managers, and anyone new to cloud security.*

---

## Table of contents

1. [The 30-second pitch](#1-the-30-second-pitch)
2. [The core idea: what is a "honeytoken"?](#2-the-core-idea-what-is-a-honeytoken)
3. [Why this problem is worth solving](#3-why-this-problem-is-worth-solving)
4. [How it works, end to end](#4-how-it-works-end-to-end)
5. [Tech stack — what was used, and why](#5-tech-stack--what-was-used-and-why)
6. [Repo tour — what lives where](#6-repo-tour--what-lives-where)
7. [Deep dive: the AWS pipeline](#7-deep-dive-the-aws-pipeline)
8. [Deep dive: the Azure pipeline](#8-deep-dive-the-azure-pipeline)
9. [The dashboard (what a user actually sees)](#9-the-dashboard-what-a-user-actually-sees)
10. [The API and data model](#10-the-api-and-data-model)
11. [How incidents get their severity](#11-how-incidents-get-their-severity)
12. [MITRE ATT&CK — the industry vocabulary this project speaks](#12-mitre-attck--the-industry-vocabulary-this-project-speaks)
13. [Infrastructure as Code (Terraform)](#13-infrastructure-as-code-terraform)
14. [Project status — what's done, what's not](#14-project-status--whats-done-whats-not)
15. [Skills this project demonstrates](#15-skills-this-project-demonstrates)
16. [Try it yourself](#16-try-it-yourself)
17. [Glossary](#17-glossary)

---

## 1. The 30-second pitch

CloudTripwire is a **decoy-based intrusion detection system** for AWS and Azure. It plants fake credentials and fake files that look valuable but are completely worthless to anyone legitimate. If *anything* ever touches them, the system knows for certain it's an attacker — automatically disables the compromised access, classifies how serious the attack is, tags it against an industry-standard attack taxonomy (MITRE ATT&CK), and displays the whole incident on a live dashboard, all within about 30–90 seconds and with no human involved.

It is a working, end-to-end system — not a mockup. The AWS side makes real AWS API calls, the Azure side makes real Azure API calls, and the dashboard is a real web application backed by a real database.

---

## 2. The core idea: what is a "honeytoken"?

Imagine leaving a wallet full of fake cash on a park bench, wired with a tracker. Nobody who isn't up to something would ever pick it up — there's no legitimate reason to. The moment it moves, you know exactly what's happening.

A **honeytoken** is the cloud-security version of that wallet. It's a piece of bait — a credential, a file, a link — that:

- **Looks valuable.** File names like `db-dump-prod.sql` or `employee-salaries-2025.csv`, or a real (but powerless) set of AWS access keys.
- **Has zero legitimate purpose.** No application, script, or employee should ever read it, log in with it, or reference it.
- **Is wired to an alarm.** The moment anything touches it, an automated pipeline fires.

This project builds two categories of honeytoken on each cloud:

| Type | AWS implementation | Azure implementation |
|---|---|---|
| **Decoy credential** | An IAM user with an access key and **zero IAM permissions** | A SAS (Shared Access Signature) token, read-only |
| **Decoy object/file** | An S3 bucket containing three "tempting" files | A Blob storage container containing the same three files |

Because nothing legitimate should ever reference these, **any interaction is a guaranteed true positive.** That single fact is what makes honeytokens special compared to most security tooling — see the next section.

---

## 3. Why this problem is worth solving

Most intrusion detection (e.g., AWS GuardDuty, Azure Defender) works by **statistical anomaly detection**: it learns what "normal" looks like for your environment and flags deviations. This is powerful, but it has a well-known weakness — **false positives**. A security team gets flooded with alerts, has to tune thresholds, and can develop "alert fatigue" where real attacks get missed in the noise.

A honeytoken sidesteps that problem entirely:

> There is no such thing as a "legitimate" use of a resource that exists purely as bait. So there is nothing to tune, and no baseline to establish. **A trigger means an attacker is in your environment**, full stop.

This project also goes a step further than "just alert someone." It closes the loop with **automated response**:

1. **Detect** — an event fires the moment the bait is touched.
2. **Contain** — the compromised credential is disabled automatically, in seconds, without waiting for a human.
3. **Document** — a structured incident record is created automatically with the who/what/where/when, mapped to a recognized attack framework (MITRE ATT&CK), ready to hand to a responder or use as an audit trail.

This "detect → contain → document" loop, done automatically and end-to-end, is the entire point of the project.

---

## 4. How it works, end to end

Here is the full journey of a single attack, from the moment a credential is stolen to the moment it shows up on the dashboard.

```
AWS                                     Azure
───────────────────────────             ───────────────────────────
Decoy IAM key / S3 canary              SAS token / Blob canary
        │                                       │
        ▼                                       ▼
   CloudTrail                         Storage Diagnostic Logs
   (logs every API call)              (logs every blob access)
        │                                       │
        ▼                                       ▼
   EventBridge rule                    Log Analytics Workspace
   (pattern-matches on the                      │
    decoy identity/bucket)                      ▼
        │                            Sentinel Analytic Rule (KQL)
        ▼                            (runs every 5 min, checks for
   Lambda: isolate_and_log.py          reads on the canary blob)
        │  • disable the IAM key                │
        │  • score severity                     ▼
        │  • map to MITRE ATT&CK       Logic App (cloudtripwire-responder)
        │  • POST the incident                  │  • map to MITRE T1530
        ▼                                       │  • POST the incident
        └───────────────────┬───────────────────┘
                            ▼
                    FastAPI  →  SQLite
                     (REST API)   (database)
                            │
                            ▼
                    React Dashboard
                (auto-refreshes every 15s)
```

Walking through the AWS side in plain language:

1. **Bait is planted.** A script (or Terraform) creates a fake IAM user with an access key and no permissions, plus an S3 bucket holding three tempting-looking files.
2. **Someone uses the bait.** In a real breach, this would be an attacker who found leaked credentials in a `.env` file, a public GitHub repo, or a misconfigured server. In this project's demo, a script (`test_trigger.py`) simulates that attacker.
3. **AWS CloudTrail** — a built-in AWS service that logs every single API call made in the account — records the attempt. Crucially, it logs the call **even if AWS denies it** (the decoy user has no permissions, so every call fails, but the *attempt* is what matters).
4. **Amazon EventBridge**, a rules engine that watches the stream of CloudTrail events, has a rule pre-configured to match anything done using the decoy identity, or anything touching the decoy bucket. When it matches, it invokes a Lambda function.
5. **The Lambda function (`isolate_and_log.py`)** does the actual incident response:
   - Figures out who did it (extracts the identity from the CloudTrail event)
   - Decides how serious it is (see [severity scoring](#11-how-incidents-get-their-severity))
   - **Disables the IAM access key** so it can never be used again — this is the "auto-revoke" part
   - If the attacker looks like they're already inside the network (an internal IP), it can also quarantine an EC2 instance by stripping its network permissions
   - Tags the event with the matching MITRE ATT&CK technique
   - Sends (`POST`s) a structured JSON incident to the dashboard's API
6. **The FastAPI backend** receives that POST, saves it to a SQLite database, and makes it available via a REST API.
7. **The React dashboard**, polling the API every 15 seconds, shows the new incident: who, what, from where, what automated action was taken, and a full timeline.

The Azure side follows the identical *logic*, using Azure-native tools instead: Storage diagnostic logs instead of CloudTrail, a Microsoft Sentinel KQL analytic rule instead of an EventBridge pattern rule, and a Logic App instead of a Lambda function. Both pipelines report into the *same* dashboard, which is what makes this "multi-cloud."

---

## 5. Tech stack — what was used, and why

| Layer | Technology | Why this choice |
|---|---|---|
| **Incident API** | Python, **FastAPI**, **SQLAlchemy**, **Pydantic** | FastAPI auto-generates interactive API docs (`/docs`), has built-in request/response validation via Pydantic, and is fast to build REST APIs with. SQLAlchemy is the ORM layer over a lightweight **SQLite** database — no external DB server needed, ideal for a self-contained demo/portfolio project. |
| **Dashboard UI** | **React**, **Vite**, **TailwindCSS**, **Recharts** | React + Vite is a fast, modern front-end stack (Vite gives near-instant dev server reloads). TailwindCSS keeps styling co-located with markup. Recharts renders the incident trend charts declaratively. |
| **AWS detection** | **CloudTrail**, **EventBridge** | CloudTrail is the only AWS service that logs *every* API call, including denied ones — essential, since the decoy user's calls always fail permission checks but still need to be seen. EventBridge is AWS's native event-pattern-matching/routing service — no polling required. |
| **AWS response** | **AWS Lambda** (Python 3.11) | Serverless — no server to run or patch, scales to zero cost when idle, and integrates natively as an EventBridge target. |
| **AWS automation** | **boto3** (AWS SDK for Python) | Used both to *provision* the honeytokens (`deploy_honeytokens.py`) and *from inside* the Lambda to call IAM/EC2 APIs during response. |
| **Azure detection** | **Storage diagnostic logs**, **Log Analytics**, **Microsoft Sentinel (KQL)** | Sentinel is Microsoft's cloud-native SIEM; KQL (Kusto Query Language) is its query language for defining detection rules against log data — the direct Azure analogue of an EventBridge pattern rule. |
| **Azure response** | **Logic App** | Azure's serverless, visual workflow/automation engine — the Azure analogue of Lambda, triggered directly by the Sentinel rule. |
| **Azure automation** | **Azure CLI (`az`)** driven from Python via `subprocess`, plus direct **Azure REST API** calls | Some Sentinel/Logic App features aren't fully exposed through the `az` CLI yet, so the deployment scripts fall back to calling the Azure Resource Manager REST API directly where needed. |
| **Infrastructure as Code** | **Terraform** (AWS provider) | Makes the entire AWS stack reproducible with `terraform apply` / tearable-down with `terraform destroy` — the professional standard for provisioning cloud infrastructure repeatably, instead of manual console clicks. |
| **Local tunneling** | **ngrok** | During local development, the FastAPI backend runs on a laptop, not a public server. ngrok exposes it to the internet temporarily so cloud services (Lambda, Logic Apps) can actually reach it with a `POST`. |
| **Threat taxonomy** | **MITRE ATT&CK** | The industry-standard, vendor-neutral catalogue of attacker tactics and techniques. Every incident this system generates is tagged with a real ATT&CK ID (e.g., `T1530`), which is how security teams communicate about attacks in a shared vocabulary. |

---

## 6. Repo tour — what lives where

```
CloudTripWire/
├── backend/                    # FastAPI REST API + SQLite database
│   └── app/
│       ├── core/                # config, ID generation, severity helper
│       ├── routers/              # incidents, metrics, evidence, health endpoints
│       ├── models.py             # SQLAlchemy table definition (1 table: Incident)
│       ├── schemas.py            # Pydantic request/response shapes
│       ├── database.py           # DB engine + session setup
│       └── main.py               # app factory, CORS, router wiring
│
├── frontend/                   # React dashboard
│   └── src/
│       ├── api/                  # Axios HTTP client + hardcoded mock data
│       ├── components/           # MetricCard, Charts, IncidentTable, IncidentDetail, Layout
│       ├── pages/                 # Dashboard, IncidentsPage, IncidentDetailPage
│       └── utils/                 # timestamp/status/text formatters
│
├── honeytokens/                # AWS honeytoken provisioning + attack simulation
│   ├── deploy_honeytokens.py    # Creates the IAM decoy user, S3 canary, CloudTrail, EventBridge rules
│   └── test_trigger.py           # Simulates an attacker using the leaked AWS keys
│
├── response/aws_lambda/        # The AWS auto-response function
│   ├── isolate_and_log.py       # Lambda handler: disable key, score severity, map MITRE, POST incident
│   ├── deploy_lambda.py          # Packages + deploys the Lambda
│   └── update_dashboard_url.py   # Updates the Lambda's dashboard URL when ngrok restarts
│
├── azure/                      # Azure honeytoken + Sentinel/Logic App setup
│   ├── deploy_azure.py          # Creates Resource Group, Storage canary, Log Analytics, SAS token
│   ├── deploy_sentinel.py        # Enables Sentinel, creates the KQL rule, deploys the Logic App
│   └── test_trigger.py           # Simulates an attacker reading the canary blob
│
├── terraform/                  # Infrastructure-as-Code for the full AWS stack
│   ├── aws.tf                    # Every AWS resource, declaratively
│   └── variables.tf
│
└── docs/
    ├── mitre-mapping.md          # Full ATT&CK technique mapping + severity decision tree
    ├── demo-guide.md              # Pre-demo checklist, 60-second script, interview Q&A prep
    └── PROJECT_OVERVIEW.md        # (this file)
```

---

## 7. Deep dive: the AWS pipeline

### Step 1 — Plant the bait (`honeytokens/deploy_honeytokens.py`)

This script does four things, in order, using `boto3` (AWS's Python SDK):

1. Creates an IAM user (`honeytoken-user`) and generates an access key for it — **no policies are attached**, so the account has zero AWS permissions. This is the "leaked credential."
2. Creates a private S3 bucket and uploads three files with deliberately tempting names — `internal/aws-backup-creds.txt`, `finance/employee-salaries-2025.csv`, `backups/db-dump-prod.sql` — plus server-side encryption and a public-access block (belt-and-suspenders: even the bait bucket itself follows security best practice).
3. Turns on **CloudTrail** — a multi-region trail with log file validation and, critically, **S3 data events enabled** (off by default in AWS — without this, `GetObject` calls on the bucket wouldn't be logged at all).
4. Creates two **EventBridge rules**: one matching any CloudTrail event where the calling identity is `honeytoken-user`, and one matching any CloudTrail event referencing the canary bucket by name.

### Step 2 — Simulate an attack (`honeytokens/test_trigger.py`)

Reads the decoy keys from a local file and uses them to call `s3:ListBuckets` and `iam:ListUsers`. Both calls are expected to fail with `AccessDenied` — that's fine, because CloudTrail logs the *attempt* regardless of the outcome. This script exists purely to demonstrate the pipeline without needing an actual external attacker.

### Step 3 — Automated response (`response/aws_lambda/isolate_and_log.py`)

This is the most substantial piece of logic in the project. When EventBridge invokes it, the Lambda:

1. Parses the CloudTrail event out of the EventBridge envelope.
2. Extracts the calling identity — handles three different AWS identity shapes: an IAM user, an assumed role (e.g. from an EC2 instance or Lambda), or an unknown type.
3. Calls `determine_severity()` — see [section 11](#11-how-incidents-get-their-severity).
4. Looks up the CloudTrail event name (e.g. `GetObject`, `AssumeRole`, `CreateUser`) in a hand-built dictionary that maps it to both a human-readable description and a **MITRE ATT&CK** technique ID.
5. **Disables the IAM key** via `iam.update_access_key(..., Status="Inactive")` — this is the actual containment action, and it happens regardless of severity.
6. If the attacker's source IP is inside a private network range (`10.x`, `172.16-31.x`, `192.168.x`) *and* the identity is an assumed role, it attempts to **quarantine an EC2 instance** by swapping its security groups for a locked-down "quarantine" group with no rules — this handles the scenario where the attacker isn't just using a leaked key remotely, but has actually compromised a server inside the AWS account.
7. Builds a structured incident (JSON) containing the principal, severity, IP, user agent, resource, a list of response actions taken, a timeline, and threat indicators — then `POST`s it to the dashboard's `/api/incidents` endpoint using nothing but Python's built-in `urllib` (no extra HTTP library dependency needed for a single POST call).

### Step 4 — Reproducibility (`terraform/aws.tf`)

Everything from steps 1 and 3 above can also be stood up in one command via Terraform (`terraform apply`), and torn down just as cleanly (`terraform destroy`). The Terraform version additionally defines a dedicated, **least-privilege IAM role for the Lambda itself** — scoped down to only `iam:UpdateAccessKey` / `iam:ListAccessKeys` on the *specific* honeytoken user ARN (not all IAM users), plus the EC2 permissions needed for quarantine. This is a deliberate security-engineering detail: the automation that responds to attacks shouldn't itself hold more power than it needs.

---

## 8. Deep dive: the Azure pipeline

Azure doesn't have a direct equivalent of CloudTrail + EventBridge + Lambda as a single named product, so this project composes the closest native Azure equivalents:

### Step 1 — Plant the bait (`azure/deploy_azure.py`)

Using the Azure CLI (`az`) driven from Python:

1. Creates a Resource Group to contain everything.
2. Creates a Storage Account (with public blob access explicitly disabled) and a `honeytokens` Blob container, then uploads the same three tempting files used on the AWS side.
3. Creates a **Log Analytics Workspace** — Azure's central log store.
4. Wires up **Diagnostic Settings** on the storage account's blob service so that every read (`StorageRead`) and write (`StorageWrite`) operation flows into that workspace.
5. Generates a **SAS token** (Shared Access Signature) — a time-limited, read-only URL that grants access to the canary container without needing a full Azure login. This SAS URL *is* the Azure honeytoken credential — anyone who finds it and uses it will show up in the storage logs.

### Step 2 — Detection + response (`azure/deploy_sentinel.py`)

1. **Enables Microsoft Sentinel** on the Log Analytics workspace (Sentinel is Microsoft's cloud SIEM/security-analytics product; it has to be explicitly turned on per workspace).
2. Creates a **Sentinel Analytic Rule** — a scheduled query written in **KQL (Kusto Query Language)** that runs every 5 minutes and checks: *"has anyone read a blob from the canary storage account via SAS or non-account-key authentication?"* If yes, it fires an alert.
3. Deploys a **Logic App** (`cloudtripwire-responder`) — an HTTP-triggered workflow that, when called, builds a structured incident payload (cloud=Azure, MITRE T1530, timestamps, caller IP, etc.) and `POST`s it to the exact same `/api/incidents` FastAPI endpoint the AWS Lambda uses. This is what makes the dashboard genuinely multi-cloud: both pipelines converge on one shared incident schema and one shared API.

Because some Sentinel and Logic App features aren't fully covered by the `az` CLI yet, this script talks directly to the **Azure Resource Manager REST API** (using an OAuth token obtained via `az account get-access-token`) for creating the analytic rule and the Logic App workflow definition — a good example of working around SDK/CLI gaps by dropping to the underlying REST layer.

### Step 3 — Simulate an attack (`azure/test_trigger.py`)

Uses the planted SAS URL to read the canary blob, generating a log entry that the Sentinel rule will pick up on its next 5-minute run.

---

## 9. The dashboard (what a user actually sees)

The frontend is a single-page React app (`frontend/src/App.jsx`) with three routes:

| Route | Component | Purpose |
|---|---|---|
| `/` | `Dashboard.jsx` | Metric cards (total/active/resolved/AWS/Azure incident counts), a time-series chart of incidents per day, and a table of the most recent incidents |
| `/incidents` | `IncidentsPage.jsx` | Full, filterable incident list |
| `/incident/:id` | `IncidentDetailPage.jsx` | Deep-dive view of a single incident: identity, IP, severity, the automated response actions taken, the full event timeline, and evidence links |

Key design decisions worth calling out to a technical reader:

- **Mock-data toggle.** The frontend can run entirely on hardcoded mock data (`frontend/src/api/incidentAPI.js`) with no backend running at all — useful for UI development, demos without cloud access, or just browsing the dashboard's look and feel. A switch in the UI flips between "Mock Data" and "Live API."
- **Polling, not push.** The dashboard re-fetches from the API every 15 seconds rather than using WebSockets — a deliberate simplicity trade-off appropriate for a low-frequency event stream like security incidents.
- **Axios client with interceptors** (`incidentAPI.js`) — centralizes error handling and leaves a clear extension point for adding auth headers later, without needing to touch every call site.

---

## 10. The API and data model

The backend exposes a small, focused REST API:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/metrics` | Aggregate counts: total, active, resolved, AWS, Azure |
| `GET` | `/api/incidents?limit=&status=&cloud=` | List incidents, newest first, with optional filters |
| `GET` | `/api/incident/{id}` | Full detail for one incident |
| `PATCH` | `/api/incident/{id}` | Update status (e.g. mark an incident "Resolved") |
| `POST` | `/api/incidents` | Ingest a new incident — this is the endpoint the AWS Lambda and Azure Logic App both call |
| `GET` | `/api/incidents/timeseries?days=7` | Daily incident counts, for the dashboard's trend chart |
| `GET` | `/api/evidence/{id}` | Evidence bundle links for an incident |
| `GET` | `/health` | Health check |

Every incident is stored as a single row with several JSON columns (`response_actions`, `timeline`, `threat_indicators`, `evidence`) — a pragmatic schema choice for an event-log-shaped record where the sub-structures don't need to be queried independently. A simplified example:

```json
{
  "id": "inc-001",
  "cloud": "AWS",
  "principal": "arn:aws:iam::123456789012:user/honeypot-user",
  "trigger_type": "S3 Access",
  "severity": "High",
  "status": "Active",
  "ip_address": "203.45.67.89",
  "resource_arn": "arn:aws:s3:::honeypot-bucket/sensitive.zip",
  "response_actions": [
    { "action": "Credential Revoked", "status": "Success" }
  ],
  "timeline": [
    { "event": "Honeytoken Triggered" },
    { "event": "Automated Response Initiated" }
  ],
  "threat_indicators": { "is_known_attacker": true, "geo_location": "Singapore" }
}
```

FastAPI's Pydantic schemas (`backend/app/schemas.py`) validate every request/response shape automatically, and interactive API docs are generated for free at `/docs` (Swagger UI) — no separate documentation to maintain by hand.

---

## 11. How incidents get their severity

Severity isn't guessed — it's computed from a small decision tree inside the Lambda (`determine_severity()` in `isolate_and_log.py`), evaluated top-to-bottom:

```
Is the source IP inside a private network range (10.x / 172.16-31.x / 192.168.x)?
    YES → Critical   (the attacker is already inside the network, not just using a leaked key remotely)

Is the event CreateUser / CreateAccessKey / AttachUserPolicy / AssumeRole?
    YES → Critical   (the attacker is trying to create persistence or escalate privileges)

Is the event ConsoleLogin without MFA?
    YES → Critical   (stolen password / credential stuffing)

Is the event GetObject / GetSecretValue / Scan / Query?
    YES → High       (active data exfiltration in progress)

Is the event RunInstances / InvokeFunction?
    YES → High       (compute/resource abuse, e.g. cryptomining)

Otherwise
    → Medium         (reconnaissance / enumeration — the attacker is still scoping things out)
```

This mirrors how a real security analyst reasons about an incident: *where* the attacker is calling from and *what* they're trying to do both matter more than any single signal in isolation.

---

## 12. MITRE ATT&CK — the industry vocabulary this project speaks

[MITRE ATT&CK](https://attack.mitre.org/) is a free, widely-adopted knowledge base of real-world attacker tactics and techniques, maintained by MITRE Corporation. Security teams across the industry use it as a common language — instead of saying "someone downloaded a file," you say "we observed **T1530 — Data from Cloud Storage**," and every other security professional immediately understands the category of behavior, without you having to explain it from scratch.

This project tags every incident it generates with a real ATT&CK technique ID. A sample of the mapping (full table in [`docs/mitre-mapping.md`](mitre-mapping.md)):

| Technique | ID | What it means here |
|---|---|---|
| Cloud Service Discovery | T1526 | Attacker is enumerating resources (`ListBuckets`, `DescribeInstances`) — early-stage recon |
| Data from Cloud Storage | T1530 | Attacker downloaded the decoy file — active exfiltration |
| Credentials in Files | T1552.001 | Attacker pulled a secret from Secrets Manager |
| Valid Accounts: Cloud Accounts | T1078.004 | Attacker used the stolen/decoy credential to authenticate |
| Create Account: Cloud Account | T1136.003 | Attacker is trying to create a persistent backdoor account |
| Resource Hijacking | T1496 | Attacker launched compute (e.g. for cryptomining) |

Speaking this vocabulary — and being explicit about what's *not* yet covered (see the "gap analysis" table in the MITRE doc) — is itself a signal of security-engineering maturity: it shows an understanding that detection coverage is always partial, and that naming the gaps is as important as naming the wins.

---

## 13. Infrastructure as Code (Terraform)

The `terraform/aws.tf` file captures the *entire* AWS side of the system as code — the decoy IAM user, the canary S3 bucket (with encryption and public-access blocking), the CloudTrail trail, the Lambda function (packaged directly from the same `isolate_and_log.py` used by the manual `boto3` script), a dedicated least-privilege IAM role for that Lambda, and both EventBridge rules with their Lambda-invoke permissions.

Why this matters, for a non-infrastructure audience: manually clicking through the AWS console to build this (as the `deploy_honeytokens.py`/`boto3` path effectively does) is error-prone and not repeatable. Terraform means the entire stack can be spun up (`terraform apply`) or completely torn down (`terraform destroy`) deterministically — important both for iterating on the project safely and for demonstrating that the design is production-shippable, not just a one-off script.

---

## 14. Project status — what's done, what's not

Per the project README, both cloud pipelines are functionally complete:

| Layer | Status |
|---|---|
| Incident API (FastAPI) | ✅ Live |
| Dashboard UI (React) | ✅ Live |
| AWS canaries + CloudTrail | ✅ Live |
| AWS detection (EventBridge) | ✅ Live |
| AWS auto-response (Lambda) | ✅ Live |
| AWS Terraform IaC | ✅ Live |
| Azure canaries + diagnostic logs | ✅ Live |
| Azure detection (Sentinel/KQL) | ✅ Live |
| Azure auto-response (Logic App) | ✅ Live |
| Evidence bundler (ZIP of CloudTrail window per incident) | 🚧 In progress |
| Terraform module for Azure | 📋 Not started |

---

## 15. Skills this project demonstrates

For a recruiter or hiring manager skimming this, here's a translation of the project into hire-relevant capabilities:

- **Cloud security engineering** — hands-on, real usage (not just conceptual knowledge) of CloudTrail, EventBridge, Lambda, IAM, S3 on AWS; Storage diagnostics, Log Analytics, Sentinel, Logic Apps on Azure.
- **Detection engineering** — designing detection logic (EventBridge pattern rules, KQL queries) rather than just consuming a vendor's pre-built alerts.
- **Incident response automation** — building an actual "detect → contain → document" pipeline, including least-privilege response permissions, not just an alert-and-hope system.
- **Full-stack development** — a working REST API (FastAPI/Python) and a working front-end (React), integrated end-to-end.
- **Infrastructure as Code** — Terraform used to make cloud infrastructure reproducible and disposable, not hand-built.
- **Security frameworks fluency** — mapping real technical events to MITRE ATT&CK, the industry-standard shared vocabulary for describing attacker behavior.
- **Working with imperfect tooling** — falling back to raw Azure REST API calls where the CLI/SDK has gaps (a very common real-world skill).
- **Communication** — the repo includes a demo script and interview Q&A prep (`docs/demo-guide.md`), showing an ability to explain technical work to a non-technical or interviewing audience.

---

## 16. Try it yourself

The dashboard can be explored **without any cloud account**, using its built-in mock data:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# → API at http://127.0.0.1:8000, interactive docs at /docs

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → Dashboard at http://localhost:5173
```

Open the dashboard, leave the **Mock Data** toggle on, and you'll see a populated dashboard immediately. Flip to **Live API** once the backend is running to see it hit the real FastAPI endpoints (which will be empty until incidents are seeded or the full cloud pipeline is deployed and triggered).

To see the *real* end-to-end pipeline (requires an AWS test account and `aws configure` set up first):

```bash
python honeytokens/deploy_honeytokens.py   # plant the bait
# deploy the Lambda, point it at your dashboard via ngrok — see docs/demo-guide.md
python honeytokens/test_trigger.py          # simulate an attacker
# watch the incident appear on the dashboard within ~30 seconds
```

---

## 17. Glossary

Plain-English definitions for every piece of jargon used above.

| Term | Meaning |
|---|---|
| **Honeytoken** | A fake credential or file planted purely as bait; any use of it is a guaranteed sign of an attacker, since nothing legitimate should ever touch it |
| **IAM** | Identity and Access Management — AWS's system for user accounts and permissions |
| **CloudTrail** | AWS service that logs every API call made in an account, including failed/denied ones |
| **EventBridge** | AWS's event-routing service — watches for events matching a pattern and triggers an action (e.g. run a Lambda) |
| **Lambda** | AWS's serverless compute service — runs a function in response to a trigger, with no server to manage |
| **S3** | AWS's object storage service (buckets and files) |
| **boto3** | The official AWS SDK for Python — used to call AWS APIs programmatically |
| **Blob storage** | Azure's equivalent of S3 — object storage for files ("blobs") |
| **SAS token (Shared Access Signature)** | A time-limited Azure credential that grants scoped access to storage without a full login |
| **Log Analytics Workspace** | Azure's central store for logs and telemetry, queried with KQL |
| **KQL (Kusto Query Language)** | The query language used to search and filter data in Azure Log Analytics / Sentinel |
| **Microsoft Sentinel** | Azure's cloud-native SIEM (Security Information and Event Management) — runs detection rules against log data and raises alerts |
| **Logic App** | Azure's serverless workflow automation service — the rough Azure equivalent of AWS Lambda for this kind of "when X happens, do Y" automation |
| **SIEM** | Security Information and Event Management — a system that collects and analyzes security event data from multiple sources |
| **MITRE ATT&CK** | A free, industry-standard knowledge base cataloguing real-world attacker tactics and techniques, used as shared vocabulary across the security industry |
| **IaC (Infrastructure as Code)** | Defining cloud infrastructure in version-controlled configuration files (here, Terraform) instead of manually clicking through a console |
| **Terraform** | A popular, cloud-agnostic Infrastructure-as-Code tool |
| **Least privilege** | A security principle: grant only the exact permissions something needs to do its job, nothing more |
| **False positive** | An alert that turns out not to be a real attack — the core weakness of anomaly/ML-based detection that honeytokens avoid by design |
| **REST API** | A common web API style using HTTP methods (`GET`, `POST`, `PATCH`) to read/write resources — what the FastAPI backend exposes |
| **FastAPI** | A modern Python web framework for building APIs, with automatic validation and interactive documentation |
| **Pydantic** | A Python library for data validation, used by FastAPI to enforce the shape of requests/responses |
| **SQLAlchemy** | A Python library (ORM) for working with databases using Python objects instead of raw SQL |
| **ngrok** | A tool that creates a temporary public URL tunneling to a service running on a local machine — used here so cloud services can reach the locally-running dashboard API during development/demos |

---

*For a shorter, faster-reading overview, see the [README](../README.md). For live-demo mechanics and interview prep, see [demo-guide.md](demo-guide.md). For the full attack-technique mapping, see [mitre-mapping.md](mitre-mapping.md).*
