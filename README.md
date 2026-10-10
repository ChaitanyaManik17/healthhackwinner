# Call Bell Router

**Health Hack, Ops Unleashed Challenge 2: AI-driven call bell routing for inpatient units.**

A patient types (later: speaks) a request on a bedside tablet. An AI model classifies it and routes it to the
right department queue (Housekeeping, Food Services, Unit Clerk/IT). Anything urgent or unclear goes straight to
the nurse as a high-priority alert, so nurses only get paged for clinical needs.

> **Data rule: synthetic data only.** Never put real patient information, names, MRNs or any PHI in this repo,
> in prompts, in test sets, or in the demo. Use made-up rooms and phrases.

## Team

| Person | Track | Folder |
| --- | --- | --- |
| Chaitya | D: Backend & Cloud (lead) | `backend/` (API + `template.yaml` for AWS) |
| Chaitanya | C1: Classifier | `ai/` |
| Ketan | C2: Test set & safety | `eval/` |
| Harsh | B1: Patient screen | `frontend/patient/` |
| Om | B2: Staff dashboard | `frontend/dashboard/` |
| David | A: Product & Impact | `docs/` |

Full task list: [`docs/CallBellRouter_Team_Task_Plan.docx`](docs/CallBellRouter_Team_Task_Plan.docx).

## Repo layout

```
.kiro/                 Kiro spec (requirements, design, tasks) and steering files
backend/               API (FastAPI, runs locally and on AWS Lambda) + AWS SAM template
ai/                    Classifier prompt and classify function (Chaitanya)
eval/                  Test set and scoring script (Ketan)
frontend/patient/      Bedside patient screen (Harsh)
frontend/dashboard/    Staff dashboard (Om)
shared/                Contracts everyone codes against (ticket JSON schema)
docs/                  Architecture, API contract, decisions, setup guides
scripts/               Helper scripts (Bedrock access check)
```

## Shared contracts (read before coding)

- Ticket schema: [`shared/ticket.schema.json`](shared/ticket.schema.json)
- API contract: [`docs/api-contract.md`](docs/api-contract.md) and [`docs/openapi.yaml`](docs/openapi.yaml)
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Decision log: [`docs/decisions.md`](docs/decisions.md). Changing a contract? Add a line there and tell the team chat.

**Safety rule:** if the model is unsure, times out, or returns invalid JSON, the ticket goes to the nurse as high priority.

## How we work (branch rule)

1. Never commit straight to `main`. Create a branch: `<name>/<topic>`, e.g. `harsh/patient-quick-buttons`.
2. Push and open a pull request into `main`. One teammate gives a quick review, then merge.
3. Pull `main` often (`git pull origin main`) to avoid big conflicts.
4. Secrets (AWS keys, tokens) go in `.env`, which is git-ignored. Never commit them. Copy `.env.example` to start.

## Getting started

1. Setup guides: [AWS](docs/aws-setup.md), [Kiro](docs/kiro-setup.md).
2. Backend locally:
   ```bash
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements-dev.txt
   pytest                                   # contract + health tests
   cd src && uvicorn app.main:app --reload --port 8000
   # open http://localhost:8000/health and http://localhost:8000/docs
   ```
3. Check Bedrock access (after AWS credentials are set): `python scripts/check_bedrock.py`
