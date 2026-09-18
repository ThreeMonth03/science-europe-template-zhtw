# Checker correction, not a native conversion failure

The first Chinese engine report failed because its Word oracle permitted no
run properties. Native and pinned Pandoc output actually retain the original
`w:rFonts w:hint="eastAsia"` on Chinese prose. A standalone terminal `。` after
the final span has no hint, as emitted by Pandoc.

The corrected oracle requires the original uniform properties on all text,
allowing hint omission only on that exact punctuation run, and rejects changed
fonts or unformatted Chinese prose. Paragraph styles and every other body XML
block must remain equal. No template font, Lua or reference DOCX was changed.

`engine-failure.json` remains failed and is bound to the original checker file.
The corrected full engine run is separate, not a relabeling of this report.
