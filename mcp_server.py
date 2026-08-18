"""
MCP Server — exposes a tool to query PostgreSQL for customer orders.

Usage (stdio, default):
    python mcp_server.py

Usage (HTTP transport):
    python mcp_server.py --transport http --port 9000
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from typing import Any, AsyncIterator

import asyncpg
from dotenv import load_dotenv
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load environment variables from .env (if present) before anything else.
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Database connection pool — initialised inside the lifespan hook.
# ---------------------------------------------------------------------------
_db_pool: asyncpg.Pool | None = None


def _get_dsn() -> str:
    """Build a PostgreSQL DSN from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")

    if not all((dbname, user, password)):
        raise RuntimeError(
            "Missing required DB env vars: DB_NAME, DB_USER, DB_PASSWORD. "
            "Copy .env.example to .env and fill in the values."
        )

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@contextlib.asynccontextmanager
async def _db_lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Create / destroy the asyncpg connection pool at server start / stop."""
    global _db_pool

    try:
        _db_pool = await asyncpg.create_pool(
            dsn=_get_dsn(),
            min_size=2,
            max_size=10,
        )
        # Quick health-check so we fail loudly on bad credentials.
        async with _db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("PostgreSQL connection pool initialised")
    except Exception as exc:
        logger.error("Failed to create DB pool: %s", exc)
        raise

    yield  # server runs here while the pool lives

    if _db_pool is not None:
        await _db_pool.close()
        logger.info("PostgreSQL connection pool closed")


# ---------------------------------------------------------------------------
# Server instance — lifespan hook passed as a constructor kwarg.
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "orders-mcp-server",
    instructions="Provides tools for querying customer orders from PostgreSQL.",
    lifespan=_db_lifespan,
)


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------
@mcp.tool()
async def get_customer_orders_above_amount(
    customer_id: int | None = None,
    customer_email: str | None = None,
    min_amount: float = 0.0,
) -> list[dict[str, Any]]:
    """Retrieve a customer's orders whose total exceeds a minimum amount in euros.

    Look up the customer either by ``customer_id`` or by ``customer_email``.
    Returns all orders where ``total_amount >= min_amount``, ordered by
    ``order_date`` descending.

    Parameters
    ----------
    customer_id : int | None
        Primary key of the customer record.  Takes precedence over
        ``customer_email`` if both are supplied.
    customer_email : str | None
        Email address of the customer (alternative lookup).  Used when
        ``customer_id`` is not provided.
    min_amount : float
        Minimum order value in euros (inclusive).  Default is 0.0 (no filter).

    Returns
    -------
    list[dict]
        Each dict contains keys: ``order_id``, ``order_date``,
        ``total_amount``, ``status``.  An empty list means no orders matched.
        On error a single dict with an ``error`` key is returned instead.
    """

    # ---- validation -------------------------------------------------
    if min_amount < 0:
        return [{"error": f"min_amount must be >= 0; got {min_amount}"}]

    if customer_id is None and customer_email is None:
        return [
            {"error": "Provide at least one of: customer_id or customer_email"}
        ]

    # ---- resolve customer_id ----------------------------------------
    resolved_id: int | None = None

    if customer_id is not None:
        resolved_id = customer_id
    elif customer_email is not None:
        try:
            async with _db_pool.acquire() as conn:  # type: ignore[union-attr]
                resolved_id = await conn.fetchval(
                    "SELECT id FROM customers WHERE email = $1",
                    customer_email,
                )
        except Exception as exc:
            logger.error("DB error while resolving customer: %s", exc)
            return [{"error": f"Database error: {exc}"}]

    if resolved_id is None:
        lookup_value = (
            str(customer_id)
            if customer_id is not None
            else customer_email
        )  # type: ignore[assignment]
        return [{"error": f"Customer not found ({lookup_value})"}]

    # ---- fetch orders -----------------------------------------------
    try:
        async with _db_pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT id           AS order_id,
                       order_date,
                       total_amount,
                       status
                FROM   orders
                WHERE  customer_id  = $1
                  AND  total_amount >= $2
                ORDER BY order_date DESC
                """,
                resolved_id,
                min_amount,
            )
    except Exception as exc:
        logger.error("DB error while fetching orders: %s", exc)
        return [{"error": f"Database error: {exc}"}]

    # ---- serialise --------------------------------------------------
    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "order_id":     row["order_id"],
                "order_date":   str(row["order_date"]),
                "total_amount": float(row["total_amount"]),
                "status":       row["status"],
            }
        )

    return results


# ---------------------------------------------------------------------------
# Entrypoint — stdio (default) or HTTP transport for remote clients.
# ---------------------------------------------------------------------------
def _parse_args():
    """Minimal argument parser to avoid adding a dependency."""
    transport = "stdio"
    port: int = 9000
    host = "127.0.0.1"

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--transport", "-t"):
            i += 1
            transport = args[i] if i < len(args) else "stdio"
        elif args[i] in ("--port", "-p"):
            i += 1
            port = int(args[i]) if i < len(args) else 9000
        elif args[i] in ("--host",):
            i += 1
            host = args[i] if i < len(args) else "127.0.0.1"
        i += 1

    return transport, host, port


def main() -> None:
    transport, host, port = _parse_args()

    logger.info("Starting MCP server (transport=%s)", transport)

    if transport == "http":
        mcp.run(transport="http", host=host, port=port)
    else:
        # stdio — the default for local MCP servers
        mcp.run()


if __name__ == "__main__":
    main()
