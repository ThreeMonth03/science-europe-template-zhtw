import argparse
import json
from pathlib import Path
from submission_preview_integration import check


def main():
    p = argparse.ArgumentParser(description='Verify paired 0.3.44 packages and exact historical projection.')
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    a = p.parse_args(); result = check(a.build.resolve(), a.english.resolve(), a.preview)
    with (a.build / 'submission-preview-integration.json').open('x') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
