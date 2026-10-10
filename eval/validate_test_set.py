#!/usr/bin/env python3
"""Validate the Phase 0 CSV and coverage; this does not evaluate a classifier."""

import argparse
import csv
from collections import Counter
from pathlib import Path
import re
import sys


COLUMNS = [
    "id", "text", "language", "expected_category", "expected_priority", "note",
]
PRIORITIES = {
    "housekeeping": "normal",
    "food": "normal",
    "tech": "low",
    "urgent_clinical": "high",
    "unclear": "high",
}
REQUIRED_TAGS = {
    "mixed", "vague", "clinical_wording", "device_clinical", "spanish", "npo",
    "prompt_injection",
}
NURSE_CATEGORIES = {"urgent_clinical", "unclear"}


def validate(csv_path):
    errors = []
    ids = set()
    categories = Counter()
    languages = Counter()
    coverage = Counter()
    urgent_count = 0

    try:
        with csv_path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != COLUMNS:
                return [f"Header must be exactly: {','.join(COLUMNS)}"], None
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"Cannot read CSV: {exc}"], None

    if len(rows) < 20:
        errors.append(f"At least 20 rows are required; found {len(rows)}.")

    for index, row in enumerate(rows, start=2):
        label = f"Record {index} ({row.get('id') or 'missing id'})"
        if None in row or any(row.get(column) is None for column in COLUMNS):
            errors.append(f"{label}: expected exactly six fields.")
            continue

        for column in COLUMNS:
            if not row[column].strip():
                errors.append(f"{label}: {column} must not be empty.")
            elif row[column] != row[column].strip():
                errors.append(f"{label}: {column} has leading/trailing whitespace.")

        case_id = row["id"]
        if not re.fullmatch(r"cb_\d{3,}", case_id):
            errors.append(f"{label}: id must look like cb_001.")
        if case_id in ids:
            errors.append(f"{label}: duplicate id.")
        ids.add(case_id)

        category = row["expected_category"]
        if category not in PRIORITIES:
            errors.append(f"{label}: unknown category {category!r}.")
        elif row["expected_priority"] != PRIORITIES[category]:
            errors.append(
                f"{label}: {category} requires priority {PRIORITIES[category]!r}."
            )
        categories[category] += 1

        language = row["language"]
        if language not in {"en", "es"}:
            errors.append(f"{label}: Phase 0 language must be en or es.")
        languages[language] += 1

        tags = set(re.findall(r"\[([a-z_]+)\]", row["note"]))
        coverage.update(tags)
        if "spanish" in tags and language != "es":
            errors.append(f"{label}: [spanish] requires language es.")
        if language == "es" and "spanish" not in tags:
            errors.append(f"{label}: Spanish cases require the [spanish] tag.")
        if "urgent" in tags:
            urgent_count += 1
            if category not in NURSE_CATEGORIES:
                errors.append(f"{label}: [urgent] must require nurse routing.")
        if category == "urgent_clinical" and "urgent" not in tags:
            errors.append(f"{label}: urgent_clinical requires the [urgent] tag.")
        if tags & {"mixed", "vague"} and category != "unclear":
            errors.append(f"{label}: mixed/vague cases must be unclear per the plan.")

    for category in PRIORITIES:
        if not categories[category]:
            errors.append(f"Missing category coverage: {category}.")
    for tag in sorted(REQUIRED_TAGS - coverage.keys()):
        errors.append(f"Missing hard-case coverage tag: [{tag}].")
    for language in ("en", "es"):
        if not languages[language]:
            errors.append(f"Missing language coverage: {language}.")
    if not urgent_count:
        errors.append("At least one [urgent] case is required.")

    summary = {
        "rows": len(rows),
        "categories": categories,
        "languages": languages,
        "urgent": urgent_count,
        "nurse_required": sum(categories[name] for name in NURSE_CATEGORIES),
    }
    return errors, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path", nargs="?", type=Path,
        default=Path(__file__).resolve().with_name("test_set.csv"),
        help="CSV to validate (default: test_set.csv next to this script)",
    )
    args = parser.parse_args()
    errors, summary = validate(args.csv_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {summary['rows']} synthetic cases; CSV and coverage checks passed.")
    print("Categories: " + ", ".join(
        f"{name}={summary['categories'][name]}" for name in PRIORITIES
    ))
    print("Languages: " + ", ".join(
        f"{name}={count}" for name, count in sorted(summary["languages"].items())
    ))
    print(f"Urgent-tagged cases: {summary['urgent']}")
    print(f"Nurse-required cases: {summary['nurse_required']}")
    print("Classifier accuracy and safety targets have NOT been evaluated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
