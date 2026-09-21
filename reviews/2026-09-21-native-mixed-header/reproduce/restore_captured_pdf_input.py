"""Restore one captured PDF-entry HTML, validating fonts and the full original hash."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import restore_source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'font', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists(), 'Never overwrite a captured or restored input'
    receipt = json.loads(a.input.with_suffix('.json').read_text())
    font = a.font.read_bytes()
    digest = hashlib.sha256(font).hexdigest()
    assert set(receipt['fonts']) == {digest}, 'Wrong or missing public font asset'
    data = restore_source(a.input.read_bytes(), {digest: font})
    assert hashlib.sha256(data).hexdigest() == receipt['full_input_sha256']
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('xb') as target:
        target.write(data)
    print(a.output)


if __name__ == '__main__':
    main()
