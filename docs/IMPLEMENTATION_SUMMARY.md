# Implementation Summary

**Last updated: 2026-05-25**

Implementation notes for the AI Zombie Project: pathfinding visualizations across three grid scales (`grid1`, `grid2`, `grid3`) and a multi-agent Freeze Tag pursuit game.

For high-level architecture and file layout see `PROJECT_SUMMARY.md`. This document focuses on **how** features were built.

---

## Part 1 — Single-Agent Pathfinding Visualizations

Three grid scales (small / medium / large), three visualization methods per scale, plus a metrics overlay that applies to all.

### 1. Search Footprint (Static PNG + Metrics)

**Files:**
- `grid1/grid1_search.py`, `grid1/grid1_astar.py`
- `grid2/grid2_search.py`, `grid2/grid2_astar.py`
- `grid3/grid3_search.py`, `grid3/grid3_astar.py`

**Per file:**
```
1. Call get_bfs_path(..., return_info=True) or get_astar_path(..., return_info=True)
2. Build numpy array visualization:
   - Light Blue (BFS) / Light Green (A*): explored nodes
   - Bright Yellow: final shortest path
   - Green square: start
   - Red square: goal
3. Create 2-panel matplotlib figure:
   - Left: grid visualization
   - Right: metrics scorecard (path length, nodes explored, time, efficiency %)
4. Save PNG: grid{N}_{bfs|astar}_footprint.png
```

**Output:** 6 PNG files (2 per grid scale) + console metrics.

---

### 2. Discovery Time Heatmaps

**Files:** `grid1/grid1_heatmaps.py`, `grid2/grid2_heatmaps.py`, `grid3/grid3_heatmaps.py`

**Per file:**
```
1. Run both BFS and A* with return_info=True
2. Extract visited sets from both
3. Render Viridis color gradient:
   - Dark: discovered early
   - Bright: discovered late
4. Side-by-side comparison:
   - Left: BFS (concentric rings = radial expansion)
   - Right: A* (focused beam = goal-directed)
5. Save PNG with colorbars: grid{N}_discovery_heatmap.png
```

**Key insight (visually demonstrated):**
- BFS expands with `f(n) = g(n)` — no heuristic guidance
- A* expands with `f(n) = g(n) + h(n)` — biased toward the goal

**Output:** 3 PNG heatmaps.

---

### 3. Comparison with Frontier Overlay (grid2 and grid3 only)

**Files:** `grid2/grid2_compare.py`, `grid3/grid3_compare.py`

Real-time Pygame visualization showing BFS-only tiles, A*-only tiles, and shared tiles. Optional frontier overlay toggle.

**Controls:** `F` = toggle frontier overlay, `ESC` = quit.

> Note: `grid1` does not have a `grid1_compare.py` — at 10×10 scale the comparison adds little, but it's a structural inconsistency worth flagging.

---

### 4. Legacy Animation Scripts

**Files:** `grid*/grid*_search_visual.py`, `grid*/grid*_astar_visual.py`

Earlier interactive Pygame animations of BFS and A* exploration. Kept for reference but no longer the primary visualization path — the static PNG footprints and heatmaps are the canonical outputs.

If you need step-by-step animation as a feature again, the canonical approach would be a `grid*_animation.py` script per scale; those files were created in an earlier iteration but have since been removed (only `__pycache__` traces remain).

---

### Metrics Overlay (applies to all visualizations)

Captured per run:

```
┌────────────────────────────┐
│ BFS Search Metrics         │
├────────────────────────────┤
│ Path Length:      55 steps │
│ Nodes Explored:   820      │
│ Execution Time:   0.003542s│
│ Efficiency:       6.71%    │
└────────────────────────────┘
```

**Formula:** `Efficiency = (path_length / nodes_explored) × 100`

**Displayed via:**
1. Right panel of footprint PNGs
2. Console output (printed after each run)

**Typical ranges:**
- BFS: ~5–15% efficiency (explores many wasted nodes)
- A*: ~40–80% efficiency (targeted exploration)

---

## Part 2 — Multi-Agent Freeze Tag Game

A real-time pursuit game on the large grid. **Prey** plans toward a stationary **reward**; **monster** plans toward the prey's current position. Both replan every tick.

