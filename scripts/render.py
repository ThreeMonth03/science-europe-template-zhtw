"""Render candidate ZIPs in the isolated local DSW, never the live service."""

import argparse
import hashlib
import json
import shutil
import socket
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

from dsw_document_template_tool.render_project import render_project

FORMATS = {
    "html": "a9293d08-59a4-4e6b-ae62-7a6a570b031c",
    "pdf": "68c26e34-5e77-4e15-9bf7-06ff92582257",
    "docx": "f4bd941a-dfbe-4226-a1fc-200fb5269311",
}

# The observed worker notification fallback itself waits up to 180 seconds.
# A 180-second client deadline can start project cleanup while that delayed job
# is finalizing (observed local deadlock). Allow queue delay plus conversion.
# This is a harness mitigation, not a fix for worker queue/transaction behavior.
RENDER_TIMEOUT_SECONDS = 600


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--language", choices=("english", "chinese"), required=True)
    parser.add_argument("--format", choices=tuple(FORMATS), required=True)
    parser.add_argument("--name", default="demo")
    parser.add_argument("--tooling", type=Path, required=True)
    parser.add_argument("--api-url", default="http://localhost:13300/wizard-api")
    args = parser.parse_args()
    if urlparse(args.api_url).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("This fixture runner only supports an isolated local DSW")
    # Alias affects this process only. Preserve the signed storage URL and Host.
    original_lookup = socket.getaddrinfo

    def local_storage_alias(host, *positional, **keywords):
        return original_lookup(
            "127.0.0.1" if host == "host.docker.internal" else host, *positional, **keywords
        )

    socket.getaddrinfo = local_storage_alias
    output = args.build.resolve() / "renders" / f"{args.name}-{args.language}.{args.format}"
    if output.exists():
        parser.error(f"Render exists; choose a new name: {output}")
    # DSW event UUIDs are database-wide identifiers, unlike reply/item paths.
    # Fresh transport IDs permit repeated runs without altering canonical facts.
    recipe = json.loads(args.project.read_text())
    event_path = args.project.parent / recipe["events_file"]
    events = json.loads(event_path.read_text())
    for event in events:
        event["uuid"] = str(uuid.uuid4())
    bundle = (args.project.parent / recipe["knowledge_model_package_id"]).resolve()
    with tempfile.TemporaryDirectory(prefix="dsw-pilot-fixture-") as temporary:
        fixture = Path(temporary)
        shutil.copyfile(bundle, fixture / "model.km")
        recipe["knowledge_model_package_id"] = "model.km"
        recipe["events_file"] = "events.json"
        (fixture / "events.json").write_text(json.dumps(events))
        (fixture / "project.json").write_text(json.dumps(recipe))
        render_project(
            project_uuid=None,
            project_ref=fixture / "project.json",
            template_dir=Path("."),
            template_package=args.build / f"{args.language}.zip",
            output_path=output,
            format_uuid=FORMATS[args.format],
            stage_id=None,
            api_url=args.api_url,
            api_key=None,
            email="albert.einstein@example.com",
            password="password",
            tdk_executable=str(args.tooling / ".venv/bin/dsw-tdk"),
            timeout_seconds=RENDER_TIMEOUT_SECONDS,
            poll_seconds=1,
            verify_ssl=True,
        )
    output.with_suffix(output.suffix + ".fixture.json").write_text(
        json.dumps(
            {
                "recipe_sha256": hashlib.sha256(args.project.read_bytes()).hexdigest(),
                "events_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
                "km_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                "package_sha256": hashlib.sha256(
                    (args.build / f"{args.language}.zip").read_bytes()
                ).hexdigest(),
                "transport_event_ids": [event["uuid"] for event in events],
                "timeout_seconds": RENDER_TIMEOUT_SECONDS,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"output": str(output), "format": args.format}))


if __name__ == "__main__":
    main()
