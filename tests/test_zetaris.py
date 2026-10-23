"""Read-only guard and failure paths for backend.zetaris; no network required."""
import pytest
import backend.zetaris as zetaris


@pytest.mark.parametrize('sql', [
    'SELECT 1',
    '  select * from NY_TAXI.taxi_zones limit 5',
    'SHOW LIGHTNING DATABASES',
    'DESCRIBE NY_TAXI.taxi_zones',
    'WITH x AS (SELECT 1 AS n) SELECT * FROM x',
    '(SELECT 1)',
])
def test_read_only_statements_are_allowed(sql):
    assert zetaris.is_read_only(sql) is True


@pytest.mark.parametrize('sql', [
    'DROP TABLE taxi_zones',
    'INSERT INTO t VALUES (1)',
    'DELETE FROM t',
    'CREATE TABLE t (a INT)',
    'UPDATE t SET a = 1',
    'ALTER TABLE t ADD COLUMN b INT',
])
def test_mutating_statements_are_rejected_by_the_guard(sql):
    assert zetaris.is_read_only(sql) is False


def test_unconfigured_returns_disabled_without_network(monkeypatch):
    monkeypatch.delenv('ZETARIS_API_KEY', raising=False)
    monkeypatch.delenv('ZETARIS_ORG_ID', raising=False)
    result = zetaris.run_sql('SELECT 1')
    assert result['status'] == 'disabled'
    assert 'ZETARIS_API_KEY' in result['message']


def test_rejected_statement_never_reaches_the_network(monkeypatch):
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    monkeypatch.setenv('ZETARIS_REST_URL', 'http://127.0.0.1:1/api/v1.0')
    result = zetaris.run_sql('DROP TABLE taxi_zones')
    # A rejected statement must not raise a connection error: it never left the module.
    assert result['status'] == 'rejected'
    assert result['rows'] == []
    assert result['query_id']


def test_failed_request_is_reported_not_raised(monkeypatch):
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    # Nothing listens here, so this exercises the failure path.
    monkeypatch.setenv('ZETARIS_REST_URL', 'http://127.0.0.1:1/api/v1.0')
    result = zetaris.run_sql('SELECT 1', timeout=2)
    assert result['status'] == 'failed'
    assert 'Zetaris request failed' in result['message']


def test_identifier_guard_on_helpers(monkeypatch):
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    assert zetaris.describe_source('NY_TAXI; DROP TABLE x')['status'] == 'rejected'
    assert zetaris.preview_rows('NY_TAXI', 'taxi_zones) --', 5)['status'] == 'rejected'