**Files (root-level):**
- `bounded_astar_game.py` — canonical variant; both agents use depth-bounded A*
- `astar-two-agents.py` — baseline; both agents use full A*
- `minimax_ambush_monster.py`, `minimax_evasive_prey.py` — unreviewed variants

### Implementation pattern (`bounded_astar_game.py`)

```python
class BoundedAStarGame:
    def __init__(self):
        self.reset()

    def _update_paths(self):
        # Prey: fixed goal (reward)
        self.prey_path = get_bounded_astar(
            tuple(self.prey_pos), tuple(reward_pos), GRID_LARGE,
            depth=PREY_DEPTH
        )
        # Monster: dynamic goal (current prey position)
        self.monster_path = get_bounded_astar(
            tuple(self.monster_pos), tuple(self.prey_pos), GRID_LARGE,
            depth=MONSTER_DEPTH
        )

    def tick(self):
        # Each agent advances one tile along its planned path
        # Check win/lose conditions
        # Re-plan for next tick
```

**Tick loop:**
1. Each agent advances one tile along its current plan.
2. Check terminal conditions (prey at reward → prey wins; monster at prey → monster wins).
3. Replan both paths against new positions.

**Pygame loop:** throttled by `STEPS_PER_FRAME` (lower = faster simulation).

**Default depth:** `PREY_DEPTH = MONSTER_DEPTH = 60` on a 30×30 grid (configurable at top of file).

> **Naming history:** This file was previously `minimax_game.py` and called `get_minimax_path` from `utils.py`. Both have been renamed — the implementation has always been depth-bounded A*, never two-player minimax with alpha-beta pruning. The two `minimax_*.py` variants still bear the old name pending review.

---

## Algorithm Implementations (utils.py)

| Function                | Algorithm                            | Heuristic    |
|-------------------------|--------------------------------------|--------------|
| `get_bfs_path`          | BFS with parent pointers             | None         |
| `get_astar_path`        | A* (tuple-keyed)                     | Manhattan    |
| `get_astar_path_fast`   | A* with integer-encoded grid indices | Manhattan    |
| `get_bounded_astar`     | Depth-bounded A*                     | Manhattan    |

### `return_info=True` contract

All four pathfinders support a stats dict via `return_info=True`:

```python
path, info = get_bfs_path(start, goal, grid, return_info=True)
# info = {
#     'nodes_expanded': int,   # all four
#     'visited': set,          # explored (x, y) tuples — all four
#     'heap_ops': int,         # A* variants only
#     'score': float,          # depth-bounded variant only
# }
```

This is what enables every visualization in Part 1 — the `visited` set drives heatmaps, `nodes_expanded` drives efficiency metrics, etc.

### Shared Manhattan helper

All three A* variants (`get_astar_path`, `get_astar_path_fast`, `get_bounded_astar`) compute the heuristic via the module-level `get_manhattan_distance(pos1, pos2)` function. Previously each one inlined `abs(dx) + abs(dy)` directly; the refactor routes them through the shared helper so swapping to Chebyshev or octile (e.g. when enabling diagonals via `get_neighbors(include_diagonals=True)`) is a single-function edit.

---

## Generated Outputs

### PNG files (per full run)
```
grid1/grid1_bfs_footprint.png
grid1/grid1_astar_footprint.png
grid1/grid1_discovery_heatmap.png

grid2/grid2_bfs_footprint.png
grid2/grid2_astar_footprint.png
grid2/grid2_discovery_heatmap.png

grid3/grid3_bfs_footprint.png
grid3/grid3_astar_footprint.png
grid3/grid3_discovery_heatmap.png
```

Plus benchmark plots in `benchmarks/`:
```
benchmarks/plots_nodes.png
benchmarks/plots_time.png
benchmarks/results.csv
```

### Interactive applications
- `grid2/grid2_compare.py`, `grid3/grid3_compare.py` — frontier-overlay comparisons
- `bounded_astar_game.py`, `astar-two-agents.py` — pursuit games
- `env/env_setup.py` — manual-movement sandbox (Phase 0 baseline)

---

## User Workflow

### Quick demo
```bash
# Single-agent visualization (small grid, instant)
python -m grid1.grid1_search
python -m grid1.grid1_astar
python -m grid1.grid1_heatmaps

# Multi-agent game (interactive)
python bounded_astar_game.py
```

