# AI Zombie Project

An AI simulation project exploring pathfinding algorithms, adversarial agent interactions, and LLM-driven tool use exposed over the Model Context Protocol (MCP).

## 🚀 Project Phases
- **Phase 1:** Survivor uses **Breadth-First Search (BFS)** to find the shortest path to supplies.
- **Phase 2:** Introduces an **Adversarial Zombie** that uses a **Greedy Heuristic (Manhattan Distance)** to hunt the survivor.
- **Phase 3:** Adds an **LLM-driven pathfinding agent** that navigates the grid via Anthropic's tool-use API, benchmarked head-to-head against BFS and A* on the same grid. Three trials matched the optimum (17 moves) at 33–41 tool calls per run.
- **Phase 4:** Wraps the LLM agent's pathfinding tools as a standalone **MCP server**, callable from Claude Desktop and any other MCP-compatible client over stdio — not just from a single Python script.

---

## 🛠️ Setup Instructions

Follow these steps to get the environment running on your local machine.

### 1. Clone the Project
```bash
git clone https://github.com/<sshk9>/AI_Zombie_Project.git
cd AI_Zombie_Project
```

### 2. Create and Activate Virtual Environment
This ensures that the project dependencies don't interfere with your system settings.

MacOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
Windows
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Simulations

Phase 1 (Search Logic):
```bash
python3 grid1_search.py
```

Phase 1 (Zombie Interaction):
```bash
python3 grid1_search_visual.py
```

Phase 3 (LLM agent vs BFS/A* benchmark):
```bash
python3 grid1/grid1_compare_algorithms.py
```
> Requires an `ANTHROPIC_API_KEY` environment variable and consumes API credits (~$0.30/run).

Phase 4 (MCP server smoke test):
```bash
python test_mcp_client.py
```
Spawns `grid_mcp_server.py` as a subprocess, connects over MCP stdio, exercises all six tools, and prints `OK` on success. See `README_MCP.md` for the full MCP server documentation and Claude Desktop integration steps.

---

## 🧠 Design Tradeoffs (Phase 4)

The MCP wrapper involved several deliberate design choices:

- **Module-level singleton state vs per-session state.** The server keeps a single `GridAgentState` instance at module scope, mirroring the inline agent in `grid1_llm_agent.py`. This makes results directly reproducible between the two implementations, but means two simultaneous clients would share state. A production version would key state by `session_id` or use FastMCP's `Context` object.
- **Wrapping existing tools verbatim vs redesigning for the protocol.** Tool return shapes (`{"success": bool, "current_pos": [x, y], ...}`) were lifted verbatim from the inline agent rather than redesigned around idiomatic MCP schemas. This preserves cross-implementation reproducibility at the cost of slightly less protocol-native tool definitions.
- **`heuristic_distance` as a tool vs computed by the model.** Manhattan distance is trivial arithmetic the model could do internally. Exposing it as a tool costs a round-trip but makes the agent's planning auditable in the trace — useful for a benchmark, less useful in production.
