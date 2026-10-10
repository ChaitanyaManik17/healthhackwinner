# Decision log

Every change to a shared contract (categories, ticket schema, API, architecture) gets a row here **before** code changes,
plus a message in the team chat. Newest first.

| Date | Decision | Why | Who agreed |
| --- | --- | --- | --- |
| 2026-10-09 | Initial contracts: 5 categories → 4 departments; ticket schema v0.1; API v0.1; polling every 2 s for live updates; FastAPI on Lambda + DynamoDB + Bedrock; region `us-east-1` | Simplest stack that demos well in 48 h | Proposed by Chaitya, to confirm in the contract meeting |
| 2026-10-09 | Safety rule: unsure, timeout, or invalid JSON → nurse, high priority | Missing an urgent request is the worst failure | Proposed, to confirm |

## Open questions (resolve in the contract meeting)

- [ ] Confidence threshold below which we escalate to the nurse (suggested: 0.7).
- [ ] Which Bedrock model the classifier uses (Chaitanya picks after the access check; record the model ID here).
- [ ] Classifier timeout (suggested: 5 s).
- [ ] Is `tech` routed to `unit_clerk_it` with priority `low`? (suggested: yes)
- [ ] Frontend stack confirmed as React + Vite? (Harsh, Om)