### Full analysis run
```bash
# All three grids — visualization
python -m grid1.grid1_search && python -m grid1.grid1_astar && python -m grid1.grid1_heatmaps
python -m grid2.grid2_search && python -m grid2.grid2_astar && python -m grid2.grid2_heatmaps
python -m grid3.grid3_search && python -m grid3.grid3_astar && python -m grid3.grid3_heatmaps

# Real-time comparisons
python -m grid2.grid2_compare
python -m grid3.grid3_compare

# Benchmark harness
python benchmarks/run_benchmarks.py
```

---

## Technical Details

### Color scheme (visualizations)
```python
BFS_EXPLORED    = (173, 216, 230)  # Light blue  — uniform exploration
ASTAR_EXPLORED  = (200, 230, 180)  # Light green — focused exploration
FINAL_PATH      = (255, 255, 0)    # Bright yellow
WALL            = (50, 50, 50)
START           = (0, 255, 0)
GOAL            = (255, 0, 0)
```

### Grid sizes
```
grid1:  10×10  =  100 nodes   (~640×640 px output)
grid2:  30×30  =  900 nodes   (~600×600 px output)
grid3:  50×40  = 2000 nodes   (~800×640 px output)
```

### Game-specific palette (`bounded_astar_game.py`)
```python
PREY_COLOR    = (30, 144, 255)   # dodger blue
MONSTER_COLOR = (220, 20, 60)    # crimson
REWARD_COLOR  = (255, 215, 0)    # gold
```

### Matplotlib output
- Heatmaps use the viridis colormap
- Footprints use `matplotlib.image` for RGB display
- All PNGs at 100 DPI (balance quality vs. file size)

---

## Dependencies

**Required:**
- Python 3.6+ (currently using 3.12 per `.pyc` filenames)
- Pygame (for `*_visual.py` animations, game scripts, and `env_setup.py`)

**For full features:**
- Matplotlib + NumPy (PNG generation for footprints, heatmaps, benchmark plots)
- Pandas (benchmark CSV analysis)

```bash
pip install -r requirements.txt
```

---

## Limitations & Future Work

### Current limitations
1. **Heatmaps show node count, not true discovery time.** True discovery-time visualization would require recording an exploration timeline (currently the visited set is recovered post-hoc from the closed set).
2. **No open-set visualization.** Only the closed set (explored nodes) is rendered; the frontier (open heap contents at each step) is not.
3. **Manhattan heuristic only.** The three A* variants all use Manhattan via `get_manhattan_distance`. Swapping is now a one-function edit, but no alternative is currently shipped.
4. **Two variant Freeze Tag scripts (`minimax_ambush_monster.py`, `minimax_evasive_prey.py`) are unreviewed.** Both still use "minimax" in their filenames despite not importing `get_bounded_astar`; either they implement their own logic worth documenting, or they're abandoned.

### Planned extensions
1. **LLM-based reasoning agent.** Wrap the puzzle environment as tools (`get_state`, `make_move`, `is_goal`) and add an agent loop using the Anthropic API with function calling. Compare classical search vs. LLM planning on solution quality and step count.
2. **Optional MCP server wrapper.** Expose the same tools as an MCP server for portability.

### Optional polish
- Record step-by-step exploration history for true incremental animation
- Open-set / frontier visualization
- Additional heuristic options (Euclidean, Chebyshev, octile)
- Comparative metrics: nodes/step ratio, effective branching factor
- GIF export instead of interactive windows

---

## Notes for Future Maintainers

- **`utils.py` is the single source of truth** for all search algorithms. The visualization scripts only consume `return_info` dicts; they don't reimplement search.
- **`config.py` exports two grid scales** (default + large). Game scripts use the large one; `env/env_setup.py` uses the default. The `grid1`/`grid2`/`grid3` directories likely embed their own grid definitions — verify before refactoring constants.
- **Renames in progress:** `get_minimax_path` → `get_bounded_astar`, `minimax_game.py` → `bounded_astar_game.py`. The two `minimax_ambush_monster.py` / `minimax_evasive_prey.py` variants have **not** been renamed pending review of what they actually implement.
- **`__pycache__/` directories** contain orphan `.pyc` files from deleted source (`phase*_*`, `grid*_minimax`, `minimax_comparison`, `minimax_game`). Safe to delete.

---

**See also:** `PROJECT_SUMMARY.md` for high-level architecture, `QUICK_START.md` for command quick-reference, `VISUALIZATIONS.md` for visualization details.