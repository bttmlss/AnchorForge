# AnchorForge — Briefing for Gemini

## What we're working on

**AnchorForge Phase 1** is a controlled experiment in symbolic program search.
The hypothesis: in an exact integer domain, conditioning *mutation choice* on
residual information — the scalar residual ε, plus along-lineage Δε and Δ²ε —
selects better transformations than unguided search at equal evaluation budget,
and the history terms add value beyond ε alone.

## How it works (one paragraph)

Programs are pipelines of integer operators (`add`, `mul`, `sq`, `neg`, `abs`,
`mod`, `fdiv`), length 1–7, evaluated exactly (no floats, no tolerance). Each
task has a hidden target program; the search sees only 8 training anchors and
halts at the first program matching them (verified later on 40 held-out
anchors: verified vs overfit). A (1+1) lineage walk proposes one mutation per
step, accepting on non-worsening ε. The guided arms choose mutation *type* from
frozen tables keyed on ε-bin (arm E), plus Δε-bin (H1), plus Δ²ε-bin (H2),
learned from uniform random walks on tuning tasks. Controls: uniform random (R),
learned marginals (M), scrambled history (HS), and exhaustive enumeration
(ENUM, a reference that can only reach length 3 at the budgets used). The
primary endpoint is verified-solve rate on 150 held-out tasks, with four
pre-registered Holm contrasts (P1: E−M, P2: H1−E, P3: H1−HS, P4: H2−H1).

## Where things stand (2026-10-14)

- **Spec:** Batch 6 draft, *not locked*. Explicit five-step freeze sequence
  (spec lock → implementation → code lock → confirmatory task lock → run).
  Pre-registered confirmatory seed: `3141592653`.
- **Implementation:** evaluator, task generator, vectorized minimal-length
  audit, ENUM precompute + independent runner, 6 mutation types, analysis
  functions — all built and unit-tested.
- **Pre-lock checks:** evaluator tests 2,055/2,055 pass; ENUM runner reproduces
  the precompute exactly on 60 tasks; all mutation types applicable. One
  finding: the task generator rejects ~21% of draws on the distinct-target
  filter (`mod` collapses outputs — a domain property), so that check was
  amended from a 95% gate to a documented diagnostic. DSL and sampling unchanged.
- **Not done:** no locks, no confirmatory task set generated, no arms run.
  Adrian is currently reviewing the amended spec before deciding on the
  specification lock.

## Useful context

- This is Phase 1a of a two-part program: (A) transferable guidance learned
  from recorded attempts, then (B) within-run learning. A pass here supports
  only "residual-conditioned guidance transfers to new tasks in this domain" —
  not broader discovery claims.
- Known limitation, stated pre-run: greedy acceptance forces Δε ≤ 0 on
  accepted lineages, so history signals mostly encode gain size/trend. A null
  on the history contrasts is weak evidence until the non-greedy follow-up
  (Phase 1b).
- Spec: `workspace/anchorforge/spec/ANCHORFORGE-PHASE1-SPEC.md`.
  Pre-lock report: `workspace/anchorforge/REPORT_PRELOCK.md`.
