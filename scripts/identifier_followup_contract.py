"""Independent expected Q13 child states and reviewed bilingual wording."""
FIELDS=('identifier-assigner','identifier-resolution')
ASSIGNERS={
    'ProjectDataSteward':('A project data steward or principal investigator will assign the persistent identifier.','持續識別碼將由計畫的資料託管員或主持人指派。'),
    'InstitDataSteward':('An institutional data steward will assign the persistent identifier.','持續識別碼將由機構的資料託管員指派。'),
    'Repository':('The repository will assign the persistent identifier.','持續識別碼將由資料儲存庫指派。'),
}
RESOLUTIONS={
    'Yes':('The repository will make sure the persistent identifier can be resolved to a digital object.','資料儲存庫將確保持續識別碼可解析至數位物件。'),
    'No':('The repository will not make sure the persistent identifier can be resolved to a digital object.','資料儲存庫將不保證持續識別碼可解析至數位物件。'),
}
LABELS={
    'identifier-assigner':('who will assign the persistent identifier','持續識別碼的指派者'),
    'identifier-resolution':('whether the repository guarantees resolution of the persistent identifier to a digital object','資料儲存庫是否保證持續識別碼可解析至數位物件'),
}


def expected_fields(replies,ids):
    """Key by dataset AND distribution IDs, never visible names or list numbers."""
    data=ids['preservingCUuid']+'.'+ids['producedDataQUuid']; expected={}
    for item in replies.get(data,[]):
        pub='.'.join([data,item,ids['isPublishedDataQUuid']])
        if replies.get(pub)!=ids['isPublishedDataYesAUuid']: continue
        distros='.'.join([pub,ids['isPublishedDataYesAUuid'],ids['publishedDistrosQUuid']])
        for distro in replies.get(distros,[]):
            parent='.'.join([distros,distro,ids['publishedDataIdentifierQUuid']]); fields={}
            expected[(item,distro)]=fields
            if replies.get(parent)!=ids['publishedDataIdentifierYesAUuid']: continue
            for field,question,choices in [('identifier-assigner','Assigns',ASSIGNERS),('identifier-resolution','Resolvable',RESOLUTIONS)]:
                raw=replies.get('.'.join([parent,ids['publishedDataIdentifierYesAUuid'],ids['publishedDataIdentifier'+question+'QUuid']]),'')
                choice=next((name for name in choices if raw==ids['publishedDataIdentifier'+question+name+'AUuid']),None)
                if choice: fields[field]=('explicit-no' if field=='identifier-resolution' and choice=='No' else 'complete',choices[choice])
                else: fields[field]=('needs-review' if str(raw or '').strip() else 'missing',LABELS[field])
    return expected


def warning_text(state,labels,language):
    if language=='chinese':
        lead='尚待補充：' if state=='missing' else '本模板無法判讀下列欄位的選項，請核對：'
        return lead+'、'.join(labels)+'。'
    lead='Information still needed: ' if state=='missing' else 'This template cannot interpret the selected answers for: '
    return lead+', '.join(labels)+'.'


def check_followups(soup,replies,ids,language,concise=False):
    expected=expected_fields(replies,ids); column=0 if language=='english' else 1
    q=soup.select_one('#q-persistent-identifier'); assert q is not None
    observed=set(); total=0; warnings=[]
    for distro in q.select('.distribution-section'):
        item=distro.find_parent(class_='dataset-section')['data-item-id']; key=(item,distro['data-item-id'])
        assert key in expected and key not in observed, ('Unexpected/duplicate distribution',key)
        observed.add(key); fields=expected[key]
        nodes=distro.select('[data-fact-id="identifier-assigner"], [data-fact-id="identifier-resolution"]')
        assert len(nodes)==len(fields), (key,'Missing or duplicated child fact')
        policy=distro.select_one('.identifier-arrangement')
        assert bool(policy)==bool(fields)
        units=distro.select('.identifier-followup-unit')
        assert len(units)==bool(fields)
        if units:
            unit=units[0]
            assert unit.parent is distro and unit.get('class')==['identifier-followup-unit','short-reading-unit']
            assert policy.parent is unit and len(unit.get_text(strip=True))<=500
            assert not unit.select('.answer-detail, ul, ol, table'), 'Only bounded owned prose may stay together'
        for field,(state,texts) in fields.items():
            matches=[n for n in nodes if n['data-fact-id']==field]; assert len(matches)==1
            node=matches[0]; total+=1
            assert node.get('data-status')==state and node.get('data-requirement-id')=='SE-5d',(key,field,'Wrong state/requirement')
            assert node.get_text()==texts[column],(key,field,'Wrong fixed wording')
            if state in ['complete','explicit-no']:
                if concise and field=='identifier-assigner':
                    assert node.name=='span' and node.parent.name=='p' and node.parent.parent is policy
                    assert node.parent.attrs=={'data-fact-id':'persistent-identifier','data-status':'complete'}
                    assert list(node.parent.children)==[node], 'Assignment sentence must express both facts alone'
                else:
                    assert node.name=='p' and node.parent is policy
            else:
                assert node.name=='span' and node.parent.name=='p' and 'data-gap' in node.parent.get('class',[])
                wrapper=node.find_parent(class_='identifier-followups')
                assert wrapper is not None and wrapper.parent is unit
                assert node.find_parent(class_='identifier-arrangement') is None
        expected_warnings=[]
        if concise and fields:
            parents=policy.select('[data-fact-id="persistent-identifier"]')
            assert len(parents)==1 and parents[0].parent is policy and parents[0].get('data-status')=='complete'
            known=fields['identifier-assigner'][0]=='complete'
            if not known:
                assert parents[0].get_text()==('Persistent identifiers will be assigned.' if language=='english' else '資料將取得持續識別碼。')
            assert len(policy.find_all('p',recursive=False))==1+int(fields['identifier-resolution'][0] in ['complete','explicit-no'])
        for state in ['missing','needs-review']:
            labels=[fields[f][1][column] for f in FIELDS if f in fields and fields[f][0]==state]
            if labels: expected_warnings.append(warning_text(state,labels,language))
        wrappers=distro.select('.identifier-followups')
        assert len(wrappers)==bool(expected_warnings), (key,'Unexpected warning wrapper')
        if wrappers:
            wrapper=wrappers[0]
            assert wrapper.get('class')==['identifier-followups','reading-gap']
            assert wrapper.find_previous_sibling() is policy
            paragraphs=wrapper.find_all(recursive=False)
            assert all(p.name=='p' and p.get('class')==['data-gap'] and p.get('data-requirement-id')=='SE-5d' for p in paragraphs)
            assert [p.get_text() for p in paragraphs]==expected_warnings,(key,'Warnings not grouped/punctuated correctly')
            warnings.extend(paragraphs)
    assert observed==set(expected), 'Dataset/distribution disappeared'
    assert len(q.select('[data-fact-id="identifier-assigner"], [data-fact-id="identifier-resolution"]'))==total, 'Child fact escaped its item scope'
    assert len(q.select('.identifier-followups p'))==len(warnings)
    return warnings
