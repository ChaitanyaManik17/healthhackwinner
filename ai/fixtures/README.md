# Phase 0 phrase inputs

`provisional_phrases.csv` contains 20 synthetic examples prepared from the team plan. They are **not David's supplied phrases**, not approved labels, and not evidence that the model passes a safety target. The Spanish example uses the language label `es` and must go to the nurse in the English-only MVP.

David's exact list is still needed. Save it locally as `david_phrases.csv` with the same six columns (`id,text,language,expected_category,expected_priority,note`), and confirm that it contains only synthetic data. The file is ignored by Git so unreviewed inputs are not committed accidentally. After the team reviews it, Ketan owns the canonical set in `eval/test_set.csv`.

For an English-only MVP, non-English input is `unclear` / `high` / `nurse`. Multilingual routing requires separate approval and safety evaluation.
