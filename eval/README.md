# eval/ — Test set and scoring (owner: Ketan)

`test_set.csv` columns: `id,text,language,expected_category,expected_priority,note`.
Categories: housekeeping, food, tech, urgent_clinical, unclear. Priorities: low, normal, high.
Key metric: **urgent requests routed to a non-nurse department = 0**. Synthetic phrases only.
