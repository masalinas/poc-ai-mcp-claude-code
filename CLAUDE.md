# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a [FastMCP](https://github.com/jlowin/fastmcp)-based Model Context Protocol server and client that exposes a single tool — `get_customer_orders_above_amount` — for querying customer orders from PostgreSQL. The server supports both stdio (default) and HTTP transports.

## Prerequisites

- **Python ≥ 3.10** (required by fastmcp; the system Python on this machine is 3.8, so use a venv or pyenv with 3.10+)
- **PostgreSQL** instance accessible via environment variables

## Quick Start

```bash
# Set up database schema and seed data
psql -d orders_db -f schema.sql
psql -d orders_db -f seed.sql

# Configure credentials
cp .env.example .env   # edit with your DB connection details

# Install dependencies (requires Python ≥ 3.10)
pip install -r requirements.txt

# Run the demo client (connects to the server via stdio automatically)
python mcp_client.py
```

## Architecture

### Core Files

| File | Role |
|------|------|
| `mcp_server.py` | FastMCP server. Creates an asyncpg connection pool on startup, exposes one tool, supports `--transport http --port 9000` or stdio (default). |
| `mcp_client.py` | Demo client that launches the server as a stdio subprocess via `PythonStdioTransport`, runs three test scenarios (by ID, by email, error case), and prints results as a formatted table. |
| `schema.sql` | DDL for `customers` and `orders` tables plus a composite index on `(customer_id, total_amount DESC, order_date DESC)`. |
| `seed.sql` | Idempotent sample data (3 customers, 11 orders). |

### Key Design Details

- **Connection pool lifecycle** is managed via FastMCP's `lifespan` hook (`_db_lifespan`). The pool is created on server start and closed on shutdown — no ad-hoc connections.
- **Tool signature**: `get_customer_orders_above_amount(customer_id: int | None, customer_email: str | None, min_amount: float) -> list[dict[str, Any]]`. At least one of `customer_id` or `customer_email` is required; `customer_id` takes precedence if both are given.
- **Error handling**: errors are returned as `[{"error": "..."}]` dicts — raw exceptions never leak to the client.
- **All SQL queries are parameterized** (`$1`, `$2` placeholders) to prevent SQL injection.

### Dependencies

- `fastmcp>=3.0` — MCP server/client framework
- `asyncpg>=0.29` — async PostgreSQL driver
- `python-dotenv>=1.0` — environment variable loading from `.env`

## Testing

There is no formal test suite (no pytest or unittest). The demo client (`mcp_client.py`) serves as the integration test — it validates three scenarios: query by ID, query by email, and an expected-error case.

To test manually with the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

## Environment Configuration

The `.env` file (not committed; see `.env.example`) must define: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. The server loads these via `load_dotenv()` at startup.
