"""Shared search skeleton. §5.1 of the spec. Identical for every arm.

(1+1) lineage walk. One parent, one proposed child per evaluation.
Acceptance: eps_child <= eps_parent (ties accepted).
Budget: N distinct canonical programs evaluated. Cache dedupes repeats.
Proposal cap: 10N ends a run that cannot find new candidates.
Restart: S=250 evals with no strict improvement -> fresh random program,
  length uniform {1..4}, history bins reset to none.
Invalid child: logged as invalid, eps carried from parent, NOT accepted.
Inapplicable proposal: logged, not evaluated, not budgeted, type redrawn.
A run halts at the first candidate with e==0 on training anchors; the
40 verification anchors (never shown to search) classify it verified/overfit.
"""
from __future__ import annotations

import random

import dsl
import mutations
import residuals
import records


S_RESTART = 250
N_INSTANCES = 39
MAX_LEN = 4


def random_program(rng: random.Random) -> tuple[int, ...]:
    L = rng.randint(1, MAX_LEN)
    return tuple(rng.randrange(N_INSTANCES) for _ in range(L))


def _evaluate(program, train_x, train_t):
    """Returns (valid, y, e, eps, eps_h). e is signed residual vector."""
    valid, y = dsl.evaluate_vector(program, train_x)
    if not valid or any(v is None for v in y):
        return False, None, None, None, None
    e = [a - b for a, b in zip(y, train_t)]
    return True, y, e, residuals.epsilon(e), residuals.epsilon_h(e)


