"""Compare authored block fragments without assuming lists/tables are flat paragraphs."""
from bs4 import NavigableString
from check_narrative_outputs import compact

INLINE = {'a', 'span', 'strong', 'em', 'b', 'i', 'code', 'sub', 'sup', 's', 'u', 'br'}


def text_runs(node):
    pending = []
    for child in node.children:
        if isinstance(child, NavigableString): pending.append(str(child))
        elif child.name in INLINE: pending.append(child.get_text())
        else:
            if compact(''.join(pending)): yield ''.join(pending)
            pending = []
            yield from text_runs(child)
    if compact(''.join(pending)): yield ''.join(pending)


def assert_native_text(node, pdf, document):
    # XML order includes real table cells as well as paragraphs and hyperlinks.
    word = ''.join(n.text or '' for n in document.element.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
    for fragment in text_runs(node):
        expected = compact(fragment)
        assert expected in compact(pdf) and expected in compact(word), ('Block text lost', fragment)
