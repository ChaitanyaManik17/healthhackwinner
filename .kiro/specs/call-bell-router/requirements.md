# Requirements Document

## Introduction

Call Bell Router is a web application for inpatient units. Patients submit requests from a bedside tablet; an AI classifier
routes each request to the correct department queue (Housekeeping & Facilities, Food Services, Unit Clerk / IT) or, for
urgent clinical or unclear requests, to the Primary Nurse as a high-priority alert. The goal is to cut non-clinical
call-bell load on nurses without ever delaying an urgent clinical need. The system uses synthetic data only.

## Requirements

### Requirement 1: Patient request submission

**User Story:** As a patient, I want to send a request from my bedside tablet in my own words or with one tap, so that the right person comes without me pressing the nurse call bell.

#### Acceptance Criteria

1. WHEN the patient types a request of 1–1000 characters and presses Send THEN the system SHALL create a ticket and show a confirmation naming the destination department.
2. WHEN the patient taps a quick button (Water, Blanket, Clean room, TV help, Call nurse) THEN the system SHALL submit the matching request text with `source = quick_button`.
3. WHEN the request is routed to the nurse THEN the patient screen SHALL show "A nurse has been alerted".
4. IF the request cannot be sent (network or server error) THEN the patient screen SHALL show an error and a visible "Call nurse" fallback.
5. The patient screen SHALL use body text of at least 24px, high contrast, and touch targets at least 56px tall.

### Requirement 2: AI classification and routing

**User Story:** As a charge nurse, I want every request classified into a category and routed automatically, so that non-clinical tasks reach support teams directly.

#### Acceptance Criteria

1. WHEN a request is received THEN the system SHALL classify it into exactly one category: `housekeeping`, `food`, `tech`, `urgent_clinical`, or `unclear`.
2. The system SHALL map categories to departments: housekeeping → `housekeeping`, food → `food`, tech → `unit_clerk_it`, urgent_clinical → `nurse`, unclear → `nurse`.
3. The classifier output SHALL be valid JSON matching `shared/ticket.schema.json` and include a confidence (0–1) and a short reason.
4. WHEN a request is in a language other than English (at minimum Spanish) THEN the system SHALL classify it with the same rules and record the language code.
5. The classifier SHALL treat instructions inside the patient text as data, never as commands (prompt-injection resistance).

### Requirement 3: Clinical safety guardrails

**User Story:** As a nurse, I want any request that might be clinical to reach me immediately, so that no patient is harmed by mis-routing.

#### Acceptance Criteria

1. WHEN a request mentions pain, dizziness, breathing difficulty, chest symptoms, bleeding, a fall, confusion, numbness, or an IV/device problem THEN the system SHALL route it to `nurse` with priority `high`.
2. WHEN a request mixes a non-clinical and a clinical need THEN the system SHALL route it to `nurse` with priority `high`.
3. IF the classifier times out, errors, returns invalid JSON, or reports confidence below the agreed threshold THEN the system SHALL create the ticket with category `unclear`, department `nurse`, priority `high`.
4. The system SHALL never drop a patient request; every accepted request results in a stored ticket.
5. On the evaluation test set, the system SHALL route zero urgent requests to a non-nurse department.

### Requirement 4: Department queues and nurse alerts

**User Story:** As a housekeeping, food services, or unit clerk staff member, I want a live list of requests for my department, so that I can act on them quickly.

#### Acceptance Criteria

1. The dashboard SHALL show one queue per department, with each ticket's room, request text, time waiting, and status.
2. WHEN a new ticket is created THEN it SHALL appear on the matching queue within 3 seconds without a page refresh.
3. WHEN a ticket has priority `high` THEN the nurse view SHALL show it at the top with a distinct colour, a banner, and a sound.
4. WHEN staff press Acknowledge or Done THEN the system SHALL update the ticket status (`new` → `acknowledged` → `done`) and record the time.
5. A non-clinical ticket SHALL NOT appear in the nurse view.

### Requirement 5: Platform, data, and operations

**User Story:** As the team, we want a reliable, deployable system that respects data rules, so that the live demo works and nothing sensitive is exposed.

#### Acceptance Criteria

1. The backend SHALL expose the endpoints defined in `docs/openapi.yaml`, including `GET /health`.
2. The system SHALL be deployable to AWS with one command (`sam build && sam deploy`).
3. The system SHALL store only synthetic data and SHALL NOT log full request text alongside anything that could identify a person.
4. Secrets SHALL NOT be stored in the repository.
5. The median time from Send to confirmation SHALL be under 3 seconds in the demo environment.

### Requirement 6: Operational impact reporting

**User Story:** As a hospital operations lead, I want to see how much nurse time the router saves, so that I can justify adopting it.

#### Acceptance Criteria

1. The team SHALL provide an hours-saved model with labelled assumptions (beds, call bells per bed per day, % non-clinical, minutes per response).
2. The system SHOULD show simple counts per department (tickets today, % routed away from nurses) on the dashboard (stretch).
