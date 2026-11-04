#!/usr/bin/env python3
"""Validate the structure of the Phase 6 conformance case catalog.

This validates catalog metadata only. It does not execute product conformance tests
or imply that any project/Runtime/renderer contract has been approved.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^(LF-COMPAT|LF-MIG|LF-CAP|LF-PARITY|LF-SEC|LF-PKG|LF-PERF|LF-OPS)-[0-9]{3}$")
PREFIX_CATEGORY = {
    "LF-COMPAT": "project-format",
    "LF-MIG": "migration",
    "LF-CAP": "capability",
    "LF-PARITY": "parity",
    "LF-SEC": "security",
    "LF-PKG": "packaging",
    "LF-PERF": "performance",
    "LF-OPS": "operations",
}
ALLOWED_SURFACES = {"studio", "exported_launcher"}
ALLOWED_LIFECYCLES = {"planned", "implemented", "retired"}
REQUIRED_CASE_FIELDS = {
    "test_id",
    "category",
    "title",
    "scenario",
    "expected_behavior",
    "product_surfaces",
    "contract_dependencies",
    "evidence_required",
    "mandatory",
    "lifecycle",
}


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_catalog(payload: Any) -> list[str]:
    """Return all catalog-structure errors; an empty list means structurally valid."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["catalog root must be a JSON object"]

    if payload.get("catalog_version") != 1:
        errors.append("catalog_version must be integer 1")
    if payload.get("catalog_status") not in {"planning", "active", "retired"}:
        errors.append("catalog_status must be planning, active, or retired")
    if not _non_empty_string(payload.get("protocol")):
        errors.append("protocol must be a non-empty string")
    if not _non_empty_string(payload.get("contract_dependency_note")):
        errors.append("contract_dependency_note must explain dependency labels")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue

        missing = sorted(REQUIRED_CASE_FIELDS - case.keys())
        if missing:
            errors.append(f"{prefix} is missing fields: {', '.join(missing)}")

        test_id = case.get("test_id")
        if not _non_empty_string(test_id) or not ID_PATTERN.fullmatch(test_id):
            errors.append(f"{prefix}.test_id must match the documented LF test ID format")
        else:
            if test_id in seen_ids:
                errors.append(f"{prefix}.test_id duplicates {test_id}")
            seen_ids.add(test_id)
            id_prefix = test_id.rsplit("-", 1)[0]
            expected_category = PREFIX_CATEGORY.get(id_prefix)
            if case.get("category") != expected_category:
                errors.append(
                    f"{prefix}.category must be {expected_category!r} for {test_id}"
                )

        for field in ("title", "scenario", "expected_behavior"):
            if not _non_empty_string(case.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")

        category = case.get("category")
        if category not in set(PREFIX_CATEGORY.values()):
            errors.append(f"{prefix}.category is not recognized")

        for field in ("product_surfaces", "contract_dependencies", "evidence_required"):
            values = case.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{prefix}.{field} must be a non-empty array")
                continue
            if any(not _non_empty_string(item) for item in values):
                errors.append(f"{prefix}.{field} must contain only non-empty strings")
            if len(values) != len(set(item for item in values if _non_empty_string(item))):
                errors.append(f"{prefix}.{field} must not contain duplicates")

        surfaces = case.get("product_surfaces")
        if isinstance(surfaces, list):
            unknown = sorted(
                item for item in surfaces
                if _non_empty_string(item) and item not in ALLOWED_SURFACES
            )
            if unknown:
                errors.append(f"{prefix}.product_surfaces has unknown values: {', '.join(unknown)}")

        if not isinstance(case.get("mandatory"), bool):
            errors.append(f"{prefix}.mandatory must be a boolean")

        if case.get("lifecycle") not in ALLOWED_LIFECYCLES:
            errors.append(
                f"{prefix}.lifecycle must be one of: {', '.join(sorted(ALLOWED_LIFECYCLES))}"
            )

    if not seen_ids:
        errors.append("catalog contains no valid test IDs")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=Path("conformance/phase6-catalog.json"),
        help="path to the conformance catalog (default: conformance/phase6-catalog.json)",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.catalog.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR: cannot read {args.catalog}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {args.catalog}: {exc}", file=sys.stderr)
        return 2

    errors = validate_catalog(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Catalog invalid: {len(errors)} error(s)", file=sys.stderr)
        return 1

    cases = payload["cases"]
    categories = sorted({case["category"] for case in cases})
    print(
        f"Catalog valid: {len(cases)} cases across {len(categories)} categories "
        f"(structure only; product tests were not run)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
