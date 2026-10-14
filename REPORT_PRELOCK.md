# AnchorForge Phase 1 — Pre-Lock Report
*2026-10-14. Spec Batch 6 (B2 amendment + confirmatory seed). Implementation
artifacts built. Appendix B pre-lock checks run on tuning tasks.
**Nothing is locked.** No confirmatory tasks generated. No arms run.*

## 1. Spec amendments (Adrian-directed)

**Batch 5:** explicit five-step freeze sequence (§0), distinguishing specification
lock / code lock / confirmatory task lock. No design changes.

**Batch 6:**
1. Appendix B item 2: replaced the "≥95% pass the distinct-target filter" gate
   with a documented generator diagnostic (raw draws, accepts, per-reason
   rejection counts/rates, programmatic validity verification, generation time,
   quota fillability). Audit trail in the amendment log: old requirement,
   observed 79.3%, rationale (mod-collapse is a domain property; quotas filled
   in 52s/42s; changing threshold/sampling would be a redesign). DSL, sampling
   and the four-distinct-target requirement unchanged.
2. §6.1: pre-registered confirmatory generation seed **`3141592653`**
   (distinct from tuning seeds 1000/2000); frozen against post-lock changes.

## 2. Implementation artifacts

`src/` (all new, pre-lock working state):
- `dsl.py` — 39 operator instances, canonical rank/unrank, exact Python-int
  evaluation with §2.2 invalid rule. Cross-validated against the vectorized path.
- `tasks.py` — task generator with reason-coded rejection logging
  (`target_invalid`, `redundant_pair`, `few_distinct_targets`, `quota_full`).
- `audit.py` — vectorized L* audit (exhaustive to length 4, two-phase
  training-first check; ~1.4s per L*=4 task). Fixed one real bug during testing
  (sq results not written back due to numpy copy semantics).
- `enum_precompute.py` — vectorized ENUM outcome precompute to rank 10,000.
- `enum_runner.py` — independent simple-loop ENUM for the 0b reproduction gate.
- `mutations.py` — 6 mutation types with pinned proposal semantics (documented
  in the module docstring; frozen at code lock).
- `analysis.py` — paired bootstrap CIs, Holm, SESOI classification, precision
  check. Unit-tested on synthetic data.

`tests/test_0a_evaluator.py` — 2,055 assertions, all pass (Stage 0a).

## 3. Pre-lock checks (Appendix B)

| Check | Result |
|---|---|
| B1 evaluator unit tests | **PASS** — 2,055/2,055 |
| B2 generator diagnostic (Batch 6 rule) | **PASS** — 1,292 draws, 60 accepted; rejections: redundant_pair 46.4%, few_distinct_targets 20.7%, quota_full 14.2%, target_invalid 0%; 0/60 accepted tasks fail validity; quotas filled in 52s/42s |
| B3 ENUM correctness (runner reproduces precompute) | **PASS** — 60/60 exact |
| B4 mutation applicability | **PASS** — all types 0.83–1.00, none rarely applicable |

Tuning tasks: 40 generated (10 each L*=3,4,5 + 10 L*≤2), seed 1000, in 52s.
Positive control: 20 tasks (L*≤2), seed 2000, in 42s. Saved in `runs/`.

ENUM precompute on the 60 tasks (N=10,000): L*=1: 6/6 verified; L*=2: 23/24
verified; L*=3: 9/10 unsolved (14.2% length-3 coverage, as spec'd); L*=4,5:
mostly unsolved with a few overfits. Matches §6.7 expectations exactly.

## 4. Finding (resolved by Batch 6 amendment)

B2 originally required ≥95% of draws to pass the distinct-target filter; the
pre-lock run observed 79.3%. Investigation showed this is a **domain property,
not a bug**: `mod(m)` with small m collapses outputs (e.g. `[add(1), mod(2),
neg, add(2)]` yields only {1,2}), so random programs are frequently
near-constant. Per Adrian's decision (2026-10-14), the gate was replaced with
the diagnostic above; the 79.3% is recorded as an observed property. The
rejection only costs generation time (52s/42s for quotas).

## 5. Spec-vs-implementation review (Adrian's step 3, 2026-10-14)

Checked against the Batch 6 spec:
- §2.1 indices, rank/unrank: implemented, 2,055 unit tests pass.
- §2.2 exact evaluation (floor semantics, 1e12 invalid): implemented; vectorized path cross-validated against reference on random programs.
- §2.3 task generation (redundant pairs per Appendix A — verified all 11; anchors; filters; target validity): implemented; 0/60 accepted tasks fail validity.
- §6.1 quotas/seeds: tuning (40) and positive-control (20) generated per spec; confirmatory seed 3141592653 in spec, set not generated (correct per freeze order).
- §6.7 ENUM precompute: implemented; independent runner reproduces 60/60 exactly.
- §6.4 analysis (bootstrap, Holm, SESOI, precision): implemented, tested on synthetic data.
- §5.1 mutation types + Appendix B4: implemented; applicability 0.83–1.00.
- Correctly pending (need arms or later stages, not authorized pre-lock): §3 residual bins, §4 record schema, §5 walk/acceptance/budget/restart, §5.2–5.4 U/training/HS, §6.2 0b-replay/0b'/0c/0d/1/2, §6.3 arms.

## 6. Not done (explicitly out of scope)

- Spec lock, code lock, confirmatory task lock: **none performed**.
- Confirmatory task set (150): **not generated** (freeze step 4, after code lock).
- Confirmatory seed: **not pre-registered** — needs a value in the spec at lock.
- Stage 0c/0d/1/2 (arms on tuning tasks): **not run** (spec §6.2: no arm runs before spec lock).
- The git repo has one working commit (hash below) as a save point, **not labeled as a lock**.

Working commit: see `git log` in `~/workspace/anchorforge/`.

## 6. Files

- `spec/ANCHORFORGE-PHASE1-SPEC.md` — Batch 5 working spec (DRAFT)
- `src/` — evaluator, generator, audit, ENUM precompute/runner, mutations, analysis
- `tests/test_0a_evaluator.py` — Stage 0a unit tests
- `runs/` — tuning_tasks.json, positive_control_tasks.json, enum_precompute_tuning.json, prelock_checks.json, run_prelock_checks.py
- `REPORT_PRELOCK.md` — this file
