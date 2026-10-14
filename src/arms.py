"""Experiment arms. §6.3 of the spec.

R, M, E, H1, H2, HS use the shared walk skeleton (§5.1) with arm-specific U.
ENUM enumerates by canonical rank and must reproduce the §6.7 precompute.
Equal evaluation budget N per run (for ENUM, N = max rank).
"""
from __future__ import annotations

import random

import dsl
import records
import residuals
import search
import tables


def run_arm(task: dict, arm: str, seed: int, N: int,
            table_set: dict | None, hs_marginal: dict | None,
            eps_binner, code_commit: str, record_path: str) -> dict:
    rng = random.Random(seed)
    if arm == "ENUM":
        return _run_enum(task, seed, N, code_commit, record_path)
    propose = tables.make_propose_type(arm, table_set, hs_marginal, rng)
    return search.run(task, arm, seed, N, propose, eps_binner,
                      code_commit, record_path)


def _run_enum(task: dict, seed: int, N: int, code_commit: str,
              record_path: str) -> dict:
    """ENUM arm. Must reproduce enum_precompute exactly (Stage 0b gate)."""
    writer = records.RecordWriter(record_path)
    tx, tt = task["train_anchors"], task["train_targets"]
    vx, vt = task["verif_anchors"], task["verif_targets"]
    result = {"task_id": task["task_id"], "arm": "ENUM", "seed": seed,
              "solved": False, "verified": False, "overfit": False,
              "evals": 0, "first_rank": None}
    for rank in range(N):
        prog = dsl.unrank(rank)
        valid, y = dsl.evaluate_vector(prog, tx)
        if not valid or any(v is None for v in y):
            e, eps, eps_h = None, None, None
            outcome = "invalid"
        else:
            e = [a - b for a, b in zip(y, tt)]
            eps, eps_h = residuals.epsilon(e), residuals.epsilon_h(e)
            outcome = "pass" if all(v == 0 for v in e) else "fail"
        rec = records.make_record(
            task_id=task["task_id"], arm="ENUM", seed=seed,
            eval_index=rank + 1, program=prog, parent_id=None,
            mutation=None, y=y if valid else None,
            e=e, eps=eps, eps_h=eps_h,
            d_eps_edge=None, d_eps_in_parent=None,
            d2_eps_in_parent=None, ctx_bins=None,
            accepted=True, outcome=outcome,
            restart_flag=False, code_commit=code_commit)
        writer.write(rec)
        if outcome == "pass":
            result.update(solved=True, first_rank=rank, evals=rank + 1)
            # classify on verification anchors
            vv, yv = dsl.evaluate_vector(prog, vx)
            if vv and all(v is not None for v in yv) and \
               all(a == b for a, b in zip(yv, vt)):
                result["verified"] = True
            else:
                result["overfit"] = True
            writer.close()
            return result
    result["evals"] = N
    writer.close()
    return result
