"""Exercise the running local API on both prepared public datasets, without literature calls."""
import json
import time
from pathlib import Path

import httpx

from scripts.fetch_public_data import SOURCES, digest

ROOT = Path(__file__).resolve().parents[1]


def main():
    summaries = []
    with httpx.Client(base_url='http://127.0.0.1:8018', timeout=20) as client:
        client.get('/api/health').raise_for_status()
        for dataset, source in SOURCES.items():
            folder = ROOT / 'data/public' / f'uci-{dataset}'
            raw = (folder / 'prepared.csv').read_bytes()
            response = client.post('/api/datasets', files={'file': ('prepared.csv', raw, 'text/csv')})
            response.raise_for_status()
            uploaded = response.json()
            response = client.post('/api/runs', json={
                'dataset_id': uploaded['dataset_id'], 'target': source['target'],
                'question': 'Which measured features help distinguish recorded diagnoses within this historical cohort?',
                'task': 'classification', 'independent_rows': True, 'allow_literature': False,
            })
            response.raise_for_status()
            run_id = response.json()['id']
            deadline = time.monotonic() + 170
            while time.monotonic() < deadline:
                response = client.get(f'/api/runs/{run_id}')
                response.raise_for_status()
                run = response.json()
                if run['status'] in ('completed_with_warnings', 'failed'):
                    break
                time.sleep(1)
            else:
                raise TimeoutError(f'{dataset} API run did not finish.')
            if run['status'] != 'completed_with_warnings':
                raise RuntimeError(f'{dataset} failed: {run.get("error")}')
            (folder / 'api-run.json').write_text(json.dumps(run, indent=2) + '\n')
            analysis = run['result']['analysis']
            if run['result']['provenance']['sha256'] != digest(raw):
                raise RuntimeError('Report provenance does not match the uploaded dataset.')
            response = client.get(f'/api/runs/{run_id}/report')
            response.raise_for_status()
            (folder / 'report.md').write_text(response.text)
            summary = {'dataset': dataset, 'source': source['page'], 'prepared_sha256': digest(raw),
                       'run_id': run_id, 'status': run['status'], 'n_analyzed': analysis['n_analyzed'],
                       'n_train': analysis['n_train'], 'n_test': analysis['n_test'],
                       'metrics': analysis['metrics'], 'scope': 'API engineering smoke test; no clinical or external validity established.'}
            summaries.append(summary)
            print(json.dumps(summary))
    (ROOT / 'data/public/smoke-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')


if __name__ == '__main__':
    main()
