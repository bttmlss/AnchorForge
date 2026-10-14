"""Minimal-length audit (L*) via exhaustive vectorized search. §2.3 of the spec.

For each task, finds the shortest DSL program (length 1..4) matching the
hidden program on all 48 anchors. L*=5 means no length-≤4 program matches.

Vectorized with numpy int64. Overflow safety: all intermediate magnitudes are
bounded by the 1e12 invalid threshold before each op, and the only op that can
overflow int64 (sq) is guarded — |v| > 1e6 implies v^2 > 1e12 (invalid) so it
is never computed in int64.
"""
from __future__ import annotations

import numpy as np

from dsl import N_INSTANCES

# op type per instance: 0=add, 1=mul, 2=sq, 3=neg, 4=abs, 5=mod, 6=fdiv
_OP_TYPE = np.zeros(N_INSTANCES, dtype=np.int64)
_PARAM = np.zeros(N_INSTANCES, dtype=np.int64)
_idx = 0
for c in list(range(-9, 0)) + list(range(1, 10)):
    _OP_TYPE[_idx] = 0; _PARAM[_idx] = c; _idx += 1
for c in (-4, -3, -2, 2, 3, 4):
    _OP_TYPE[_idx] = 1; _PARAM[_idx] = c; _idx += 1
_OP_TYPE[_idx] = 2; _idx += 1   # sq
_OP_TYPE[_idx] = 3; _idx += 1   # neg
_OP_TYPE[_idx] = 4; _idx += 1   # abs
for m in range(2, 10):
    _OP_TYPE[_idx] = 5; _PARAM[_idx] = m; _idx += 1
for d in range(2, 6):
    _OP_TYPE[_idx] = 6; _PARAM[_idx] = d; _idx += 1
assert _idx == N_INSTANCES

_SQ_GUARD = 10 ** 6  # |v| > 1e6 -> v^2 > 1e12 -> invalid; never computed
_INVALID = 10 ** 12
_CHUNK = 250_000


def _programs_of_length(L: int) -> np.ndarray:
    """All 39^L index tuples, lexicographic (== rank order within length)."""
    n = N_INSTANCES ** L
    grids = np.unravel_index(np.arange(n, dtype=np.int64), (N_INSTANCES,) * L)
    return np.stack(grids, axis=1)  # (n, L)


def _apply_position(values: np.ndarray, invalid: np.ndarray,
                    prog: np.ndarray, j: int) -> None:
    """Apply op position j in-place. values: (n, k) int64. invalid: (n, k) bool."""
    p = prog[:, j]
    ot = _OP_TYPE[p]
    pr = _PARAM[p]
    v = values
    # add
    m = ot == 0
    if m.any():
        v[m] += pr[m][:, None]
    # mul
    m = ot == 1
    if m.any():
        v[m] *= pr[m][:, None]
    # sq (guarded: |v| > 1e6 implies v^2 > 1e12, so never computed in int64)
    m = ot == 2
    if m.any():
        m2d = m[:, None]  # broadcast rows -> (n, k)
        too_big = m2d & (np.abs(v) > _SQ_GUARD)
        invalid |= too_big
        do_sq = m2d & ~too_big
        v[do_sq] = v[do_sq] * v[do_sq]
    # neg
    m = ot == 3
    if m.any():
        v[m] = -v[m]
    # abs
    m = ot == 4
    if m.any():
        v[m] = np.abs(v[m])
    # mod (Python floor semantics == numpy for int64 with positive modulus)
    m = ot == 5
    if m.any():
        v[m] %= pr[m][:, None]
    # fdiv (floor)
    m = ot == 6
    if m.any():
        v[m] //= pr[m][:, None]
    # invalid threshold
    invalid |= np.abs(v) > _INVALID


def evaluate_programs(prog: np.ndarray, anchors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized evaluation. Returns (valid (n,), values (n, k))."""
    n = prog.shape[0]
    k = anchors.shape[0]
    values = np.broadcast_to(anchors, (n, k)).copy()
    invalid = np.zeros((n, k), dtype=bool)
    for j in range(prog.shape[1]):
        _apply_position(values, invalid, prog, j)
    valid = ~invalid.any(axis=1)
    return valid, values


def _programs_of_length_chunked(L: int):
    n = N_INSTANCES ** L
    for start in range(0, n, _CHUNK):
        end = min(start + _CHUNK, n)
        grids = np.unravel_index(np.arange(start, end, dtype=np.int64),
                                 (N_INSTANCES,) * L)
        yield np.stack(grids, axis=1)


def audit_task(task) -> None:
    """Set task.L_star and task.n_eq in place. §2.3.

    Two-phase: match on the 8 training anchors first (cheap), then verify
    the hits on the 40 verification anchors. Exact count at the found level.
    """
    train_a = np.array(task.train_anchors, dtype=np.int64)
    train_t = np.array(task.train_targets, dtype=np.int64)
    verif_a = np.array(task.verif_anchors, dtype=np.int64)
    verif_t = np.array(task.verif_targets, dtype=np.int64)
    for L in (1, 2, 3, 4):
        c = 0
        for prog in _programs_of_length_chunked(L):
            valid8, values8 = evaluate_programs(prog, train_a)
            hit = valid8 & (values8 == train_t).all(axis=1)
            if hit.any():
                ph = prog[hit]
                valid40, values40 = evaluate_programs(ph, verif_a)
                c += int((valid40 & (values40 == verif_t).all(axis=1)).sum())
        if c > 0:
            task.L_star = L
            task.n_eq = c
            return
    task.L_star = 5
    task.n_eq = 1  # lower bound; enough since ENUM cannot reach length 5
