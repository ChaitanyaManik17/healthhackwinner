# Proposed Phase 0 urgency and routing rules

**Status: proposed from the team task plan; awaiting David's confirmation and the team's contract agreement.** These rules support a synthetic-data routing demonstration. They are not clinical triage guidance and do not establish that a request or patient is medically safe.

Source: `docs/CallBellRouter_Team_Task_Plan.docx`, Sections 3, 5 (David and Chaitanya), 7, and 8. The plan assigns the final urgency rules to David. No approved rule set or David-authored list of 20 phrases was present when this draft was prepared.

## Routing contract

| Category | Department | Priority | Escalate to nurse |
| --- | --- | --- | --- |
| `housekeeping` | `housekeeping` | `normal` | `false` |
| `food` | `food` | `normal` | `false` |
| `tech` | `unit_clerk_it` | `low` | `false` |
| `urgent_clinical` | `nurse` | `high` | `true` |
| `unclear` | `nurse` | `high` | `true` |

Anything urgent or uncertain goes to the nurse. A request spanning categories is `unclear` and reaches the nurse, so a single-ticket router does not silently discard part of a request. Several needs within one category can remain in that category.

## Proposed clinical triggers

David's assignment lists pain, dizziness, shortness of breath, bleeding, falls, chest tightness, confusion, "can't feel", IV problems, and nil per os questions. These apply to the meaning of the request, including ordinary paraphrases, rather than only exact keyword matches. A stated clinical concern is never downgraded because the model thinks it is mild.

The following conservative handling is proposed for ambiguous boundaries and needs David's review:

| Synthetic request | Proposed result | Routing reason |
| --- | --- | --- |
| "Please bring an extra pillow." | `housekeeping` / normal | Ordinary bedding request. |
| "My pillow is hurting my neck." | `urgent_clinical` / high, nurse | Reports pain; no pain exception is approved. |
| "Can I have apple juice?" | `food` / normal | Ordinary refreshment request. |
| "I'm NPO. Can I have water?" | `urgent_clinical` / high, nurse | Permission under an eating/drinking restriction requires nursing review. |
| "I'm not allowed to eat, but bring me a sandwich." | `urgent_clinical` / high, nurse | A food request cannot bypass a stated restriction. |
| "Can I eat before my procedure?" | `urgent_clinical` / high, nurse | Asks about permission to eat in a clinical context. |
| "The TV remote does not work." | `tech` / low | Purely mechanical amenity issue. |
| "My IV is beeping and my arm is wet." | `urgent_clinical` / high, nurse | IV concern belongs with a nurse. |
| "The pump alarm is going off." | `urgent_clinical` / high, nurse | Clinical equipment warning, not an IT amenity issue. |
| "Did I miss my medication?" | `urgent_clinical` / high, nurse | Medication concern. |
| "Water, and my chest feels tight." | `unclear` / high, nurse | Mixed clinical and nonclinical request. |
| "Clean the room and fix the TV." | `unclear` / high, nurse | Different service categories in one ticket. |
| "I need help." | `unclear` / high, nurse | No clear need is established. |

Swallowing difficulty, uncertainty about eating/drinking restrictions, medication questions, clinical equipment warnings, and procedure-related food permission are conservative extensions of the plan's nurse rule. David must confirm these boundaries with the team. The application never answers whether food, drink, medicine, or equipment actions are safe.

## Uncertainty and failure handling

- Provisional minimum confidence for a non-nurse route: **0.80**. This must be agreed with David and Ketan. If changed, update `MIN_CONFIDENCE` in the review helper, the prompt's threshold, and the model handoff record together. It is an uncalibrated model estimate, not a measured safety score.
- Low confidence, an unknown category, contradictory content, unsupported language, empty text, or an instruction-only attack becomes `unclear` / `nurse` / `high` / `true`.
- Timeout, access/model errors, invalid JSON, duplicate keys, extra/missing keys, invalid field types, metadata changes, and inconsistent routing combinations must produce a runtime nurse fallback. The model prompt alone cannot enforce these guarantees; the validator must enforce the output contract.
- A known clinical concern in a mixed request still reaches the nurse. The proposed category for mixed requests is `unclear`, matching the plan's table.
- Instructions embedded in the patient's text cannot change the routing rules. If a clear service request remains after ignoring those instructions, classify that request normally. If the remaining need is uncertain, send it to the nurse.
- Nurse routing is a ticket destination. Neither the classifier nor its reason may claim that a nurse was paged, alerted, or has responded unless the application separately confirms delivery.

## Language and data scope

Phase 0 uses synthetic English text only. The review helper enforces a nurse fallback when the language tag is not exactly `en`. The prompt also directs the model to send non-English text mislabeled `en` to the nurse; recognizing that mismatch depends on the model and must be evaluated. Spanish and other language fixtures exercise the conservative fallback; they do not demonstrate approved multilingual support. Do not silently translate requests or change the supplied language value. Voice and multilingual support start only after the team's safety targets pass and the team approves expanding scope, as required by the plan.

## Review items for David and Ketan

1. Confirm the clinical trigger list, the proposed extensions, and the no-exception treatment of pillow-related neck pain.
2. Confirm how mixed service requests should be represented; this draft routes any request spanning categories to the nurse.
3. Confirm the provisional 0.80 confidence threshold and safety targets. The plan suggests zero urgent requests routed away from the nurse and at least 90% overall accuracy, but these are not yet agreed results.
4. Provide David's final 20 phrases and expected labels. Proposed fixtures cannot be recorded as David's reviewed phrases.
5. Review symptoms expressed indirectly, negated symptoms, historical symptoms, clinical vocabulary used figuratively, and non-English requests before approving production or multilingual use.

After confirmation, record the decision, date, reviewer, and any changes in the team contract. Re-run the test set after every prompt or rule change and keep measured results separate from these proposed rules.
