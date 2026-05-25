# AI Zombie Project: Complete Feature Summary

**Last updated: 2026-05-25**

---

## Project Overview

A Python project comparing classical search algorithms (BFS, A*) across three grid scales, with two distinct deliverables:

1. **Single-agent pathfinding visualizations** — BFS vs. A* compared via static footprints, discovery-time heatmaps, and side-by-side comparisons across small/medium/large grids.
2. **Multi-agent "Freeze Tag" game** — a real-time pursuit game where a **prey** agent tries to reach a stationary **reward** while a **monster** agent chases it. Both agents replan every tick. This is where the project's "Zombie" theme lives.

---

## Architecture

```
AI_Zombie_Project/
├── config.py                       # Centralized config: grids, sizes, colors, positions
├── utils.py                        # Core algorithms: BFS, A*, A* fast, depth-bounded A*
├── requirements.txt
├── .gitignore
│
├── ROOT-LEVEL GAME SCRIPTS         # Multi-agent Freeze Tag variants
│   ├── astar-two-agents.py         # Prey (A*) vs Monster (A*)
│   ├── bounded_astar_game.py       # Prey & Monster both use depth-bounded A*
│   ├── minimax_ambush_monster.py   # Variant emphasizing monster strategy (unreviewed)
│   └── minimax_evasive_prey.py     # Variant emphasizing prey strategy (unreviewed)
│
├── env/                            # Standalone environment (Phase 0)
│   ├── env_setup.py                # Manual arrow-key movement on the grid
│   └── env_visuals.py              # (visualization helpers — not reviewed)
│
├── grid1/   (small grid)
│   ├── grid1_search.py             # BFS: footprint + metrics
│   ├── grid1_astar.py              # A*:  footprint + metrics
│   ├── grid1_heatmaps.py           # Discovery time gradient
│   ├── grid1_search_visual.py      # (legacy animation)
│   ├── grid1_astar_visual.py       # (legacy animation)
│   ├── grid1_bfs_footprint.png
│   ├── grid1_astar_footprint.png
│   ├── grid1_discovery_heatmap.png
│   └── __init__.py
│
├── grid2/   (medium grid)
│   ├── grid2_search.py             # BFS: footprint + metrics
│   ├── grid2_astar.py              # A*:  footprint + metrics
│   ├── grid2_heatmaps.py           # Discovery time gradient
│   ├── grid2_compare.py            # Comparison with frontier overlay
│   ├── grid2_search_visual.py      # (legacy animation)
│   ├── grid2_astar_visual.py       # (legacy animation)
│   ├── grid2_bfs_footprint.png
│   ├── grid2_astar_footprint.png
│   ├── grid2_discovery_heatmap.png
│   └── __init__.py
│
├── grid3/   (large grid)
│   ├── grid3_search.py             # BFS: footprint + metrics
│   ├── grid3_astar.py              # A*:  footprint + metrics
│   ├── grid3_heatmaps.py           # Discovery time gradient
│   ├── grid3_compare.py            # Comparison with frontier overlay
│   ├── grid3_search_visual.py      # (legacy animation)
│   ├── grid3_astar_visual.py       # (legacy animation)
│   ├── grid3_bfs_footprint.png
│   ├── grid3_astar_footprint.png
│   ├── grid3_discovery_heatmap.png
│   └── __init__.py
│
├── benchmarks/
│   ├── run_benchmarks.py           # Multi-trial performance harness
│   ├── results.csv                 # Recorded trial results
│   ├── plots_nodes.png             # Nodes-explored comparison chart
│   └── plots_time.png              # Execution-time comparison chart
│
└── docs/
    ├── README.md
    ├── PROJECT_SUMMARY.md          # This file
    ├── IMPLEMENTATION_SUMMARY.md
    ├── QUICK_START.md
    └── VISUALIZATIONS.md
```

> **Note on legacy artifacts:** `__pycache__/` directories contain leftover `.pyc` files from deleted or renamed source — notably `phase1/2/3_*` files from before the grid rename, `grid*_minimax.cpython-312.pyc`, `minimax_comparison.cpython-312.pyc`, and now `minimax_game.cpython-312.pyc` (orphaned by the `bounded_astar_game.py` rename). `git status` confirms these are untracked. Safe to delete: `del /S __pycache__` on Windows, or `find . -name __pycache__ -type d -exec rm -rf {} +` on Unix.

---

## Part 1 — Single-Agent Pathfinding Visualizations

Three grid scales (grid1 = small, grid2 = medium, grid3 = large), three visualization methods per scale.

