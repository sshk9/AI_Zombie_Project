"""
MCP server exposing the grid1 pathfinding tools.

Wraps the four tools used inline in `grid1/grid1_llm_agent.py`
(`get_neighbors`, `is_wall`, `heuristic_distance`, `make_move`) plus
two helpers (`get_state`, `reset`) so the grid agent can be driven from
Claude Desktop or any MCP-compatible client over stdio.

Grid, start, and goal are loaded from `config.py` at the project root.
Tool semantics are kept identical to `GridAgentState.execute_tool` in
`grid1_llm_agent.py` so results stay reproducible between the two
implementations.

Run standalone (smoke test):
    python grid_mcp_server.py
The server speaks JSON-RPC on stdin/stdout, so it will appear to hang
waiting for input -- that's correct. Ctrl+C to exit. Nothing should
ever be printed to stdout outside the MCP protocol; debug output must
go to stderr.

Claude Desktop config (Windows, %APPDATA%\\Claude\\claude_desktop_config.json):
    {
      "mcpServers": {
        "grid": {
          "command": "C:\\\\Users\\\\User\\\\AI_Zombie_Project\\\\.venv\\\\Scripts\\\\python.exe",
          "args": ["C:\\\\Users\\\\User\\\\AI_Zombie_Project\\\\grid_mcp_server.py"]
        }
      }
    }
"""

import os
import sys

# Ensure `config` (at the project root, alongside this file) is
# importable regardless of the cwd Claude Desktop spawns us in -- the
# spawn cwd is usually the Claude Desktop install dir, not the project.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from mcp.server.fastmcp import FastMCP  # noqa: E402

from config import GRID, PLAYER_START_POS, GOAL_POS  # noqa: E402


# ---------------------------------------------------------------------------
# Grid state (lifted from grid1/grid1_llm_agent.py::GridAgentState)
# ---------------------------------------------------------------------------

class GridAgentState:
    """Holds mutable agent state and answers grid queries.

    Kept structurally identical to the class in grid1_llm_agent.py so
    the two implementations stay in sync. Coordinates are (x, y) where
    x is the column and y is the row; cells are indexed as grid[y][x].
    Walls are encoded as 1; any other value is passable.
    """

    def __init__(self, start, goal, grid):
        self.grid = grid
        self.width = len(grid[0])
        self.height = len(grid)
        self.start = tuple(start)
        self.goal = tuple(goal)
        self.current_pos = tuple(start)
        self.path = [tuple(start)]
        self.goal_reached = False
        self.invalid_moves = 0

    def cell_status(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return "out_of_bounds"
        return "wall" if self.grid[y][x] == 1 else "passable"


# Module-level singleton. Re-bound by reset().
_state = GridAgentState(PLAYER_START_POS, GOAL_POS, GRID)


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("grid")


@mcp.tool()
def get_neighbors(x: int, y: int) -> dict:
    """Return the passable adjacent cells (up/down/left/right) of (x, y).

    Walls and out-of-bounds cells are excluded. Use this to scout which
    directions are open from a given cell.
    """
    result = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = x + dx, y + dy
        if (
            0 <= nx < _state.width
            and 0 <= ny < _state.height
            and _state.grid[ny][nx] != 1
        ):
            result.append([nx, ny])
    return {"neighbors": result}


@mcp.tool()
def is_wall(x: int, y: int) -> dict:
    """Check the status of cell (x, y).

    Returns one of: 'wall' (blocked), 'passable' (open), or
    'out_of_bounds' (outside the grid). Use this to probe specific
    cells when planning.
    """
    return {"status": _state.cell_status(x, y)}


@mcp.tool()
def heuristic_distance(from_x: int, from_y: int, to_x: int, to_y: int) -> dict:
    """Manhattan distance between (from_x, from_y) and (to_x, to_y).

    Equals |from_x - to_x| + |from_y - to_y|. This is a lower bound on
    the true shortest-path cost (an admissible heuristic). Useful for
    deciding which neighbor moves closer to the goal.
    """
    return {"distance": abs(from_x - to_x) + abs(from_y - to_y)}


@mcp.tool()
def make_move(x: int, y: int) -> dict:
    """Move from the current position to (x, y).

    The target must be an orthogonal neighbor (Manhattan distance
    exactly 1), in bounds, and not a wall. Returns success/failure,
    the new current position, and whether the goal has been reached.
    Invalid moves do not advance the position but are still counted.
    """
    cx, cy = _state.current_pos

    if _state.goal_reached:
        _state.invalid_moves += 1
        return {
            "success": False,
            "error": "Already at goal; no further moves needed.",
            "current_pos": [cx, cy],
            "goal_reached": True,
        }

    if abs(x - cx) + abs(y - cy) != 1:
        _state.invalid_moves += 1
        return {
            "success": False,
            "error": (
                f"Target ({x},{y}) is not adjacent to current position "
                f"({cx},{cy}). Moves must be exactly one step "
                f"up/down/left/right."
            ),
            "current_pos": [cx, cy],
            "goal_reached": False,
        }

    status = _state.cell_status(x, y)
    if status != "passable":
        _state.invalid_moves += 1
        return {
            "success": False,
            "error": f"Target ({x},{y}) is {status}.",
            "current_pos": [cx, cy],
            "goal_reached": False,
        }

    _state.current_pos = (x, y)
    _state.path.append((x, y))
    if _state.current_pos == _state.goal:
        _state.goal_reached = True
    return {
        "success": True,
        "current_pos": [x, y],
        "goal_reached": _state.goal_reached,
    }


@mcp.tool()
def get_state() -> dict:
    """Return the current grid agent state.

    Includes current position, start, goal, grid dimensions, the path
    taken so far, whether the goal has been reached, and the count of
    invalid moves. Call this at the start of a session to discover
    where the agent stands without having to make a move first.
    """
    return {
        "current_pos": list(_state.current_pos),
        "start": list(_state.start),
        "goal": list(_state.goal),
        "width": _state.width,
        "height": _state.height,
        "path": [list(p) for p in _state.path],
        "goal_reached": _state.goal_reached,
        "invalid_moves": _state.invalid_moves,
    }


@mcp.tool()
def reset() -> dict:
    """Reset the agent to the starting position with a clean path/counters.

    Reloads grid, start, and goal from `config.py`. Use this to begin a
    fresh run without restarting the server.
    """
    global _state
    _state = GridAgentState(PLAYER_START_POS, GOAL_POS, GRID)
    return {
        "ok": True,
        "current_pos": list(_state.current_pos),
        "goal": list(_state.goal),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # FastMCP.run() defaults to stdio transport, which is what Claude
    # Desktop expects. Do NOT print to stdout from anywhere else in
    # this process -- stdout is the MCP protocol channel and stray
    # writes will desynchronize the client.
    mcp.run()
