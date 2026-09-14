"""Recover only the existing synthetic pilot's missing bind-mounted config.

Does not start/recreate services or change their databases. Reads the existing
pilot DB/object-store credentials in memory; never prints them or uses keyring.
The generated directory is ignored, private, and outside /tmp cleanup.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote
import yaml

ROOT = Path(__file__).resolve().parents[1]


def inspect(name):
    result = json.loads(subprocess.check_output(['docker', 'inspect', 'science-europe-pilot-' + name + '-1'], text=True))[0]
    assert result['Config']['Labels']['com.docker.compose.project'] == 'science-europe-pilot'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tooling', type=Path, required=True)
    args = parser.parse_args()
    # Only already-existing containers and the local CI config are in scope.
    postgres, minio, server = (inspect(name) for name in ('postgres', 'minio', 'server'))
    assert server['HostConfig']['PortBindings']['3000/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '13300'}]
    pg = dict(value.split('=', 1) for value in postgres['Config']['Env'])
    s3 = dict(value.split('=', 1) for value in minio['Config']['Env'])
    port = minio['HostConfig']['PortBindings']['9000/tcp'][0]['HostPort']
    config = yaml.safe_load((args.tooling / '.github/dsw/config/application.yml').read_text())
    config['database']['connectionString'] = 'postgresql://' + quote(pg['POSTGRES_USER'], safe='') + ':' + quote(pg['POSTGRES_PASSWORD'], safe='') + '@postgres:5432/' + quote(pg['POSTGRES_DB'], safe='')
    config['s3'].update(url='http://host.docker.internal:' + port, username=s3['MINIO_ROOT_USER'], password=s3['MINIO_ROOT_PASSWORD'])
    config['mail']['enabled'] = False
    output = Path(tempfile.mkdtemp(prefix='pilot-runtime-', dir=ROOT / 'outputs'))
    os.chmod(output, 0o700)
    (output / 'config').mkdir()
    target = output / 'config/application.yml'
    target.write_text(yaml.safe_dump(config))
    # The container's user can read the bind-mounted file; host parent is 0700.
    os.chmod(target, 0o644)
    shutil.copyfile(args.tooling / '.github/dsw/docker-compose.yml', output / 'docker-compose.yml')
    print(output)


if __name__ == '__main__': main()
