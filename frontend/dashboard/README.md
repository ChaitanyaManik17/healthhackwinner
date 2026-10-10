# frontend/dashboard/ — Staff dashboard (owner: Om)

React + Vite. Polls `GET /tickets/updates?since=` every 2 s, updates status with `PATCH /tickets/{id}` (see `docs/api-contract.md`).
Nurse view: high-priority tickets on top with banner + sound.
