"""ENUM runner: independent implementation for the §6.2 0b correctness gate.

Deliberately simple Python loop using dsl.evaluate (exact Python ints).
Must reproduce enum_precompute.precompute() exactly on every task.
"""
from __future__ import annotations

from dsl import unrank, evaluate


def run_enum(task, N: int) -> dict:
    """Enumerate ranks 0..N-1. Returns {first_rank, outcome}."""
    for rank in range(N):
        prog = unrank(rank)
        ok, vals = _match_training(prog, task)
        if ok:
            return {"first_rank": rank, "outcome": _classify(prog, task)}
    return {"first_rank": None, "outcome": "unsolved"}


def _match_training(prog, task) -> tuple[bool, list]:
    for x, t in zip(task.train_anchors, task.train_targets):
        ok, v = evaluate(prog, x)
        if not ok or v != t:
            return False, []
    return True, []


def _classify(prog, task) -> str:
    for x, t in zip(task.verif_anchors, task.verif_targets):
        ok, v = evaluate(prog, x)
        if not ok or v != t:
            return "overfit"
    return "verified"
