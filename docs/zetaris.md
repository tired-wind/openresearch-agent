# Zetaris integration (DATA layer)

Zetaris is the governed data layer the agent reasons over. The event requires it
running locally; the adapter here is the only path from this codebase to it.

## Route and contract

Direct REST, one statement per call:

```text
POST {ZETARIS_REST_URL}/sql-editor/sqls/run
Authorization: Bearer <ZETARIS_API_KEY>
X-Org-ID: <numeric organisation id>
X-Request-ID: <fresh UUID per request>
{"queryId": "<uuid>", "sql": "...", "source": "SqlEditor", "limit": 1000}
```

Response shape actually observed on the local install:

```json
{"headers": ["one"], "data": [["1"]], "total": 1, "timeUsed": 63}
```

**Every value comes back as a string**, and decimals may use exponent notation.
Convert before comparing; never assume a JSON number.

## Decisions

- **Read-only by default.** `run_sql` rejects anything that is not
  `SELECT / SHOW / DESCRIBE / DESC / WITH / EXPLAIN` before a request is built.
  The governed dataset must not be mutated by an agent, and the retrieval story
  is only credible if the data it cites cannot change underneath it.
- **Failures are returned, not raised.** `status='failed'` with a message, the
  same shape `backend/literature.py` uses, so one outage cannot crash a run.
  A 401 message points at `Management > API Tokens`; a 400 points at `X-Org-ID`.
- **`query_id` is kept.** Every execution returns the UUID it was sent with, so a
  report can cite the exact query that produced a number.
- **Identifier guard.** `describe_source` / `preview_rows` reject anything that
  is not alphanumeric or underscore, because those names are interpolated into
  SQL (statement execution, not parameters).

## Credentials

`ZETARIS_API_KEY` lives in `.env` only (gitignored). It is created in the UI at
**Management → API Tokens**; the platform shows it once, allows three per user,
and each carries an expiry. `ZETARIS_ORG_ID` is the numeric ID from
**Management → Organisation**, not the name.

## Verify

```bash
python scripts/check_zetaris.py            # SELECT 1, SHOW LIGHTNING DATABASES, SHOW DATASOURCES
python scripts/check_zetaris.py --raw      # include the raw response body
python scripts/check_zetaris.py "SHOW TABLES IN NY_TAXI"
python -m pytest tests/test_zetaris.py -q
```

## Current limits

- The agent's analysis still runs on uploaded CSV locally; wiring a Zetaris
  dataset as the *source* of the analysed table is the next step, and
  `run_sql` is the only interface it needs.
- Files on this laptop are not visible to Zetaris; a file must sit in storage the
  platform can reach (for example S3) before it can be registered.
- No write path, by design.


## Integration review boundary

The client guard conservatively refuses semicolons, comments, mutating keywords and invalid row limits, including writes hidden behind WITH or EXPLAIN. It is not a SQL authorization engine and cannot guarantee side-effect-free functions. Use a server account with actual read-only permissions. The adapter is not exposed as an Agent tool and is not yet the dashboard data source. Live connectivity in the handoff log was reported on the contributor Windows machine, not independently repeated on the maintainer Mac.
