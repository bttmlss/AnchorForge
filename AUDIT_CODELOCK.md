# Independent specification-to-implementation audit
## AnchorForge Phase 1 — pre-code-lock

**Date:** 2026-10-14
**Spec:** `spec/ANCHORFORGE-PHASE1-SPEC.md` (Batch 6, locked 2026-10-14,
commit `a3678f9`, tag `spec-lock`)
**Scope:** All implementation built after the spec lock (`src/residuals.py`,
`src/records.py`, `src/search.py`, `src/tables.py`, `src/arms.py`,
`src/stages.py`, additions to `src/mutations.py` and `src/analysis.py`).
**Method:** Line-by-line code review against the locked spec, plus targeted
runtime checks. **No confirmatory tasks generated. No arms run.** All runtime
checks used tuning tasks only, with tiny budgets, for implementation
verification — not for estimating any experimental outcome.

---

## Bugs found and fixed

1. **Non-deterministic seeds (CRITICAL).** `stages.run_seed()` and
   `tables.train()` used Python's built-in `hash()`, which is salted per
   process (`PYTHONHASHSEED`). Seeds would not reproduce across runs,
   violating Stage 0b(iii) (replay from seed). Fixed: both now use
   SHA-256 of a documented string (`task_id|arm|rep`, `train|task_id|rep`).
   Verified: identical seeds produce byte-identical JSONL records.

2. **Record schema incomplete.** `mutation{type, location, param}` (§4)
   was logged with null location/param. Added `mutations.propose_with_info()`
   (backward-compatible; existing `propose()` untouched, pre-lock B4 unaffected).
   Verified: `propose_with_info` returns byte-identical children to `propose`
   on 1,000 randomized trials.

3. **"Random walks" vs independent sampling.** `fit_eps_binner()` and
   `collect_steerability()` sampled independent random programs; the spec
   says "random walks". Both now do actual walks (random program → up to 5
   uniform random mutation steps, collecting at each step).

## Verified correct

- **§3 residuals.** ε = mean log2(1+|e|) (0 iff e=0 ✓); ε_H = fraction
  nonzero ✓; Δε_in/Δ²ε_in read along the *accepted* lineage ✓; Δε bins
  (none/flat/small/large, 0.25·ε(g) threshold) ✓; Δ²ε bins (none/accel/decel/
  steady, 1.25×/0.75×) ✓; ε-bin fitter (4 quantiles) ✓.
- **§4 records.** All 21 schema fields present in every row ✓; `y_sel`
  indexing matches §1 (1-indexed diagonal) ✓; `d_eps_edge` and `ctx_bins`
  only on accepted rows, per spec ✓; inapplicable rows carry null
  evaluation fields ✓.
- **§5.1 skeleton.** (1+1) walk ✓; acceptance ε_child ≤ ε_parent with ties
  accepted ✓; inapplicable logged / not evaluated / not budgeted / type
  redrawn ✓; budget = N distinct canonical programs, cache dedupes ✓;
  10N proposal cap ends run as unsolved+flagged ✓; restart after 250 evals
  with no strict improvement → fresh random program (len 1–4), lineage
  reset (bins → none) ✓; invalid child logged with ε carried from parent,
  **not** accepted ✓.
- **§5.2 U.** Laplace p̂=(s+1)/(n+2) ✓; mixture 0.95·p̂/Σp̂ + 0.05/6 keeps
  every type alive (verified: unseen context samples ~uniform) ✓; per-arm
  contexts (M marginal, E ε-bin, H1 ε×Δε, H2 ε×Δε×Δ²ε) ✓.
- **§5.3 training.** 20 seeds/task, uniform-random types, shared skeleton;
  tables frozen after build; no test-time updates (no code path exists) ✓.
- **§5.4 HS.** Scrambled Δε-bin drawn from training-set marginal in *both*
  training (two-pass, seeded) and test (per-run RNG, independent of
  lineage) ✓.
- **§5.5 stopping.** All five rows implemented; verified halts at first
  training-anchor pass and classifies on the 40 held-out anchors
  (invalid-on-verification → overfit) ✓.
- **§6.3 arms.** All seven (R, M, E, H1, H2, HS, ENUM) run through the
  same skeleton/entry point with equal budget N ✓.
- **§6.7 / 0b(ii).** ENUM arm reproduces the precomputed outcome *and*
  first-training-match rank exactly on 5/5 sampled tuning tasks ✓.
- **0b(iii) replay.** Same seed → byte-identical records ✓.
- **§6.4 analysis.** Paired bootstrap CI, Holm, SESOI classification,
  precision check present; added §6.6 summary diagnostics (rates,
  per-L*, ENUM-hard sensitivity) ✓.
- **§7 / 0c.** S1 (spread ≥ 0.03 + 1,000 label-shuffles within bin,
  p ≤ 0.0125 Bonferroni) and S2 (op×bin interaction via within-type
  bin-label permutation, p ≤ 0.01) implemented as specified ✓.
- **0d.** Smallest N in {1000, 2000, 5000, 10000} with R verified-rate in
  [0.15, 0.50] ✓.

## Notes (not bugs)

- **Initial/restart parent redraw.** If a random initial or restart program
  is invalid on training anchors, it is redrawn (deterministic in the run
  RNG). The spec does not dictate this; it is the only coherent choice
  (an invalid parent has no ε to walk from). Documented here.
- **Repeat restart parent.** If a restart draws a program already in the
  cache, it becomes the parent without consuming budget or logging a row
  (it was already evaluated). Correct per the dedupe rule.
- **High repeat/inapplicable rates on short parents.** Observed 60% repeats
  + 34% inapplicable on a length-1 parent in a smoke test. This is the
  specified behavior (dedupe + redraw + 10N cap), not a defect — short
  programs have small neighborhoods.
- **S2 operationalization.** The spec names a logistic-model interaction;
  the implementation uses a permutation test on the type×bin interaction
  statistic (bin labels shuffled within type). This is a valid calibration
  of the same null ("type effectiveness does not depend on ε"); the exact
  model form is an analysis choice, not a protocol deviation.
- **0d "adjust once".** Implemented as: first N in the pre-registered list
  whose rate lands in [0.15, 0.50]. If none lands, the closest is reported
  with a flag for manual review (the "adjust once" is then a human step,
  not a silent code path).

## What was NOT done (per the audit boundary)

- No confirmatory tasks generated (seed `3141592653` untouched).
- No arm runs beyond tiny-budget smoke tests on tuning tasks.
- No Stage 0c/0d/1/2 execution. The code paths exist and are unit-tested;
  running them is post-code-lock work.
- No peeking at confirmatory outcomes (there are none).

## Recommendation

The implementation matches the locked specification. The three bugs found
were fixed and re-verified. The code is ready for the **code lock** commit
(spec freeze step 3) pending Adrian's approval. After the lock: Stage 0c/0d
on tuning tasks → Stage 1 training → confirmatory generation (seed
`3141592653`) → task lock → Stage 2.
