# FastMCP Orders Server

A Model Context Protocol (MCP) server built with [FastMCP](https://github.com/jlowin/fastmcp) that exposes a tool for querying customer orders from a PostgreSQL database.

---

## Project Structure

```
├── mcp_server.py        # FastMCP server — stdio transport (default), HTTP optional
├── mcp_client.py        # Demo client — connects via stdio, calls the tool
├── .env.example         # Template for DB credentials
├── requirements.txt     # Python dependencies
├── schema.sql           # DDL to create customers + orders tables
├── seed.sql             # Sample data for local testing
└── README.md            # This file
```

---

## Prerequisites

- **Python** ≥ 3.10
- **PostgreSQL** instance with a database containing the schema described below

### Database Schema

The server expects two tables:

| Table      | Columns                                      |
|------------|----------------------------------------------|
| `customers`| `id` (PK), `name` (text), `email` (text, unique) |
| `orders`   | `id` (PK), `customer_id` (FK→customers), `order_date`, `total_amount` (numeric, €), `status` |

Run the provided SQL files to create them:

```bash
psql -d orders_db -f schema.sql
psql -d orders_db -f seed.sql
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure database credentials

Copy the env template and fill in your connection details:

```bash
cp .env.example .env
nano .env   # edit values to match your PostgreSQL instance
```

---

## Running the Server

### Stdio transport (default)

```bash
python mcp_server.py
```

This is the standard mode for local MCP servers and works with Claude Desktop, the MCP Inspector, and any stdio-compatible client.

### HTTP transport (optional — remote clients)

```bash
python mcp_server.py --transport http --port 9000
```

Useful when clients need a remote HTTP endpoint instead of a local process.

---

## Running the Demo Client

The bundled client connects to the server via stdio and runs three test scenarios:

```bash
python mcp_client.py
```

**Expected output** (with seed data loaded):

```
[TEST 1] Orders for customer_id=1 with min_amount=100.0
  Order ID   Date          Amount (€)     Status
  --------------------------------------------------------
  5          2025-06-15    180.75 €       completed
  3          2025-03-01    520.00 €       shipped
  1          2025-01-10    250.00 €       completed

  → 3 order(s) found

[TEST 2] Orders for 'carlos@example.com' with min_amount=300.0
  Order ID   Date          Amount (€)     Status
  --------------------------------------------------------
  8          2025-05-10    890.00 €       shipped
  6          2025-02-01    340.00 €       completed

  → 2 order(s) found

[TEST 3] Lookup nonexistent email (expecting error)
  ⚠ Customer not found (nobody@nowhere.com)
```

---

## Testing with the MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is an interactive tool for exploring MCP servers.

```bash
npx @modelcontextprotocol/inspector node mcp_server.js
```

For Python servers:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

1. The inspector opens a browser window on `http://localhost:6287`.
2. In the UI, locate **get_customer_orders_above_amount** under *Tools*.
3. Fill in parameters (e.g., `{"customer_id": 1, "min_amount": 100}`) and click **Call**.
4. Inspect the structured JSON response.

---

## Tool Specification

### `get_customer_orders_above_amount`

Retrieve a customer's orders whose total exceeds a minimum amount in euros.

| Parameter        | Type             | Required | Description                                           |
|------------------|------------------|----------|-------------------------------------------------------|
| `customer_id`    | `int \| None`    | No       | Primary key of the customer (takes precedence if both given) |
| `customer_email` | `str \| None`    | No       | Email address for alternative lookup                   |
| `min_amount`     | `float`          | No       | Minimum order value in € (inclusive, default 0.0)     |

At least one of `customer_id` or `customer_email` must be provided.

**Returns:** `list[dict]` — each dict has keys `order_id`, `order_date`, `total_amount`, `status`. Results are ordered by `order_date` descending.

**Error responses** are returned as a list containing a single dict with an `"error"` key (no raw stack traces leak to the client).

---

## Security Notes

- **No hardcoded credentials** — all DB parameters come from environment variables loaded via `python-dotenv`.
- **Parameterized queries only** — SQL injection is prevented by using `$1`, `$2` placeholders throughout.
- **Connection pooling** — an `asyncpg` pool (2–10 connections) is created once at server startup and closed at shutdown.
