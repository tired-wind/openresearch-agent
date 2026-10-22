"""Only retrieved PubMed records become references; no invented support labels."""
import time
from datetime import datetime, timezone
import httpx
from defusedxml import ElementTree as ET
BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

def retrieve(query: str, client: httpx.Client | None = None) -> dict:
    own = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(12), follow_redirects=False)
    def get(path, params):
        for attempt in range(2):
            try:
                r = client.get(BASE + '/' + path, params=params)
                r.raise_for_status()
                if len(r.content) > 2_000_000:
                    raise ValueError('Source response exceeds limit')
                return r
            except (httpx.HTTPError, ValueError):
                if attempt: raise
                time.sleep(1)
    try:
        search = get('esearch.fcgi', {'db':'pubmed','term':query,'retmode':'json','retmax':5,'tool':'OpenResearchAgent'})
        ids = search.json()['esearchresult']['idlist']
        if not ids:
            return {'status':'empty','query':query,'records':[], 'message':'No PubMed matches. No supporting or conflicting evidence established.'}
        time.sleep(.6)
        fetched = get('efetch.fcgi', {'db':'pubmed','id':','.join(ids),'retmode':'xml','tool':'OpenResearchAgent'})
        root = ET.fromstring(fetched.content)
        records=[]
        for article in root.findall('.//PubmedArticle'):
            def txt(path):
                node=article.find(path)
                return ''.join(node.itertext()) if node is not None else ''
            pmid=txt('.//MedlineCitation/PMID')
            if pmid not in ids or not pmid.isdigit(): continue
            title=txt('.//ArticleTitle')
            if not title: continue
            doi=next((n.text for n in article.findall('.//ArticleId') if n.get('IdType')=='doi'), None)
            abstracts=[''.join(n.itertext()) for n in article.findall('.//Abstract/AbstractText')]
            records.append({'evidence_id':f'pubmed-{pmid}','evidence_type':'retrieved_source','pmid':pmid,'doi':doi,'title':title,
                'authors':[' '.join(filter(None,[a.findtext('ForeName'),a.findtext('LastName'),a.findtext('CollectiveName')])) for a in article.findall('.//Author')][:12],
                'year':txt('.//JournalIssue/PubDate/Year') or txt('.//JournalIssue/PubDate/MedlineDate'),
                'abstract':'\n'.join(abstracts)[:16000], 'url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                'access':'abstract_only' if abstracts else 'metadata_only', 'relation':'uncertain',
                'assessment':'Retrieved search candidate. Support, contradiction and direct relevance require content review.',
                'retrieved_at':datetime.now(timezone.utc).isoformat()})
        return {'status':'retrieved' if records else 'empty','query':query,'records':records, 'message':'Identifiers verified against fetched records; scientific support not established.'}
    except Exception as exc:
        return {'status':'failed','query':query,'records':[],'message':f'PubMed retrieval failed ({type(exc).__name__}); no fallback citations generated.'}
    finally:
        if own: client.close()
