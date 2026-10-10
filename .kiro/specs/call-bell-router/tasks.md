# Implementation Plan

Owner in brackets. Phase 0 = setup and contracts; Phase 1 = walking skeleton (fake classifier end to end); Phase 2+ in later updates.

## Phase 0: Align and spec

- [x] 0.1 Repo scaffold, README with synthetic-data rule, branch rule, .gitignore, .env.example [Chaitya]
  - _Requirements: 5.3, 5.4_
- [x] 0.2 Ticket JSON schema in `shared/ticket.schema.json` [Chaitya, to confirm in contract meeting]
  - _Requirements: 2.1, 2.2, 2.3_
- [x] 0.3 API contract `docs/openapi.yaml` + `docs/api-contract.md` [Chaitya, to confirm in contract meeting]
  - _Requirements: 5.1_
- [x] 0.4 Architecture one-pager `docs/architecture.md` [Chaitya]
- [x] 0.5 Backend hello-world (`GET /health`) runnable locally, SAM template ready [Chaitya]
  - _Requirements: 5.1, 5.2_
- [ ] 0.6 Deploy hello-world to AWS and post the URL [Chaitya]
  - _Requirements: 5.2_
- [ ] 0.7 Bedrock access check passes (`scripts/check_bedrock.py`); model ID recorded in `docs/decisions.md` [Chaitanya]
- [ ] 0.8 Urgency rules written [David] → handed to Chaitanya
  - _Requirements: 3.1, 3.2_
- [ ] 0.9 First 20 labelled test phrases in `eval/test_set.csv` [Ketan]
  - _Requirements: 3.5_
- [ ] 0.10 Wireframes approved: patient screen [Harsh], dashboard [Om]
  - _Requirements: 1.5, 4.1, 4.3_
- [ ] 0.11 Problem statement + hours-saved formula [David]
  - _Requirements: 6.1_

## Phase 1: Walking skeleton

- [ ] 1.1 `TicketStore` with in-memory and DynamoDB implementations [Chaitya]
  - _Requirements: 3.4, 4.4_
- [ ] 1.2 `POST /requests` with a stub classifier (everything → housekeeping) + safety fallback wiring [Chaitya]
  - _Requirements: 1.1, 3.3, 3.4_
- [ ] 1.3 `GET /tickets`, `PATCH /tickets/{id}`, `GET /tickets/updates` [Chaitya]
  - _Requirements: 4.1, 4.2, 4.4_
- [ ] 1.4 Add Bedrock invoke permission to the Lambda role; wire real `ai.classify` behind `POST /classify` [Chaitya + Chaitanya]
  - _Requirements: 2.1–2.5_
- [ ] 1.5 `ai/classify.py` with prompt, JSON validation, timeout and fallback [Chaitanya]
  - _Requirements: 2.1–2.5, 3.1–3.3_
- [ ] 1.6 `eval/score.py` reporting accuracy and missed-urgent count [Ketan]
  - _Requirements: 3.5_
- [ ] 1.7 Patient screen calling `POST /requests` with confirmation and error states [Harsh]
  - _Requirements: 1.1–1.5_
- [ ] 1.8 Dashboard with department queues, polling, status buttons, nurse alert [Om]
  - _Requirements: 4.1–4.5_
- [ ] 1.9 Demo script v1 and deck outline [David]
  - _Requirements: 6.1_
