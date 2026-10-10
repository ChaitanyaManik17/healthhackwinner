# Call Bell Router

A Health Hack prototype that routes synthetic patient requests to the appropriate department and escalates urgent or unclear requests to a nurse.

**Use synthetic data only. Never enter real patient information, credentials, or clinical records into this repository or the demo.**

The team assignments and Phase 0 exit criteria are in `docs/CallBellRouter_Team_Task_Plan.docx`. Work on branches named `<name>/<topic>` and merge into `main` through a pull request reviewed by a teammate.

## Chaitanya's Phase 0

The classifier setup is in `ai/`. It includes a proposed system prompt and urgency rules, the exact ticket JSON Schema, a strict validator, and tools for a Bedrock smoke test and phrase review. This phase does not deploy the application or implement the `/classify` endpoint.

Start with [the setup and handoff guide](docs/chaitanya_phase0.md). [The checklist](docs/chaitanya_phase0_status.md) distinguishes completed local work from the AWS and team inputs still needed.

Run the offline checks from the repository root:

```sh
python3 -m unittest discover -s ai/tests -v
python3 -m ai.validate_ticket ai/examples/housekeeping.json
```

No AWS credentials are needed for these checks. Only the live Bedrock tools require the dependencies in `ai/requirements.txt` and an authenticated Workshop Studio session.
