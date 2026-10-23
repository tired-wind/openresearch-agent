"""Zetaris is the data layer: every number comes from a real SQL execution.

Direct REST route. One statement per call. Values come back as strings -- REST
returns text for every type, and decimals may use exponent notation, so convert
before comparing. Read-only by default: only SELECT/SHOW/DESCRIBE/WITH/EXPLAIN
leave this module, because an agent must not mutate the governed dataset.
"""
from __future__ import annotations
import os
import re
from typing import Any
from uuid import uuid4
import httpx

DEFAULT_REST = 'http://localhost:8888/api/v1.0'
MAX_ROWS = 1000
READ_ONLY = ('select', 'show', 'describe', 'desc', 'with', 'explain')


def settings() -> tuple[str, str, str]:
    rest = (os.environ.get('ZETARIS_REST_URL') or DEFAULT_REST).rstrip('/')
    return rest, os.environ.get('ZETARIS_ORG_ID', ''), os.environ.get('ZETARIS_API_KEY', '')


def configured() -> bool:
    rest, org, key = settings()
    return bool(rest and org and key)


def is_read_only(sql: str) -> bool:
    # Conservative guard, not a substitute for a read-only Zetaris account.
    # Reject multiple statements/comments and any mutating token, including
    # writes behind WITH/EXPLAIN. Some harmless queries are intentionally refused.
    if not sql or any(marker in sql for marker in (';', '--', '/*', '*/', '\x00')):
        return False
    tokens = set(re.findall(r'[a-z_]+', sql.lower()))
    if tokens & {'insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate',
                 'merge', 'replace', 'grant', 'revoke', 'copy', 'into', 'call',
                 'execute', 'exec', 'load', 'set', 'use', 'cache', 'uncache', 'refresh', 'analyze'}:
        return False
    stripped = sql.strip().lstrip('(').strip()
    first = stripped.split(None, 1)[0].lower() if stripped else ''
    return first in READ_ONLY


def run_sql(sql: str, limit: int = MAX_ROWS, *, client: httpx.Client | None = None, timeout: float = 120.0) -> dict[str, Any]:
    """Execute one statement against Zetaris and return a provenance-carrying result.

    Never raises for expected failures: the caller gets status='failed' plus a
    message, mirroring backend.literature.retrieve.
    """
    rest, org, key = settings()
    query_id = str(uuid4())
    base = {'sql': sql, 'query_id': query_id, 'headers': [], 'rows': [], 'total': 0, 'time_used_ms': None}
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        return {**base, 'status': 'rejected', 'message': 'Row limit must be an integer between 1 and 1000.'}
    if not (rest and org and key):
        return {**base, 'status': 'disabled', 'message': 'Zetaris is not configured; set ZETARIS_REST_URL, ZETARIS_ORG_ID and ZETARIS_API_KEY.'}
    if not is_read_only(sql):
        return {**base, 'status': 'rejected', 'message': 'Only read-only statements are allowed; the governed dataset is never modified here.'}

    own = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=False)
    try:
        response = client.post(
            f'{rest}/sql-editor/sqls/run',
            headers={
                'Authorization': f'Bearer {key}',
                'X-Org-ID': org,
                'X-Request-ID': str(uuid4()),
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={'queryId': query_id, 'sql': sql, 'source': 'SqlEditor', 'limit': limit},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError('Unexpected response body')
        headers = body.get('headers') or []
        rows = body.get('data') or []
        return {
            **base,
            'status': 'ok',
            'headers': [str(h) for h in headers],
            'rows': rows if isinstance(rows, list) else [],
            'total': int(body.get('total') or len(rows) or 0),
            'time_used_ms': body.get('timeUsed'),
            'message': f'Executed against Zetaris as read-only SQL; {len(rows)} row(s) returned.',
        }
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response is not None else ''
        hint = ' Check that X-Org-ID is the numeric organisation ID.'
        if exc.response is not None and exc.response.status_code == 401:
            hint = ' The API key is missing, wrong or expired: create a fresh key under Management > API Tokens.'
        return {**base, 'status': 'failed', 'message': f'Zetaris returned HTTP {exc.response.status_code if exc.response is not None else "?"}.{hint} {detail}'.strip()}
    except Exception as exc:
        return {**base, 'status': 'failed', 'message': f'Zetaris request failed ({type(exc).__name__}): {exc}'}
    finally:
        if own:
            client.close()


def list_databases(client: httpx.Client | None = None) -> dict[str, Any]:
    """Registered Lightning databases (sample data and file/REST sources)."""
    return run_sql('SHOW LIGHTNING DATABASES', client=client)


def describe_source(name: str, client: httpx.Client | None = None) -> dict[str, Any]:
    """Tables inside one registered source, qualified as <source>.<table>."""
    if not name.replace('_', '').isalnum():
        return {'status': 'rejected', 'sql': '', 'query_id': '', 'headers': [], 'rows': [], 'total': 0, 'time_used_ms': None, 'message': 'Source names must be alphanumeric or underscore.'}
    return run_sql(f'SHOW TABLES IN {name}', client=client)


def preview_rows(source: str, table: str, limit: int = 5, client: httpx.Client | None = None) -> dict[str, Any]:
    """Read a few rows from <source>.<table> without touching anything else."""
    for part in (source, table):
        if not part.replace('_', '').isalnum():
            return {'status': 'rejected', 'sql': '', 'query_id': '', 'headers': [], 'rows': [], 'total': 0, 'time_used_ms': None, 'message': 'Identifiers must be alphanumeric or underscore.'}
    return run_sql(f'SELECT * FROM {source}.{table} LIMIT {int(limit)}', limit=limit, client=client)
