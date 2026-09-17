# Checker development observations

No candidate template or translated source changed after the native run began.

The initial isolated PDF comparison stopped because the prior suffix checker
accepts only `•`, whereas this fixture's Q11 page has mixed `•◦◦••` generated
markers. The source HTML contains neither glyph as authored text. The replacement
checker validates each suffix marker's type/count, text-bearing bbox line and
indent, and compares complete signatures before/after. It never strips arbitrary
authored bullets. Both languages' rich/partial/multiple-format comparisons passed.

The initial isolated Chinese DOCX comparison stopped because plain CJK runs carry
the existing exact `w:rFonts w:hint="eastAsia"` property. Admit precisely this
property or no direct property for changed fixed prose; retained characters keep
their original formatting, and all other body XML, numbering and links compare
exactly. Bold, font-family and arbitrary style substitutions remain disallowed.

The first baseline Word-preview batch started before the last native DOCX was
ready. It stopped with 9/10 previews; its report and files are retained locally.
After native completion, a fresh full batch produced all 10 previews, each bound
to its source DOCX hash. This is not counted as a native rendering failure.

Font bounding-box overlap diagnostics are recorded, not mislabeled as visible
collisions: font metrics are not ink bounds. Page-bound and paragraph-retention
checks are separate from visual inspection.
