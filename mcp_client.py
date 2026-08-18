"""
MCP Client — connects to the orders MCP server via stdio and demonstrates
calling the ``get_customer_orders_above_amount`` tool.

Usage:
    python mcp_client.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

# ---------------------------------------------------------------------------
# Path to the server script (sibling file in the same directory)
# ---------------------------------------------------------------------------
_SERVER_SCRIPT = Path(__file__).parent / "mcp_server.py"


def _build_client() -> Client:
    """Create a client that launches the MCP server as a stdio subprocess."""
    transport = PythonStdioTransport(
        str(_SERVER_SCRIPT),
        # The .env file lives next to mcp_server.py — pass cwd so dotenv loads it.
        cwd=str(Path(__file__).parent),
    )
    return Client(transport)


def _print_orders(orders: list[dict] | None) -> None:
    """Pretty-print a list of order dicts as a formatted table."""
    if not orders:
        print("  (no orders matched the filter)")
        return

    print(
        f"  {'Order ID':<10} {'Date':<14} "
        f"{'Amount (€)':<14} {'Status'}"
    )
    print("  " + "-" * 52)
    for order in orders:
        print(
            f"  {order['order_id']:<10} "
            f"{order['order_date']:<14} "
            f"{order['total_amount']:>12.2f} €   "
            f"{order['status']}"
        )
    print(f"\n  → {len(orders)} order(s) found")


async def demo() -> None:
    """Connect to the MCP server and call the orders tool."""

    print("=" * 60)
    print("  MCP Client Demo — get_customer_orders_above_amount")
    print("=" * 60)

    # --- Test 1: query by customer_id ----------------------------------
    print("\n[TEST 1] Orders for customer_id=1 with min_amount=100.0\n")

    try:
        async with _build_client() as client:
            result = await client.call_tool(
                "get_customer_orders_above_amount",
                {"customer_id": 1, "min_amount": 100.0},
            )

        # Result may contain errors or order dicts
        data = result.data if hasattr(result, "data") else result
        if isinstance(data, list) and any("error" in d for d in data):
            for err in data:
                print(f"  ⚠ {err['error']}")
        else:
            _print_orders(data)

    except Exception as exc:
        print(f"  ❌ Failed to connect or call tool: {exc}")

    # --- Test 2: query by email ----------------------------------------
    print("\n[TEST 2] Orders for 'carlos@example.com' with min_amount=300.0\n")

    try:
        async with _build_client() as client:
            result = await client.call_tool(
                "get_customer_orders_above_amount",
                {"customer_email": "carlos@example.com", "min_amount": 300.0},
            )

        data = result.data if hasattr(result, "data") else result
        if isinstance(data, list) and any("error" in d for d in data):
            for err in data:
                print(f"  ⚠ {err['error']}")
        else:
            _print_orders(data)

    except Exception as exc:
        print(f"  ❌ Failed to connect or call tool: {exc}")

    # --- Test 3: error case — customer not found -----------------------
    print("\n[TEST 3] Lookup nonexistent email (expecting error)\n")

    try:
        async with _build_client() as client:
            result = await client.call_tool(
                "get_customer_orders_above_amount",
                {
                    "customer_email": "nobody@nowhere.com",
                    "min_amount": 0.0,
                },
            )

        data = result.data if hasattr(result, "data") else result
        if isinstance(data, list) and any("error" in d for d in data):
            for err in data:
                print(f"  ⚠ {err['error']}")
        else:
            print(f"  Unexpected success: {data}")

    except Exception as exc:
        print(f"  ❌ Connection error: {exc}")

    print("\n" + "=" * 60)
    print("  Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