### A) Search Footprint (static PNG + metrics)
- Side-by-side comparison of explored nodes (color) vs. final path (yellow)
- Files: `grid*_search.py` (BFS), `grid*_astar.py` (A*)
- Outputs: `grid*_bfs_footprint.png`, `grid*_astar_footprint.png`
- Best for: written reports, static analysis

### B) Discovery Time Heatmaps
- Viridis color gradient showing the order in which nodes were discovered
- BFS produces concentric rings around the start; A* produces an elongated, goal-directed beam
- Files: `grid*_heatmaps.py`
- Outputs: `grid*_discovery_heatmap.png`
- Best for: understanding algorithmic bias visually

### C) Comparison with Frontier Overlay (grid2 and grid3 only)
- Real-time Pygame visualization showing BFS-only tiles, A*-only tiles, and shared tiles
- Controls: `F` = toggle frontier overlay, `ESC` = quit
- Files: `grid2_compare.py`, `grid3_compare.py`
- Best for: advanced side-by-side analysis

### D) Legacy Animation Scripts
- `grid*_search_visual.py` and `grid*_astar_visual.py` — earlier interactive Pygame versions, kept for reference but not the primary visualization path

> `grid1/` is missing a `grid1_compare.py` (grid2 and grid3 have one). At 10×10 scale, the comparison may not add useful information, but it's a structural inconsistency worth noting.

---

## Part 2 — Multi-Agent Freeze Tag Game

A real-time pursuit game on the large grid. Two planning agents compete:

| Agent       | Goal                                | Symbol         |
|-------------|-------------------------------------|----------------|
| **Prey**    | Reach the stationary Reward         | Blue P (●)     |
| **Monster** | Catch the Prey                      | Red M (●)      |
| **Reward**  | Stationary, never moves             | Gold diamond ◇ |

Both agents recompute their plan **every game tick** — the monster's goal is the prey's current position, which moves every step, so static planning isn't enough.

**Win conditions:**
- ✅ Prey reaches reward → **PREY WINS!**
- ❌ Monster catches prey → **MONSTER WINS!**

**Game variants:**

| Script                       | Prey planner      | Monster planner   | Notes                                     |
|------------------------------|-------------------|-------------------|-------------------------------------------|
| `astar-two-agents.py`        | A*                | A*                | Baseline: both use optimal pathfinding    |
| `bounded_astar_game.py`      | depth-bounded A*  | depth-bounded A*  | Depth horizon 60 for both (configurable)  |
| `minimax_ambush_monster.py`  | (see file)        | (see file)        | Monster-strategy variant — unreviewed     |
| `minimax_evasive_prey.py`    | (see file)        | (see file)        | Prey-strategy variant — unreviewed        |

**Controls (all game scripts):**
- `SPACE` — pause / resume
- `R` — restart
- `ESC` — quit
- Game auto-closes 4 seconds after either side wins

---

## Part 3 — Environment Setup (env/)

- **`env_setup.py`** — "Phase 0" of the project: a standalone manual-movement sandbox. Arrow keys move the player on the default grid; tests wall collision and grid rendering. This is the baseline that existed before any AI was added — useful as a known-good rendering reference when something else breaks.
- **`env_visuals.py`** — Visualization helpers (not reviewed for this summary).

---

## Part 4 — Benchmarks (benchmarks/)

- **`run_benchmarks.py`** — multi-trial performance harness for BFS, A*, and A* fast
- **`results.csv`** — recorded trial data (columns: phase, algorithm, run, time, nodes_expanded, heap_ops, path_len). Check this file directly for the current trial count rather than relying on the summary.
- **`plots_nodes.png`** — nodes-explored comparison chart
- **`plots_time.png`** — execution-time comparison chart

---

## Algorithm Implementations (utils.py)

| Function                | Algorithm                            | Heuristic    | Optimal?                |
|-------------------------|--------------------------------------|--------------|-------------------------|
| `get_bfs_path`          | BFS with parent pointers             | None         | Yes                     |
| `get_astar_path`        | A* (tuple-keyed)                     | Manhattan    | Yes                     |
| `get_astar_path_fast`   | A* with integer-encoded grid indices | Manhattan    | Yes                     |
| `get_bounded_astar`     | Depth-bounded A*                     | Manhattan    | Only within depth budget|

All four support `return_info=True` to get a stats dict:
```python
{
    'nodes_expanded': int,      # all four
    'visited': set,             # explored (x, y) tuples — all four
    'heap_ops': int,            # A* variants only
    'score': float              # depth-bounded variant only
}
```

