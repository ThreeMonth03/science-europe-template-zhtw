# Translation Workspace

This folder is the sentence-preserving workspace generated from the
compact DSW template.

- Edit `src/**/*.j2` in place.
- Generated `__tr_block_####` comment markers keep whole headings,
  paragraphs, and list items together so later string extraction can work
  on complete units without changing Jinja scope.
- Run `make compact-template` to rebuild a DSW-uploadable template.
- Do not edit `.transform/manifest.json` manually.

The original upstream README is preserved in `UPSTREAM-README.md`.
