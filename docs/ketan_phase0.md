# Ketan — Phase 0 handoff and manual steps

Prepared from [the team task plan](CallBellRouter_Team_Task_Plan.docx), dated
2026-10-09. Scope: Ketan's C2 tasks only. Branch: **`ketan`**, as requested by Ketan.

## Deliverables and status

| Ketan's Phase 0 sub-task | Deliverable | Status |
| --- | --- | --- |
| Create `eval/test_set.csv` with the six specified columns and 20 rows | [Test set](../eval/test_set.csv) | Implemented; structural validation passes |
| Cover mixed, vague, comfort-item pain, IV, Spanish, NPO and injection cases | [Coverage and label rationale](../eval/README.md#coverage-in-the-first-20-cases) | Included; semantic label review pending David |
| Agree safety targets with David | [Proposed gates and metric definitions](../eval/README.md#proposed-acceptance-targets--pending-david) | Prepared; David's agreement is pending |

A dependency-free [CSV validator](../eval/validate_test_set.py) supports review.
Its PASS output establishes dataset structure and annotated coverage, not model
safety or clinical correctness. Phase 0 cannot be recorded as fully signed off
until David confirms the rules, labels and targets.

## Steps Ketan must complete with the team

1. **Review the proposed labels with David.** Open
   [the CSV](../eval/test_set.csv) and
   [the routing policy](../eval/README.md#routing-and-proposed-label-policy).
   Review every row, focusing on `cb_014` (pillow causing neck pain), `cb_012`
   (water plus chest tightness), `cb_020` (two non-clinical departments), `cb_018`
   (NPO), and the translations in `cb_016`/`cb_017`. Ask for David's final urgency
   rules. Until he confirms otherwise, the proposed pain and uncertain cases go
   to a nurse at high priority.
2. **Get explicit agreement on the gates.** Confirm zero urgent non-nurse routes,
   zero nurse-required routing failures, at least 90% category-plus-priority
   accuracy (18/20 on this revision), and valid, consistent final tickets. Confirm
   that mixed clinical `cb_012` belongs in the urgent denominator and that all 20
   rows, including Spanish, remain in the overall denominator. The separate
   Spanish probes do not authorize a multilingual launch.
3. **Record the actual decision below.** Enter David's decision, date, final
   urgency-rule reference and agreed exceptions. Update the CSV and target
   definitions if needed, retaining stable case IDs. If a boundary remains
   disputed, leave sign-off pending. Never mark agreement based only on the
   suggested targets in the plan.
4. **Validate any edits locally.** From a terminal, run:

   ```sh
   cd "/Users/ketan/Desktop/Ting Ting"
   git switch ketan
   python3 eval/validate_test_set.py
   git diff --check
   ```

   Expected for the current revision: PASS, 20 cases, 10 urgent-tagged and 12
   nurse-required. There are no Python package installs, AWS keys or Bedrock
   credentials needed for this Phase 0 check. If counts or labels change, update
   the coverage and gate denominators in `eval/README.md` before committing.
5. **Share the handoff with Chaitanya.** Send the `ketan` branch and
   `eval/README.md`, after the label review. Ask him to use only each row's `text`
   and `language` as classifier input and to provide the callable classifier or
   `/classify` endpoint, agreed output schema, timeout and confidence policy for
   Phase 1. Expected labels and notes are for evaluation, not model input.
6. **Commit any review changes and push them.** Only run the commit step if files
   changed during review:

   ```sh
   git add eval/test_set.csv eval/README.md docs/ketan_phase0.md
   git commit -m "Record Phase 0 safety review and agreed labels"
   git push origin ketan
   ```

7. **Request teammate review before merging.** On GitHub, open the repository,
   choose Pull requests → New pull request, set base to `main` and compare to
   `ketan`, then review the changed files. Use the title
   `Add Ketan's Phase 0 test set and safety targets`, summarize the CSV, coverage
   and validation, and accurately state whether David's sign-off is still pending.
   Ask one teammate to review before merging, following the team plan. A branch
   push alone does not merge into `main`.

Suggested message for Ketan to send to David (prepared, not sent):

> My Phase 0 branch has 20 synthetic cases and proposed safety gates. Can you
> review the labels, especially pillow-related neck pain, mixed requests and NPO?
> Proposed gates: zero urgent cases routed away from a nurse; all nurse-required
> cases nurse/high with escalation; at least 90% exact category+priority accuracy;
> valid, consistent final tickets. Please confirm or send changes and your final
> urgency rules so I can record the agreement.

## Decision record — fill only after confirmation

- Status: **Pending David's review**
- Ketan's dataset review: pending
- David's decision: pending
- Review date: pending
- Agreed urgency-rules file/link: pending
- Pillow/neck-pain label (`cb_014`): proposed `urgent_clinical/high`; pending
- Mixed-request labels (`cb_012`, `cb_020`): proposed `unclear/high`; pending
- Spanish labels/translations: pending review
- Safety and accuracy gates: proposed as linked above; pending
- Exceptions or changes: none agreed yet

## Shared setup, if not already done

The team-wide exit criteria also require repo access, AWS Workshop Studio and
Kiro logins, plus the team's API/schema agreement. These are not substitutes for
the three Ketan deliverables above.

- **GitHub:** the requested branch is `ketan`. If GitHub denies a later push,
  accept the repository invitation and ask Chaitya to confirm your account has
  write access. Authenticate using your own GitHub account; do not paste tokens
  into the repository or chat.
- **AWS:** use the event's Workshop Studio invitation and Chaitya's region/model
  instructions. Ask the event AWS team if the invitation or Bedrock access is
  blocked. No AWS access is needed to validate this CSV.
- **Kiro:** follow the team plan's student setup using your Rutgers email and
  the event/team's verification instructions. Chaitya owns setup assistance.
- **Contract:** confirm the final category/schema/API and David's urgency-rule
  files when Chaitya publishes them. This initial repository contains the task
  plan only, so draft contract assumptions are explicitly documented in the eval
  README and must be reconciled with the final files.

## Phase 1 handoff, not completed in Phase 0

Once Chaitanya supplies a classifier and David confirms labels, implement the
scorer, grow the dataset, review failures, and inject timeout/bad-JSON/empty-input
failures. Record real results against a dataset and classifier revision. No
accuracy percentage, fallback-test pass or model safety certification has been
produced by this Phase 0 work.
