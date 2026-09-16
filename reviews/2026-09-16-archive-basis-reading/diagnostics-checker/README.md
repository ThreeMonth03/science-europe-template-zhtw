# Initial comparator diagnosis

The first targeted English DOCX comparison failed with
`Non-owned Word paragraph, table, format or answer changed`.
Removing the criteria list causes Pandoc's immediate following migration
paragraph to use BodyText instead of FirstParagraph. Both styles have identical
paragraph and run properties; FirstParagraph is based on BodyText. The revised
checker admits only this immediate-successor transition, verifies the style
equivalence, and still compares every other XML attribute and character.

The first checker also assumed all summary runs lacked direct properties.
Inspection of the Chinese output showed the pre-existing `eastAsia` font hint.
The revision permits only properties already present on the replaced owned
paragraphs, not new font sizes or formatting. No candidate source or ZIP changed.

The initial developer diagnostic also tried to read paragraph text from a table
node and raised TypeError; that diagnostic was corrected to select paragraph
nodes. It did not change artifacts or constitute a successful acceptance run.

`archive-basis-first-three.json` records the first whole-document comparator
attempt: it passed a detached Tag to a helper that creates new DOM nodes and
expects a BeautifulSoup document. The caller now reparses the selected DMP
subtree as a document. The expected transformation is unchanged.

`archive-basis-first-three-v2.json` then reached DOCX, passed English, and failed
on Chinese summary punctuation runs which inherit the paragraph style (None),
whereas all original Chinese list runs carry an East Asian hint. Inherited
formatting is now admitted alongside the exact prior properties; paragraph
style, font size and unchanged XML remain independently checked.

The first eight-case run passed 15 language/case pairs, then stopped on the
long Chinese PDF: the shorter Q11 changes which budget paragraph starts each
continuation page (13 → 16 and 50 → 53). Repeated table labels/resource identity
therefore move in raw extraction. The revised checker first validates the
complete original budget sequence and every continuation's exact prefix,
then excludes only these repeated page prefixes. Original identity and all
60 authored paragraphs remain checked. It does not globally remove matching
text. The failed report and checker snapshot are preserved here.
