"""Apply an explicitly reviewed source→translation list after a tree refresh.

Development-only migration, not an automatic build or runtime translation step.
Unmatched/new source sentences are never guessed or filled.
"""
import argparse
import json
from pathlib import Path

from dsw_document_template_tool._translation_tree.document import (
    TRANSLATION_SECTION_PATTERN,
    parse_sentence_text,
    parse_translation_document,
)
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    phrases = json.loads((ROOT / "docs/readability-phrases.json").read_text())
    tree = ROOT / "translation"
    changed, missing = 0, []
    for unit in load_tree_manifest(tree)["units"]:
        path = tree / unit["document_path"]
        source = parse_sentence_text(document_path=path, source_lang="en")
        current = parse_translation_document(document_path=path, source_lang="en", target_lang="zh_Hant")
        if source in phrases and current != phrases[source]:
            changed += 1
            if args.apply:
                document = path.read_text()
                match = TRANSLATION_SECTION_PATTERN.search(document)
                start, end = match.span("translation_text")
                path.write_text(document[:start] + phrases[source] + document[end:])
                current = phrases[source]
        if not current.strip():
            missing.append(source)
    print(json.dumps({"applied": args.apply, "changed": changed, "untranslated": missing}, ensure_ascii=False, indent=2))
    if missing and args.apply:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
