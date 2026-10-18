from somoy_jatri.research.automatic import enrich


def test_enrichment_rejects_fabricated_quotes_and_preserves_existing_indices(monkeypatch):
    text='The original capital was Memphis. The pyramids are ancient monuments. The necropolis stretches over a long distance.'
    class Response:
        def raise_for_status(self):pass
        text=''
    response=Response();response.text='<p>'+text+'</p>'
    monkeypatch.setattr('somoy_jatri.research.automatic.requests.get',lambda *a,**kw:response)
    facts=[{'claim':f'Existing fact {i}','source_id':'s1'} for i in range(3)]
    additions=[{'claim':f'Sourced detail {i}','source_id':'s1','source_quote':text} for i in range(3)]
    additions.append({'claim':'Invented detail','source_id':'s1','source_quote':'This quotation is not in the source text.'})
    monkeypatch.setattr('somoy_jatri.research.automatic.Groq.json',lambda *a:{'facts':additions})
    dossier={'location':'Memphis','period':'Old Kingdom','facts':list(facts),'sources':[{'id':'s1','url':'https://example.org'}]}
    result=enrich(dossier)
    assert result['facts'][:3]==facts
    assert len(result['facts'])==6
    assert all(f['claim']!='Invented detail' for f in result['facts'])
