"""Record schema. §4 of the spec.

One JSONL row per evaluation, never dropped, failures included.
"""
from __future__ import annotations

import hashlib
import json


def candidate_id(program: tuple[int, ...]) -> str:
    """Candidate id = hash of canonical program. §2.1."""
    h = hashlib.sha1()
    h.update(",".join(map(str, program)).encode())
    return h.hexdigest()[:16]


def y_sel(y: list[int] | None, eval_index: int, k: int) -> int | None:
    """Historical diagonal pick, logged only. §1."""
    if y is None:
        return None
    return y[((eval_index - 1) % k)]


def make_record(*, task_id: str, arm: str, seed: int, eval_index: int,
                program: tuple[int, ...], parent_id: str | None,
                mutation: dict | None, y: list[int] | None,
                e: list[int] | None, eps: float | None, eps_h: float | None,
                d_eps_edge: float | None, d_eps_in_parent: float | None,
                d2_eps_in_parent: float | None, ctx_bins: dict | None,
                accepted: bool, outcome: str, restart_flag: bool,
                code_commit: str) -> dict:
    assert outcome in ("pass", "fail", "invalid", "inapplicable")
    return {
        "task_id": task_id,
        "arm": arm,
        "seed": seed,
        "eval_index": eval_index,
        "candidate_id": candidate_id(program),
        "program": list(program),
        "parent_id": parent_id,
        "mutation": mutation,
        "y": y,
        "y_sel": y_sel(y, eval_index, 8),
        "e": e,
        "eps": eps,
        "eps_H": eps_h,
        "d_eps_edge": d_eps_edge,
        "d_eps_in_parent": d_eps_in_parent,
        "d2_eps_in_parent": d2_eps_in_parent,
        "ctx_bins": ctx_bins,
        "accepted": accepted,
        "outcome": outcome,
        "restart_flag": restart_flag,
        "code_commit": code_commit,
    }


class RecordWriter:
    def __init__(self, path: str):
        self._f = open(path, "w")

    def write(self, rec: dict) -> None:
        self._f.write(json.dumps(rec) + "\n")

    def close(self) -> None:
        self._f.close()
