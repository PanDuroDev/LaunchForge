from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.validate_conformance_catalog import validate_catalog


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "conformance" / "phase6-catalog.json"


def minimal_case(**overrides):
    """Build one small valid case, applying requested field overrides."""
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
    """Build a valid one-case catalog with a registry for its dependencies."""
    selected_case = case if case is not None else minimal_case()
    return {
        "catalog_version": 1,
        "catalog_status": "planning",
        "protocol": "docs/phase6/CONFORMANCE_PLAN.md",
        "contract_dependency_note": "Labels only; not approved API names.",
        "dependency_registry": sorted(set(selected_case["contract_dependencies"])),
        "cases": [selected_case],
    }


class ConformanceCatalogTests(unittest.TestCase):
    """Exercise the catalog validator using the committed catalog and bad fixtures."""

    def setUp(self):
        """Load the committed catalog for repository-level validation tests."""
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_repository_catalog_is_structurally_valid(self):
        """Accept the committed catalog when all fields and references are valid."""
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_repository_catalog_contains_all_protocol_families(self):
        """Ensure every conformance family in the protocol has catalog cases."""
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

    def test_catalog_tracks_uuid_and_application_icon_contract_edges(self):
        """Keep current Phase 0 schema-consistency gaps represented as planned cases."""
        cases = {case["test_id"]: case for case in self.catalog["cases"]}
        uuid_case = cases["LF-COMPAT-007"]
        icon_case = cases["LF-COMPAT-008"]

        self.assertEqual(uuid_case["category"], "project-format")
        self.assertEqual(uuid_case["lifecycle"], "planned")
        self.assertIn("phase0:project-format", uuid_case["contract_dependencies"])
        self.assertIn("lowercase UUIDv4", uuid_case["expected_behavior"])
        self.assertIn("reject uppercase spellings", uuid_case["expected_behavior"])

        self.assertEqual(icon_case["category"], "project-format")
        self.assertEqual(icon_case["lifecycle"], "planned")
        self.assertIn("phase0:filesystem-security-policy", icon_case["contract_dependencies"])
        self.assertIn("packaged resource bytes", icon_case["expected_behavior"])

    def test_phase3_data_binding_and_network_egress_cases_are_planned(self):
        """Keep data mapping and host egress requirements explicit before integration."""
        cases = {case["test_id"]: case for case in self.catalog["cases"]}
        mapping = cases["LF-CAP-006"]
        egress = cases["LF-SEC-006"]

        self.assertEqual(mapping["category"], "capability")
        self.assertEqual(mapping["lifecycle"], "planned")
        self.assertIn("phase3:data-binding-contract", mapping["contract_dependencies"])
        self.assertIn("RFC 6901", mapping["scenario"])
        self.assertIn("fail closed", mapping["expected_behavior"])

        self.assertEqual(egress["category"], "security")
        self.assertEqual(egress["lifecycle"], "planned")
        self.assertIn("phase3:network-egress-policy", egress["contract_dependencies"])
        self.assertIn("DNS-rebinding", egress["scenario"])
        self.assertIn("at connection time", egress["expected_behavior"])

    def test_portable_package_preflight_case_is_planned(self):
        """Keep the Windows package verifier requirement in the planned catalog."""
        cases = {case["test_id"]: case for case in self.catalog["cases"]}
        package = cases["LF-PKG-006"]

        self.assertEqual(package["category"], "packaging")
        self.assertEqual(package["lifecycle"], "planned")
        self.assertIn("phase5:package-contract", package["contract_dependencies"])
        self.assertIn("hostile archive entries", package["scenario"])
        self.assertIn("standard non-elevated Windows user", package["expected_behavior"])
        self.assertIn("separate fresh-user clean-VM acceptance report", package["evidence_required"])

    def test_dependency_registry_matches_case_references(self):
        """Require a unique registry containing every and only referenced dependency."""
        referenced = {
            dependency
            for case in self.catalog["cases"]
            for dependency in case["contract_dependencies"]
        }
        registry = self.catalog["dependency_registry"]
        self.assertEqual(len(registry), len(set(registry)))
        self.assertEqual(set(registry), referenced)

    def test_duplicate_test_ids_are_rejected(self):
        """Reject two catalog entries that use the same stable test ID."""
        catalog = minimal_catalog()
        catalog["cases"].append(copy.deepcopy(catalog["cases"][0]))
        errors = validate_catalog(catalog)
        self.assertTrue(any("duplicates LF-COMPAT-999" in error for error in errors))

    def test_category_must_match_test_id_prefix(self):
        """Reject category metadata that disagrees with the stable test ID prefix."""
        errors = validate_catalog(minimal_catalog(minimal_case(category="security")))
        self.assertTrue(any("category must be 'project-format'" in error for error in errors))

    def test_contract_dependencies_cannot_be_empty(self):
        """Require at least one explicit prerequisite-area label per case."""
        errors = validate_catalog(
            minimal_catalog(minimal_case(contract_dependencies=[]))
        )
        self.assertTrue(
            any("contract_dependencies must be a non-empty array" in error for error in errors)
        )

    def test_unknown_product_surface_is_rejected(self):
        """Reject a surface not defined by the protocol."""
        errors = validate_catalog(
            minimal_catalog(minimal_case(product_surfaces=["browser"]))
        )
        self.assertTrue(any("unknown values: browser" in error for error in errors))

    def test_mandatory_must_be_a_boolean(self):
        """Reject string and numeric substitutes for the mandatory flag."""
        errors = validate_catalog(minimal_catalog(minimal_case(mandatory="true")))
        self.assertTrue(any("mandatory must be a boolean" in error for error in errors))

    def test_boolean_is_not_accepted_as_catalog_version_integer(self):
        """Treat booleans as a different JSON type from the required version integer."""
        catalog = minimal_catalog()
        catalog["catalog_version"] = True
        errors = validate_catalog(catalog)
        self.assertTrue(any("catalog_version must be integer 1" in error for error in errors))

    def test_unregistered_dependency_is_rejected(self):
        """Reject a dependency reference that is missing from the canonical registry."""
        catalog = minimal_catalog(
            minimal_case(contract_dependencies=["phase2:asset-layout-contracts"])
        )
        catalog["dependency_registry"] = ["phase0:project-format"]
        errors = validate_catalog(catalog)
        self.assertTrue(any("unregistered dependency" in error for error in errors))

    def test_malformed_dependency_label_is_rejected(self):
        """Reject dependency labels that do not follow the canonical identifier grammar."""
        catalog = minimal_catalog(
            minimal_case(contract_dependencies=["phase7:Project Format"])
        )
        errors = validate_catalog(catalog)
        self.assertTrue(any("has invalid format" in error for error in errors))

    def test_unknown_catalog_and_case_fields_are_rejected(self):
        """Reject misspelled or unreviewed fields at both catalog levels."""
        catalog = minimal_catalog()
        catalog["unexpected"] = "value"
        catalog["cases"][0]["unexpected"] = "value"
        errors = validate_catalog(catalog)
        self.assertTrue(any("catalog has unknown fields" in error for error in errors))
        self.assertTrue(any("cases[0] has unknown fields" in error for error in errors))

    def test_non_object_root_is_reported(self):
        """Return a useful validation error when the JSON root is not an object."""
        self.assertEqual(validate_catalog([]), ["catalog root must be a JSON object"])


if __name__ == "__main__":
    unittest.main()
