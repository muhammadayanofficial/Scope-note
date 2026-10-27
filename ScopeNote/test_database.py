import json
import tempfile
import unittest
from pathlib import Path

from database import delete_brief, get_brief, init_db, list_briefs, save_brief


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        init_db(self.db_path)
        self.analysis = {
            "title": "Bakery website",
            "summary": "Create a simple bakery website.",
            "goals": ["Show menu"],
            "requirements": ["Mobile responsive"],
            "deliverables": ["Website"],
            "questions": ["What is the deadline?"],
            "risks": [],
            "boundaries": [],
            "acceptance_criteria": [],
            "client_summary": "Please confirm this brief.",
            "suggested_next_step": "Confirm the scope.",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_get_brief(self):
        brief_id = save_brief(self.db_path, "Website", "Need a bakery website.", self.analysis, "Local rules")
        brief = get_brief(self.db_path, brief_id)
        self.assertEqual(brief["analysis"]["title"], "Bakery website")
        self.assertEqual(brief["source_text"], "Need a bakery website.")

    def test_list_and_delete(self):
        brief_id = save_brief(self.db_path, "Website", "Need a bakery website.", self.analysis, "Local rules")
        self.assertEqual(len(list_briefs(self.db_path)), 1)
        self.assertTrue(delete_brief(self.db_path, brief_id))
        self.assertEqual(len(list_briefs(self.db_path)), 0)
        self.assertFalse(delete_brief(self.db_path, brief_id))


if __name__ == "__main__":
    unittest.main()