def run(task: dict, arm: str, seed: int, N: int, propose_type,
        eps_binner, code_commit: str, record_path: str,
        edge_callback=None) -> dict:
    """Run one arm on one task.

    propose_type(ctx) -> mutation-type string, where ctx is a dict with
      eps_bin, d_eps_bin, d2_eps_bin (or None for R).
    task: dict with task_id, train_anchors (8), train_targets (8),
      verif_anchors (40), verif_targets (40).
    edge_callback(ctx, mtype, strictly_lower): called for each evaluated
      child (valid or invalid; not inapplicable/repeats). Used for training.
    Returns a summary dict.
    """
    rng = random.Random(seed)
    writer = records.RecordWriter(record_path)
    train_x, train_t = task["train_anchors"], task["train_targets"]
    verif_x, verif_t = task["verif_anchors"], task["verif_targets"]

    cache: set[str] = set()
    n_distinct = 0
    n_proposals = 0
    eval_index = 0
    lineage_eps: list[float] = []
    no_improve = 0
    result = {"task_id": task["task_id"], "arm": arm, "seed": seed,
              "solved": False, "verified": False, "overfit": False,
              "evals": 0, "restarts": 0, "cap_hit": False}

    def log_parent_row(program, valid, y, e, eps, eps_h, restart_flag,
                       outcome):
        nonlocal eval_index, n_distinct
        eval_index += 1
        pid = records.candidate_id(program)
        cache.add(pid)
        n_distinct += 1
        rec = records.make_record(
            task_id=task["task_id"], arm=arm, seed=seed,
            eval_index=eval_index, program=program, parent_id=None,
            mutation=None, y=y, e=e, eps=eps, eps_h=eps_h,
            d_eps_edge=None, d_eps_in_parent=None, d2_eps_in_parent=None,
            ctx_bins=None, accepted=True, outcome=outcome,
            restart_flag=restart_flag, code_commit=code_commit)
        writer.write(rec)
        return pid

    def check_solved(program) -> bool:
        """e==0 on training anchors -> verify on 40 held-out anchors."""
        valid, yv = dsl.evaluate_vector(program, verif_x)
        if not valid or any(v is None for v in yv):
            return False  # invalid on verification -> overfit
        return all(a == b for a, b in zip(yv, verif_t))

    # --- initialize parent (redraw until valid on training anchors) ---
    parent = random_program(rng)
    valid, y, e, eps, eps_h = _evaluate(parent, train_x, train_t)
    while not valid:
        parent = random_program(rng)
        valid, y, e, eps, eps_h = _evaluate(parent, train_x, train_t)
    parent_id = log_parent_row(parent, valid, y, e, eps, eps_h, False,
                               "pass" if all(v == 0 for v in e) else "fail")
    lineage_eps = [eps]
    if all(v == 0 for v in e):
        result.update(solved=True, verified=check_solved(parent),
                      evals=eval_index)
        result["overfit"] = not result["verified"]
        writer.close()
        return result

    # --- main walk ---
    while True:
        if n_distinct >= N:
            break  # budget exhausted -> unsolved
        if n_proposals >= 10 * N:
            result["cap_hit"] = True
            break

        # context from accepted lineage
        d_p, d_g = residuals.lineage_deltas(lineage_eps)
        if len(lineage_eps) >= 2:
            eps_g = lineage_eps[-2]
        else:
            eps_g = 0.0
        ctx = {
            "eps_bin": eps_binner.bin(eps),
            "d_eps_bin": residuals.delta_bin(d_p, eps_g),
            "d2_eps_bin": residuals.delta2_bin(d_p, d_g),
        }
        d_eps_in_parent, d2_eps_in_parent = d_p, (
            (d_p - d_g) if (d_p is not None and d_g is not None) else None)

        mtype = propose_type(ctx if arm != "R" else None)
        child, loc, par = mutations.propose_with_info(parent, mtype, rng)
        n_proposals += 1
        if child is None:
            # inapplicable: logged, not evaluated, not budgeted, redraw
            eval_index += 1
            rec = records.make_record(
                task_id=task["task_id"], arm=arm, seed=seed,
                eval_index=eval_index, program=parent, parent_id=parent_id,
                mutation={"type": mtype, "location": None, "param": None},
                y=None, e=None, eps=None, eps_h=None,
                d_eps_edge=None, d_eps_in_parent=None,
                d2_eps_in_parent=None, ctx_bins=None,
                accepted=False, outcome="inapplicable",
                restart_flag=False, code_commit=code_commit)
            writer.write(rec)
            continue

        cid = records.candidate_id(child)
        if cid in cache:
            continue  # dedupe: not evaluated, not logged, not budgeted

        # evaluate child
        c_valid, cy, ce, ceps, ceps_h = _evaluate(child, train_x, train_t)
        cache.add(cid)
        n_distinct += 1
        eval_index += 1

        if not c_valid:
            # invalid: logged, eps carried from parent, NOT accepted
            if edge_callback is not None:
                edge_callback(ctx, mtype, False)
            rec = records.make_record(
                task_id=task["task_id"], arm=arm, seed=seed,
                eval_index=eval_index, program=child, parent_id=parent_id,
                mutation={"type": mtype, "location": loc, "param": par},
                y=None, e=None, eps=eps, eps_h=eps_h,
                d_eps_edge=None, d_eps_in_parent=None,
                d2_eps_in_parent=None, ctx_bins=None,
                accepted=False, outcome="invalid",
                restart_flag=False, code_commit=code_commit)
            writer.write(rec)
            no_improve += 1
        else:
            c_outcome = "pass" if all(v == 0 for v in ce) else "fail"
            c_accepted = ceps <= eps
            d_edge = ceps - eps
            if edge_callback is not None:
                edge_callback(ctx, mtype, ceps < eps)
            rec = records.make_record(
                task_id=task["task_id"], arm=arm, seed=seed,
                eval_index=eval_index, program=child, parent_id=parent_id,
                mutation={"type": mtype, "location": loc, "param": par},
                y=cy, e=ce, eps=ceps, eps_h=ceps_h,
                d_eps_edge=(d_edge if c_accepted else None),
                d_eps_in_parent=(d_eps_in_parent if c_accepted else None),
                d2_eps_in_parent=(d2_eps_in_parent if c_accepted else None),
                ctx_bins=(ctx if c_accepted else None),
                accepted=c_accepted, outcome=c_outcome,
                restart_flag=False, code_commit=code_commit)
            writer.write(rec)
            if c_accepted:
                parent, parent_id = child, cid
                eps, eps_h = ceps, ceps_h
                lineage_eps.append(ceps)
                if ceps < lineage_eps[-2]:
                    no_improve = 0
                else:
                    no_improve += 1
            else:
                no_improve += 1

            if c_outcome == "pass":
                # halt at first training-anchor pass; verify on held-out
                result.update(solved=True, evals=eval_index)
                if check_solved(child):
                    result["verified"] = True
                else:
                    result["overfit"] = True
                writer.close()
                return result

        # restart check
        if no_improve >= S_RESTART:
            parent = random_program(rng)
            valid, y, e, eps, eps_h = _evaluate(parent, train_x, train_t)
            while not valid:
                parent = random_program(rng)
                valid, y, e, eps, eps_h = _evaluate(parent, train_x, train_t)
            # count if new
            pid = records.candidate_id(parent)
            if pid not in cache:
                parent_id = log_parent_row(parent, valid, y, e, eps, eps_h,
                                           True,
                                           "pass" if all(v == 0 for v in e)
                                           else "fail")
            else:
                # repeat of a cached program: still becomes parent, not logged
                # as a new eval, not budgeted
                parent_id = pid
            lineage_eps = [eps]
            no_improve = 0
            result["restarts"] += 1
            if all(v == 0 for v in e):
                result.update(solved=True, evals=eval_index)
                if check_solved(parent):
                    result["verified"] = True
                else:
                    result["overfit"] = True
                writer.close()
                return result

    result["evals"] = eval_index
    writer.close()
    return result
