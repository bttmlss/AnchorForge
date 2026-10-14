"""AnchorForge DSL: operators, program representation, exact evaluation.

Reference implementation using Python integers (exact, unbounded).
§2.1, §2.2 of the spec.

A program is a tuple of operator-instance indices (0-38), length 1..7,
applied left to right.
"""
from __future__ import annotations

INVALID_THRESHOLD = 10 ** 12
MAX_LEN = 7

# Instance index -> (op_name, param). §2.1 ordering.
_INSTANCES: list[tuple[str, int | None]] = []
for c in range(-9, 0):
    _INSTANCES.append(("add", c))
for c in range(1, 10):
    _INSTANCES.append(("add", c))
for c in (-4, -3, -2, 2, 3, 4):
    _INSTANCES.append(("mul", c))
_INSTANCES.append(("sq", None))
_INSTANCES.append(("neg", None))
_INSTANCES.append(("abs", None))
for m in range(2, 10):
    _INSTANCES.append(("mod", m))
for d in range(2, 6):
    _INSTANCES.append(("fdiv", d))

assert len(_INSTANCES) == 39
N_INSTANCES = 39


def instance(idx: int) -> tuple[str, int | None]:
    return _INSTANCES[idx]


def describe(program: tuple[int, ...]) -> str:
    parts = []
    for a in program:
        op, p = _INSTANCES[a]
        parts.append(f"{op}({p})" if p is not None else op)
    return "[" + ", ".join(parts) + "]"


def canonical_rank(program: tuple[int, ...]) -> int:
    """0-based rank: length-major, lexicographic within length. §2.1."""
    L = len(program)
    base = sum(N_INSTANCES ** l for l in range(1, L))
    return base + sum(a * (N_INSTANCES ** (L - 1 - j)) for j, a in enumerate(program))


def unrank(rank: int) -> tuple[int, ...]:
    """Inverse of canonical_rank."""
    L = 1
    while rank >= sum(N_INSTANCES ** l for l in range(1, L + 1)):
        L += 1
    base = sum(N_INSTANCES ** l for l in range(1, L))
    r = rank - base
    out = []
    for j in range(L):
        div = N_INSTANCES ** (L - 1 - j)
        out.append(r // div)
        r %= div
    return tuple(out)


def apply_op(x: int, idx: int) -> int:
    op, p = _INSTANCES[idx]
    if op == "add":
        return x + p  # type: ignore[operator]
    if op == "mul":
        return x * p  # type: ignore[operator]
    if op == "sq":
        return x * x
    if op == "neg":
        return -x
    if op == "abs":
        return abs(x)
    if op == "mod":
        return x % p  # type: ignore[operator]  # Python floor semantics, p > 0
    if op == "fdiv":
        return x // p  # type: ignore[operator]  # Python floor semantics, p > 0
    raise ValueError(op)


def evaluate(program: tuple[int, ...], x: int) -> tuple[bool, int | None]:
    """Exact evaluation. Returns (valid, value). Invalid if any intermediate
    exceeds 1e12 in magnitude (§2.2)."""
    v = x
    for a in program:
        v = apply_op(v, a)
        if abs(v) > INVALID_THRESHOLD:
            return False, None
    return True, v


def evaluate_vector(program: tuple[int, ...], xs: list[int]) -> tuple[bool, list[int | None]]:
    """Evaluate on several anchors. valid=False if invalid on ANY anchor."""
    vals: list[int | None] = []
    for x in xs:
        ok, v = evaluate(program, x)
        if not ok:
            return False, []
        vals.append(v)
    return True, vals  # type: ignore[return-value]
