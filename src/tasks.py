"""AnchorForge task generator. §2.3 of the spec.

A task = hidden program g + 8 training anchors + 40 verification anchors.
Generation logs every rejected draw with a reason code.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from dsl import N_INSTANCES, evaluate, instance

TRAIN_K = 8
VERIF_K = 40
ANCHOR_LO, ANCHOR_HI = -20, 20
VERIF_LO, VERIF_HI = -40, 40

REASONS = ("target_invalid", "redundant_pair", "few_distinct_targets", "quota_full")


def _redundant_pair(a: int, b: int) -> bool:
    """Appendix A: left-to-right redundant adjacent instance pairs."""
    op1, p1 = instance(a)
    op2, p2 = instance(b)
    if op1 == "mod" and op2 == "mod":
        return p1 == p2
    return (op1, op2) in {
        ("add", "add"), ("mul", "mul"),
        ("neg", "neg"), ("neg", "mul"), ("mul", "neg"),
        ("abs", "abs"), ("neg", "abs"), ("neg", "sq"),
        ("abs", "sq"), ("sq", "abs"),
    }


def has_redundant_pair(program: tuple[int, ...]) -> bool:
    return any(_redundant_pair(program[i], program[i + 1]) for i in range(len(program) - 1))


@dataclass
class Task:
    task_id: str
    g: tuple[int, ...]
    d_nominal: int
    train_anchors: list[int]
    verif_anchors: list[int]
    train_targets: list[int]
    verif_targets: list[int]
    seed: int
    L_star: int | None = None
    n_eq: int | None = None


@dataclass
class GenerationStats:
    drawn: int = 0
    accepted: int = 0
    rejected: dict[str, int] = field(default_factory=lambda: {r: 0 for r in REASONS})

    def log_reject(self, reason: str) -> None:
        assert reason in REASONS
        self.rejected[reason] += 1
        self.drawn += 1


def draw_candidate(rng: random.Random, d_nominal: int, task_id: str, seed: int,
                   stats: GenerationStats) -> Task | None:
    """Draw one candidate task. Returns None (and logs reason) if rejected
    before the L* audit. The L* audit / stratification happens in generate()."""
    g = tuple(rng.randrange(N_INSTANCES) for _ in range(d_nominal))
    if has_redundant_pair(g):
        stats.log_reject("redundant_pair")
        return None
    train_anchors = rng.sample(range(ANCHOR_LO, ANCHOR_HI + 1), TRAIN_K)
    verif_pool = [x for x in range(VERIF_LO, VERIF_HI + 1) if x not in train_anchors]
    verif_anchors = rng.sample(verif_pool, VERIF_K)

    # target validity on all 48 anchors (§2.3)
    train_targets: list[int] = []
    for x in train_anchors:
        ok, v = evaluate(g, x)
        if not ok:
            stats.log_reject("target_invalid")
            return None
        train_targets.append(v)  # type: ignore[arg-type]
    verif_targets: list[int] = []
    for x in verif_anchors:
        ok, v = evaluate(g, x)
        if not ok:
            stats.log_reject("target_invalid")
            return None
        verif_targets.append(v)  # type: ignore[arg-type]

    if len(set(train_targets)) < 4:
        stats.log_reject("few_distinct_targets")
        return None

    stats.drawn += 1
    return Task(task_id=task_id, g=g, d_nominal=d_nominal,
                train_anchors=train_anchors, verif_anchors=verif_anchors,
                train_targets=train_targets, verif_targets=verif_targets, seed=seed)


def generate(tasks_needed: dict[int | str, int], seed: int, id_prefix: str,
             audit_fn) -> tuple[list[Task], GenerationStats]:
    """Generate tasks until each L* stratum reaches its quota.
    tasks_needed: {3: n, 4: n, 5: n, 'le2': n}. audit_fn(task) sets L_star/n_eq.
    Returns (tasks, stats)."""
    rng = random.Random(seed)
    stats = GenerationStats()
    quotas = dict(tasks_needed)
    have: dict[int | str, int] = {k: 0 for k in quotas}
    tasks: list[Task] = []
    i = 0
    while any(have[k] < quotas[k] for k in quotas):
        i += 1
        d_nominal = rng.choice((3, 4, 5))
        t = draw_candidate(rng, d_nominal, f"{id_prefix}-{i:05d}", seed, stats)
        if t is None:
            continue
        audit_fn(t)  # sets t.L_star, t.n_eq
        key: int | str = t.L_star if t.L_star is not None and t.L_star >= 3 else "le2"
        if key not in quotas or have[key] >= quotas[key]:
            stats.log_reject("quota_full")
            continue
        have[key] += 1
        stats.accepted += 1
        tasks.append(t)
    return tasks, stats
