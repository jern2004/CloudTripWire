# CloudTripwire (Demo Guide)

Use this before every demo or interview. Run through it once the day before so nothing surprises you.

---

## Pre-demo checklist (do this 10 minutes before)

```
□ AWS CLI working:       aws sts get-caller-identity
□ Backend running:       cd backend && uvicorn app.main:app --reload
□ Frontend running:      cd frontend && npm run dev
□ ngrok running:         ngrok http 8000
□ Lambda URL updated:    python response/aws_lambda/update_dashboard_url.py <ngrok-base-url>
                         e.g. python response/aws_lambda/update_dashboard_url.py https://xxxx.ngrok-free.dev
                         (pass the base URL only — the script adds /api/incidents automatically)
□ Dashboard on Live API: http://localhost:5173 → click "Mock Data" → "Live API"
□ Honeytoken key active: aws iam list-access-keys --user-name honeytoken-user
```

If the honeytoken key shows `Inactive` (it gets disabled every time you test), create a fresh one:
```bash
# Delete the old inactive key first
aws iam delete-access-key \
  --user-name honeytoken-user \
  --access-key-id <old-key-id>

# Create a new one
aws iam create-access-key --user-name honeytoken-user
# Paste the new keys into honeytokens/honeytoken_keys.txt
```

---

## The 60-second demo script

**Say this while doing it:**

> "CloudTripwire plants decoy credentials and files across AWS. Any access to them is
> guaranteed malicious — no tuning, no baseline, zero false positives."

**1. Show the dashboard** — point out the metric cards and incident table.

> "This is the incident dashboard. It's pulling live from a FastAPI backend backed by
> SQLite. Auto-refreshes every 15 seconds."

**2. Open a second terminal and run the trigger:**
```bash
python honeytokens/test_trigger.py
```

> "I'm now simulating an attacker who found a leaked .env file containing the decoy
> AWS credentials. They're trying to list S3 buckets and IAM users."

**3. Wait 15–30 seconds, watch the dashboard.**

> "CloudTrail logged the API call. EventBridge matched the detection rule and invoked
> the Lambda response function."

**4. Point to the new incident that appeared.**

> "The IAM key was disabled automatically — 2 seconds after the touch. The attacker
> is locked out before they can probe further. The incident is now on the dashboard
> with a full timeline."

**5. Click the incident row → show detail page.**

> "Every incident has a full detail view — who, what IP, what tool they used, what
> action was taken, and the full event timeline. The severity is determined
> automatically based on signals: internal IP means Critical, external recon is Medium."

**6. Point to response actions section.**

> "The response was fully automated. No human had to intervene. Detection to
> containment in under 30 seconds."

---

## If something goes wrong mid-demo

**Dashboard not updating → manual refresh:**
```bash
# Use the direct Lambda invoke instead of waiting for CloudTrail
aws lambda invoke \
  --function-name cloudtripwire-responder \
  --payload file:///tmp/payload.json \
  /tmp/response.json && cat /tmp/response.json
```

**ngrok session expired (free tier times out after a few hours):**
```bash
# Restart ngrok
ngrok http 8000
# Update Lambda with new URL
python response/aws_lambda/update_dashboard_url.py <new-ngrok-url>
```

**Backend not running:**
```bash
cd backend && uvicorn app.main:app --reload
```

**No incidents on dashboard:**
```bash
# Seed sample data
cd backend && python seed.data.py
```

---

## Interview questions and how to answer them

**"How does it detect the honeytoken being used?"**

> CloudTrail records every AWS API call — even failed ones, before the permission
> check. EventBridge has a rule that pattern-matches on the decoy username. The moment
> any call comes in from that identity, EventBridge fires the Lambda within seconds.

**"Why zero false positives?"**

> The honeytoken user has no permissions and exists in no real system. Nothing
> legitimate ever calls it. Any access is definitionally malicious — there's no
> threshold to tune, no baseline to establish.

**"How do you determine severity?"**

> Three signals: source IP, event type, and identity type. Internal IP means the
> attacker is already inside — Critical. Exfiltration events like GetSecretValue are
> High. Reconnaissance like ListBuckets from external IP is Medium. Console login
> without MFA is always Critical regardless of IP.

**"What MITRE techniques does this cover?"**

> T1552 credential access, T1530 data from cloud storage, T1526 cloud service
> discovery, T1078.004 valid cloud accounts, T1496 resource hijacking. The full
> mapping is in docs/mitre-mapping.md.

**"What would you add if you had more time?"**

> Azure side is partially built — Sentinel analytic rules and Logic Apps for the
> same pattern on Azure. Also Terraform to make the entire AWS setup reproducible
> with one command. And a proper evidence bundler that zips the CloudTrail window
> into a forensic package per incident.

**"How is this different from GuardDuty?"**

> GuardDuty uses ML and behavioural baselines — it can have false positives and
> needs tuning. A honeytoken is a logical trap: there is no legitimate use case,
> so the signal is binary. It also gives you immediate automated response, not
> just an alert. They complement each other — GuardDuty for broad coverage,
> honeytokens for guaranteed high-signal detections.

---

## Architecture in one paragraph (memorise this)

> CloudTripwire plants decoy IAM credentials and S3 objects in AWS. CloudTrail
> records every API call. An EventBridge rule watches for activity from the decoy
> identity and triggers a Lambda function within seconds of detection. The Lambda
> disables the compromised key, captures the forensic context — IP, user agent,
> event type — and posts a structured incident to a FastAPI REST API. A React
> dashboard displays the incident in real time with severity classification,
> automated response actions, and a full event timeline. The same pattern is
> replicated on Azure using Sentinel analytics rules and Logic Apps.

---

## Key numbers to remember

| Metric | Value |
|---|---|
| Detection latency | < 60 seconds (CloudTrail → EventBridge → Lambda) |
| Key disabled in | ~2 seconds (Lambda → IAM UpdateAccessKey) |
| Dashboard refresh | Every 15 seconds |
| False positive rate | 0% — any access to a decoy is definitionally malicious |
| Honeytoken types | IAM key, S3 object canary, beacon link |
| MITRE techniques covered | 8 across 5 tactics |
