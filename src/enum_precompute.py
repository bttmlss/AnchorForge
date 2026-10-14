"""ENUM outcome precompute. §6.7 of the spec.

Vectorized code path, independent from the ENUM runner (enum_runner.py).

Walks ranks 0..max_rank-1 in exact enumeration order, evaluates each against
the 8 training anchors, records the first training-set match and its rank,
and classifies it on the 40 verification anchors (verified / overfit).
No match within budget -> unsolved.
"""
from __future__ import annotations

import numpy as np

from audit import evaluate_programs, _programs_of_length_chunked
from dsl import N_INSTANCES

LEN1 = N_INSTANCES            # 39
LEN2 = N_INSTANCES ** 2       # 1521
RANK_L2_END = LEN1 + LEN2     # 1560


def _length3_prefix(count: int):
    """First `count` length-3 programs in rank order (lexicographic)."""
    grids = np.unravel_index(np.arange(count, dtype=np.int64),
                             (N_INSTANCES,) * 3)
    return np.stack(grids, axis=1)


def precompute(task, max_rank: int = 10000) -> dict:
    """Returns {first_rank, outcome} with outcome in verified/overfit/unsolved."""
    train_a = np.array(task.train_anchors, dtype=np.int64)
    train_t = np.array(task.train_targets, dtype=np.int64)
    verif_a = np.array(task.verif_anchors, dtype=np.int64)
    verif_t = np.array(task.verif_targets, dtype=np.int64)

    # Evaluate in rank order: length 1, length 2, length-3 prefix.
    groups = []
    n1 = min(LEN1, max_rank)
    if n1 > 0:
        groups.append((0, next(_programs_of_length_chunked(1))[:n1]))
    if max_rank > LEN1:
        n2 = min(LEN2, max_rank - LEN1)
        groups.append((LEN1, next(_programs_of_length_chunked(2))[:n2]))
    if max_rank > RANK_L2_END:
        n3 = max_rank - RANK_L2_END
        groups.append((RANK_L2_END, _length3_prefix(n3)))

    first_rank = None
    first_prog = None
    for base, prog in groups:
        if prog.shape[0] == 0:
            continue
        valid, values = evaluate_programs(prog, train_a)
        hit = valid & (values == train_t).all(axis=1)
        idx = np.flatnonzero(hit)
        if len(idx):
            first_rank = base + int(idx[0])
            first_prog = prog[int(idx[0])]
            break

    if first_rank is None:
        return {"first_rank": None, "outcome": "unsolved"}

    valid, values = evaluate_programs(first_prog.reshape(1, -1), verif_a)
    if bool(valid[0]) and bool((values[0] == verif_t).all()):
        outcome = "verified"
    else:
        outcome = "overfit"  # includes invalid-on-verification
    return {"first_rank": first_rank, "outcome": outcome}
