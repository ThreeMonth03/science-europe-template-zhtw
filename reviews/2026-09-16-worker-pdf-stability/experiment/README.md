# Font lifetime diagnostic — not a deployed worker or template release

The pinned DSW worker includes WeasyPrint 68.1, Python 3.13.13 and Pango 1.56.4.
Its sources contain two ownership defects subsequently fixed upstream:

- [HarfBuzz face ownership, #2799](https://github.com/Kozea/WeasyPrint/pull/2799):
  backport only [36b599168ed7007384f4187c479b25b2b229370a](https://github.com/Kozea/WeasyPrint/commit/36b599168ed7007384f4187c479b25b2b229370a),
  not the optional font lookup refactor.
- [Fontconfig double unref, #2843](https://github.com/Kozea/WeasyPrint/issues/2843):
  backport [98778130c92a4f1a70363b4e9243e098fd0acd5e](https://github.com/Kozea/WeasyPrint/commit/98778130c92a4f1a70363b4e9243e098fd0acd5e).

These are plausible causes, **not an established diagnosis of our previous exit
139**. Both original and patched workers passed our bounded probes. The failed
worker's old stack trace is unavailable; its state said `OOMKilled=false`.

`patch_fonts.py` checks both full original file hashes and unique replacement
anchors before writing anything. It makes exactly the ownership changes above;
no dependency update or layout algorithm change. The upstream BSD license is
retained alongside the patch. The installed WeasyPrint version still reports
68.1, so record image/source hashes, not just `pip freeze`.

Build from the repo root. The Dockerfile-specific allowlist sends only two patch
scripts as context; it excludes outputs, private configs and other repository
files. The stock digest is unchanged and the prior tables-only image is retained.

```sh
docker build -f experiments/worker-pdf-stability/Dockerfile \
  -t science-europe-pilot-worker:4.30-font-lifetime-experiment .
```

Run `scripts/probe_worker_pdf_lifecycle.py --help`. Each probe uses a named,
no-network, read-only container, read-only source mounts, temporary cache,
disabled core dumps and `faulthandler`. No keyring, host home, database, S3 or
production configuration is mounted. A bounded timeout kills only its named
probe; stdout/stderr and exit state are saved before removing the stopped
container. Nonzero results exit nonzero; they must not be discarded.

- `--probe render`: calls the actual installed DSW `WeasyPrintStep` repeatedly
  in one Python process. Inputs are frozen **HTML exports**, not captured native
  PDF-entry HTML; PDF-only template classes are absent. Page counts can therefore
  differ from accepted native 0.3.25 samples. Do not replace those samples.
- `--probe font-lifetime --cases PilotTC.ttf`: adapts the upstream #2799 lifetime
  regression to our bundled font. It intentionally releases original Pango owners
  before subsetting. This is not a reconstruction of the original queue incident.
- `--gc after-each`: forces collection between iterations; `natural` does not.
- `--save-all`: needed for `compare_worker_replays.py`, which compares all page
  words/coordinates, dimensions, URL annotations, font listing and 96 dpi pixels.

The first two historic probes had unwritable cache warnings (retained). Later
baseline and patched probes both set `XDG_CACHE_HOME=/tmp/cache`, and neither
emitted stderr. Compare matched runs, not unlike cache conditions.

## Adoption and upgrade boundary

This image is **not selected by any Compose override**. The native preparation
script rejects its font sources instead of calling it a tables-only experiment.
Before adoption: add an explicitly named runtime variant, replay the complete
native HTML/PDF/DOCX queue using identical packages, retain faulthandler logs and
longer-run evidence, then restore the local stock worker. Do not infer production
or Microsoft Word acceptance from these probes.

Do not make this a permanent fork of WeasyPrint. On an upstream worker upgrade,
review dependency/source changes and retire patches already incorporated; a
changed hash must fail, not be silently accepted. Test engine upgrades separately
from template and translation edits. This backport is not a security support
claim for 68.1, and a later full dependency/security upgrade still needs review.
