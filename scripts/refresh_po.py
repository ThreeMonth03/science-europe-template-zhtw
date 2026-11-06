"""Review a locked English POT against the authoritative Traditional Chinese PO."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re

import polib
import yaml

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
        if not entry.msgid.strip():
            raise ValueError('Empty catalog message is unsupported')
        if entry.msgctxt == '' or '\x04' in (entry.msgctxt or '') + entry.msgid or entry.msgid_plural or entry.msgstr_plural:
            raise ValueError('Empty context, EOT or plural catalog key is unsupported')
        source_parameters = parameters(entry.msgid)
        if entry.msgstr.strip() and source_parameters != parameters(entry.msgstr):
            raise ValueError('Translation placeholder mismatch: ' + entry.msgid)
    return set(result)


def locked_pot(pot_path, pipeline_path):
    """Accept source-owner POT artifacts only when their provenance matches the lock."""
    config = yaml.safe_load(Path(pipeline_path).read_text(encoding='utf-8'))
    source = config.get('source') if isinstance(config, dict) else None
    if not isinstance(source, dict):
        raise ValueError('Pipeline source lock is missing')
    fields = ('organization_id', 'template_id', 'version')
    if any(not isinstance(source.get(field), str) or not source[field].strip() for field in fields):
        raise ValueError('Pipeline source coordinate is missing or malformed')
    coordinate = ':'.join(source[field] for field in fields)
    commit = source.get('commit')
    if not isinstance(commit, str) or re.fullmatch(r'[0-9a-f]{40}', commit) is None:
        raise ValueError('Pipeline source commit must be an exact 40-character Git commit')
    pot_bytes = Path(pot_path).read_bytes()
    try:
        pot = polib.pofile(pot_bytes.decode('utf-8'))
    except (OSError, UnicodeError) as error:
        raise ValueError('Malformed UTF-8 POT catalog') from error
    expected = {'Language': 'en', 'X-DSW-Template': coordinate, 'X-DSW-Source-Commit': commit}
    for header, value in expected.items():
        if pot.metadata.get(header) != value:
            raise ValueError(f'POT {header} must match the pipeline source lock: {value}')
    if not pot or any(entry.obsolete or entry.msgstr or entry.msgstr_plural for entry in pot):
        raise ValueError('POT must contain non-empty, untranslated active template entries only')
    keys(pot)
    return pot_bytes, pot, coordinate, commit


def refresh(pot_path, po_path=ROOT / 'locales/zh-Hant.po', output=None,
            pipeline_path=ROOT / 'pipeline.yml'):
    pot_bytes, pot, coordinate, commit = locked_pot(pot_path, pipeline_path)
    po_path = Path(po_path).resolve()
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
        raise ValueError('Merged active keys differ from the locked English POT')
    ordered = lambda pairs: sorted(pairs, key=lambda p: (p[0] is not None, p[0] or '', p[1]))
    report = dict(source=coordinate, source_commit=commit, accepted=False,
                  added=ordered(added), removed=ordered(removed),
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
    parser.add_argument('--pot', type=Path, required=True, help='English POT exported from the locked source commit')
    parser.add_argument('--po', type=Path, default=ROOT / 'locales/zh-Hant.po')
    parser.add_argument('--output', type=Path, help='New review directory; omit for a read-only check')
    args = parser.parse_args()
    report = refresh(args.pot, args.po, args.output)
    print(json.dumps(report, ensure_ascii=False))
    if args.output is None and report['needs_review']:
        raise SystemExit(1)
