"""Mutation operators. §5.1 of the spec.

Six types. propose(program, mtype, rng) returns the child program, or None if
the proposal is inapplicable (logged, not evaluated, not budgeted).

Decisions pinned here (frozen at code lock; reviewable):
- REPLACE_OP: location uniform; new instance uniform among the 38 others
  (never a silent no-op).
- NUDGE_PARAM: parameterized position uniform; direction ±1 uniform; the
  nudged param must be a legal value for that op (add: c!=0), else inapplicable.
- RESAMPLE_PARAM: parameterized position uniform; new param uniform among the
  legal values excluding the current one.
- INSERT: insertion position uniform in 0..L; instance uniform 0..38;
  inapplicable if L==7.
- DELETE: position uniform; inapplicable if L==1.
- SWAP_ADJACENT: left index uniform in 0..L-2; inapplicable if L<2.
"""
from __future__ import annotations

import random

from dsl import N_INSTANCES, MAX_LEN, instance

MUTATION_TYPES = ("REPLACE_OP", "NUDGE_PARAM", "RESAMPLE_PARAM",
                  "INSERT", "DELETE", "SWAP_ADJACENT")

# op -> sorted list of legal params
_PARAM_VALUES: dict[str, list[int]] = {
    "add": list(range(-9, 0)) + list(range(1, 10)),
    "mul": [-4, -3, -2, 2, 3, 4],
    "mod": list(range(2, 10)),
    "fdiv": list(range(2, 6)),
}

# (op, param) -> instance index, for parameterized ops
_INDEX_OF: dict[tuple[str, int], int] = {}
for _i in range(N_INSTANCES):
    _op, _p = instance(_i)
    if _p is not None:
        _INDEX_OF[(_op, _p)] = _i


def _param_positions(program: tuple[int, ...]) -> list[int]:
    return [j for j, a in enumerate(program) if instance(a)[1] is not None]


def propose(program: tuple[int, ...], mtype: str,
            rng: random.Random) -> tuple[int, ...] | None:
    L = len(program)
    if mtype == "REPLACE_OP":
        j = rng.randrange(L)
        cur = program[j]
        new = rng.randrange(N_INSTANCES - 1)
        if new >= cur:
            new += 1
        return program[:j] + (new,) + program[j + 1:]
    if mtype == "NUDGE_PARAM":
        pos = _param_positions(program)
        if not pos:
            return None
        j = rng.choice(pos)
        op, p = instance(program[j])
        assert p is not None
        q = p + rng.choice((-1, 1))
        if q not in _PARAM_VALUES[op]:
            return None
        return program[:j] + (_INDEX_OF[(op, q)],) + program[j + 1:]
    if mtype == "RESAMPLE_PARAM":
        pos = _param_positions(program)
        if not pos:
            return None
        j = rng.choice(pos)
        op, p = instance(program[j])
        assert p is not None
        choices = [c for c in _PARAM_VALUES[op] if c != p]
        q = rng.choice(choices)
        return program[:j] + (_INDEX_OF[(op, q)],) + program[j + 1:]
    if mtype == "INSERT":
        if L >= MAX_LEN:
            return None
        j = rng.randrange(L + 1)
        new = rng.randrange(N_INSTANCES)
        return program[:j] + (new,) + program[j:]
    if mtype == "DELETE":
        if L <= 1:
            return None
        j = rng.randrange(L)
        return program[:j] + program[j + 1:]
    if mtype == "SWAP_ADJACENT":
        if L < 2:
            return None
        j = rng.randrange(L - 1)
        lst = list(program)
        lst[j], lst[j + 1] = lst[j + 1], lst[j]
        return tuple(lst)
    raise ValueError(mtype)
