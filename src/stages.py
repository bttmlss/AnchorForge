"""Experiment stages. §6.2 of the spec.

0c: steerability bar (§7) on tuning tasks.
0d: budget calibration (smallest N with R verified-rate in [0.15, 0.50]).
1:  table training (§5.3).
2:  confirmatory run (held-out; NOT run before code+task locks).

Seeds: 20 per task per arm, deterministic from (task_id, arm, rep).
"""
from __future__ import annotations

import json
import os
import random

import arms
import dsl
import mutations
import residuals
import search
import tables


def run_seed(task_id: str, arm: str, rep: int) -> int:
    """Deterministic seed per (task, arm, rep). Uses SHA-256 (NOT Python's
    salted hash()) so seeds reproduce across processes. Documented."""
    import hashlib
    h = hashlib.sha256(f"{task_id}|{arm}|{rep}".encode()).hexdigest()
    return int(h[:8], 16) % 2**31


# ---------------------------------------------------------------- Stage 0c
def collect_steerability(tuning_tasks: list[dict], eps_binner,
                         n_walks_per_task: int = 10, walk_len: int = 5,
                         per_type: int = 4, seed: int = 77) -> list[tuple]:
    """(mtype, eps_bin, improved) for proposals on random-walk parents.
    improved = strictly lower child ε. Inapplicable skipped."""
    rng = random.Random(seed)
    rows = []
    for task in tuning_tasks:
        tx, tt = task["train_anchors"], task["train_targets"]
        for _ in range(n_walks_per_task):
            parent = search.random_program(rng)
            for _ in range(walk_len):
                valid, y = dsl.evaluate_vector(parent, tx)
                if valid and not any(v is None for v in y):
                    e = [a - b for a, b in zip(y, tt)]
                    peps = residuals.epsilon(e)
                    pb = eps_binner.bin(peps)
                    for m in tables.MTYPES:
                        for _ in range(per_type):
                            child = mutations.propose(parent, m, rng)
                            if child is None:
                                continue
                            cv, cy = dsl.evaluate_vector(child, tx)
                            if not cv or any(v is None for v in cy):
                                improved = False
                            else:
                                ce = [a - b for a, b in zip(cy, tt)]
                                improved = residuals.epsilon(ce) < peps
                            rows.append((m, pb, improved))
                nxt = mutations.propose(
                    parent, rng.choice(tables.MTYPES), rng)
                if nxt is not None:
                    parent = nxt
    return rows


def s1_test(rows: list[tuple], n_shuffle: int = 1000,
            seed: int = 913) -> dict:
    """S1: in ≥1 bin, spread ≥0.03 and beats label-shuffle null at p≤0.0125."""
    rng = random.Random(seed)
    out = {"pass": False, "bins": {}}
    for b in range(4):
        cell = [(m, imp) for (m, bb, imp) in rows if bb == b]
        if not cell:
            continue
        # p(m,b) per type
        pm = {}
        for m in tables.MTYPES:
            imps = [imp for (mm, imp) in cell if mm == m]
            pm[m] = sum(imps) / len(imps) if imps else 0.0
        mean_p = sum(pm.values()) / len(pm)
        spread = max(pm.values()) - mean_p
        bin_res = {"spread": spread, "p": None, "pass": False,
                   "n": len(cell)}
        if spread >= 0.03:
            labels = [m for (m, _) in cell]
            imps = [imp for (_, imp) in cell]
            ge = 0
            for _ in range(n_shuffle):
                rng.shuffle(labels)
                spm = {}
                for m in tables.MTYPES:
                    ii = [imp for (lab, imp) in zip(labels, imps)
                          if lab == m]
                    spm[m] = sum(ii) / len(ii) if ii else 0.0
                smean = sum(spm.values()) / len(spm)
                if max(spm.values()) - smean >= spread:
                    ge += 1
            p = (ge + 1) / (n_shuffle + 1)
            bin_res["p"] = p
            bin_res["pass"] = p <= 0.0125
        out["bins"][b] = bin_res
        if bin_res["pass"]:
            out["pass"] = True
    return out


def s2_test(rows: list[tuple], n_shuffle: int = 1000,
            seed: int = 914) -> dict:
    """S2: op×bin interaction. Statistic = variance across bins of the
    type-effect profile; null shuffles bin labels within type. p≤0.01."""
    rng = random.Random(seed)
    # observed: for each type, p(improved|type,bin); interaction stat =
    # sum over types of variance across bins
    def stat(data):
        tot = 0.0
        for m in tables.MTYPES:
            ps = []
            for b in range(4):
                imps = [imp for (mm, bb, imp) in data
                        if mm == m and bb == b]
                if imps:
                    ps.append(sum(imps) / len(imps))
            if len(ps) > 1:
                mu = sum(ps) / len(ps)
                tot += sum((p - mu) ** 2 for p in ps) / len(ps)
        return tot
    obs = stat(rows)
    # null: shuffle bin labels within each type
    by_type = {}
    for (m, b, imp) in rows:
        by_type.setdefault(m, []).append((b, imp))
    ge = 0
    for _ in range(n_shuffle):
        shuf = []
        for m, lst in by_type.items():
            bins = [b for (b, _) in lst]
            rng.shuffle(bins)
            shuf.extend((m, b, imp)
                        for b, (_, imp) in zip(bins, lst))
        if stat(shuf) >= obs:
            ge += 1
    p = (ge + 1) / (n_shuffle + 1)
    return {"stat": obs, "p": p, "pass": p <= 0.01}


