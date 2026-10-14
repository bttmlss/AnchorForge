# Code Lock Record — AnchorForge Phase 1

**Date:** 2026-10-14
**Lock commit:** `27ee20b5c4b27add45f4f9210538b0543947ee4b`
**Tag:** `code-lock`
**Spec lock:** `a3678f9` (tag `spec-lock`) — protocol and seed `3141592653`
remain frozen under `locks/SPEC_LOCK.md`.

## What this lock covers

The complete implementation and analysis scripts as audited in
`AUDIT_CODELOCK.md`:

| Module | SHA-256 |
|---|---|
| `src/analysis.py` | `a856bb4dcef419aa5148a8c43881a5267887ffafb693b4b523785da8a138b430` |
| `src/arms.py` | `3e229a5d21122314a22d3cbd1d3683b1ce3365b381da6ef86c68b2ad082bbd43` |
| `src/audit.py` | `757c3aec69679da1e6a155226499e5bdcfd8f23bcef9983e8f9bfccee02c3231` |
| `src/dsl.py` | `3dfcce6f3674e3c436cfda335ee5620b2c2da06c7e56d51ccd1cd706a44c9da5` |
| `src/enum_precompute.py` | `b35ecf710054079b2adbb5140261d249d1edb6aa36849038de4b3cd2d5684de3` |
| `src/enum_runner.py` | `b18714c43a20bec3c1bf141806205066bb6c91ee20a4f91679cf27449995c7b6` |
| `src/mutations.py` | `2f8405baa8db1b4b2ea393a6eafcd8f3597363a39dec8419aaecb54f20cde3af` |
| `src/records.py` | `8310b77fad92ca6db1122173380a6958bca64a8327778dcf3756f7cb7cdcbc49` |
| `src/residuals.py` | `f9ce2586795f54cee6e4f4f41461405ede602a815724695e704755d20c6fa7d9` |
| `src/search.py` | `a68f806b96ad6966e19d9ed2d4716a3d042be5eaa3ed94f35a5a1074b537a609` |
| `src/stages.py` | `33b21b2275e204dd559d8fcdce76726fb6b6e031636db1bc9915886b8a936993` |
| `src/tables.py` | `692f9be2be0906abc69f11e8c29017ee435fd2ad9d5e701d66545f909050fd2a` |
| `src/tasks.py` | `703c889144f9335df557e5b4f5ceae09a198cf0c702776b9439916ea454155f1` |
| `tests/test_0a_evaluator.py` | `d354fda328e52d88ac4f3ecced79681c3d9ffe2506316df6707df4ddb5933dcf` |
| `tests/test_1a_new_modules.py` | `2d378e8b6f636d558d414d3e3a3d269b775337c9c2e5733e4d8ae94e86fef361` |
| `runs/run_prelock_checks.py` | `2c5b2887c1dc14bca8cbf93f645686df8e0ade4b34722328de80286107e75db3` |

## What this lock does NOT cover

- The confirmatory task set (150 tasks) — not yet generated.
- The confirmatory task lock (freeze step 4) — not yet created.
- Any experimental result. No arms have run; no confirmatory outcomes exist.
- The tuning/positive-control task JSONs under `runs/` (data, not code).

## Audit basis

`AUDIT_CODELOCK.md`: independent spec-to-implementation review against the
locked Batch 6 spec. Three bugs found and fixed before this lock
(salted-hash seeds, record location/param, random-walk fidelity). ENUM arm
reproduces the §6.7 precompute exactly; seeds reproduce byte-identical
records. No confirmatory tasks generated; no arms run; no peeking.

## Amendment policy

Any change to the locked code after this commit requires a dated amendment
disclosed alongside results, per the spec. The locked protocol itself can
only change via the spec amendment policy (never silent edits).