> **Heuristic helper:** All three A* variants (`get_astar_path`, `get_astar_path_fast`, `get_bounded_astar`) compute the heuristic via the shared `get_manhattan_distance` function in `utils.py`. To swap heuristics (Chebyshev, octile, etc. — useful when enabling diagonals via `get_neighbors(include_diagonals=True)`), edit that single function.

---

## Grid Configurations (config.py)

`config.py` exports **two grid scales**:

| Scale         | Constants                                                                                                  | Used by                                       |
|---------------|------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| Default       | `GRID`, `TILE_SIZE`, `GRID_WIDTH`, `GRID_HEIGHT`, `PLAYER_START_POS`, `GOAL_POS`                            | `env/env_setup.py`                            |
| Large         | `GRID_LARGE`, `TILE_SIZE_LARGE`, `GRID_WIDTH_LARGE`, `GRID_HEIGHT_LARGE`, `PLAYER_START_POS_LARGE`, `GOAL_POS_LARGE` | All multi-agent game scripts (30×30 by default) |

The grid1/grid2/grid3 directories likely embed their own grid definitions (or use additional constants in `config.py`); verify before refactoring.

---

## Running the Scripts

### Single-grid visualizations
```bash
# Small grid
python -m grid1.grid1_search
python -m grid1.grid1_astar
python -m grid1.grid1_heatmaps

# Medium grid
python -m grid2.grid2_search
python -m grid2.grid2_astar
python -m grid2.grid2_heatmaps
python -m grid2.grid2_compare

# Large grid
python -m grid3.grid3_search
python -m grid3.grid3_astar
python -m grid3.grid3_heatmaps
python -m grid3.grid3_compare
```

### Multi-agent games
```bash
python astar-two-agents.py
python bounded_astar_game.py
python minimax_ambush_monster.py
python minimax_evasive_prey.py
```

> The filename `astar-two-agents.py` uses a hyphen, so it can only be **run** — it can't be **imported** (`import astar-two-agents` is invalid Python). Rename to `astar_two_agents.py` if you ever want to reuse its game class.

### Standalone environment (Phase 0)
```bash
python env/env_setup.py
```

### Benchmarks
```bash
python benchmarks/run_benchmarks.py
```

---

## Dependencies

**Required:**
- Python 3.6+ (project is currently using 3.12, per `.pyc` filenames)
- Pygame (animations, all game scripts, env)

**Optional:**
- Matplotlib + NumPy (footprints, heatmaps, benchmark plots)
- Pandas (benchmark CSV analysis)

```bash
pip install -r requirements.txt
```

---

## Known Cleanup Opportunities

These don't block anything — they're polish for portfolio/grading:

1. **Orphan `.pyc` files** in `__pycache__/` directories. `git status` confirms they're untracked. Delete safely.
2. **Hyphenated filename** `astar-two-agents.py` can't be imported. Rename to underscores if reuse is wanted.
3. **Missing `grid1_compare.py`** — present in grid2 and grid3. Add for symmetry, or document the omission.
4. **Variant scripts still use "minimax" naming.** `minimax_ambush_monster.py` and `minimax_evasive_prey.py` were not touched in the bounded_astar rename pass — they don't import `get_bounded_astar` (formerly `get_minimax_path`), so they implement their own planning logic. Verify what they actually do; if it's also depth-bounded A* rather than true two-player minimax, rename them for naming consistency with `bounded_astar_game.py`.
5. **Sibling summary files** in `docs/` (IMPLEMENTATION_SUMMARY, QUICK_START, VISUALIZATIONS, README) should each get a `Last updated:` line and a once-over for drift like this file just had.

---

## Customization Quick Reference

| To change                | Edit                                                                 |
|--------------------------|----------------------------------------------------------------------|
| Grid layout / size       | `config.py` — `GRID`, `GRID_LARGE`, and their `_WIDTH`/`_HEIGHT`     |
| Project palette          | `config.py` — `BG_COLOR`, `WALL_COLOR`, `GRID_LINE_COLOR`, etc.      |
| Game agent colors        | Top of each game script — `PREY_COLOR`, `MONSTER_COLOR`, `REWARD_COLOR` |
| A* heuristic             | `get_manhattan_distance` in `utils.py` (all three A* variants share it) |
| Bounded A* depth         | `PREY_DEPTH`, `MONSTER_DEPTH` in `bounded_astar_game.py` (default 60)|
| Game speed               | `STEPS_PER_FRAME` at the top of each game script (lower = faster)    |
| Animation FPS            | `FPS` in `config.py`                                                 |

---

**See also:** `VISUALIZATIONS.md` for detailed visualization documentation, `QUICK_START.md` for quick commands, `IMPLEMENTATION_SUMMARY.md` for implementation notes.

🧟‍♂️ Happy zombie-evading.