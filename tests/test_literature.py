import httpx
from backend.literature import retrieve
from backend.report import critique

def test_records_are_retrieved_and_uncertain():
    def handler(req):
        if 'esearch' in req.url.path:return httpx.Response(200,json={'esearchresult':{'idlist':['123']}})
        return httpx.Response(200,text='<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Real fixture title</ArticleTitle><Abstract><AbstractText>Test abstract.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>')
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:r=retrieve('fixture query',c)
    assert r['records'][0]['pmid']=='123'
    assert r['records'][0]['relation']=='uncertain'
    assert r['records'][0]['access']=='abstract_only'

def test_retrieval_failure_never_invents_sources():
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(503))) as c:r=retrieve('test',c)
    assert r['status']=='failed' and r['records']==[]
