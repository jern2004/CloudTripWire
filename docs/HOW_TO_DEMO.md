# How to Demo CloudTripwire

Two versions here: a **Quick Demo** (2 minutes, no cloud account needed, works right now on your machine) and the **Full Demo** (a real simulated attack against real AWS/Azure infrastructure, more impressive but needs setup). Pick based on how much time you have and whether you're online with cloud access.

Both assume you've already got the app installed once (see [README.md](../README.md) if not).

---

## Quick Demo — "here's what I built" (2 minutes, zero setup)

Good for: a screen-share with a friend, a quick portfolio walkthrough, sanity-checking everything still works, or warming up right before the Full Demo.

### 1. Start it up

Open two terminals.

**Terminal 1 — backend:**
```powershell
cd C:\Users\User\CloudTripWire\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8080
```
*(Port 8080, not 8000 — on this machine, Windows/Hyper-V has 8000 reserved. Your `frontend/.env` already points at 8080, so just leave this as-is.)*

**Terminal 2 — frontend:**
```powershell
cd C:\Users\User\CloudTripWire\frontend
npm run dev
```
Open the URL it prints — `http://localhost:5173`.

### 2. Show the empty/live state

The dashboard should load showing the **green "● Live"** indicator with an empty incident list ("All honeytokens are secure. No suspicious activity detected.") — a real, working connection to a real backend, just nothing has happened yet. Worth pointing out explicitly: *this isn't a mockup, it's a live database with nothing in it.*

### 3. Populate it with realistic sample data

In a third terminal (leave the other two running):
```powershell
cd C:\Users\User\CloudTripWire\backend
$env:API_BASE_URL="http://127.0.0.1:8080/api"
python seed.data.py
```
This posts 5 realistic fake incidents (AWS + Azure, mixed severities) straight through the real API — not the frontend's hardcoded mock data, actual database rows. Refresh the dashboard.

### 4. What to walk through

- **Dashboard** — metric cards (total/active/AWS/Azure), the incidents-over-time chart, incidents-by-cloud chart, recent incidents table.
- **Click an incident row** → detail page: principal, IP, severity, MITRE ATT&CK tag, the automated response actions taken, and the full timeline. Explain: *"This is what a real attacker touching a decoy AWS credential would generate automatically — no human wrote this incident, a Lambda function did."*
- **All Incidents page** → search/filter by cloud, status, or free text.
- **Mark one Resolved** → shows the status update flowing through the real API.
- Point out the **Mock Data / Live API toggle** in the top right — mention that the whole dashboard also works with zero backend at all (useful if you ever demo somewhere without a laptop charger and 20 minutes to spare).

### 5. The one-sentence pitch to say out loud

> "CloudTripwire plants fake credentials and fake files in AWS and Azure that no real system should ever touch. The moment something does, it's automatically disabled, classified, and logged here — in under 30 seconds, with zero human involvement."

That's the whole Quick Demo. If your audience wants to see it actually happen against real infrastructure, move to the Full Demo below (or save it for next time).

---

## Full Demo — real attack simulation against real cloud infra

Good for: interviews, technical audiences, anyone who wants to see it actually fire against a real AWS account rather than pre-seeded data. Needs: an AWS account with CLI access, `ngrok`, and ~10 minutes of setup before your audience shows up.

### Pre-demo checklist (do this 10 minutes before, alone)

```powershell
aws sts get-caller-identity                     # confirm AWS CLI works
```
```powershell
# Terminal 1
cd C:\Users\User\CloudTripWire\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8080
```
```powershell
# Terminal 2
cd C:\Users\User\CloudTripWire\frontend
npm run dev
```
```powershell
# Terminal 3 — expose your backend so AWS can reach it
ngrok http 8080
```
Copy the `https://xxxx.ngrok-free.dev` URL ngrok prints, then:
```powershell
# Terminal 4
cd C:\Users\User\CloudTripWire\response\aws_lambda
python update_dashboard_url.py https://xxxx.ngrok-free.dev
```
In the browser: click the **Mock Data** button to switch it to **Live API**.

Check the honeytoken key is still active (it gets disabled every time you actually trigger it):
```powershell
aws iam list-access-keys --user-name honeytoken-user
```
If it shows `Inactive`, re-arm it:
```powershell
aws iam delete-access-key --user-name honeytoken-user --access-key-id <old-key-id>
aws iam create-access-key --user-name honeytoken-user
```
Then paste the new key pair into `honeytokens/honeytoken_keys.txt`.

*(If you haven't deployed the AWS side at all yet on this machine: run `python honeytokens/deploy_honeytokens.py` then `python response/aws_lambda/deploy_lambda.py` once, first. That's a one-time setup, not something you repeat per demo.)*

### The 60-second script (say this while doing it)

**1. Set the scene:**
> "CloudTripwire plants decoy credentials and files across AWS. Any access to them is guaranteed malicious — no tuning, no baseline, zero false positives."

**2. Show the clean dashboard**, pointing at the metric cards and empty/existing incident table.
> "This is pulling live from a FastAPI backend. It auto-refreshes every 15 seconds."

**3. Open a new terminal and run the attacker simulation:**
```powershell
cd C:\Users\User\CloudTripWire
python honeytokens\test_trigger.py
```
> "I'm simulating an attacker who found a leaked `.env` file with these decoy AWS credentials. They're trying to list S3 buckets and IAM users."

**4. Wait ~15–30 seconds, watching the dashboard.**
> "CloudTrail just logged that API call. EventBridge matched it against a detection rule and invoked a Lambda function — nobody clicked anything."

**5. Point to the new incident that appears.**
> "The IAM key was disabled automatically, about 2 seconds after the touch. The attacker's locked out before they can probe any further, and the incident's already here with a full timeline."

**6. Click into the incident detail.**
> "Full context: who, what IP, what tool, what MITRE ATT&CK technique this maps to, and every automated response action that ran — no human wrote any of this."

### If something goes wrong mid-demo

| Problem | Fix |
|---|---|
| Dashboard not updating after 30s | `aws lambda invoke --function-name cloudtripwire-responder --payload file://payload.json response.json` to fire it manually |
| ngrok URL expired / session reset | Restart `ngrok http 8080`, then rerun `update_dashboard_url.py` with the new URL |
| "Network Error" / CSP-looking errors in console | Hard-refresh (`Ctrl+Shift+R`) — a stale cached `index.html` can hold an old CSP |
| Nothing shows up at all, panic | Fall back to the Quick Demo path: `python backend\seed.data.py` gets you a populated dashboard in 5 seconds, and nobody in the room needs to know it's not a live trigger |

### Want the Azure side too?

Same idea, different plumbing — Storage diagnostic logs → Sentinel KQL rule → Logic App instead of CloudTrail → EventBridge → Lambda. Trigger it with:
```powershell
python azure\test_trigger.py
```
This one also calls the Logic App directly as its last step, so you see the incident almost immediately rather than waiting on Sentinel's real 5-minute schedule.

---

## After the demo, if asked...

For the harder follow-up questions ("how is this different from GuardDuty," "how do you score severity," MITRE technique details) — that's all in [demo-guide.md](demo-guide.md), which is the deeper interview-prep companion to this doc. Skim it once the night before anything that matters.

If you set an `INCIDENT_API_KEY` at some point (see [BUILD_NOTES.md](BUILD_NOTES.md) §3), remember the Lambda/Logic App/frontend all need the matching value too, or the pipeline goes quiet without any obvious error on screen.
