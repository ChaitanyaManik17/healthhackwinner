# API contract (v0.1)

The single source of truth is [`openapi.yaml`](openapi.yaml). This page is the readable summary.
Owner: Chaitya. Changes go in [`decisions.md`](decisions.md) first.

Base URL: `http://localhost:8000` locally; the AWS URL is posted in the team chat after each deploy.
All bodies are JSON. Times are ISO 8601 UTC.

| Method & path | Purpose | Caller | Phase |
| --- | --- | --- | --- |
| `GET /health` | Liveness check, returns `{"status":"ok"}` | Anyone | 0 (live) |
| `POST /requests` | Patient submits a request; returns the routed ticket | Patient screen | 1 |
| `GET /tickets?department=&status=` | List tickets for one department, newest first | Dashboard | 1 |
| `PATCH /tickets/{ticket_id}` | Change status: `new` → `acknowledged` → `done` | Dashboard | 1 |
| `GET /tickets/updates?since=` | Tickets created or changed after a timestamp (dashboard polls every 2 s) | Dashboard | 1 |
| `POST /classify` | Classifier only, no ticket stored (for testing) | `eval/` scripts | 1 |

## `POST /requests`

Request:

```json
{ "room": "412B", "text": "Can I get an extra pillow?", "language": "en", "source": "text" }
```

- `room` (required), `text` (required, 1–1000 chars), `language` (optional, ISO 639-1; the classifier detects it if missing), `source` (optional: `text` | `quick_button` | `voice`).

Response `201`: a full [Ticket](../shared/ticket.schema.json).

```json
{
  "ticket_id": "t_0001",
  "room": "412B",
  "raw_text": "Can I get an extra pillow?",
  "language": "en",
  "category": "housekeeping",
  "department": "housekeeping",
  "priority": "normal",
  "confidence": 0.95,
  "escalate_to_nurse": false,
  "reason": "comfort item request",
  "status": "new",
  "created_at": "2026-10-10T14:03:00Z"
}
```

The patient screen shows a message based on `department`: e.g. "Your request was sent to Housekeeping" or, for `nurse`, "A nurse has been alerted".

**Safety behaviour (non-negotiable):** if classification fails for any reason (timeout, invalid JSON, low confidence), the backend still returns `201` with `category: "unclear"`, `department: "nurse"`, `priority: "high"`, `escalate_to_nurse: true`. A patient request is never lost.

## `GET /tickets`

Query: `department` (optional: `housekeeping` | `food` | `unit_clerk_it` | `nurse`), `status` (optional, default: `new` and `acknowledged`).
Response `200`: `{ "tickets": [Ticket, ...] }`, sorted with `priority: high` first, then newest first.

## `PATCH /tickets/{ticket_id}`

Request: `{ "status": "acknowledged" }`. Response `200`: the updated Ticket. `404` if not found, `422` for a bad status.

## `GET /tickets/updates?since=2026-10-10T14:03:00Z`

Response `200`: `{ "tickets": [Ticket, ...], "server_time": "..." }`. The dashboard passes `server_time` back as `since` on the next poll.
We start with polling every 2 seconds because it is simple and reliable for the demo; WebSockets are a stretch goal.

## `POST /classify`

Request: `{ "text": "...", "language": "es" }` → Response `200`: the classification fields only
(`language`, `category`, `department`, `priority`, `confidence`, `escalate_to_nurse`, `reason`).

## Errors

All errors use `{ "detail": "message" }` with the usual codes: `400`/`422` bad input, `404` not found, `500` server error.

## Mocking before the backend is ready

Frontends can use the example responses above, or run the backend locally. Until Phase 1 endpoints land,
`POST /requests` is not implemented.