def stage_0c(tuning_tasks: list[dict], eps_binner) -> dict:
    rows = collect_steerability(tuning_tasks, eps_binner)
    # check cell counts
    from collections import Counter
    cc = Counter((m, b) for (m, b, _) in rows)
    min_cell = min(cc.values()) if cc else 0
    s1 = s1_test(rows)
    s2 = s2_test(rows)
    return {"n_proposals": len(rows), "min_cell": min_cell,
            "S1": s1, "S2": s2}


# ---------------------------------------------------------------- Stage 0d
def fit_eps_binner(tuning_tasks: list[dict], seed: int = 555,
                   n_walks_per_task: int = 40, walk_len: int = 5
                   ) -> residuals.EpsBinFitter:
    """Fit 4 quantile bins from tuning-set random-walk ε values."""
    rng = random.Random(seed)
    eps_vals = []
    for task in tuning_tasks:
        tx, tt = task["train_anchors"], task["train_targets"]
        for _ in range(n_walks_per_task):
            prog = search.random_program(rng)
            for _ in range(walk_len):
                valid, y = dsl.evaluate_vector(prog, tx)
                if valid and not any(v is None for v in y):
                    e = [a - b for a, b in zip(y, tt)]
                    eps_vals.append(residuals.epsilon(e))
                # random step
                nxt = mutations.propose(
                    prog, rng.choice(tables.MTYPES), rng)
                if nxt is not None:
                    prog = nxt
    return residuals.EpsBinFitter().fit(eps_vals)


def stage_0d(tuning_tasks_345: list[dict], eps_binner,
             code_commit: str, record_dir: str) -> dict:
    """Smallest N in {1000,2000,5000,10000} with R verified-rate in
    [0.15, 0.50] on L* 3-5 tuning tasks. 20 seeds/task."""
    os.makedirs(record_dir, exist_ok=True)
    for N in (1000, 2000, 5000, 10000):
        n_ver, n_tot = 0, 0
        for task in tuning_tasks_345:
            for rep in range(20):
                s = run_seed(task["task_id"], "R", rep)
                rp = f"{record_dir}/0d_N{N}_{task['task_id']}_r{rep}.jsonl"
                r = arms.run_arm(task, "R", s, N, None, None,
                                 eps_binner, code_commit, rp)
                n_tot += 1
                n_ver += 1 if r["verified"] else 0
        rate = n_ver / n_tot
        if 0.15 <= rate <= 0.50:
            return {"N": N, "verified_rate": rate,
                    "n_tasks": len(tuning_tasks_345)}
    return {"N": None, "verified_rate": rate,
            "n_tasks": len(tuning_tasks_345),
            "note": "no N in range; closest reported"}


# ---------------------------------------------------------------- Stage 1
def stage_1(tuning_tasks: list[dict], N: int, eps_binner,
            code_commit: str, record_dir: str, table_path: str) -> dict:
    table_set, hs_marginal = tables.train(
        tuning_tasks, N, eps_binner, code_commit, record_dir)
    tables.save_tables(table_set, hs_marginal, table_path)
    return {"table_path": table_path,
            "n_tasks": len(tuning_tasks)}


# ---------------------------------------------------------------- Stage 2
def stage_2(confirmatory_tasks: list[dict], N: int, eps_binner,
            table_path: str, code_commit: str, record_dir: str,
            summary_path: str) -> dict:
    """Confirmatory run. NOT run before code+task locks."""
    table_set, hs_marginal = tables.load_tables(table_path)
    os.makedirs(record_dir, exist_ok=True)
    arms_list = ["R", "M", "E", "H1", "H2", "HS", "ENUM"]
    summaries = []
    for task in confirmatory_tasks:
        for arm in arms_list:
            for rep in range(20):
                s = run_seed(task["task_id"], arm, rep)
                rp = (f"{record_dir}/{task['task_id']}_{arm}"
                      f"_r{rep}.jsonl")
                r = arms.run_arm(task, arm, s, N, table_set,
                                 hs_marginal, eps_binner,
                                 code_commit, rp)
                summaries.append(r)
    with open(summary_path, "w") as f:
        json.dump(summaries, f)
    return {"n_runs": len(summaries), "summary_path": summary_path}
