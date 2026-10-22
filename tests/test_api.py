import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend import storage
from backend.app import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'ROOT',tmp_path)
    with TestClient(app) as c:yield c

def test_end_to_end_real_worker(client):
    d=client.post('/api/demo').json()
    r=client.post('/api/runs',json={'dataset_id':d['dataset_id'],'target':'outcome','question':'Which predictors are useful?','independent_rows':True})
    assert r.status_code==202
    rid=r.json()['id']
    for _ in range(150):
        state=client.get('/api/runs/'+rid).json()
        if state['status'] not in ('queued','running'):break
        time.sleep(.2)
    assert state['status']=='completed_with_warnings',state
    assert state['result']['literature']['status']=='disabled'
    assert state['result']['analysis']['n_test']==80
    report=client.get('/api/runs/'+rid+'/report')
    assert report.status_code==200 and 'not causal evidence' in report.text
    assert (storage.ROOT/'runs'/rid/'analysis.json').exists()
    assert client.get('/api/runs/'+rid+'/evidence').json()['provenance']['kind']=='synthetic_demo_not_clinical'

def test_bad_requests_and_origin(client):
    assert client.post('/api/demo',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/runs/not-a-uuid').status_code==422
    assert client.post('/api/datasets',files={'file':('a.csv',b'a,a\n1,2')}).status_code==422
    d=client.post('/api/demo').json()
    base={'dataset_id':d['dataset_id'],'target':'outcome','question':'Analyze this dataset'}
    assert client.post('/api/runs',json=base).status_code==422
    assert client.post('/api/runs',json={**base,'independent_rows':True,'target':'nope'}).status_code==422
    assert client.post('/api/runs',json={**base,'independent_rows':True,'allow_literature':True}).status_code==422
