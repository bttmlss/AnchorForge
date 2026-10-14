"""Pre-lock checks runner. Appendix B items 1-4.

B1: evaluator unit tests (Stage 0a).
B2: task-generator audit (distinct-target filter pass rate).
B3: L* audit + ENUM precompute on tuning/positive-control tasks;
    ENUM runner reproduces precompute exactly.
B4: mutation-type applicability rates on random programs.

Generates tuning tasks (40) and positive-control tasks (20). Does NOT
generate the confirmatory set (freeze step 4, after code lock).
"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parent / "src"
sys.path.insert(0, str(SRC))

from tasks import generate
from audit import audit_task
from enum_precompute import precompute
from enum_runner import run_enum
from mutations import MUTATION_TYPES, propose
from dsl import N_INSTANCES

RUNS = HERE
TUNING_SEED = 1000
POSCTL_SEED = 2000

results: dict = {"checks": {}}


def task_to_dict(t):
    return {
        "task_id": t.task_id, "g": list(t.g), "d_nominal": t.d_nominal,
        "train_anchors": t.train_anchors, "verif_anchors": t.verif_anchors,
        "train_targets": t.train_targets, "verif_targets": t.verif_targets,
        "seed": t.seed, "L_star": t.L_star, "n_eq": t.n_eq,
    }


def main():
    t0 = time.time()

    # ---- B1: evaluator unit tests
    print("B1: evaluator unit tests...", flush=True)
    r = subprocess.run([sys.executable, str(HERE.parent / "tests" / "test_0a_evaluator.py")],
                       capture_output=True, text=True)
    b1_pass = r.returncode == 0
    print(r.stdout.strip().splitlines()[-1])
    results["checks"]["B1_evaluator_unit_tests"] = {
        "pass": b1_pass, "detail": r.stdout.strip().splitlines()[-1]}

    # ---- generate tuning tasks (40) + positive control (20)
    print("generating tuning tasks (40)...", flush=True)
    t1 = time.time()
    tuning, stats_t = generate({3: 10, 4: 10, 5: 10, "le2": 10},
                               TUNING_SEED, "tune", audit_task)
    print(f"  done in {time.time()-t1:.0f}s; {stats_t}", flush=True)
    print("generating positive-control tasks (20)...", flush=True)
    t1 = time.time()
    posctl, stats_p = generate({"le2": 20}, POSCTL_SEED, "pos", audit_task)
    print(f"  done in {time.time()-t1:.0f}s; {stats_p}", flush=True)

    (RUNS / "tuning_tasks.json").write_text(
        json.dumps([task_to_dict(t) for t in tuning], indent=1))
    (RUNS / "positive_control_tasks.json").write_text(
        json.dumps([task_to_dict(t) for t in posctl], indent=1))

    # ---- B2: generator diagnostic (Batch 6: replaces the 95% gate)
    print("B2: generator diagnostic...", flush=True)
    total_drawn = stats_t.drawn + stats_p.drawn
    total_accepted = stats_t.accepted + stats_p.accepted
    fdt = stats_t.rejected["few_distinct_targets"] + stats_p.rejected["few_distinct_targets"]
    dt_pass_rate = 1 - fdt / total_drawn
    rej = {k: stats_t.rejected[k] + stats_p.rejected[k]
           for k in stats_t.rejected}
    rej_rates = {k: round(v / total_drawn, 4) for k, v in rej.items()}
    # verify every accepted task satisfies target-validity rules
    from dsl import evaluate
    bad = 0
    for t in tuning + posctl:
        ok48 = all(evaluate(t.g, x)[0] for x in t.train_anchors + t.verif_anchors)
        if not ok48 or len(set(t.train_targets)) < 4:
            bad += 1
    print(f"  draws={total_drawn} accepted={total_accepted} "
          f"distinct-target pass rate={dt_pass_rate:.4f} (observed, not a gate)")
    print(f"  rejections: {rej} rates: {rej_rates}")
    print(f"  accepted tasks failing validity: {bad}/{total_accepted}")
    results["checks"]["B2_generator_diagnostic"] = {
        "pass": bad == 0,  # gate is now: validity holds + quotas filled
        "draws": total_drawn, "accepted": total_accepted,
        "distinct_target_pass_rate_observed": round(dt_pass_rate, 4),
        "rejections": rej, "rejection_rates": rej_rates,
        "accepted_failing_validity": bad}

    # ---- B3: ENUM precompute + runner reproduction
    print("B3: ENUM precompute + reproduction...", flush=True)
    all_tasks = tuning + posctl
    pre = []
    t1 = time.time()
    for t in all_tasks:
        pre.append(precompute(t, max_rank=10000))
    print(f"  precompute done in {time.time()-t1:.1f}s", flush=True)
    (RUNS / "enum_precompute_tuning.json").write_text(json.dumps(
        [{"task_id": t.task_id, **p} for t, p in zip(all_tasks, pre)], indent=1))
    mism = 0
    t1 = time.time()
    for t, p in zip(all_tasks, pre):
        q = run_enum(t, 10000)
        if q["first_rank"] != p["first_rank"] or q["outcome"] != p["outcome"]:
            mism += 1
            print(f"  MISMATCH {t.task_id}: precompute {p} vs runner {q}")
    print(f"  runner reproduction: {len(all_tasks)-mism}/{len(all_tasks)} exact "
          f"({time.time()-t1:.0f}s)")
    # L* distribution sanity
    from collections import Counter
    ldist = Counter(t.L_star for t in all_tasks)
    print(f"  L* distribution: {dict(sorted(ldist.items()))}")
    results["checks"]["B3_enum_correctness"] = {
        "pass": mism == 0,
        "reproduced": f"{len(all_tasks)-mism}/{len(all_tasks)}",
        "L_star_distribution": {str(k): v for k, v in sorted(ldist.items())}}

    # ---- B4: mutation applicability rates
    print("B4: mutation applicability...", flush=True)
    rng = random.Random(3000)
    N = 2000
    rates = {}
    for mtype in MUTATION_TYPES:
        ok = 0
        for _ in range(N):
            L = rng.randint(1, 7)
            prog = tuple(rng.randrange(N_INSTANCES) for _ in range(L))
            if propose(prog, mtype, rng) is not None:
                ok += 1
        rates[mtype] = round(ok / N, 4)
    print(f"  applicability: {rates}")
    results["checks"]["B4_mutation_applicability"] = {
        "pass": all(v > 0.5 for v in rates.values()),
        "rates": rates, "note": "flag if any type rarely applicable"}

    results["elapsed_s"] = round(time.time() - t0, 1)
    (RUNS / "prelock_checks.json").write_text(json.dumps(results, indent=2))
    print(f"\nALL PRE-LOCK CHECKS DONE in {results['elapsed_s']:.0f}s")
    for k, v in results["checks"].items():
        print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'}")


if __name__ == "__main__":
    main()
