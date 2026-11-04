from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validate_conformance_catalog import validate_catalog


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "conformance" / "phase6-catalog.json"


def minimal_case(**overrides):
    case = {
        "test_id": "LF-COMPAT-999",
        "category": "project-format",
        "title": "Example project check",
        "scenario": "Open a contract fixture.",
        "expected_behavior": "Return a deterministic compatibility result.",
        "product_surfaces": ["studio"],
        "contract_dependencies": ["phase0:project-format"],
        "evidence_required": ["result report"],
        "mandatory": True,
        "lifecycle": "planned",
    }
    case.update(overrides)
    return case


def minimal_catalog(case=None):
    return {
        "catalog_version": 1,
        "catalog_status": "planning",
        "protocol": "docs/phase6/CONFORMANCE_PLAN.md",
        "contract_dependency_note": "Labels only; not approved API names.",
        "cases": [case or minimal_case()],
    }


class ConformanceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_repository_catalog_is_structurally_valid(self):
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_repository_catalog_contains_all_protocol_families(self):
        prefixes = {case["test_id"].rsplit("-", 1)[0] for case in self.catalog["cases"]}
        self.assertEqual(
            prefixes,
            {
                "LF-COMPAT",
                "LF-MIG",
                "LF-CAP",
                "LF-PARITY",
                "LF-SEC",
                "LF-PKG",
                "LF-PERF",
                "LF-OPS",
            },
        )

    def test_duplicate_test_ids_are_rejected(self):
        catalog = minimal_catalog()
        catalog["cases"].append(copy.deepcopy(catalog["cases"][0]))
        errors = validate_catalog(catalog)
        self.assertTrue(any("duplicates LF-COMPAT-999" in error for error in errors))

    def test_category_must_match_test_id_prefix(self):
        errors = validate_catalog(minimal_catalog(minimal_case(category="security")))
        self.assertTrue(any("category must be 'project-format'" in error for error in errors))

    def test_contract_dependencies_cannot_be_empty(self):
        errors = validate_catalog(minimal_catalog(minimal_case(contract_dependencies=[])))
        self.assertTrue(any("contract_dependencies must be a non-empty array" in error for error in errors))

    def test_unknown_product_surface_is_rejected(self):
        errors = validate_catalog(minimal_catalog(minimal_case(product_surfaces=["browser"])))
        self.assertTrue(any("unknown values: browser" in error for error in errors))

    def test_mandatory_must_be_a_boolean(self):
        errors = validate_catalog(minimal_catalog(minimal_case(mandatory="true")))
        self.assertTrue(any("mandatory must be a boolean" in error for error in errors))

    def test_boolean_is_not_accepted_as_catalog_version_integer(self):
        catalog = minimal_catalog()
        catalog["catalog_version"] = True
        errors = validate_catalog(catalog)
        self.assertTrue(any("catalog_version must be integer 1" in error for error in errors))

    def test_non_object_root_is_reported(self):
        self.assertEqual(validate_catalog([]), ["catalog root must be a JSON object"])


if __name__ == "__main__":
    unittest.main()
