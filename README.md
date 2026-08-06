# Swasthya Setu (স্বাস্থ্য সেতু) — Health Bridge

**SIH25083 — Digital Health Record Management System for Migrant Workers in Kerala**
Team Synapse | SRM Ramapuram

A health record that travels with the worker — QR-based, multilingual, and centrally
accessible from any registered clinic.

---

## Quick Start (any team member's laptop)

```bash
# 1. Clone/copy this folder, then:
cd swasthya_setu
pip install -r requirements.txt --break-system-packages

# 2. On Ubuntu/Debian, install the OCR engine (already on the build machine, may be
#    needed fresh on your laptop):
sudo apt-get install -y tesseract-ocr

# 3. Set up the database
python manage.py migrate

# 4. One command to create demo logins + a sample patient (Ramesh):
python manage.py seed_demo

# 5. (Optional but recommended) create an admin superuser for the /admin/ panel:
python manage.py createsuperuser

# 6. Run it
python manage.py runserver 0.0.0.0:8000
```

Visit **http://127.0.0.1:8000/** — or from another laptop on the same WiFi,
**http://<your-laptop's-local-IP>:8000/** (find your IP with `ipconfig` on Windows).

---

## Demo Logins (created by `seed_demo`)

| Role | Username | Password | What they see |
|---|---|---|---|
| **Central Government** (superuser) | `centralgov` | `demo1234` | Approve/reject clinic staff registration requests |
| Clinic Staff (pre-approved) | `clinicstaff` | `demo1234` | Patient lookup, add visits, propose record edits |
| Clinic Staff (PENDING — for live demo) | `newclinic_demo` | `demo1234` | Cannot log in until Central Government approves — try logging in as this user to see the block message, then approve it as `centralgov` |
| Patient (Ramesh, pre-loaded with a sample visit) | `ramesh_demo` | `demo1234` | QR code, scheme eligibility, AI chat, visit history, pending edit approvals |

For a live demo, also **register a fresh patient live** to show the QR generation
happening in real time — don't rely only on the pre-seeded one.

---

## The Approval Workflow (this is your governance/data-integrity story for judges)

**1. Clinic Staff Registration → Central Government Approval**
Anyone can request a clinic staff account from the unified `/` page, but the account
is created **inactive**. They cannot log in until the Central Government (a Django
superuser — represents the actual government body in a real deployment) approves
the request from `/govt/`. Try it live: log in as `newclinic_demo` first (blocked),
then as `centralgov`, approve the request, then log in as `newclinic_demo` again (works).

**2. Clinic-Proposed Edits → Patient Approval**
Clinic staff can freely **add new visit records** (that's additive, always allowed —
a clinic should be able to document a new visit). But if staff want to change a
patient's *existing* details (name, worksite, conditions, allergies), that change is
**held as a pending request**, not applied directly. The patient sees it on their own
dashboard and must explicitly Approve or Reject it. This is a genuine "patient data
sovereignty" feature — no one can silently rewrite a migrant worker's record without
their knowledge, which matters a lot for a vulnerable population.

This two-layer approval system (government-level for who can act, patient-level for
what happens to their own data) is a meaningfully stronger governance story than a
typical CRUD app, and worth highlighting explicitly to judges.

---

## Enabling the Live AI Assistant

Without an API key, the assistant runs in **offline fallback mode** — it still
answers medication/follow-up/condition questions correctly using rule-based logic
on the record, so the demo works even with no internet. This is a deliberate
design choice: **the assistant degrades gracefully instead of breaking.**

To enable full LLM-powered multilingual responses (recommended for the actual
judging demo), set an environment variable before running the server:

```bash
export GROQ_API_KEY="your_key_here"      # recommended - fast + generous free tier
# OR
export OPENAI_API_KEY="your_key_here"
```

Get a free Groq API key at **console.groq.com** — takes under 2 minutes, no card required.

---

