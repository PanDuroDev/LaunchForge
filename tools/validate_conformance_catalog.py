#!/usr/bin/env python3
"""Validate the Phase 6 conformance catalog without running product tests.

The validator checks catalog metadata only. It does not execute Launcher
Studio, Runtime, renderer, migration, packaging, or security behavior.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(
    r"^(LF-COMPAT|LF-MIG|LF-CAP|LF-PARITY|LF-SEC|LF-PKG|LF-PERF|LF-OPS)-[0-9]{3}$"
)
DEPENDENCY_PATTERN = re.compile(r"^phase[0-5]:[a-z0-9]+(?:-[a-z0-9]+)*$")
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
ALLOWED_CATALOG_STATUSES = {"planning", "active", "retired"}
ALLOWED_LIFECYCLES = {"planned", "implemented", "retired"}
REQUIRED_CATALOG_FIELDS = {
    "catalog_version",
    "catalog_status",
    "protocol",
    "contract_dependency_note",
    "dependency_registry",
    "cases",
}
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
    """Return whether value is a non-empty string after whitespace trimming."""
    return isinstance(value, str) and bool(value.strip())


def validate_catalog(payload: Any) -> list[str]:
    """Return all catalog structure errors; an empty list means it is valid.

    This validates metadata and cross-references only. It makes no claim that
    a planned case has been executed against LaunchForge product behavior.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["catalog root must be a JSON object"]

    missing_catalog_fields = sorted(REQUIRED_CATALOG_FIELDS - payload.keys())
    unknown_catalog_fields = sorted(payload.keys() - REQUIRED_CATALOG_FIELDS)
    if missing_catalog_fields:
        errors.append(
            "catalog is missing fields: " + ", ".join(missing_catalog_fields)
        )
    if unknown_catalog_fields:
        errors.append(
            "catalog has unknown fields: " + ", ".join(unknown_catalog_fields)
        )

    if type(payload.get("catalog_version")) is not int or payload.get("catalog_version") != 1:
        errors.append("catalog_version must be integer 1")

    catalog_status = payload.get("catalog_status")
    if (
        not isinstance(catalog_status, str)
        or catalog_status not in ALLOWED_CATALOG_STATUSES
    ):
        errors.append(
            "catalog_status must be one of: "
            + ", ".join(sorted(ALLOWED_CATALOG_STATUSES))
        )

    if not _non_empty_string(payload.get("protocol")):
        errors.append("protocol must be a non-empty string")
    if not _non_empty_string(payload.get("contract_dependency_note")):
        errors.append("contract_dependency_note must explain dependency labels")

    raw_registry = payload.get("dependency_registry")
    registered_dependencies: set[str] = set()
    if not isinstance(raw_registry, list) or not raw_registry:
        errors.append("dependency_registry must be a non-empty array")
    else:
        for index, dependency in enumerate(raw_registry):
            if not _non_empty_string(dependency):
                errors.append(
                    f"dependency_registry[{index}] must be a non-empty string"
                )
                continue
            if not DEPENDENCY_PATTERN.fullmatch(dependency):
                errors.append(
                    f"dependency_registry[{index}] has invalid format: {dependency}"
                )
                continue
            if dependency in registered_dependencies:
                errors.append(
                    f"dependency_registry contains duplicate: {dependency}"
                )
            registered_dependencies.add(dependency)

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        case_prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{case_prefix} must be an object")
            continue

        missing = sorted(REQUIRED_CASE_FIELDS - case.keys())
        unknown = sorted(case.keys() - REQUIRED_CASE_FIELDS)
        if missing:
            errors.append(f"{case_prefix} is missing fields: {', '.join(missing)}")
        if unknown:
            errors.append(f"{case_prefix} has unknown fields: {', '.join(unknown)}")

        test_id = case.get("test_id")
        if not _non_empty_string(test_id) or not ID_PATTERN.fullmatch(test_id):
            errors.append(
                f"{case_prefix}.test_id must match the documented LF test ID format"
            )
        else:
            if test_id in seen_ids:
                errors.append(f"{case_prefix}.test_id duplicates {test_id}")
            seen_ids.add(test_id)
            id_prefix = test_id.rsplit("-", 1)[0]
            expected_category = PREFIX_CATEGORY.get(id_prefix)
            if case.get("category") != expected_category:
                errors.append(
                    f"{case_prefix}.category must be {expected_category!r} for {test_id}"
                )

        for field in ("title", "scenario", "expected_behavior"):
            if not _non_empty_string(case.get(field)):
                errors.append(f"{case_prefix}.{field} must be a non-empty string")

        category = case.get("category")
        if (
            not isinstance(category, str)
            or category not in set(PREFIX_CATEGORY.values())
        ):
            errors.append(f"{case_prefix}.category is not recognized")

        for field in (
            "product_surfaces",
            "contract_dependencies",
            "evidence_required",
        ):
            values = case.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"{case_prefix}.{field} must be a non-empty array")
                continue
            if any(not _non_empty_string(item) for item in values):
                errors.append(
                    f"{case_prefix}.{field} must contain only non-empty strings"
                )
            valid_strings = [
                item for item in values if _non_empty_string(item)
            ]
            if len(valid_strings) != len(set(valid_strings)):
                errors.append(f"{case_prefix}.{field} must not contain duplicates")

        surfaces = case.get("product_surfaces")
        if isinstance(surfaces, list):
            unknown_surfaces = sorted(
                item
                for item in surfaces
                if _non_empty_string(item) and item not in ALLOWED_SURFACES
            )
            if unknown_surfaces:
                errors.append(
                    f"{case_prefix}.product_surfaces has unknown values: "
                    + ", ".join(unknown_surfaces)
                )

        dependencies = case.get("contract_dependencies")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not _non_empty_string(dependency):
                    continue
                if not DEPENDENCY_PATTERN.fullmatch(dependency):
                    errors.append(
                        f"{case_prefix}.contract_dependencies has invalid format: "
                        f"{dependency}"
                    )
                elif dependency not in registered_dependencies:
                    errors.append(
                        f"{case_prefix}.contract_dependencies references "
                        f"unregistered dependency: {dependency}"
                    )

        if not isinstance(case.get("mandatory"), bool):
            errors.append(f"{case_prefix}.mandatory must be a boolean")

        lifecycle = case.get("lifecycle")
        if (
            not isinstance(lifecycle, str)
            or lifecycle not in ALLOWED_LIFECYCLES
        ):
            errors.append(
                f"{case_prefix}.lifecycle must be one of: "
                + ", ".join(sorted(ALLOWED_LIFECYCLES))
            )

    if not seen_ids:
        errors.append("catalog contains no valid test IDs")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run catalog validation and return a process exit status.

    Exit status 0 means the catalog structure is valid, 1 means validation
    errors were found, and 2 means the catalog could not be read or parsed.
    """
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
        "(structure only; product tests were not run)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
