"""Reversible storage allowance for this isolated synthetic run, not production.

DSW's worker applies abs(storage). Preserve the seeded negative sign and every
other tenant-limit field. No templates, objects, documents or volumes are erased.
"""
import argparse
import json
from pathlib import Path
import subprocess

TENANT = '00000000-0000-0000-0000-000000000000'
ORIGINAL = -1500000000
TEMPORARY = -1750000000
IMAGE = 'sha256:aadf2c0696f5ef357aa7a68da995137f0cf17bad0bf6e1f17de06ae5c769b302'


def sql(query):
    image = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}',
                                     'science-europe-pilot-postgres-1'], text=True).strip()
    assert image == IMAGE
    return subprocess.check_output(['docker', 'exec', 'science-europe-pilot-postgres-1', 'sh', '-c',
        'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"',
        'owned-entity-label-storage-budget', query], text=True).strip()


def state():
    return json.loads(sql("SELECT row_to_json(t) FROM tenant_limit_bundle t WHERE uuid='" + TENANT + "';"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['raise', 'restore']); p.add_argument('--receipt', type=Path, required=True)
    a = p.parse_args(); current = state()
    if a.action == 'raise':
        assert not a.receipt.exists() and current['storage'] == ORIGINAL
        assert sql('SELECT count(*) FROM document;') == '0', 'Do not change allowance during a render'
        report = dict(before=current, temporary_storage=TEMPORARY, production_touched=False,
                      data_deleted=False, restored=False, applied=False)
        with a.receipt.open('x') as stream: stream.write(json.dumps(report, indent=2) + '\n')
        old, new = ORIGINAL, TEMPORARY
    else:
        report = json.loads(a.receipt.read_text()); assert report['applied'] and not report['restored']
        expected = dict(report['before'], storage=TEMPORARY)
        assert current == expected, 'Other local limits changed; do not overwrite them'
        assert sql('SELECT count(*) FROM document;') == '0'
        old, new = TEMPORARY, ORIGINAL
    output = sql("UPDATE tenant_limit_bundle SET storage=" + str(new) + " WHERE uuid='" + TENANT
                 + "' AND storage=" + str(old) + ' RETURNING storage;')
    assert output.splitlines() == [str(new), 'UPDATE 1']
    actual = state(); assert actual == dict(current, storage=new)
    if a.action == 'raise': report.update(applied=True, during=actual)
    else: report.update(restored=True, after=actual)
    a.receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(action=a.action, storage=new, production_touched=False)))


if __name__ == '__main__': main()
