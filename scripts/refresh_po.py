"""Check current POT/PO keys; explicitly output a new review draft, never approval."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
from types import SimpleNamespace

import polib
from dsw.templating.pot import extract_catalog, render_pot_file

ROOT = Path(__file__).resolve().parents[1]
FORMAT = r'%%|%\(([^)]+)\)([-+#0 ]*\d*(?:\.\d+)?[diouxXeEfFgGcrsa])'


def parameters(text):
    if '%' in re.sub(FORMAT, '', text):
        raise ValueError('Unescaped percent in catalog text')
    return Counter((m[1], m[2]) for m in re.finditer(FORMAT, text) if m[1])


def keys(entries):
    result = [(e.msgctxt, e.msgid) for e in entries]
    if len(result) != len(set(result)):
        raise ValueError('Duplicate active catalog keys')
    for entry in entries:
        if entry.msgctxt == '' or '\x04' in (entry.msgctxt or '') + entry.msgid or entry.msgid_plural or entry.msgstr_plural:
            raise ValueError('Empty context, EOT or plural catalog key is unsupported')
        source_parameters = parameters(entry.msgid)
        if entry.msgstr.strip() and source_parameters != parameters(entry.msgstr):
            raise ValueError('Translation placeholder mismatch: ' + entry.msgid)
    return set(result)


def refresh(english, po_path=ROOT / 'locales/zh-Hant.po', output=None):
    english, po_path = Path(english).resolve(), Path(po_path).resolve()
    metadata = json.loads((english / 'template.json').read_text())
    if metadata.get('language') != 'en':
        raise ValueError('Extract from the shared English template only')
    coordinate = ':'.join(metadata[k] for k in ('organizationId', 'templateId', 'version'))
    files = [SimpleNamespace(file_name=p.relative_to(english).as_posix(), content=p.read_text())
             for p in (english / 'src').rglob('*') if p.suffix in {'.j2', '.jinja', '.jinja2', '.jnj'}]
    result = extract_catalog(files, project=coordinate, version=metadata['version'], language='en')
    if not files or result.failed_files:
        raise ValueError('Incomplete POT extraction: ' + ', '.join(result.failed_files))
    pot_bytes = render_pot_file(result)
    pot = polib.pofile(pot_bytes.decode('utf-8'))
    raw = po_path.read_bytes()
    original = polib.pofile(raw.decode('utf-8'))
    if original.metadata.get('Language') != 'zh-Hant':
        raise ValueError('PO Language must be zh-Hant')
    before, wanted = keys([e for e in original if not e.obsolete]), keys(pot)
    added, removed = wanted - before, before - wanted
    candidate = copy.deepcopy(original)
    if added or removed:
        retired = [e for e in candidate if e.obsolete]
        candidate[:] = [e for e in candidate if not e.obsolete]
        candidate.merge(pot)  # Exact keys only; never borrow an obsolete translation.
        candidate.extend(retired)
    live = [e for e in candidate if not e.obsolete]
    if keys(live) != wanted:
        raise ValueError('Merged active keys differ from the official POT')
    ordered = lambda pairs: sorted(pairs, key=lambda p: (p[0] is not None, p[0] or '', p[1]))
    report = dict(source=coordinate, accepted=False, added=ordered(added), removed=ordered(removed),
                  active_keys=len(wanted), fuzzy=sum('fuzzy' in e.flags for e in live),
                  untranslated=sum(not e.msgstr.strip() for e in live))
    report['needs_review'] = bool(added or removed or report['fuzzy'] or report['untranslated'])
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True)  # Refuse existing directories, files and symlinks.
        (output / 'template.pot').write_bytes(pot_bytes)
        (output / 'zh-Hant.review.po').write_bytes(str(candidate).encode('utf-8') if added or removed else raw)
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--po', type=Path, default=ROOT / 'locales/zh-Hant.po')
    parser.add_argument('--output', type=Path, help='New review directory; omit for a read-only check')
    args = parser.parse_args()
    report = refresh(args.english, args.po, args.output)
    print(json.dumps(report, ensure_ascii=False))
    if args.output is None and report['needs_review']:
        raise SystemExit(1)
