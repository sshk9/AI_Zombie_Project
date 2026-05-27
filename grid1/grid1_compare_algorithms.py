"""
Benchmark BFS, A*, and the LLM agent on the same grid1 problem.

Reports path length, planning work (nodes expanded for classical, tool calls
for LLM), tokens, wall time, and whether the path matched optimal. Optionally
appends one row per algorithm to benchmarks/results.csv for tracking runs
over time.

Run:
    python grid1/grid1_compare_algorithms.py
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone

# Make `config`, `utils`, and the `grid1` package importable when run from
# the project root.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import GRID, PLAYER_START_POS, GOAL_POS  # noqa: E402
from utils import get_bfs_path, get_astar_path  # noqa: E402
from grid1.grid1_llm_agent import run_llm_agent  # noqa: E402


# ---------------------------------------------------------------------------
# Knobs
# ---------------------------------------------------------------------------

LLM_TRIALS = 3              # bump to 3-5 for variance estimate (multiplies API cost)
LLM_MODEL = "claude-sonnet-4-6"
LLM_MAX_CALLS = 100
SAVE_CSV = True
CSV_PATH = os.path.join(_PROJECT_ROOT, "benchmarks", "results.csv")


# ---------------------------------------------------------------------------
# Per-algorithm runners — each returns a dict with the same shape
# ---------------------------------------------------------------------------

def bench_bfs(start, goal, grid):
    t0 = time.perf_counter()
    path, info = get_bfs_path(start, goal, grid=grid, return_info=True)
    elapsed = time.perf_counter() - t0
    return {
        "algorithm": "BFS",
        "path_length": (len(path) - 1) if path else None,
        "planning_work": info["nodes_expanded"],
        "invalid_moves": None,
        "input_tokens": None,
        "output_tokens": None,
        "wall_time_s": elapsed,
        "finish_reason": "success" if path else "no_path",
    }


def bench_astar(start, goal, grid):
    t0 = time.perf_counter()
    path, info = get_astar_path(start, goal, grid=grid, return_info=True)
    elapsed = time.perf_counter() - t0
    return {
        "algorithm": "A*",
        "path_length": (len(path) - 1) if path else None,
        "planning_work": info["nodes_expanded"],
        "invalid_moves": None,
        "input_tokens": None,
        "output_tokens": None,
        "wall_time_s": elapsed,
        "finish_reason": "success" if path else "no_path",
    }


def bench_llm(start, goal, grid, max_calls=LLM_MAX_CALLS, model=LLM_MODEL):
    t0 = time.perf_counter()
    try:
        result = run_llm_agent(
            start=start,
            goal=goal,
            grid=grid,
            max_calls=max_calls,
            model=model,
            verbose=False,
        )
        elapsed = time.perf_counter() - t0
        return {
            "algorithm": f"LLM ({model})",
            "path_length": result["path_length"] if result["goal_reached"] else None,
            "planning_work": result["tool_calls"],
            "invalid_moves": result["invalid_moves"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "wall_time_s": elapsed,
            "finish_reason": result["finish_reason"],
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "algorithm": f"LLM ({model})",
            "path_length": None,
            "planning_work": None,
            "invalid_moves": None,
            "input_tokens": None,
            "output_tokens": None,
            "wall_time_s": elapsed,
            "finish_reason": f"error: {type(e).__name__}: {e}",
        }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt(val, fmt="{}"):
    return "-" if val is None else fmt.format(val)


def print_results(results, optimal_length=None):
    headers = [
        "Algorithm",
        "Path len",
        "Optimal?",
        "Planning work",
        "Invalid",
        "In tokens",
        "Out tokens",
        "Time (s)",
        "Finish",
    ]

    rows = []
    for r in results:
        if r["path_length"] is None:
            opt_flag = "-"
        elif optimal_length is None:
            opt_flag = " "
        else:
            opt_flag = "yes" if r["path_length"] == optimal_length else "no"

        rows.append([
            r["algorithm"],
            _fmt(r["path_length"]),
            opt_flag,
            _fmt(r["planning_work"]),
            _fmt(r["invalid_moves"]),
            _fmt(r["input_tokens"]),
            _fmt(r["output_tokens"]),
            _fmt(r["wall_time_s"], "{:.3f}"),
            r["finish_reason"],
        ])

    widths = [
        max(len(str(h)), *(len(str(row[i])) for row in rows))
        for i, h in enumerate(headers)
    ]
    sep = "  "
    print(sep.join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print(sep.join("-" * w for w in widths))
    for row in rows:
        print(sep.join(str(c).ljust(widths[i]) for i, c in enumerate(row)))


def append_csv(results, csv_path):
    new_file = not os.path.exists(csv_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = [
        "timestamp",
        "grid_scale",
        "algorithm",
        "path_length",
        "planning_work",
        "invalid_moves",
        "input_tokens",
        "output_tokens",
        "wall_time_s",
        "finish_reason",
    ]
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            writer.writeheader()
        for r in results:
            row = {
                "timestamp": timestamp,
                "grid_scale": "grid1",
            }
            for k in fieldnames:
                if k not in row:
                    row[k] = r.get(k)
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start = PLAYER_START_POS
    goal = GOAL_POS
    grid = GRID

    print(f"grid1 benchmark: start={start}, goal={goal}, "
          f"size={len(grid[0])}x{len(grid)}")
    print()

    results = []

    print("Running BFS...", flush=True)
    results.append(bench_bfs(start, goal, grid))

    print("Running A*...", flush=True)
    results.append(bench_astar(start, goal, grid))

    # BFS is optimal on an unweighted grid — use its path length as the baseline.
    optimal_length = results[0]["path_length"]

    for trial in range(LLM_TRIALS):
        label = f" (trial {trial + 1}/{LLM_TRIALS})" if LLM_TRIALS > 1 else ""
        print(f"Running LLM agent{label}...", flush=True)
        r = bench_llm(start, goal, grid)
        if LLM_TRIALS > 1:
            r["algorithm"] = f"{r['algorithm']} #{trial + 1}"
        results.append(r)

    print()
    print_results(results, optimal_length=optimal_length)

    if SAVE_CSV:
        append_csv(results, CSV_PATH)
        print()
        rel = os.path.relpath(CSV_PATH, _PROJECT_ROOT)
        print(f"Appended {len(results)} row(s) to {rel}")


if __name__ == "__main__":
    main()