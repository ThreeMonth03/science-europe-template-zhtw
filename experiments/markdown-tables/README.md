# Local worker experiment; not a template release

The stock DSW 4.30 worker's `render_markdown` does not enable Python-Markdown
pipe tables. This image adds only the bundled `tables` extension, preserving
DSW's list/backslash preprocessor. No new Python dependency is installed.

Both the base image digest and the exact source-file hash are pinned. A changed
worker fails the patch: review and re-test it, never blindly reapply it.

Build locally:

```sh
docker build -t science-europe-pilot-worker:4.30-tables-experiment experiments/markdown-tables
```

Apply the override ONLY to the disposable `science-europe-pilot` Compose project,
after stock-worker baseline renders finish. Recreate ONLY its `docworker` service.
Never point these instructions at production. Restore the original Compose file
without the override and verify the original image before shutting the pilot down.

The historical Compose file interpolates database/storage environment variables
even for a worker-only operation. Its worker itself uses only a read-only mounted
configuration, not those environment values. If the original shell variables are
unavailable, non-secret interpolation placeholders may be used ONLY with the
explicit `up -d --no-deps docworker` command. Never reuse such an invocation for
the server, database, storage, or a whole-stack `up`. Do not regenerate or print
the existing service credentials just to recreate this one worker.

Compare identical English/Chinese package hashes and identical input fixture
hashes under the two workers. Store variant output separately with manifest status
`runtime-experiment`; do not stage it as a regular `candidate`. A successful
pipe-table render does not establish full Science Europe or visual acceptance.

The patch must be adopted upstream or maintained as an explicitly owned runtime
dependency if eventually deployed. It is not a Chinese translation workaround.
