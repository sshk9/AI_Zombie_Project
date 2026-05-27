"""
LLM-based pathfinding agent for grid1.

The model navigates the grid by issuing tool calls instead of running a
classical search. Used in grid1_compare_algorithms.py to benchmark against
BFS and A*.

Run standalone:
    python grid1/grid1_llm_agent.py
"""

import json
import os
import sys

# Make `config` and `utils` (at project root) importable when run as
# `python grid1/grid1_llm_agent.py` from the repo root.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import anthropic  # noqa: E402

from config import GRID, PLAYER_START_POS, GOAL_POS  # noqa: E402


# ---------------------------------------------------------------------------
# Tool schemas sent to the API
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_neighbors",
        "description": (
            "Return the passable adjacent cells (up/down/left/right) of (x, y). "
            "Walls and out-of-bounds cells are excluded. Use this to scout which "
            "directions are open from a given cell."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Column (0-indexed)"},
                "y": {"type": "integer", "description": "Row (0-indexed)"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "is_wall",
        "description": (
            "Check the status of cell (x, y). Returns one of: "
            "'wall' (blocked), 'passable' (open), or 'out_of_bounds' "
            "(outside the grid). Use this to probe specific cells when planning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "heuristic_distance",
        "description": (
            "Manhattan distance between (from_x, from_y) and (to_x, to_y), "
            "i.e. |from_x - to_x| + |from_y - to_y|. This is a lower bound on "
            "the true shortest-path cost (an admissible heuristic). Useful for "
            "deciding which neighbor moves you closer to the goal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_x": {"type": "integer"},
                "from_y": {"type": "integer"},
                "to_x": {"type": "integer"},
                "to_y": {"type": "integer"},
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        },
    },
    {
        "name": "make_move",
        "description": (
            "Move from your current position to (x, y). The target must be an "
            "orthogonal neighbor (Manhattan distance exactly 1), in bounds, and "
            "not a wall. Returns success/failure, your new current position, "
            "and whether you've reached the goal. Invalid moves do not advance "
            "you but still consume a tool call."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target column"},
                "y": {"type": "integer", "description": "Target row"},
            },
            "required": ["x", "y"],
        },
    },
]


SYSTEM_PROMPT = """\
You are navigating a 2D grid to reach a goal. The grid contains walls
(impassable cells) that you cannot see directly — you must use tools to
probe the environment.

Coordinate system: cells are (x, y) where x is the column (0-indexed,
left to right) and y is the row (0-indexed, top to bottom). Movement is
to one of four orthogonal neighbors (up/down/left/right). No diagonals.

You have a fixed budget of tool calls. Plan before moving — wasted moves
and unnecessary probing cost you budget. Reaching the goal in fewer moves
is better. If you get stuck against a wall, back up and try a different
direction; do not repeatedly probe the same cell.
"""


# ---------------------------------------------------------------------------
# Agent state + tool execution
# ---------------------------------------------------------------------------

class GridAgentState:
    """Holds mutable agent state and executes tools against the grid."""

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

    def _cell_status(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return "out_of_bounds"
        return "wall" if self.grid[y][x] == 1 else "passable"

    def execute_tool(self, name, args):
        """Dispatch a single tool call. Returns a JSON-serializable dict."""
        if name == "get_neighbors":
            x, y = args["x"], args["y"]
            result = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and self.grid[ny][nx] != 1
                ):
                    result.append([nx, ny])
            return {"neighbors": result}

        if name == "is_wall":
            return {"status": self._cell_status(args["x"], args["y"])}

        if name == "heuristic_distance":
            d = (
                abs(args["from_x"] - args["to_x"])
                + abs(args["from_y"] - args["to_y"])
            )
            return {"distance": d}

        if name == "make_move":
            x, y = args["x"], args["y"]
            cx, cy = self.current_pos

            if self.goal_reached:
                self.invalid_moves += 1
                return {
                    "success": False,
                    "error": "Already at goal; no further moves needed.",
                    "current_pos": [cx, cy],
                    "goal_reached": True,
                }

            if abs(x - cx) + abs(y - cy) != 1:
                self.invalid_moves += 1
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

            status = self._cell_status(x, y)
            if status != "passable":
                self.invalid_moves += 1
                return {
                    "success": False,
                    "error": f"Target ({x},{y}) is {status}.",
                    "current_pos": [cx, cy],
                    "goal_reached": False,
                }

            self.current_pos = (x, y)
            self.path.append((x, y))
            if self.current_pos == self.goal:
                self.goal_reached = True
            return {
                "success": True,
                "current_pos": [x, y],
                "goal_reached": self.goal_reached,
            }

        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_llm_agent(
    start,
    goal,
    grid,
    max_calls=100,
    model="claude-sonnet-4-6",
    max_tokens=4096,
    verbose=False,
):
    """
    Run the LLM agent until it reaches the goal, exhausts the budget, or
    stops issuing tool calls.

    Returns a dict with keys: finish_reason, goal_reached, path, path_length,
    tool_calls, invalid_moves, input_tokens, output_tokens.
    """
    state = GridAgentState(start, goal, grid)
    client = anthropic.Anthropic()

    initial_user = (
        f"You start at ({start[0]}, {start[1]}). "
        f"The goal is at ({goal[0]}, {goal[1]}). "
        f"The grid is {len(grid[0])} columns wide and {len(grid)} rows tall. "
        f"You have a budget of {max_calls} tool calls. Reach the goal."
    )
    messages = [{"role": "user", "content": initial_user}]

    total_tool_calls = 0
    input_tokens = 0
    output_tokens = 0
    finish_reason = None

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        # Echo assistant text if verbose (planning/commentary the model emits)
        if verbose:
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    print(f"[think] {block.text.strip()}")

        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            finish_reason = "stopped"
            break

        # Process every tool_use block in this turn — the API requires one
        # tool_result per tool_use in the next user message.
        tool_results = []
        for block in tool_use_blocks:
            total_tool_calls += 1
            if total_tool_calls > max_calls:
                result = {"error": "Budget exhausted. No further tool calls allowed."}
            else:
                result = state.execute_tool(block.name, dict(block.input))

            if verbose:
                print(f"[{total_tool_calls:3d}] {block.name}({dict(block.input)}) -> {result}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

        if state.goal_reached:
            finish_reason = "success"
            break
        if total_tool_calls >= max_calls:
            finish_reason = "budget_exhausted"
            break

    return {
        "finish_reason": finish_reason,
        "goal_reached": state.goal_reached,
        "path": state.path,
        "path_length": len(state.path) - 1,
        "tool_calls": total_tool_calls,
        "invalid_moves": state.invalid_moves,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_llm_agent(
        start=PLAYER_START_POS,
        goal=GOAL_POS,
        grid=GRID,
        max_calls=100,
        verbose=True,
    )
    print()
    print("=" * 60)
    print(f"Finish reason   : {result['finish_reason']}")
    print(f"Goal reached    : {result['goal_reached']}")
    print(f"Path length     : {result['path_length']} moves")
    print(f"Tool calls used : {result['tool_calls']} / 100")
    print(f"Invalid moves   : {result['invalid_moves']}")
    print(f"Input tokens    : {result['input_tokens']}")
    print(f"Output tokens   : {result['output_tokens']}")
    print(f"Path            : {result['path']}")