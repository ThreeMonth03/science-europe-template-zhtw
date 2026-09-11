import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_pilot import validate_archive_only


class PilotCaseTests(unittest.TestCase):
    def document(self):
        return BeautifulSoup('''<div id="q-how-data"><p data-fact-id="new-data" data-status="missing">Missing</p></div>
          <div id="q-store-backup"><p data-fact-id="during-project-archive" data-status="complete">Yes</p>
          <p data-fact-id="archive-frequent-backup-need" data-status="explicit-no">Not needed frequently</p></div>
          <div id="q-access-security"><p data-status="missing-output">Security details missing</p>
          <a href="#q-store-backup">See question 5</a></div>''', 'html.parser')

    def test_archive_only_does_not_require_unrelated_datasets_or_budget(self):
        validate_archive_only(self.document())

    def test_reference_cannot_replace_missing_security_marker(self):
        doc = self.document(); doc.select_one('#q-access-security [data-status]').decompose()
        with self.assertRaises(AssertionError): validate_archive_only(doc)
