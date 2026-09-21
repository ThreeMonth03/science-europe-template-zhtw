# Q15 empty-budget omission and Q9 Word table-flow diagnostics

Prototype only. Frozen evidence: [empty-budget review](../../reviews/2026-09-21-empty-budget/README.md).
The exact parent is the sealed `2026-09-21-ethics-lead/after` package. Neither
the English source nor Chinese translation tree is changed by these scripts.

`budget_recipe.py` defines three reversible, Q15-only source edits;
`budget_probe.py` projects the old DOM independently from reachable cost lists.
`budget_trial.py probe` exercises both languages, escaping settings and three
format paths. `packages` requires the exact local tables-only worker and parent
ZIP hashes. Run native exports serially with `scripts/run_missing_info.py`.

`budget_native.py check` verifies twelve pairs against the sealed baseline and
the **older** page limits, so an inherited 7 → 8 regression cannot become an
accepted 8-page baseline. The unresolved native Word header-only continuation
remains a visual blocker. `preview` is a bounded recovery for this run's partial
preview receipt: it requires all native renders to be complete, verifies every
existing preview hash, creates only missing previews and keeps the old receipt.
Future runs should generate all native inputs before starting the ordinary
preview script; do not manufacture a partial receipt to reuse this recovery.

`diagnose_word.py` generates separate diagnostic copies from exact native DOCX
inputs. Its five modes isolate non-final paragraph keep, direct row cantSplit,
their combination, and inherited table-style cantSplit. These copies must never
replace native outputs or be presented as an implemented template fix.

`budget_collect.py` collects fresh evidence after checks and scoped runtime
cleanup. Validate compacted checks and diagnostic inventories before invoking
the one-time `seal_review_archive.py`; never edit or reseal a frozen archive.

Next: implement the effective bounded short-table properties through a supported
template conversion path, verify long/multiblock/spanning/nested tables remain
breakable, then integrate the accumulated prototypes into English and rebuild
Chinese via the existing translation pipeline. No global table lock, manual
document repair as a deliverable, version bump, or production deployment here.

Read-only follow-up inspection of the pinned tables-only worker image found the
existing `EnrichDocxStep` (`enrich-docx`): it can render a named Jinja template
against an existing DOCX member using `rewrite:word/document.xml=render:...`.
This is a candidate for a template-owned final step, **not implemented or
validated here**. First prove a no-op round trip, use a Lua-generated marker only
after independently bounding the AST, and require exact XML/component retention
outside the marked rows. Do not perform global string substitution on all rows
or key off user text. Recheck this capability against the pinned deployment
worker before selecting it; the actual implementation inspected was
`dsw.document_worker.templates.steps.word.EnrichDocxStep` in image
`sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11`.
