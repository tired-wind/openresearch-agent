"""Download two explicitly licensed UCI datasets; preserve originals under ignored data/."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'heart': {
        'url': 'https://archive.ics.uci.edu/static/public/45/heart+disease.zip',
        'page': 'https://archive.ics.uci.edu/dataset/45/heart+disease',
        'sha256': 'b17cd273da9ce1caa4710fce80227ea454d4dbf9fcbc8e6a9121672751563adc',
        'member': 'processed.cleveland.data', 'dictionary': 'heart-disease.names',
        'target': 'disease_present', 'rows': 303,
        'attribution': 'Janosi, Steinbrunn, Pfisterer & Detrano (1989). Heart Disease. UCI. DOI:10.24432/C52P4X',
    },
    'breast': {
        'url': 'https://archive.ics.uci.edu/static/public/17/breast+cancer+wisconsin+diagnostic.zip',
        'page': 'https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic',
        'sha256': 'bc154869ef13f753f9e2b5a17e248cfe1ba4b6721db7c4da9f4880e40b05d3af',
        'member': 'wdbc.data', 'dictionary': 'wdbc.names',
        'target': 'diagnosis', 'rows': 569,
        'attribution': 'Wolberg, Mangasarian, Street & Street (1993). Breast Cancer Wisconsin (Diagnostic). UCI. DOI:10.24432/C5DW2B',
    },
}
HEART_COLUMNS = 'age sex cp trestbps chol fbs restecg thalach exang oldpeak slope ca thal num'.split()
HEART_CATEGORIES = {'sex': {0, 1}, 'cp': {1, 2, 3, 4}, 'fbs': {0, 1},
                    'restecg': {0, 1, 2}, 'exang': {0, 1}, 'slope': {1, 2, 3}, 'thal': {3, 6, 7}}
MORPHOLOGY = 'radius texture perimeter area smoothness compactness concavity concave_points symmetry fractal_dimension'.split()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(raw: bytes, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(io.BytesIO(raw), header=None, na_values=['?'])
    if dataset == 'heart':
        if df.shape[1] != 14:
            raise ValueError('Expected 14 Cleveland columns.')
        df.columns = HEART_COLUMNS
        df = df.apply(pd.to_numeric, errors='raise')
        if df['num'].isna().any() or not set(df['num']) <= {0, 1, 2, 3, 4}:
            raise ValueError('Unexpected heart outcome codes.')
        # Drop the original outcome, or it would reveal the binary target exactly.
        df['disease_present'] = (df.pop('num') > 0).astype(int)
        for col, allowed in HEART_CATEGORIES.items():
            if not set(df[col].dropna()) <= allowed:
                raise ValueError(f'Unexpected category in {col}.')
            df[col] = df[col].map(lambda x: f'{col}_{int(x)}' if pd.notna(x) else None)
        changes = ['Use processed.cleveland.data only; archive WARNING flags cleveland.data as corrupt.',
                   'Replace num with disease_present=(num>0); remove num from predictors.',
                   'Parse ? as missing; preserve missing rows for training-only imputation.',
                   'Prefix sex/cp/fbs/restecg/exang/slope/thal codes to preserve nominal types in CSV.']
    elif dataset == 'breast':
        if df.shape[1] != 32:
            raise ValueError('Expected 32 WDBC columns.')
        df.columns = ['patient_id', 'diagnosis'] + [f'{x}_{s}' for s in ('mean', 'se', 'worst') for x in MORPHOLOGY]
        df = df.drop(columns=['patient_id'])
        if df['diagnosis'].isna().any() or not set(df['diagnosis']) <= {'M', 'B'}:
            raise ValueError('Unexpected diagnosis codes.')
        df.loc[:, df.columns != 'diagnosis'] = df.drop(columns='diagnosis').apply(pd.to_numeric, errors='raise')
        changes = ['Drop patient ID.', 'Preserve diagnosis M=malignant, B=benign.',
                   'Name features in source order: mean, standard error, worst (largest-three mean).']
    else:
        raise ValueError('Unknown dataset.')
    return df, changes


def fetch(dataset: str) -> dict:
    source = SOURCES[dataset]
    folder = ROOT / 'data' / 'public' / f'uci-{dataset}'
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / 'source.zip'
    if archive.exists():
        raw = archive.read_bytes()
    else:
        with httpx.stream('GET', source['url'], timeout=30, follow_redirects=False) as response:
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > 1024 * 1024:
                    raise ValueError('Download exceeds 1 MiB limit.')
                chunks.append(chunk)
            raw = b''.join(chunks)
    if digest(raw) != source['sha256']:
        raise ValueError('Source archive changed. Review source and checksum before updating; no data replaced.')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        member = z.read(source['member'])
        dictionary = z.read(source['dictionary'])
    df, changes = prepare(member, dataset)
    if len(df) != source['rows']:
        raise ValueError('Unexpected source row count.')
    if not archive.exists():
        archive.write_bytes(raw)
    output = df.to_csv(index=False).encode()
    (folder / 'prepared.csv').write_bytes(output)
    (folder / source['dictionary']).write_bytes(dictionary)
    manifest = {**source, 'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                'verified_at': datetime.now(timezone.utc).isoformat(), 'member_sha256': digest(member),
                'prepared_sha256': digest(output), 'columns': list(df.columns),
                'missing_by_column': {k: int(v) for k, v in df.isna().sum().items() if v},
                'class_counts': {str(k): int(v) for k, v in df[source['target']].value_counts().items()},
                'transformations': changes, 'python': platform.python_version(), 'pandas': pd.__version__,
                'scope': 'Historical benchmark; not causal evidence, prospective risk prediction, or clinical validation.'}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'dataset': dataset, 'path': str(folder / 'prepared.csv'),
                      'rows': len(df), 'columns': len(df.columns), 'target': source['target']}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=['heart', 'breast', 'all'])
    args = parser.parse_args()
    for name in SOURCES if args.dataset == 'all' else [args.dataset]:
        fetch(name)
