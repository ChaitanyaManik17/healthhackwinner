# Project structure

```
backend/                 Chaitya   FastAPI app (app/), SAM template, tests/
ai/                      Chaitanya classifier prompt + classify() function
eval/                    Ketan     test_set.csv + scoring script
frontend/patient/        Harsh     bedside patient screen
frontend/dashboard/      Om        staff dashboard + nurse alert
shared/                  everyone  ticket.schema.json (contract)
docs/                    David + Chaitya  architecture, API contract, decisions, setup, deck material
scripts/                 helpers (check_bedrock.py)
.kiro/specs/call-bell-router/  requirements, design, tasks
```

- Work only inside your own folder unless the task says otherwise.
- Branch per task: `<name>/<topic>`; pull request into `main`; one reviewer.
