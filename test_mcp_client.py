"""
Smoke test for grid_mcp_server.py.

Spawns the MCP server as a subprocess, connects to it over stdio using
the MCP Python client SDK, and exercises each of the six tools to
verify protocol-level behavior end-to-end. Prints a short report.

Run from the project root with the venv active:
    python test_mcp_client.py

Exits with code 0 on success, non-zero on any tool failure.
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(_THIS_DIR, "grid_mcp_server.py")


def _payload(result):
    """Extract the JSON dict a FastMCP tool returned.

    FastMCP serializes a tool's dict return value into a single text
    content block, so we parse that block as JSON.
    """
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    raise RuntimeError(f"No text content in tool result: {result}")


async def main():
    params = StdioServerParameters(
        command=sys.executable,  # same interpreter that's running this script
        args=[SERVER_SCRIPT],
    )

    print("Connecting to grid MCP server over stdio...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # ----- list_tools -----
            tools = (await session.list_tools()).tools
            names = [t.name for t in tools]
            print(f"\n{len(tools)} tools registered: {names}")
            expected = {
                "get_neighbors", "is_wall", "heuristic_distance",
                "make_move", "get_state", "reset",
            }
            missing = expected - set(names)
            assert not missing, f"Missing tools: {missing}"

            # ----- get_state (baseline) -----
            print("\n--- get_state (baseline) ---")
            state = _payload(await session.call_tool("get_state", {}))
            print(f"  pos={state['current_pos']}  goal={state['goal']}  "
                  f"grid={state['width']}x{state['height']}")
            start = tuple(state["current_pos"])
            goal = tuple(state["goal"])

            # ----- is_wall (sample three cells) -----
            print("\n--- is_wall ---")
            for x, y in [start, (-1, -1), goal]:
                r = _payload(await session.call_tool("is_wall", {"x": x, "y": y}))
                print(f"  is_wall({x},{y}) -> {r['status']}")

            # ----- get_neighbors of start -----
            print("\n--- get_neighbors ---")
            sx, sy = start
            nbrs = _payload(await session.call_tool(
                "get_neighbors", {"x": sx, "y": sy}))
            print(f"  neighbors of {start} -> {nbrs['neighbors']}")
            assert nbrs["neighbors"], "Start has no passable neighbors -- bad grid?"

            # ----- heuristic_distance start -> goal -----
            print("\n--- heuristic_distance ---")
            gx, gy = goal
            h = _payload(await session.call_tool(
                "heuristic_distance",
                {"from_x": sx, "from_y": sy, "to_x": gx, "to_y": gy}))
            expected_h = abs(sx - gx) + abs(sy - gy)
            print(f"  Manhattan({start}, {goal}) = {h['distance']} "
                  f"(expected {expected_h})")
            assert h["distance"] == expected_h

            # ----- make_move: invalid (non-adjacent) -----
            print("\n--- make_move (invalid: non-adjacent) ---")
            bad = _payload(await session.call_tool(
                "make_move", {"x": gx, "y": gy}))
            print(f"  success={bad['success']}  error={bad.get('error', '')!r}")
            assert bad["success"] is False

            # ----- make_move: valid step -----
            print("\n--- make_move (valid step) ---")
            nx, ny = nbrs["neighbors"][0]
            step = _payload(await session.call_tool(
                "make_move", {"x": nx, "y": ny}))
            print(f"  step to ({nx},{ny}): success={step['success']}  "
                  f"new_pos={step['current_pos']}")
            assert step["success"] is True

            # ----- reset + verify clean state -----
            print("\n--- reset ---")
            r = _payload(await session.call_tool("reset", {}))
            print(f"  reset -> {r}")
            state = _payload(await session.call_tool("get_state", {}))
            assert tuple(state["current_pos"]) == start
            assert state["invalid_moves"] == 0
            assert state["path"] == [list(start)]
            print(f"  state after reset: pos={state['current_pos']}  "
                  f"path={state['path']}  invalid_moves={state['invalid_moves']}")

    print("\nOK: all six tools responded correctly over MCP stdio.")


if __name__ == "__main__":
    asyncio.run(main())
