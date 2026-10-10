# Product: Call Bell Router

Hackathon project (Health Hack, Ops Unleashed Challenge 2). A web app that routes inpatient call-bell requests with AI.

- Up to 60–70% of call-bell activations are non-clinical (water, blankets, cleaning, TV). When they all go to nurses,
  it causes alarm fatigue and slower response to real clinical needs.
- A patient types (later: speaks) a request on a bedside tablet. An LLM classifies it and routes it to Housekeeping & Facilities,
  Food Services, Unit Clerk / IT, or the Primary Nurse.
- **Safety first:** urgent clinical requests (pain, dizziness, breathing, bleeding, falls, chest symptoms, confusion, IV problems)
  and anything unclear, mixed, or failed go to the nurse as high priority. A missed urgent request is the worst possible failure.
- Users: patients (often elderly or stressed; need large text, simple words) and staff (need a scannable queue).
- Judging: Safety & Accuracy, Web App Execution, Operational Impact, Live Demo.
- **Synthetic data only. Never use or generate real patient information.**
