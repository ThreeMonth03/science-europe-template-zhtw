import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import render
from cleanup_owned_runtime_templates import validate_render_report


class RenderTimeoutTests(unittest.TestCase):
    def test_queue_margin_is_passed_to_tool_and_recorded(self):
        self.assertEqual(render.RENDER_TIMEOUT_SECONDS, 600)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'model.km').write_text('{}')
            (root / 'events.json').write_text('[]')
            (root / 'english.zip').write_bytes(b'unit-test-package')
            recipe = root / 'fixture.json'
            recipe.write_text(json.dumps(dict(events_file='events.json', knowledge_model_package_id='model.km')))
            (root / 'renders').mkdir()
            argv = ['render.py', '--build', str(root), '--project', str(recipe), '--language', 'english', '--format', 'html', '--tooling', str(root)]
            with patch.object(sys, 'argv', argv), patch.object(render, 'render_project') as call, patch.object(render.socket, 'getaddrinfo'):
                render.main()
            self.assertEqual(call.call_args.kwargs['timeout_seconds'], 600)
            self.assertEqual(call.call_args.kwargs['poll_seconds'], 1)
            receipt = json.loads((root / 'renders/demo-english.html.fixture.json').read_text())
            self.assertEqual(receipt['timeout_seconds'], 600)
            self.assertEqual(len(receipt['runner_sha256']), 64)

    def test_failed_cleanup_is_opt_in_and_does_not_accept_running_or_mixed_batches(self):
        failed = dict(all_renders_succeeded=False, renders=[dict(rendered=True), dict(rendered=False)])
        with self.assertRaises(AssertionError):
            validate_render_report(failed, 2)
        validate_render_report(failed, 2, True)
        for rows in [[], [True], [False, True], [False, False]]:
            with self.assertRaises(AssertionError):
                validate_render_report(dict(all_renders_succeeded=False, renders=[dict(rendered=v) for v in rows]), 2, True)
        validate_render_report(dict(all_renders_succeeded=True, renders=[dict(rendered=True)]), 1)
