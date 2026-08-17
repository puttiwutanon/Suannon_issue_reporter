import os
import httpx
from fastapi import HTTPException
from .config import logger

D1_QUERY_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}"
    "/d1/database/{database_id}/query"
)


def _run(sql: str, params: list | tuple | None = None) -> list[dict]:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    database_id = os.getenv("CLOUDFLARE_D1_DATABASE_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not all([account_id, database_id, api_token]):
        raise HTTPException(
            status_code=500,
            detail="D1 is not configured (missing CLOUDFLARE_* env vars)",
        )

    url = D1_QUERY_URL.format(account_id=account_id, database_id=database_id)
    body = {"sql": sql, "params": list(params) if params else []}

    try:
        resp = httpx.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        data = resp.json()
    except Exception as e:
        logger.error(f"❌ D1 request error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database connection failure")

    if not data.get("success"):
        logger.error(f"❌ D1 query error: {data.get('errors')}")
        raise HTTPException(status_code=500, detail="Database query failed")

    # D1's /query endpoint returns one result block per SQL statement.
    # We only ever send one statement at a time, so take the first.
    result_block = data["result"][0]
    return result_block.get("results", [])


def fetch_all(sql: str, params: list | tuple | None = None) -> list[dict]:
    return _run(sql, params)


def fetch_one(sql: str, params: list | tuple | None = None) -> dict | None:
    rows = _run(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: list | tuple | None = None) -> dict | None:
    """For INSERT/UPDATE/DELETE. If the SQL has a RETURNING clause,
    returns the first returned row as a dict; otherwise returns None."""
    rows = _run(sql, params)
    return rows[0] if rows else None
