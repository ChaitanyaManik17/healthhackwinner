# Chaitanya Phase 0 status

Phase 0 is **not complete** until the real Workshop Studio call and David's exact phrase review are finished. Work started October 9, 2026; local verification was completed October 10, 2026 in the user's timezone.

| Assigned sub-task | Current state | Evidence or remaining input |
| --- | --- | --- |
| Get Bedrock model access, run one-line test, and record a fast low-cost model | Prepared; live verification pending | Nova Micro ID recorded; probe and setup guide prepared. No AWS profile, credentials, or region was configured locally. Need workshop access and confirmed region. |
| Draft system prompt with five categories, urgency rules, JSON-only output, and unsure means nurse | Draft implemented; David confirmation pending | `ai/system_prompt.txt` and `ai/urgency_rules.md`; uses the plan's trigger list and marks added boundaries as proposals. |
| Define exact ticket output schema and add JSON validator | Implemented; local checks recorded below | `ai/ticket.schema.json`, `ai/validate_ticket.py`, routing and metadata checks, strict parsing, and offline tests. Team contract agreement remains a shared exit criterion. |
| Try David's 20 phrases by hand and note failures | Prepared; actual review pending | 20 provisional synthetic phrases and review helper provided. David's exact phrases and live model outputs were not available. No measured model accuracy or safety pass is claimed. |

## Local verification

- `python3 -m unittest discover -s ai/tests -v`: **47 tests passed** (15 validator tests and 32 Bedrock tool tests). No AWS calls were made by the tests.
- All five example tickets pass both the strict Python validator and JSON Schema with date-time format checks.
- The provisional CSV validates and contains exactly 20 synthetic phrases.
- The probe's `--check-only` result: region missing, no credential configuration present, zero network calls, live call not executed.
- The documented CLI arguments were checked with `--help`; all Python modules compile successfully.

Offline tests use fake Bedrock responses and never establish live model access or clinical safety.

## Needed from Chaitanya and the team

- The event Workshop Studio link, an authenticated session or approved local profile, and the region agreed with Chaitya.
- David's finalized urgency rules and actual 20 synthetic phrases with labels.
- Review of the prompt, contract boundaries, and proposed confidence threshold by David and Ketan.
- One teammate's review of the pull request before merging into `main`.

The detailed instructions are in [the setup and handoff guide](chaitanya_phase0.md). The remaining shared Phase 0 deliverables are owned by the other teammates in the original plan.
