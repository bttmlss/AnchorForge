"""Residual signals. §3 of the spec.

- ε: mean of log2(1+|e_j|) over the k=8 training anchors.
- ε_H: fraction of anchors with e_j != 0 (sensitivity re-analysis only).
- Δε_in, Δ²ε_in: read along the ACCEPTED lineage (not iteration order).
- Bins: ε-bin (4 quantile bins, cut points fit once on tuning random walks,
  frozen after Stage 0d); Δε-bin; Δ²ε-bin.
"""
from __future__ import annotations

import math
import numpy as np


def epsilon(e_vec) -> float:
    """Primary scalar residual. Zero iff e == 0."""
    return float(np.mean(np.log2(1.0 + np.abs(np.asarray(e_vec, dtype=float)))))


def epsilon_h(e_vec) -> float:
    """Secondary: fraction of anchors with nonzero residual."""
    e = np.asarray(e_vec)
    return float(np.mean(e != 0))


class EpsBinFitter:
    """4 quantile bins for parent ε. Fit once on tuning-set random-walk ε
    values (Stage 0d), then frozen."""

    def __init__(self):
        self.cuts: tuple[float, float, float] | None = None

    def fit(self, eps_values) -> "EpsBinFitter":
        q = np.quantile(np.asarray(eps_values, dtype=float), [0.25, 0.5, 0.75])
        self.cuts = (float(q[0]), float(q[1]), float(q[2]))
        return self

    def bin(self, eps: float) -> int:
        assert self.cuts is not None, "EpsBinFitter not fit"
        c0, c1, c2 = self.cuts
        if eps < c0:
            return 0
        if eps < c1:
            return 1
        if eps < c2:
            return 2
        return 3


def delta_bin(d_eps_in: float | None, eps_parent: float) -> str:
    """Δε-bin. d_eps_in=None at root/restart."""
    if d_eps_in is None:
        return "none"
    if d_eps_in == 0.0:
        return "flat"
    if abs(d_eps_in) < 0.25 * eps_parent:
        return "small"
    return "large"


def delta2_bin(d_eps_in_p: float | None, d_eps_in_g: float | None) -> str:
    """Δ²ε-bin. None when no grandparent (or no parent)."""
    if d_eps_in_p is None or d_eps_in_g is None:
        return "none"
    ap, ag = abs(d_eps_in_p), abs(d_eps_in_g)
    if ap > 1.25 * ag:
        return "accel"
    if ap < 0.75 * ag:
        return "decel"
    return "steady"  # includes both zero


def lineage_deltas(eps_lineage: list[float]) -> tuple[float | None, float | None]:
    """Given accepted-lineage ε values (oldest..current parent), return
    (Δε_in(p), Δε_in(g)) for the current parent. None where undefined."""
    n = len(eps_lineage)
    if n < 2:
        return None, None
    d_p = eps_lineage[-1] - eps_lineage[-2]
    d_g = eps_lineage[-2] - eps_lineage[-3] if n >= 3 else None
    return d_p, d_g
