# AnchorForge

Residual-conditioned mutation guidance for symbolic program search.

**Phase 1a hypothesis:** in an exact integer domain, conditioning mutation
choice on residual information (ε, Δε, Δ²ε) selects better transformations
than unguided search at equal evaluation budget, and the history terms add
value beyond ε alone — with the guidance learned on tuning tasks transferring
to held-out tasks.

## Status (2026-10-14)

- **Specification: LOCKED** (`spec/ANCHORFORGE-PHASE1-SPEC.md`, Batch 6).
  Lock record: `locks/SPEC_LOCK.md`. Pre-registered confirmatory seed: `3141592653`.
- Implementation built; pre-lock checks pass (`REPORT_PRELOCK.md`).
- **No results yet.** No confirmatory tasks generated, no arms run.

## Layout

| Path | Contents |
|---|---|
| `spec/` | Locked Phase 1 specification (Batch 6) |
| `src/` | Evaluator, task generator, L* audit, ENUM precompute/runner, mutations, analysis |
| `tests/` | Evaluator unit tests (Stage 0a) |
| `runs/` | Tuning tasks, ENUM precompute, pre-lock check outputs + runner |
| `locks/` | Specification lock record |
| `REPORT_PRELOCK.md` | Pre-lock check report |
| `GEMINI_BRIEFING.md` | One-page project briefing |

## Reproduce the pre-lock checks

```bash
cd runs && python3 run_prelock_checks.py
```

Requires Python 3.10+ and numpy. The L* audit is the slow step (~1–2 min for
the tuning set on a laptop).

## Audit trail

The authoritative lock history (spec-lock tag, verified hashes) is recorded in
`locks/SPEC_LOCK.md`. Any protocol change after the specification lock follows
the amendment policy in the spec: dated amendments, nothing edited in place.
