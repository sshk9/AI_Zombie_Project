# Grid MCP Server

`grid_mcp_server.py` wraps the four pathfinding tools used inline by
`grid1/grid1_llm_agent.py` (`get_neighbors`, `is_wall`,
`heuristic_distance`, `make_move`) as a standalone MCP server, so the
same tools are callable from Claude Desktop and any other
MCP-compatible client over stdio -- not just from the one Python
script.

Two helper tools are added on top:

| Tool                  | Purpose                                                              |
| --------------------- | -------------------------------------------------------------------- |
| `get_neighbors`       | Passable orthogonal neighbors of `(x, y)`.                           |
| `is_wall`             | Status of `(x, y)`: `wall`, `passable`, or `out_of_bounds`.          |
| `heuristic_distance`  | Manhattan distance between two cells (admissible heuristic).         |
| `make_move`           | Step the agent one cell up/down/left/right. Validates adjacency etc. |
| `get_state`           | Current position, goal, path, dimensions, counters.                  |
| `reset`               | Re-initialize the agent from `config.py` for a fresh run.            |

Grid, start, and goal are loaded from `config.py` at the project root,
the same source the inline agent uses. Tool semantics (return shapes,
error strings, Manhattan heuristic) are kept identical to
`GridAgentState.execute_tool` in `grid1_llm_agent.py` so behavior stays
reproducible between the two implementations.

## Install

From the project root, with `.venv` active:

```
pip install mcp
```

Requires Python 3.10+ and `mcp >= 1.2.0`.

## Smoke test

```
python grid_mcp_server.py
```

The process will appear to hang -- that is correct. MCP speaks
JSON-RPC on stdin/stdout, so a stdio server waits silently for the
client to send a request. If you see a traceback before the hang,
something is wrong (most likely `config.py` isn't importable from the
script's directory). Ctrl+C to exit.

For an interactive test with a UI, use the MCP Inspector:

```
pip install "mcp[cli]"
mcp dev grid_mcp_server.py
```

## Wire up Claude Desktop

The config file lives at `%APPDATA%\Claude\claude_desktop_config.json`
on Windows. Open it with **Settings -> Developer -> Edit Config**, or
create it directly. Paste in:

```json
{
  "mcpServers": {
    "grid": {
      "command": "C:\\Users\\User\\AI_Zombie_Project\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\User\\AI_Zombie_Project\\grid_mcp_server.py"]
    }
  }
}
```

If the file already has an `mcpServers` block with other servers, just
add the `"grid": {...}` entry inside it -- don't replace the whole
object.

A few things that will silently break this if you skip them:

- **Paths must be absolute** and **backslashes must be escaped** (`\\`)
  inside JSON strings.
- **`command` must point at the venv's `python.exe`**, not bare
  `python`. Claude Desktop spawns the process without your shell PATH,
  so a bare `python` will resolve to whatever system Python it can
  find -- which won't have `mcp` installed.
- **Fully quit Claude Desktop** (right-click the tray icon -> Quit)
  before reopening. Closing the window isn't enough; the config is
  only re-read on a real restart.
- **JSON must be valid** -- no trailing commas. Claude Desktop silently
  drops a broken config without surfacing the error.

After restarting, you should see a tools icon in the chat input;
clicking it lists the `grid` server with all six tools. If it doesn't
appear, the log at `%APPDATA%\Claude\logs\mcp.log` usually shows why.