## What's Actually Built vs. What's Roadmap (be upfront about this in your pitch)

**✅ Fully working:**
- Unified login/register hub — one page, tabs for Login / Patient / Clinic Staff
- Patient registration with QR-coded unique Health ID
- Clinic staff registration with Central Government (superuser) approval gate —
  accounts are inactive until approved
- Patient-consent edit requests — clinic-proposed changes to existing patient
  details require the patient's explicit approval before they apply
- Role-based login (Patient / Clinic Staff / Central Government), via Django's auth + groups
- One central database — any clinic staff login can look up ANY patient (this
  demonstrates the "no fragmentation across states" story without needing real
  distributed sync)
- Multilingual AI assistant that answers questions grounded strictly in the
  patient's own record (works offline via fallback, or live via Groq/OpenAI)
- Document upload + OCR text extraction (Tesseract) on prescriptions/lab reports
- Rule-based PM-JAY scheme eligibility flagging

**🔜 Honest roadmap (say this proactively when presenting):**
- Real encrypted data storage / compliance-grade security infrastructure
- True offline-first sync for genuinely low-connectivity worksites
- Live government scheme API integration (currently rule-based, not connected
  to a real PM-JAY database)
- Handwriting-specific OCR (current OCR is reliable on printed/typed text;
  handwritten prescriptions are a known hard case — flag this if a judge tests
  it live with a handwritten sample)

Being upfront about this list is a strength in judging, not a weakness — it shows
engineering maturity.

---

## Deploying to Render (for a stable public URL, not dependent on a laptop)

1. Push this project to a GitHub repo
2. On Render: New → Web Service → connect your repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn swasthya_setu.wsgi`
5. Add environment variables in Render's dashboard: `GROQ_API_KEY`, and set
   `DEBUG=False` in settings for production
6. **Important:** Render's free tier spins down after inactivity — visit your
   URL yourself 10-15 minutes before your judging slot to "wake it up"
7. **Important:** SQLite on Render's free tier doesn't persist reliably across
   restarts — re-run `python manage.py seed_demo` right after each deploy/restart
   so your demo data is fresh

---

## Project Structure

```
swasthya_setu/
├── manage.py
├── requirements.txt
├── swasthya_setu/          # project settings, urls
└── records/                 # the main app
    ├── models.py            # Patient, VisitRecord
    ├── views.py              # registration, dashboards, AI endpoint, clinic lookup
    ├── forms.py
    ├── urls.py
    ├── admin.py              # customized admin (usable as a backup clinic view)
    ├── utils.py              # QR generation, OCR extraction
    ├── ai_assistant.py       # multilingual assistant logic
    ├── management/commands/seed_demo.py   # one-command demo data setup
    └── templates/records/    # all HTML templates
```

---

## For the Pitch: The Full Demo Script

1. **Governance first:** Log in as `newclinic_demo` — show the "pending approval"
   block. Then log in as `centralgov`, approve it on `/govt/`. Log in as
   `newclinic_demo` again — now it works. This 30-second beat proves your
   governance layer is real, not just claimed.
2. Show Ramesh's dashboard — QR code, his existing Hypertension record
3. Ask the AI assistant: "What medication am I on?" — show the grounded answer
4. Switch to Clinic Staff (`clinicstaff`), look up Ramesh by Health ID — full
   history instantly visible from a "different clinic"
5. Add a new visit record with an uploaded prescription photo — OCR extracts
   the text automatically
6. Click "Propose Edit to Details," change Ramesh's worksite, submit — show
   it does NOT change yet
7. Log back in as Ramesh — show the pending approval card, approve it — show
   the change now applies. This is your "patient data sovereignty" moment.
8. Point out the PM-JAY eligibility flag
9. Close with the honest roadmap slide — security, offline sync, live scheme API

This is a genuinely complete governance + clinical + AI demo in under 5 minutes —
longer than before, but it now tells a much stronger, more realistic system story.
