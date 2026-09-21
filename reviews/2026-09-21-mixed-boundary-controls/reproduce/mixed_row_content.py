"""Row-scoped oracle for the marked public mixed-budget fixtures, in any order.

Generated continuation headers are removed only at verified page/row boundaries.
Every complete cell paragraph/list item is consumed exactly once in its own row;
cell painting order may vary across pages, but order inside each cell may not.
"""
from bs4 import BeautifulSoup

MARKERS = {'•', '◦', '\uf0b7', '\uf0a1'}
compact = lambda value: ''.join(value.split())


def cell_tokens(cell):
    nodes = [node for node in cell.select('p, li') if node.name == 'p' or not node.find('p')]
    values = [compact(node.get_text()) for node in nodes]
    assert values and all(values) and ''.join(values) == compact(cell.get_text()), 'Unaccounted cell text'
    return values


def content(pages, source, expanded=True):
    soup = BeautifulSoup(source, 'html.parser')
    tables = soup.select('#q-required-resources .resource-table')
    assert len(tables) == 1 and not MARKERS.intersection(soup.get_text())
    table = tables[0]; rows = table.tbody.find_all('tr', recursive=False)
    cells = [row.find_all('td', recursive=False) for row in rows]
    assert rows and all(len(value) == 3 for value in cells)
    tokens = [[cell_tokens(cell) for cell in row] for row in cells]
    titles = [row[0][0] for row in tokens]
    assert len(set(titles)) == len(titles)
    long_indices = [i for i, row in enumerate(tokens) if any('MIX-LONG-09-PARA-' in p for p in row[0])]
    assert len(long_indices) == 1
    long_index = long_indices[0]; long_tokens = tokens[long_index]
    header = compact(table.thead.get_text())
    identity = titles[long_index] + ''.join(long_tokens[1] + long_tokens[2])
    full_header = header + identity
    assert all(header not in atom for row in tokens for cell in row for atom in cell)
    assert all(full_header not in compact(n.get_text()) for n in soup.select('.answer-detail'))
    values = []; repeats = []; seen_long = False
    for number, page in enumerate(pages, 1):
        value = ''.join(c for c in page if c not in MARKERS)
        if expanded and seen_long and value.startswith(full_header):
            value = value[len(full_header):]
            repeats.append(dict(page=number, kind='long-identity'))
        elif value.startswith(header):
            value = value[len(header):]
            repeats.append(dict(page=number, kind='columns'))
        seen_long |= titles[long_index] in value
        values.append(value)
    whole = ''.join(values)
    positions = [whole.index(title) for title in titles]
    assert all(whole.count(title) == 1 for title in titles), 'Ambiguous or repeated row identity'
    assert positions == sorted(positions), 'Resource order changed'
    locations = [number for number, value in enumerate(values, 1) for _ in value]
    prefix = whole[:positions[0]]
    if prefix.endswith(header): prefix = prefix[:-len(header)]
    assert header not in prefix
    assert header in pages[locations[positions[0]] - 1], 'Initial column headings missing'
    canonical = prefix; result = []; long_details = None
    for index, (row, grouped, start) in enumerate(zip(rows, tokens, positions)):
        stop = positions[index + 1] if index + 1 < len(rows) else len(whole)
        value = whole[start:stop]
        # A new ordinary/expanded table can begin between two resource rows.
        if value.endswith(header): value = value[:-len(header)]; stop -= len(header)
        atoms = [(column, n, text) for column, cell in enumerate(grouped) for n, text in enumerate(cell)]
        assert len({text for _, _, text in atoms}) == len(atoms), 'Ambiguous repeated atom inside one row'
        pending = list(range(len(atoms))); found = []; cursor = start
        while value:
            matches = [n for n in pending if value.startswith(atoms[n][2])]
            assert len(matches) == 1, (index + 1, 'Missing, interleaved, duplicated or wrong-row text', value[:160])
            n = matches[0]; text = atoms[n][2]
            found.append(dict(atom=n, text=text, pages=sorted(set(locations[cursor:cursor + len(text)]))))
            cursor += len(text); value = value[len(text):]; pending.remove(n)
        assert not pending, (index + 1, 'Lost cell paragraph')
        for column in range(3):
            sequence = [atoms[v['atom']][1] for v in found if atoms[v['atom']][0] == column]
            assert sequence == list(range(len(grouped[column]))), 'Paragraph order within a cell changed'
        canonical += ''.join(text for _, _, text in atoms)
        result.append(dict(index=index + 1, identity=row['data-item-id'], pages=sorted(set(locations[start:stop])),
                           paragraph_count=len(atoms), long=index == long_index))
        if index == long_index:
            purposes = [v for v in found if v['text'].startswith('MIX-LONG-09-PARA-')]
            assert len(purposes) == 60
            for n, paragraph in enumerate(purposes, 1):
                marker = f'MIX-LONG-09-PARA-{n:02d}:'
                assert paragraph['text'].startswith(marker) and whole.count(marker) == 1
            purpose_pages = sorted({page for paragraph in purposes for page in paragraph['pages']})
            allocation = [v for v in found if atoms[v['atom']][:2] == (0, len(grouped[0]) - 1)]
            assert len(allocation) == 1
            name_pages = [n for n, page in enumerate(pages, 1) if titles[long_index] in page]
            long_details = dict(index=index + 1, expanded=expanded, purpose_pages=purpose_pages,
                complete_purpose_paragraphs=60, split_purpose_paragraphs=[v['text'].split(':', 1)[0] for v in purposes if len(v['pages']) != 1],
                missing_identity_header_pages=[n for n in purpose_pages if full_header not in pages[n - 1]] if expanded else None,
                name_pages=name_pages, purpose_pages_without_name=sorted(set(purpose_pages) - set(name_pages)),
                last_purpose_pages=purposes[-1]['pages'], allocation_pages=allocation[0]['pages'],
                tail_together=purposes[-1]['pages'] == allocation[0]['pages'] and len(allocation[0]['pages']) == 1)
    assert long_details
    return dict(canonical=canonical, rows=result, repeated_headers=repeats, long=long_details)
