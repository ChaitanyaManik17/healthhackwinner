# Tech stack

- Backend: Python 3.12, FastAPI, Pydantic v2, Mangum (Lambda adapter). Runs locally with `uvicorn app.main:app --reload`.
- Infra: AWS SAM (`backend/template.yaml`): API Gateway HTTP API, Lambda (python3.12, arm64), DynamoDB (on-demand). Region us-east-1.
- LLM: Claude on Amazon Bedrock via the official `anthropic` Python SDK, `AnthropicBedrockMantle` client.
  Model ID comes from the `BEDROCK_MODEL_ID` env var (Bedrock IDs use the `anthropic.` prefix). Never hard-code credentials.
- Frontends: React + Vite (TypeScript), static hosting. Live updates by polling `GET /tickets/updates` every 2 seconds.
- Tests: pytest for backend, ai and eval.

## Contracts (do not change without a row in docs/decisions.md)

- Ticket schema: `shared/ticket.schema.json`
- API: `docs/openapi.yaml` (summary in `docs/api-contract.md`)

## Coding rules

- Classifier output must be validated against the schema; on any failure return the nurse/high-priority fallback.
- Keep secrets in `.env` (git-ignored) or Lambda environment/IAM. Never log full request bodies with anything that could be PHI.
- Small, readable functions; type hints in Python; no unused dependencies.
