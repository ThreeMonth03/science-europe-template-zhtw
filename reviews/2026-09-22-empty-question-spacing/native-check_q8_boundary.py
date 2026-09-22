"""Observe Q8 name/permission boundaries in synthetic Word previews only."""
import itertools,json
from bs4 import BeautifulSoup
import check

def locate(text,needle,start=0,end=None):
    end=len(text) if end is None else end
    position=text.find(needle,start,end)
    assert needle and position>=0,'Missing expected synthetic text'
    assert text.find(needle,position+1,end)<0,'Ambiguous synthetic text'
    return position

def main():
    rows=[]
    for case,locale,profile,arm in itertools.product(['SYN-COMPLETE','SYN-OTHER'],['en','zh-Hant'],['review','submission'],['baseline','candidate']):
        folder=check.ROOT/arm/'renders'/f'{case}-{locale}-{profile}'
        soup=BeautifulSoup((folder/'word-entry.html').read_text(),'html.parser')
        q8=soup.select_one('#q-copyright-ipr');q9=soup.select_one('#q-ethical-issues')
        item=q8.select_one('.answer > ul > li');label=item.find('div',recursive=False)
        permission=label.next_sibling
        assert isinstance(permission,str) and check.compact(permission)
        _,_,pages=check.pdf(folder/'word-preview/document.pdf')
        text=''.join(pages)
        begin=locate(text,check.compact(q8.h3.get_text()))
        end=locate(text,check.compact(q9.h3.get_text()),begin)
        name=check.compact(label.get_text());intro=check.compact(permission)
        name_pos=locate(text,name,begin,end);intro_pos=locate(text,intro,name_pos+len(name),end)
        def page_at(offset):
            total=0
            for number,page in enumerate(pages,1):
                total+=len(page)
                if offset<total:return number
            raise AssertionError('Position outside pages')
        name_end=page_at(name_pos+len(name)-1);intro_start=page_at(intro_pos)
        rows.append(dict(case=case,locale=locale,profile=profile,arm=arm,
            label_end_page=name_end,permission_start_page=intro_start,
            label_kept_with_permission=name_end==intro_start))
    with (check.ROOT/'q8-boundaries.json').open('x') as f:
        f.write(json.dumps(dict(observation_only=True,native_ms_word=False,rows=rows),indent=2)+'\n')
    print(json.dumps(dict(observations=len(rows),split_boundaries=[r for r in rows if not r['label_kept_with_permission']])))

if __name__=='__main__':main()
