# Shared Word-only short-table pipeline prototype

This extends the sealed `2026-09-21-empty-budget/after` packages without changing
the English source tree, translation tree, version, existing assets, or format
UUIDs. Both Word formats receive the same two language-independent files:

- `short-tables.lua`, after the existing filters: bound direct Q9 answer-detail
  tables to 2–4 rows, 2–4 columns, one simple paragraph per cell, at most 80
  weighted characters per cell and 500 total. Reject spans, captions, nested
  blocks, custom attributes, long ASCII tokens and adjacent tables. Only
  non-final rows receive the existing `Pilot Table Lead` paragraph style.
- `short-tables.xml.j2`, through DSW's existing `enrich-docx` step: consume exact
  generated XML comment markers, verify the expected serialization, and add
  direct `w:cantSplit` row properties. Remove markers without changing outside
  XML whitespace. The final row does not keep the following prose with it.

HTML/PDF/LaTeX/ODT paths are untouched. User-authored strings are never searched
to select a table. Authored HTML comments do not become OpenXML markers; escaped
lookalike text remains literal. This is template-owned conversion, not editing
downloaded Word files after delivery and not a new worker patch.

## Checks

`probe_markers.py` diagnoses raw marker serialization. `table_probe.py` runs 37
synthetic controls in the exact pinned image via `engine_runner.py`. The actual
EnrichDocxStep rewrite/repack method is used offline; only its app constructor
is bypassed in that harness. Twelve actual local-DSW API cases separately
exercise the complete constructor and pipeline. The no-op control requires
every uncompressed DOCX member, including core metadata, to remain identical.

`table_probe.xml_delta` independently projects row properties and non-final
paragraph styles back into the old XML. All other content, links, table widths,
headers, properties and blocks must be unchanged. `engine_preview.py` checks
long-row controls span multiple pages and full nonheader character counts match,
binding repeated header instances to actual tblHeader rows and page geometry.

`table_native.py` binds all twelve output pairs to exact package/fixture hashes,
checks HTML bytes and PDF geometry/pixels unchanged, eight Word no-op controls,
four exact short-table deltas, all authored paragraphs and links, preserved
historical page limits, continued long-paragraph flow, and complete 3×2 short
table geometry on one page. Word preview means LibreOffice, not MS Word QA.

Generate all native inputs before starting the preview script. The prototype
only accesses the isolated localhost pilot and public synthetic fixtures.
`table_collect.py` records both local runtime batches and their cleanup receipts;
validate a new archive before one-time sealing. Never rewrite an old seal.

## Upgrade boundary

The XML contract deliberately targets the observed Pandoc 3.8.3 serialization
and pinned DSW 4.30 worker. Unexpected marked XML fails conversion instead of
silently applying a broad replacement. A runtime upgrade needs the no-op,
37-case engine, native bilingual and long-table checks rerun first. Unmarked
documents are exact no-ops. Self-closing extra paragraphs were caught by a
negative test, the guard was strengthened, and native outputs were regenerated
from the updated package; the first guard's evidence is retained separately.

## Translation integration blocker

The native prototype packages contain an unexpanded `.xml.j2` helper in both
languages. `translation_probe.py` separately rehearses the existing expansion,
translation export and sync on only the two shared files. The usual `.j2` route
**fails**: seven machine-XML fragments are classified as translatable prose and
the expanded XML changes. Do not integrate this layout into the source tree.

Keeping identical helper bytes as `src/word/short-tables.xml` passes that minimal
translation rehearsal, produces zero translation units and preserves both files
through expansion and sync. This asset-path alternative has **not** been tested
in the native DSW package pipeline. The successful native `.j2` run and successful
minimal `.xml` translation run are distinct evidence, not end-to-end acceptance.

Next: verify packaging/loading/rendering the `.xml` asset through native DSW.
Then integrate the shared helpers and preceding source prototypes into the
English repository, rebuild Chinese through the existing translator, pin the
new complete English SHA, and compare actual paired-version packages to these
frozen prototypes. Do not create permanent language/profile patch branches
or duplicate Word implementations in the Chinese repository. This prototype
does not constitute full DMP quality/compliance, a global submission toggle,
Microsoft Word acceptance, or permission to deploy to production.
