# CloudTripwire — MITRE ATT&CK Mapping

Maps each honeytoken trigger to the ATT&CK technique it detects.

> Framework version: ATT&CK v14  
> Cloud matrix: https://attack.mitre.org/matrices/enterprise/cloud/

---

## Coverage by tactic

| Tactic | Techniques Covered |
|---|---|
| Initial Access | T1078.004 |
| Credential Access | T1552.001 |
| Discovery | T1526, T1530 |
| Collection | T1530 |
| Privilege Escalation | T1078.004, T1548 |
| Persistence | T1136.003, T1098.001 |
| Impact | T1496, T1648 |

---

## Detailed mapping

### T1526 — Cloud Service Discovery
**Tactic:** Discovery  
**Honeytoken trigger:** IAM key used to enumerate AWS resources

| CloudTrail Event | What the attacker is doing |
|---|---|
| `ListBuckets` | Mapping what S3 buckets exist |
| `DescribeInstances` | Finding EC2 instances to target |
| `DescribeSecurityGroups` | Learning network topology |
| `ListSecrets` | Looking for stored credentials |
| `ListFunctions` | Discovering Lambda functions |

**Why it matters:** This is the reconnaissance phase. Attackers always enumerate before they exfiltrate. Catching them here stops the attack before they find anything real.

---

### T1530 — Data from Cloud Storage
**Tactic:** Collection  
**Honeytoken trigger:** S3 canary object accessed or DynamoDB decoy table scanned

| CloudTrail Event | What the attacker is doing |
|---|---|
| `GetObject` | Downloading a file from the canary S3 bucket |
| `Scan` | Dumping an entire DynamoDB table |
| `Query` | Targeted data extraction from DynamoDB |

**Detection logic:**  
Any `GetObject` on `cloudtripwire-canary-*` bucket is malicious — no legitimate system reads from it. Severity set to **High** because active exfiltration is in progress.

---

### T1552.001 — Credentials in Files
**Tactic:** Credential Access  
**Honeytoken trigger:** AWS Secrets Manager decoy secret accessed

| CloudTrail Event | What the attacker is doing |
|---|---|
| `GetSecretValue` | Extracting a stored secret (DB password, API key) |
| `ListSecrets` | Scanning for what secrets exist |

**Why it matters:** Attackers who reach Secrets Manager are in your network and moving laterally. Source IP being internal (`10.x.x.x`) at this stage means a compromised EC2 instance — severity escalates to **Critical**.

---

### T1078.004 — Valid Accounts: Cloud Accounts
**Tactic:** Initial Access / Privilege Escalation  
**Honeytoken trigger:** Decoy IAM key used for any API call, or console login on honeytoken account

| CloudTrail Event | What the attacker is doing |
|---|---|
| Any API call via `honeytoken-user` | Using stolen credentials found externally |
| `ConsoleLogin` (MFAUsed: No) | Manual console access with stolen password |
| `AssumeRole` on decoy role | Trying to escalate to a more powerful role |

**Severity signal:** Console login without MFA = **Critical** regardless of IP. MFA bypass or credential stuffing implies deliberate, targeted attack.

---

### T1136.003 — Create Account: Cloud Account
**Tactic:** Persistence  
**Honeytoken trigger:** Attacker tries to create a backdoor IAM user

| CloudTrail Event | What the attacker is doing |
|---|---|
| `CreateUser` | Creating a persistent backdoor account |
| `CreateLoginProfile` | Giving a new user console access |

**Why it matters:** Creating accounts means the attacker plans to come back. This is a late-stage persistence technique — they've already done recon and exfil and now want to maintain access. Severity: **Critical**.

---

### T1098.001 — Additional Cloud Credentials
**Tactic:** Persistence  
**Honeytoken trigger:** New access keys created for an existing account

| CloudTrail Event | What the attacker is doing |
|---|---|
| `CreateAccessKey` | Generating a new key on an existing account they control |
| `AttachUserPolicy` | Escalating permissions on an account they've taken over |

---

### T1496 — Resource Hijacking
**Tactic:** Impact  
**Honeytoken trigger:** Attacker launches compute resources (cryptomining)

| CloudTrail Event | What the attacker is doing |
|---|---|
| `RunInstances` | Launching EC2 instances for cryptomining |
| `RequestSpotInstances` | Cheaper compute for mining |

**Financial impact:** A single cryptomining campaign can generate thousands of dollars in AWS bills within hours. Detection here = direct cost savings. Severity: **High**.

---

### T1648 — Serverless Execution
**Tactic:** Impact  
**Honeytoken trigger:** Decoy Lambda function invoked

| CloudTrail Event | What the attacker is doing |
|---|---|
| `InvokeFunction` | Running code in your Lambda environment |

---

## Severity decision tree

```
Source IP is internal (10.x / 172.x / 192.168.x)?
    YES → Critical  (attacker already inside your network)
    NO  ↓

Event is CreateUser / CreateAccessKey / AttachUserPolicy / AssumeRole?
    YES → Critical  (persistence / privilege escalation)
    NO  ↓

Event is ConsoleLogin with MFAUsed = No?
    YES → Critical  (credential stuffing / stolen password)
    NO  ↓

Event is GetObject / GetSecretValue / Scan / Query?
    YES → High      (active data exfiltration)
    NO  ↓

Event is RunInstances / InvokeFunction?
    YES → High      (resource abuse)
    NO  ↓

Default → Medium    (reconnaissance / enumeration)
```

---

## Gap analysis — what CloudTripwire does not yet cover

| Technique | ID | Why not covered yet |
|---|---|---|
| Exfiltration over Web Service | T1567.002 | Requires monitoring outbound data volume |
| Modify Cloud Compute Infrastructure | T1578 | Needs EC2 modification event monitoring |
| Steal Application Access Token | T1528 | OAuth token theft harder to honeytoken |
| Impair Defenses: Disable Cloud Logs | T1562.008 | Would need CloudTrail to monitor itself |

These are candidates for future detection rules.
