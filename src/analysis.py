"""Confirmatory analysis functions. §6.4 of the spec.

Implemented and unit-tested pre-lock; frozen at code lock (freeze step 3).
Operates on per-task verified-solve rates (fraction of seeds verified).
"""
from __future__ import annotations

import numpy as np

SESOI = 0.05
FAMILY_ALPHA = 0.05
N_BOOT = 10_000


def arm_rate(per_task_rates: np.ndarray) -> float:
    """Mean verified-solve rate over tasks."""
    return float(np.mean(per_task_rates))


def paired_bootstrap_ci(x: np.ndarray, y: np.ndarray,
                        n_boot: int = N_BOOT, seed: int = 0,
                        alpha: float = FAMILY_ALPHA) -> tuple[float, float, float]:
    """Paired (by task) bootstrap CI for mean(x - y). Returns (est, lo, hi)."""
    rng = np.random.default_rng(seed)
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    n = len(d)
    est = float(np.mean(d))
    boots = np.empty(n_boot)
    for b in range(n_boot):
        boots[b] = np.mean(rng.choice(d, size=n, replace=True))
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return est, float(lo), float(hi)


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (family alpha applied by caller)."""
    m = len(p_values)
    order = np.argsort(p_values)
    adj = np.empty(m)
    for rank, idx in enumerate(order):
        adj[idx] = min(1.0, (m - rank) * p_values[idx])
    # enforce monotonicity in sorted order
    sord = np.sort(adj[order])
    for i in range(1, m):
        sord[i] = max(sord[i], sord[i - 1])
    out = np.empty(m)
    out[order] = sord
    return [float(v) for v in out]


def bootstrap_paired_pvalue(x: np.ndarray, y: np.ndarray,
                            n_boot: int = N_BOOT, seed: int = 1) -> float:
    """Two-sided bootstrap p-value for mean(x-y) != 0 (inversion of CI)."""
    rng = np.random.default_rng(seed)
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    n = len(d)
    est = np.mean(d)
    boots = np.array([np.mean(rng.choice(d, size=n, replace=True))
                      for _ in range(n_boot)])
    # two-sided: fraction of bootstraps on the opposite side of 0 from est
    if est >= 0:
        p = float(np.mean(boots <= 0))
    else:
        p = float(np.mean(boots >= 0))
    return min(1.0, 2 * p)


def classify_contrast(est: float, lo: float, hi: float,
                      sesoi: float = SESOI) -> str:
    """supported / detected but small / null / inconclusive. §6.4."""
    if lo > 0 and est >= sesoi:
        return "supported"
    if lo > 0 and est < sesoi:
        return "detected but small"
    if lo >= -sesoi and hi <= sesoi:
        return "null"
    return "inconclusive"


def precision_ok(x: np.ndarray, y: np.ndarray, sesoi: float = SESOI) -> tuple[bool, float, float]:
    """§6.4 precision check: is 3.3*SE <= SESOI? Returns (ok, se, 3.3*se)."""
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    se = float(np.std(d, ddof=1) / np.sqrt(len(d)))
    return (3.3 * se <= sesoi), se, 3.3 * se
