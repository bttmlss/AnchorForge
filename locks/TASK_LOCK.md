# Confirmatory Task Lock — AnchorForge Phase 1

**Date:** 2026-10-14
**Freeze step:** 4 (after spec lock `a3678f9`, code lock `27ee20b`)
**Generation seed (preregistered):** `3141592653`
**Generated:** once, 2026-10-14. The seed must not change merely because the
resulting tasks look inconvenient (spec §6.1).

## Artifacts

| File | SHA-256 |
|---|---|
| `runs/confirmatory_tasks.json` (150 tasks) | `afb29e1b6803b26e638569e02ec3950e56ddbdadd70334a8c2fde08bc54c35de` |
| `runs/enum_precompute_confirmatory.json` (150 precomputes) | `d7d40ae99f00c3162395990909cb9b63f7c72763bdb770fe12ca4cbf212c8331` |

## Task set

- 150 held-out tasks: 50 each of L* = 3, 4, 5.
- Each task: 8 training anchors + 40 verification anchors, L* audit,
  target-validity verified at generation.
- ENUM precompute (rank ≤ 10,000): 12 verified, 4 overfit, 134 unsolved
  at N=10,000. Outcomes at the calibrated N=5,000 are read off by rank.

## What this lock does NOT cover

- Experimental results. No arms have run on these tasks.
- The Stage 2 confirmatory run (freeze step 5) — not yet executed.

## Amendment policy

Regenerating this set under a new seed requires a dated amendment with the
discarded set disclosed, per spec §6.1.
