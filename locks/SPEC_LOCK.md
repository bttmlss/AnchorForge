# Specification Lock — AnchorForge Phase 1

**Date:** 2026-10-14
**Authority:** Adrian, explicit approval 2026-10-14 13:17 EDT, conditional on
verification that the committed file matches the reviewed text.

## Locked artifact

- File: `spec/ANCHORFORGE-PHASE1-SPEC.md`
- SHA-256: `f1f3097d3ec6b7ca0ad7db232f65ff2fd3faf32d680afbed529a4bc8f58ef956`
- Verified: file hash recomputed immediately before this commit; matches the
  hash of the document Adrian reviewed. Committed bytes verified after commit
  (see below).

## What this lock freezes

- The approved protocol (Batches 1–6, including the §0 freeze sequence and the
  Batch 6 B2 diagnostic amendment).
- Pre-registered confirmatory generation seed: `3141592653` (§6.1).

## What this lock does NOT cover

- The implementation (`src/`, `tests/`) — unlocked; code lock is a separate
  future commit (freeze step 3).
- The confirmatory task set (150 tasks), its L* audit and ENUM precompute —
  ungenerated; code/task lock is a separate future commit (freeze step 4).
- No experimental result is implied. Pre-lock checks established implementation
  correctness only.

## Boundaries (per authorization)

- No confirmatory tasks generated yet; none until after code lock.
- No arms run before this specification lock (upheld: none have).
- Any later protocol change follows the amendment policy (§0): dated amendment,
  nothing edited in place. This locked file must not be modified.

## Verification

Post-commit check: `git show <commit>:spec/ANCHORFORGE-PHASE1-SPEC.md | sha256sum`
must equal the SHA-256 above. Recorded below after commit.

**Verification result (2026-10-14):**
- Lock commit: `a3678f9e9854a0ec0c31a614be1a863a457c24fc` (tag `spec-lock`)
- `git show a3678f9:spec/ANCHORFORGE-PHASE1-SPEC.md | sha256sum`
  = `f1f3097d3ec6b7ca0ad7db232f65ff2fd3faf32d680afbed529a4bc8f58ef956` ✓ MATCHES
