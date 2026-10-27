import unittest

from scope_engine import analyze_request, derive_title, local_analysis, normalize_analysis


class ScopeEngineTests(unittest.TestCase):
    def setUp(self):
        self.message = (
            "We need a website for a local bakery. It should show our menu and cake photos, "
            "let customers send custom cake enquiries, and work well on mobile phones. "
            "We already have a logo but need help preparing the content."
        )

    def test_derive_title(self):
        self.assertIn("We need a website", derive_title(self.message))

    def test_local_analysis_has_expected_sections(self):
        result = local_analysis(self.message, "Website", "", "")
        for key in ("title", "summary", "goals", "requirements", "deliverables", "questions", "risks", "boundaries", "acceptance_criteria", "client_summary", "suggested_next_step"):
            self.assertIn(key, result)
        self.assertGreater(len(result["questions"]), 0)
        self.assertGreater(len(result["requirements"]), 0)

    def test_normalization_fills_missing_lists(self):
        result = normalize_analysis({"title": "Test", "summary": "A clear summary."}, self.message)
        self.assertTrue(result["requirements"])
        self.assertTrue(result["questions"])
        self.assertTrue(result["client_summary"])

    def test_no_api_key_uses_local_rules(self):
        result, mode, warning = analyze_request(self.message, "Website", "", "", "")
        self.assertEqual(mode, "Local rules")
        self.assertIsNone(warning)
        self.assertIn("requirements", result)


if __name__ == "__main__":
    unittest.main()
