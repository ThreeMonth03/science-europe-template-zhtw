#!/usr/bin/env bash
# Existing native regressions, partitioned only by language. Run from the ZH repo.
# No historical contract is removed, weakened, or silently skipped here.
set -euo pipefail

group=${1:?Expected english or chinese}
build=${2:?Expected prepared build directory}
case "$group" in english|chinese) ;; *) echo "Unknown group: $group" >&2; exit 2 ;; esac
SE_PYTHON=${SE_PYTHON:-../tooling/.venv/bin/python}
SE_ENGLISH=${SE_ENGLISH:-../english}
mkdir -p outputs/ci
timings="outputs/ci/native-$group.tsv"
printf 'probe\tseconds\texit_code\n' > "$timings"

run() {
    local script=$1 started=$SECONDS status=0
    shift
    printf 'Starting %s (%s)\n' "$script" "$group"
    "$SE_PYTHON" "$SE_ENGLISH/scripts/$script" "$@" || status=$?
    printf '%s\t%s\t%s\n' "$script" "$((SECONDS - started))" "$status" >> "$timings"
    # Retain the failure code; the workflow waits for BOTH language processes.
    return "$status"
}

metadata_gap_view() {
    # Only this old Q3 wording proof needs the sealed historical question.
    # Keep the current rendering assets and every other native check unchanged.
    "$SE_PYTHON" - "$SE_ENGLISH" "$build" "$group" <<'PY'
import json, sys
from pathlib import Path
sys.path[:0] = [str(Path('scripts').resolve()), str(Path(sys.argv[1]).resolve() / 'scripts')]
from current_source_repairs import metadata_gap_view
build, language = Path(sys.argv[2]), sys.argv[3]
prepared = build / ('en' if language == 'english' else 'translated')
view = build / ('historical-metadata-gap-' + language)
proof = metadata_gap_view(prepared, language, view)
(build / ('metadata-gap-historical-view-' + language + '.json')).write_text(json.dumps(proof, indent=2) + '\n')
print(view)
PY
}

if [[ "$group" == english ]]; then
    run probe_empty_section_spacing.py --output "$build/empty-section-engine.json"
    run probe_submission_flow_word.py --source-dir "$build/en" --output "$build/submission-flow-engine-en.json"
    run probe_budget_word.py --output "$build/budget-word-probe.json"
    run probe_q8_word.py --output "$build/q8-word-probe.json"
    run probe_q9_word.py --output "$build/q9-word-probe.json"
    run probe_short_resource_rows.py --source-dir "$build/en" --engine --output "$build/short-resource-rows-engine-en.json"
    run probe_short_resources.py --source-dir "$build/en" --engine --output "$build/short-resources-engine-en.json"
    run probe_preservation_reading.py --source-dir "$build/en" --output "$build/preservation-reading-engine-en.json"
    run probe_storage_context.py --source-dir "$build/en" --output "$build/storage-context-engine-en.json"
    run probe_q5_word_join.py --source-dir "$build/en" --output "$build/q5-word-join-engine-en.json"
    SE_METADATA_VIEW=$(metadata_gap_view)
    run probe_metadata_gap_prose.py --source-dir "$SE_METADATA_VIEW" --output "$build/metadata-gap-prose-engine-en.json"
    run probe_archive_gap_panels.py --source-dir "$build/en" --output "$build/archive-gap-engine-english.json"
    run probe_word_short_budget.py --source-dir "$build/en" --output "$build/word-short-budget-english.json"
    run probe_short_budget.py --source-dir "$build/en" --output "$build/short-budget-english.json"
    run probe_empty_pdf.py --source-dir "$build/en" --output "$build/empty-pdf-probe-english.json"
    run probe_long_budget_word.py --output "$build/long-budget-word-probe.json"
    run probe_budget_pdf.py --output "$build/budget-pdf-probe.json"
    run probe_pdf_budget_reading.py --engine --output "$build/pdf-budget-reading-probe-english.json"
else
    run probe_submission_flow_word.py --source-dir "$build/translated" --output "$build/submission-flow-engine-zh.json"
    run probe_short_resource_rows.py --source-dir "$build/translated" --engine --output "$build/short-resource-rows-engine-zh.json"
    run probe_short_resources.py --source-dir "$build/translated" --engine --output "$build/short-resources-engine-zh.json"
    run probe_preservation_reading.py --source-dir "$build/translated" --output "$build/preservation-reading-engine-zh.json"
    run probe_storage_context.py --source-dir "$build/translated" --output "$build/storage-context-engine-zh.json"
    run probe_q5_word_join.py --source-dir "$build/translated" --output "$build/q5-word-join-engine-zh.json"
    SE_METADATA_VIEW=$(metadata_gap_view)
    run probe_metadata_gap_prose.py --source-dir "$SE_METADATA_VIEW" --frozen tests/fixtures/metadata-0.3.36.zh-Hant.html.j2 --language chinese --output "$build/metadata-gap-prose-engine-zh.json"
    run probe_archive_gap_panels.py --source-dir "$build/translated" --output "$build/archive-gap-engine-chinese.json"
    run probe_identifier_spacing.py --source-dir "$build/translated" --output "$build/identifier-spacing-engine.json"
    run probe_word_short_budget.py --source-dir "$build/translated" --output "$build/word-short-budget-chinese.json"
    run probe_short_budget.py --source-dir "$build/translated" --output "$build/short-budget-chinese.json"
    run probe_empty_pdf.py --source-dir "$build/translated" --output "$build/empty-pdf-probe-chinese.json"
    run probe_pdf_budget_reading.py --source-dir "$build/translated" --prior-question tests/fixtures/budget-0.3.18.zh-Hant.html.j2 --output "$build/pdf-budget-reading-probe-chinese.json"
fi
