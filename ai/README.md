# ai/ — Classifier (owner: Chaitanya)

Phase 1 deliverable: `classify(text, language=None) -> Classification` (see `backend/src/app/models.py` and `shared/ticket.schema.json`).
Rules: JSON-only output validated against the schema; timeout ~5 s; on any failure return `nurse_fallback()`.
Start with `python scripts/check_bedrock.py` to confirm Bedrock access, then record the model id in `docs/decisions.md`.
