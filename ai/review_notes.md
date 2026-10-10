# Phase 0 phrase review notes

No live model review has been run. David's exact 20 phrases have not been supplied. The provisional examples in `fixtures/provisional_phrases.csv` have been checked against the proposed urgency rules by reading the phrases; model outputs, latency, failures, and human signoff remain pending.

The important questions for David are:

- Does all pain require the nurse, including "My pillow is hurting my neck"? The proposed rule says yes.
- Are all NPO, medication, and clinical equipment questions nurse requests? The proposed rule says yes.
- Does a mixed request use `unclear` or `urgent_clinical`? The proposed prompt uses `unclear` with nurse/high as in Section 3 of the team plan.
- Does a request spanning two different nonclinical departments go to the nurse? The proposed prompt does this to avoid silently losing part of a request.
- Is 0.80 an acceptable provisional confidence threshold? Model confidence is an uncalibrated estimate and does not establish clinical safety.

## How to record the actual review

Run the Bedrock probe successfully first. Run `ai.review_phrases` on David's synthetic CSV. Open the resulting JSON report and inspect every row's raw model output, validation result, final ticket, label comparison, and error. Add a human reviewer, review date, and commentary for each failure in this file or a separate reviewed copy. Fix the prompt, rerun, and keep the earlier reports for comparison.

Keep missed urgent routes, invalid outputs, and provider failures separate. A nurse fallback protects routing during an error but does not prove the model understood a phrase. The suggested team targets (zero urgent requests routed outside the nurse, at least 90% overall) remain proposals until David and Ketan agree them. Ketan owns the formal scoring script in Phase 1.
