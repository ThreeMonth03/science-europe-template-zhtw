"""Reconstruct the locked PDF path and trial only its ordinary mixed-table groups."""
import re
from bs4 import BeautifulSoup
from jinja2 import Environment,FileSystemLoader
from markupsafe import Markup

TABLE=re.compile(r'<table class="resource-table">.*?</table>',re.S)


def fragments(source):
    """Read captured owned fragments, not authored prose or replacement sentences."""
    header=re.search(r'<thead>(.*?)</thead>',source,re.S);assert header
    body=re.search(r'<tbody>(.*?)</tbody>',source,re.S);assert body
    matches=list(re.finditer(r'<tr data-item-id="([a-zA-Z0-9._-]+)">(.*?)</tr>',body[1],re.S))
    assert ''.join(m[0] for m in matches).split()==body[1].split(), 'Unexpected table body'
    rows=[]
    for match in matches:
        cells=re.fullmatch(r'<td>(.*?)</td><td>(.*?)</td><td>(.*?)</td>',match[2],re.S);assert cells
        assert '<table' not in match[0]
        first=cells[1];end=first.index('</p>')+4
        row=dict(id=match[1],title=first[:end],purpose=first[end:],budget=cells[2],funding=cells[3],original=match[0])
        rows.append({k:Markup(v) if k!='id' else v for k,v in row.items()})
    return Markup(header[1]),rows


def pdf_baseline(source,english):
    env=Environment(loader=FileSystemLoader(english),extensions=['jinja2.ext.do'],autoescape=True)
    reading=env.get_template('src/budget-reading.html.j2').module
    original=list(TABLE.finditer(source));assert len(original)==1
    table=original[0][0];header,rows=fragments(table)
    result=source.replace(table,str(reading.render(Markup(table),header,rows)),1)
    result=str(env.get_template('src/pdf/short-resources.html.j2').module.document(Markup(result)))
    return result


def trial(source,english):
    from short_resource_rows_contract import eligible,project_hints
    env=Environment(loader=FileSystemLoader(english),extensions=['jinja2.ext.do'],autoescape=True)
    helper=env.get_template('src/pdf/short-resource-rows.html.j2').module
    soup=BeautifulSoup(source,'html.parser')
    # This rehearsal is deliberately limited to an already expanded long table.
    if not soup.select('table.pdf-resource-reading'):return source,[]
    selected=[];result=source
    for match in TABLE.finditer(source):
        original=match[0];_,rows=fragments(original)
        expected=[r['id'] for r in rows if eligible(r)] if 4<=len(rows)<=32 else []
        changed=str(helper.table(Markup(original),rows))
        actual=[r['data-item-id'] for r in BeautifulSoup(changed,'html.parser').select('.pdf-short-resource-row')]
        assert actual==expected
        assert project_hints(changed)==original,'Only known row-opening hints may differ'
        assert result.count(original)==1;result=result.replace(original,changed,1);selected.extend(actual)
    assert project_hints(result)==source
    return result,selected


def matrix(english):
    header='<tr><th scope="col">Resource</th><th scope="col">Budget</th><th scope="col">Funding</th></tr>'
    prefix='<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead>'+header+'</thead><tbody>'
    def fixture(count):
        rows=[]
        for n in range(count):
            row=dict(id='resource-'+str(n),title='<p><strong>Resource '+str(n)+'</strong></p>',
                purpose='<p>Keep original files.</p><p>FAIR activities.</p>',budget='<p>0 TWD</p>',funding='<p>Institute.</p>')
            row['original']='<tr data-item-id="'+row['id']+'"><td>'+row['title']+row['purpose']+'</td><td>'+row['budget']+'</td><td>'+row['funding']+'</td></tr>'
            rows.append(row)
        return rows
    env=Environment(loader=FileSystemLoader(english),extensions=['jinja2.ext.do'],autoescape=True)
    reading=env.get_template('src/budget-reading.html.j2').module
    cases=[]
    for count,position in [(9,0),(9,4),(9,8),(7,3),(32,0),(32,16),(32,31),(33,32)]:
        rows=fixture(count)
        row=rows[position];row['purpose']='<div class="answer-detail" data-fact-id="resource-justification" data-status="complete">'+''.join('<p>LONG-'+str(n)+': retain original purpose.</p>' for n in range(60))+'</div><p>FAIR.</p>'
        row['original']='<tr data-item-id="'+row['id']+'"><td>'+row['title']+row['purpose']+'</td><td>'+row['budget']+'</td><td>'+row['funding']+'</td></tr>'
        source=prefix+''.join(r['original'] for r in rows)+'</tbody></table>'
        header,values=fragments(source)
        baseline=str(reading.render(Markup(source),header,values));after,selected=trial(baseline,english)
        expected=sum(n for n in [position,count-position-1] if n>=4) if count<=32 else 0
        assert len(selected)==expected,(count,position,len(selected),expected)
        cases.append(dict(case=f'rows-{count}-long-{position+1}',before=baseline,after=after,selected=selected))
    return cases
