# ANCHORFORGE-PHASE1-SPEC.md
## AnchorForge — Phase 1 Spec (DRAFT, not locked)

**Status:** Draft for cross-agent review. Nothing has been run. Batch 5 (2026-10-14) adds the explicit freeze sequence; still not locked.
**Companion:** Discovery.md (concept brief)
**Lock rule:** Two distinct locks, in the freeze order below. The spec locks by commit hash before any arm runs. Stage 0 uses tuning tasks only. Changes after a lock go in dated amendments; nothing is edited in place.

### Freeze sequence

1. **Specification lock.** The spec document is frozen by commit hash, and the task-generation seed and generation rules (§2.3, §6.1) are pre-registered in it. No arm runs before this point. Tuning tasks may be generated and used for Stage 0 at any time; they are not part of either lock.
2. **Implementation.** The generator, evaluator, audit, ENUM precompute and analysis scripts are implemented and exercised on tuning tasks only (Appendix B).
3. **Code lock.** The code and analysis scripts are frozen by commit hash. After this point no code changes without an amendment.
4. **Confirmatory task lock.** The confirmatory task set (150 tasks), its \(L^*\) audit table and its ENUM precompute are generated exactly once from the pre-registered seed, using the frozen code. Their hashes are recorded in a second lock commit (the code/task lock). They are deterministic functions of the seed and the frozen code, so generating them is not tuning. If any quota, filter, ordering or N changes after this, the set is regenerated under a new pre-registered seed and the discarded set is disclosed.
5. **Confirmatory run.** Arms run on the locked confirmatory set with the locked code. No spec or code changes during the run. Any required correction is disclosed and handled by the amendment/re-run policy (§6.2 0b).

---

## 0. Hypothesis and scope

**Hypothesis.** In an exact symbolic domain, conditioning mutation choice on residual information (ε, and along-lineage Δε and Δ²ε) selects better transformations than unguided search at equal evaluation budget, and the history terms add value beyond ε alone.

**Phase 1a tests:** whether residual-conditioned operator-outcome statistics, learned from recorded attempts on tuning tasks, transfer to held-out tasks. That table is the stored history \(\mathcal{M}\) of the brief, frozen before testing.

**Phase 1a does not test:** within-run learning, gradient methods, lexicon growth, LLM-proposed mutations, float or geometric domains, or any novelty claim. Novelty is not claimed until the formulation is compared against program synthesis, symbolic regression and adaptive control.

**What a pass lets us say.** Phase 1a is the first gate of a two-part program: (A) transferable guidance learned from recorded attempts, and (B) learning transformation structure itself (within-run adaptation, lexicon, learned proposals). A Phase 1a pass supports exactly this sentence: *residual-conditioned mutation guidance learned on some tasks transfers to new tasks in this symbolic domain.* It does not support "AnchorForge discovers new transformation principles." The next gate for (B) is Phase 2a (§9).

**Open decisions flagged for reviewers:** (1) the scalar ε in §3; (2) the budget N in Stage 0d; (3) the six mutation types in §5.1; (4) the coarse bins for Δε and Δ²ε in §3; (5) greedy acceptance, whose limitation is stated in §8; (6) the minimal-length audit in §2.3 and the ENUM interpretation in §6.7.

---

## 1. Notation

The historical line stays as the project's origin and as the log schema:

\[
\boxed{(f_i(x))_i = x_i}
\]

Working notation, with distinct letters so nothing is identity-by-definition:

| Symbol | Meaning |
|---|---|
| \(X=\{x^{(1)},\dots,x^{(k)}\}\) | Anchor set. Fixed for the whole run, never altered by search. |
| \(f_i\) | Candidate program at evaluation \(i\) (§2.1). |
| \(y_i=f_i(X)\in\mathbb{Z}^k\) | Full output vector, \(y_i[j]=f_i(x^{(j)})\). |
| \(x_i\) (historical) | Recorded output state, defined as \(y_i\) (the full vector). |
| \(y^{sel}_i\) | The historical diagonal pick, \(y_i[((i-1)\bmod k)+1]\). Logged only, never used for scoring, because scoring it would discard \(k-1\) of \(k\) components. |
| \(t\in\mathbb{Z}^k\) | Independent target, \(t_j=g(x^{(j)})\) for a hidden program \(g\) the search never sees. |
| \(e_i=t-y_i\) | Signed residual vector. |
| \(\epsilon_i\) | Scalar residual (§3). |

**Working form of the historical line.** Success is \(y_i=t\), equivalently \(e_i=0\). The target comes from outside the search, so success is a real check.

---

## 2. Domain

### 2.1 Representation
A program is an ordered pipeline of operator instances, length 1 to 7, applied left to right to an integer. Canonical form is the tuple of `(op, param)` pairs, and its hash is the candidate id.

| Op | Params | Instances |
|---|---|---|
| `add(c)` | c in {-9..-1, 1..9} | 18 |
| `mul(c)` | c in {-4,-3,-2,2,3,4} | 6 |
| `sq` | none | 1 |
| `neg` | none | 1 |
| `abs` | none | 1 |
| `mod(m)` | m in {2..9} | 8 |
| `fdiv(d)` | d in {2..5} (floor division) | 4 |

That is 39 operator instances. Length-5 programs number about 9e7, so enumeration within the budget reaches only length 2 and part of length 3.

**Instance index and canonical rank.** Operator instances are indexed 0–38 in this order: `add(-9..-1)` = 0–8, `add(1..9)` = 9–17, `mul(-4,-3,-2,2,3,4)` = 18–23, `sq` = 24, `neg` = 25, `abs` = 26, `mod(2..9)` = 27–34, `fdiv(2..5)` = 35–38. A program of length \(L\) is the tuple \((a_1,\dots,a_L)\) of instance indices. Programs are ordered by length, then by tuple compared lexicographically from the left. The 0-based **rank** is

\[
\text{rank}(a_1,\dots,a_L)=\sum_{l=1}^{L-1}39^{\,l}+\sum_{j=1}^{L}a_j\,39^{\,L-j}
\]

so length 1 occupies ranks 0–38, length 2 ranks 39–1,559, length 3 ranks 1,560–60,878, and length 4 begins at rank 60,879.

### 2.2 Exact evaluation
Python integers only, with floor semantics. Any intermediate value above 1e12 in magnitude makes the candidate **invalid**. Equality is exact. There is no tolerance anywhere in Phase 1a, which settles Q8 of the brief for this domain.

### 2.3 Tasks
- Hidden program \(g\) of nominal length \(d\in\{3,4,5\}\), operators sampled uniformly, rejecting any program containing a redundant adjacent pair (Appendix A). That filter is only a cheap prefilter and is known to be incomplete: `mul(c)→fdiv(c)` is the identity, `sq→mod(2)` equals `mod(2)`, and non-adjacent equivalences exist. Nominal length is therefore not the same as difficulty.
- **Minimal functional length \(L^*\).** Before lock, compute \(L^*\) exactly for every task: the length of the shortest DSL program that matches \(g\) on the task's 48 evaluation anchors (8 training + 40 verification), searching exhaustively up to length 4 (about 2.4M programs, tractable with chunked vectorized evaluation). \(L^*=5\) means no program of length ≤ 4 matches on all 48 anchors. **\(L^*\) is an audited fact about those 48 sampled anchors, not a claim of global functional equivalence over all integers.** It is also not what ENUM will do: the search halts at the first program matching the 8 *training* anchors, which can be an overfit that precedes any verified equivalent. ENUM's actual outcome is precomputed separately (§6.7). Tasks are stratified and labeled by \(L^*\), not by nominal length. Generation continues until each stratum \(L^*\in\{3,4,5\}\) reaches its quota; tasks with \(L^*\le2\) go to the positive-control pool. Also record \(n_{eq}(g)\), the number of length-\(L^*\) programs matching \(g\) on those anchors (exact for \(L^*\le4\); for \(L^*=5\) only the lower bound 1 is known, which is enough because ENUM cannot reach that length).
- \(k=8\) training anchors, distinct integers in [-20, 20]. Reject tasks whose 8 targets have fewer than 4 distinct values, which removes near-constant functions.
- Verification set: 40 distinct anchors in [-40, 40], excluding the training anchors. Used only for the final solved/overfit classification, never shown to the search.
- **Target validity.** Reject a task if \(g\) is invalid under §2.2 on any of its 48 anchors (8 training + 40 verification), so every target vector is well-defined under the evaluator's own rules. Invalid candidates stay part of the search; only the target is required to be valid. Every rejected draw is logged with a reason code (`target_invalid`, `redundant_pair`, `few_distinct_targets`, `quota_full`), and rejection counts by reason are reported.
- A run **halts at the first candidate with \(e=0\) on the training anchors.** If it also matches all 40 verification anchors it is **verified**; otherwise it is **overfit**. The run does not continue after an overfit, so verification leaks nothing to the search.

---

## 3. Residual signals

**Primary scalar:**
\[
\epsilon = \frac{1}{k}\sum_{j=1}^{k}\log_2\!\big(1+|e_j|\big)
\]
Chosen because it is zero exactly when \(e=0\), is monotone in each \(|e_j|\), and does not let one huge component swamp the rest. **Secondary:** \(\epsilon_H\) = fraction of anchors with \(e_j\neq0\). \(\epsilon_H\) is used only in one pre-declared sensitivity re-analysis. Both are logged for every evaluation. The signed vector \(e\) is logged but not used by U in Phase 1a (see §8).

**Lineage, not iteration order.** Every evaluation creates an edge from a parent to a child. Accepted edges form the lineage. History signals are read along the accepted lineage only. For current parent \(p\) with accepted parent \(g\) and grandparent \(gg\):

\[
\Delta\epsilon_{in}(p)=\epsilon(p)-\epsilon(g),\qquad
\Delta^2\epsilon_{in}(p)=\Delta\epsilon_{in}(p)-\Delta\epsilon_{in}(g)
\]

Differencing consecutive iterations is never used, since those can be unrelated programs.

**Bins (frozen after Stage 0d; cut points tuned once on tuning data):**

| Feature | Bins |
|---|---|
| ε-bin | 4 quantile bins of parent ε, cut points from tuning-set random walks |
| Δε-bin | none (root or restart); flat (\(\Delta\epsilon_{in}=0\)); small (0 < \(\|\Delta\epsilon_{in}\|\) < 0.25 ε(g)); large (≥ 0.25 ε(g)) |
| Δ²ε-bin | none; accel (\(\|\Delta\epsilon_{in}(p)\|\) > 1.25 \(\|\Delta\epsilon_{in}(g)\|\)); decel (< 0.75×); steady (otherwise, including both zero) |

---

## 4. Record schema

One JSONL row per evaluation, never dropped, failures included:

`task_id, arm, seed, eval_index, candidate_id, program, parent_id, mutation{type, location, param}, y (full vector), y_sel, e (signed vector), eps, eps_H, d_eps_edge, d_eps_in_parent, d2_eps_in_parent, ctx_bins, accepted, outcome {pass | fail | invalid | inapplicable}, restart_flag, code_commit`

The full run is reproducible from the seed, the task file and the commit hash.

---

## 5. Search skeleton and the update rule U

### 5.1 Shared skeleton (identical for every arm)
- **Walk:** (1+1) lineage walk. One parent, one proposed child per evaluation.
- **Acceptance:** accept the child if \(\epsilon_{child}\le\epsilon_{parent}\) (ties accepted, so neutral drift is allowed).
- **Mutation types (6):** `REPLACE_OP`, `NUDGE_PARAM` (±1), `RESAMPLE_PARAM`, `INSERT`, `DELETE`, `SWAP_ADJACENT`. Location and parameter are uniform given the type.
- **Inapplicable proposals** (e.g. `DELETE` on a length-1 program) are logged as `inapplicable`, not evaluated, not budgeted, not counted in table statistics. The type is redrawn.
- **Budget:** N distinct canonical programs evaluated per run. A cache dedupes repeats, and a proposal cap of 10N ends a run that cannot find new candidates.
- **Restart:** after S = 250 evaluations with no strict improvement of the parent's ε, restart from a fresh random program of length uniform in {1..4}. History bins reset to `none`.

### 5.2 U in Phase 1a
\[
f_{i+1}=U\big(f_i,\epsilon_i,\Delta\epsilon_i,\Delta^2\epsilon_i,\mathcal{M}\big)
\]
**Consumes:** the current parent, its ε-bin, and (per arm) its Δε-bin and Δ²ε-bin, looked up in the frozen table \(\mathcal{M}\).
**Produces:** a mutation type \(m\sim P(m\mid ctx)\), then uniform location and parameter.
**Table:** \(\hat p(m\mid ctx)=(s+1)/(n+2)\), where \(s\) counts edges with strictly lower child ε and \(n\) counts all edges for that type and context. Sampling uses \(P(m\mid ctx)=0.95\cdot\hat p/\sum\hat p+0.05/6\), so every type stays alive.

### 5.3 Training
Tables are built on tuning tasks from **uniform-random-type** walks (20 seeds per task) under the shared skeleton, then frozen. Training cost is reported next to results. No table updates occur at test time.

### 5.4 Scrambled-history control (HS)
Same context cardinality as H1 (ε-bin × Δε-bin). The Δε-bin is replaced by a draw from its training-set marginal, independent of the actual lineage, **in both training and test**. This separates "history carries information" from "a larger context helped."

### 5.5 Stopping and failure

| Event | Handling |
|---|---|
| No strict improvement for S evaluations | Restart (§5.1). |
| Budget N exhausted | Run ends **unsolved**. |
| Invalid candidate | Logged as `invalid`, ε carried from the parent, never scored as ∞. |
| Proposal cap reached | Run ends unsolved, flagged. |
| Training-anchor pass, verification fail | **Overfit**, run halts. |
| Oscillation | Cannot occur under greedy acceptance. See §8. |

---

## 6. Experiment

### 6.1 Splits
- **Tuning:** 40 tasks (10 each of \(L^*=3,4,5\), plus 10 with \(L^*\le2\)). Used for Stage 0, bins, budget calibration and table training.
- **Confirmatory:** 150 held-out tasks (50 each of \(L^*=3,4,5\)). No arm runs on it before lock. The task set, its \(L^*\) audit and its ENUM precompute are generated once from a pre-registered seed after code freeze (freeze step 4), and hashed into the code/task lock commit. **Pre-registered confirmatory generation seed: `3141592653`** (distinct from the tuning seeds 1000 and 2000). Once the spec is locked, this seed must not change merely because the resulting tasks look inconvenient. They are deterministic functions of the task and the frozen code, so computing them is not tuning. Changing any quota, filter, order or N after seeing them requires an amendment and a regenerated task set under a new seed, with the discarded set disclosed.
- **Positive control:** 20 held-out tasks with \(L^*\le2\), including generated tasks the audit showed to have a shorter equivalent.
- **Seeds:** 20 per task per arm.

### 6.2 Staging
- **0a. Evaluator unit tests.** Hand-built programs recover known targets, every op is checked on edge values, and invalid detection is exercised.
- **0a′. Minimal-length audit (§2.3).** Compute \(L^*\) and \(n_{eq}\) for every task, and precompute ENUM's outcome and first-training-match rank on every task: tuning, positive-control and confirmatory (§6.1, §6.7).
- **0b. Implementation correctness (hard gate).** (i) The 0a unit tests pass. (ii) The ENUM arm's actual runs reproduce the precomputed outcome and first-training-match rank exactly on every task on which ENUM runs: tuning, positive-control and confirmatory. For confirmatory tasks this is checked when the ENUM arm runs, after spec and code are frozen. It is a deterministic implementation check, not an opportunity to tune anything against those tasks. A mismatch stops the run and is handled by amendment: the confirmatory run is invalid for every arm that shares the faulty component, so it is fixed, disclosed and re-run. (iii) Replay: every run logged as verified is re-verified on all 48 anchors by an independent evaluator, and every run reproduces from its seed. Any failure stops everything.
- **0b′. Positive-control performance (reported, not a bug trigger).** On \(L^*\le2\) tasks, report two separate measurements for R and ENUM. **Run-level outcomes** (mutually exclusive and exhaustive): verified, overfit, unsolved (a run ended by the proposal cap counts as unsolved and is also reported separately). **Candidate-level diagnostics:** the fraction of evaluated candidates that are invalid, the proposal-cap rate, and the inapplicable-proposal rate. ENUM's expected result is its precomputed one, already checked in 0b. No pre-registered task construction guarantees a particular control rate, and an overfit can legitimately halt a run on a task that has a short equivalent, so no rate threshold is treated as a bug. A control rate for R below 0.5 is flagged for review before Stage 0c, not auto-stopped, and the review explains the shortfall by splitting the non-verified runs into overfit (the 8 anchors under-determined the task) and unsolved (budget too small for the skeleton, which feeds the N calibration in 0d), with the candidate-level diagnostics as context. Invalid candidates are never a terminal run outcome (§5.5).
- **0c. Steerability (§7).**
- **0d. Budget calibration.** Pick the smallest N in {1000, 2000, 5000, 10000} that puts arm R's verified-solve rate on \(L^*\) 3–5 tuning tasks inside [0.15, 0.50]. Adjust once, then freeze. Report ENUM's coverage at that N (§6.7). ENUM's outcomes on tuning tasks must reproduce the precomputed ones exactly; any mismatch is a bug in the audit or the evaluator. A hit by ENUM is not by itself evidence that the DSL is too small.
- **1. Training** of the tables (§5.3).
- **2. Confirmatory run** on held-out tasks.

### 6.3 Arms (equal evaluation budget N per run)

| Arm | Context used by U | Trained |
|---|---|---|
| R | none, uniform mutation type | no |
| M | none, learned marginal over types | yes |
| E | ε-bin | yes |
| H1 | ε-bin × Δε-bin | yes |
| H2 | ε-bin × Δε-bin × Δ²ε-bin | yes |
| HS | ε-bin × scrambled Δε-bin | yes |
| ENUM | enumeration by size (reference, descriptive only) | no |

M exists because any gain from the guided arms could come from learning which operator types succeed in general, not from ε. E must beat M for ε to count.

### 6.4 Primary endpoint and comparisons
**Endpoint:** verified-solve rate within N on held-out \(L^*\) 3–5 tasks. Per-task rate is the fraction of the 20 seeds verified. Arm-level rate is the mean over tasks. Comparisons are paired by task, with CIs from a 10,000-resample task-level bootstrap.

**Holm family (4, family α = 0.05, two-sided):**

| ID | Contrast | Question |
|---|---|---|
| P1 | E − M | Does ε add beyond learned marginals? |
| P2 | H1 − E | Does Δε add beyond ε? |
| P3 | H1 − HS | Is it history information, or just capacity? |
| P4 | H2 − H1 | Does Δ²ε add beyond Δε? |

**Descriptive only:** M − R (does learning anything help), and ENUM.
**SESOI:** 5 percentage points absolute. Classify each contrast as **supported** (Holm-adjusted CI excludes 0 and point estimate ≥ SESOI), **detected but small**, **null** (CI inside ±SESOI) or **inconclusive**.
**Precision check before the confirmatory run:** estimate the SE of a paired difference from tuning data. If 3.3 × SE exceeds the SESOI, add seeds or tasks first. Compute is cheap.

### 6.5 Decision table

| Result | Conclusion | Next |
|---|---|---|
| P1 not supported | ε adds nothing beyond learned marginals on this substrate | Phase 1c (§9) |
| P1 supported; P2 or P3 not supported | ε helps, history not shown to add, but §8 limits what this can show | Phase 1b (§9) before concluding |
| P1, P2, P3 supported | History carries information beyond ε | Read P4; proceed to Phase 2 planning |
| ENUM ≥ best guided arm on the primary endpoint | At this size the learning machinery has shown no advantage over enumeration. Not a failure of the idea, a statement about this problem size. Check §6.7 first: if ENUM's solves are all \(L^*=3\) tasks inside its precomputed reach, the cause is coverage of length 3, not a DSL defect. | Re-run the primary endpoint on the ENUM-hard subset. Enlarge the DSL and re-calibrate N only if the gap persists there. |

### 6.6 Diagnostics reported with results
Overfit rate per arm. Evaluations-to-solve (restricted mean survival time up to N). Per-\(L^*\) results. The primary endpoint recomputed on the **ENUM-hard subset** (tasks ENUM does not solve at N), pre-declared as a sensitivity analysis. Fraction of decisions where Δ²ε-bin is defined. The op × ε-bin success table as a heatmap. ε vs \(\epsilon_H\) sensitivity. Candidate-level rates of `invalid` and `inapplicable` proposals, and the proposal-cap rate.

### 6.7 Interpreting ENUM successes

ENUM enumerates by length, lexicographic within a length. It fully covers lengths 1 and 2 (39 + 1,521 = 1,560 programs), then a prefix of length 3 (59,319 programs). Length 4 begins after 60,879 programs, so **at any N ≤ 60,879 ENUM cannot reach length 4.**

Coverage of the length-3 level at budget N is (N − 1,560) / 59,319:

| N | 2,000 | 5,000 | 10,000 |
|---|---|---|---|
| Length-3 coverage | 0.7% | 5.8% | 14.2% |

**ENUM's outcome on every task is a deterministic fact computed before lock**, not luck to be estimated afterwards. It is not read off \(L^*\). ENUM halts at the first program matching the 8 training anchors, so a short training-only match that precedes any verified equivalent produces an **overfit**. The pre-lock precompute therefore walks ENUM's reachable prefix (the first N programs) in exact enumeration order, evaluates each against the 8 training anchors, records the first training-set match and its rank, and classifies that candidate on the 40 verification anchors as verified or overfit (a candidate invalid on any verification anchor counts as overfit). No match within N is unsolved. Because N is only fixed in Stage 0d, the precompute runs to the maximum candidate budget (10,000) and stores the first training match, its rank and its classification. The outcome at any calibrated N is then read off: rank < N gives that classification, otherwise unsolved. The precompute uses an independent vectorized code path, so the ENUM arm's actual runs, which must reproduce it exactly, test both implementations.

**Enumeration order (fixed):** ENUM evaluates exactly the programs of rank 0 through N−1 (§2.1), one per budget unit, invalid candidates included, with no behavioral deduplication and no skipping of redundant programs. "Rank" everywhere in this section means this 0-based index.

Each ENUM result is classified by cause:

| ENUM result | Cause | Handling |
|---|---|---|
| Verified solve on a task with \(L^*\ge4\) (N ≤ 60,879) | Impossible if the audit is right: it would be a program of length ≤ 3 matching all 48 anchors. | Stop. Audit or evaluator bug. Fix by amendment, disclose, re-run the audit. |
| Verified solve on a task with \(L^*=3\) | Within-coverage hit: the first training match in ENUM's order is a verified equivalent inside the prefix. | Not evidence the DSL is too small. Report the rank of the first training match. |
| Overfit (halts on a training-only match), any \(L^*\) | Expected where precomputed: a short program fits the 8 training anchors but not the 40 verification anchors, ahead of any verified equivalent. | Counts as not verified. Report the rate and the rank. This is also a direct measure of how often 8 anchors under-determine a task. |
| Verified solve on a task with \(L^*\le2\) | Positive-control behavior. | Expected. |
| Outcome (verified / overfit / unsolved) or rank differs from the precomputed one | Bug in the precompute or the ENUM implementation. | Stop and fix by amendment. |

ENUM therefore answers one question only: what does plain enumeration achieve at this N on length-3 tasks. It can only overfit or fail at \(L^*\ge4\) while N ≤ 60,879. "DSL too small" is not inferred from any single ENUM success. It is inferred only from the decision-table row in §6.5, and only after the ENUM-hard subset analysis.

---

## 7. Stage 0c: steerability bar

Before any arm runs, on tuning tasks only, estimate \(p(m,b)=P(\epsilon_{child}<\epsilon_{parent})\) for each mutation type \(m\) and ε-bin \(b\), from at least 2,000 proposals per cell on parents drawn from random walks.

- **S1 (types differ):** in at least one bin, the spread \(\max_m p(m,b)-\bar p(b)\) is ≥ 0.03 absolute and exceeds the label-shuffle null (1,000 shuffles of type labels within bin) at p ≤ 0.0125 (Bonferroni over 4 bins).
- **S2 (type effectiveness depends on ε):** the op × bin interaction in a logistic model of improvement is significant at p ≤ 0.01, calibrated by shuffling bin labels within type.

| S1 | S2 | Handling |
|---|---|---|
| pass | pass | Run the full ladder. |
| pass | fail | Run the ladder. **Pre-registered prediction:** M beats R, E does not beat M. |
| fail | any | Skip the ladder. Go to Phase 1c. |

---

## 8. Known limitations (stated before the run)

1. **Greedy acceptance makes Δε_in ≤ 0 on every accepted lineage.** The history signals therefore mostly encode the size and trend of the last gain. Overshoot and oscillation, the things first and second differences are meant to detect, cannot appear. A null on P2 is weak evidence until Phase 1b.
2. **ε is a magnitude, not a direction.** The log compression discards the sign of each residual component, so `NUDGE_PARAM` direction is chosen blindly. The signed vector \(e\) is logged but unused.
3. **Tables are trained off-policy** (uniform-random walks) and tested on-policy, so the context distribution shifts at test time.
4. **Unary pipelines are a narrow domain.** No branching, no binary ops, no recursion.
5. **The bins and the ε function are design choices.** Tuned once on tuning data, then frozen.
6. **Phase 1a tests transfer across tasks, not within-run learning.**
7. **ENUM is informative only at \(L^*=3\).** At any N ≤ 60,879 it cannot reach length 4, so it is a reference for the shortest stratum and a correctness check on the audit, not a competitor on the harder strata.

---

## 9. Deferred, with gates

- **Phase 1b (non-greedy acceptance).** Metropolis acceptance at one fixed temperature (chosen on tuning data) so Δε_in takes both signs. Fires only if P1 is supported and P2 or P3 are not.
- **Phase 1c (residual as direction).** Constructive operators that use the signed vector: append `add(c)` with c = median of e when e is near-constant, append `mul` when \(t_j/y_j\) is constant, and signed-direction `NUDGE_PARAM`. This is the closest analogue of an actuator with known sign. Fires if Stage 0c fails or P1 is not supported.
- **Phase 2a (within-run learning).** The next gate for part (B), and the first test of learning during a run. Same contexts as E and H1, but the table starts from the frozen prior and updates online from the run's own edges, with the prior weight pre-registered on tuning data. Compared with the frozen arm at equal N. Fires if P1 is supported.
- **Phase 2 (lexicon and learned proposals).** Canonical subtrees with parameter slots, per-rule outcome statistics, a learned proposal model, and float or geometric domains. Starts only after Phase 2a. Provenance is logged from day one regardless.

---

## 10. Traceability to Discovery.md §8

| Q | Where addressed |
|---|---|
| 1 Notation and target | §1 |
| 2 Nontrivial signal | §1, §2.3 (independent hidden \(g\)) |
| 3 Representation | §2.1 |
| 4 Update rule | §5.2 |
| 5 Role of residual history | §6.3, §6.4 (E, H1, H2, HS) |
| 6 Memory and lexicon | §4 (provenance now), §9 (lexicon deferred) |
| 7 Learning vs enumeration vs overfit | §2.3, §6.3 (ENUM), §6.4 |
| 8 Exactness | §2.2 |
| 9 Stopping and failure | §5.5 |
| 10 Minimal experiment | §6 |

---

## Appendix A: redundant adjacent pairs rejected in target programs
Left-to-right pairs: `add→add`, `mul→mul`, `neg→neg`, `neg→mul`, `mul→neg`, `abs→abs`, `neg→abs`, `neg→sq`, `abs→sq`, `sq→abs`, `mod(m)→mod(m)` (same m).

## Appendix B: pre-lock free checks
1. Evaluator unit tests pass (Stage 0a).
2. Task-generator diagnostic (Batch 6 amendment; replaces the former ≥95% pass-rate gate). Report: total raw draws and accepted tasks; rejection counts and rates per reason code (`target_invalid`, `redundant_pair`, `few_distinct_targets`, `quota_full`); programmatic verification that every accepted task satisfies the target-validity rules (§2.3: valid on all 48 anchors, ≥4 distinct training targets); wall-clock generation time and confirmation that quotas fill within a practical limit. The distinct-target pass rate is recorded as an observed property of the generator, not a pass/fail gate. (Pre-lock observation: 79.3% on the tuning/positive-control run; rejections dominated by `mod`-collapse, a domain property. Quotas filled in 52s/42s, so rejection is an efficiency cost, not evidence of a broken generator.) The DSL, sampling procedure and four-distinct-target requirement are unchanged.
3. Minimal-length audit and ENUM precompute: \(L^*\) and \(n_{eq}\) computed for every task; ENUM's outcome (verified / overfit / unsolved) and first-training-match rank precomputed by walking ENUM's enumeration order against the 8 training anchors, through an independent code path; the ENUM runs on tuning tasks reproduce them exactly (§6.7).
4. Applicability rates for each mutation type on random programs (flags types that are rarely applicable).
5. Commit hash recorded: at specification lock (freeze step 1), the spec; at code lock (freeze step 3), the generator, the evaluator and the analysis script; at confirmatory task lock (freeze step 4), the confirmatory task file, its \(L^*\) audit table and its ENUM precompute (generated once from a pre-registered seed after code freeze).

## Amendment log

**Batch 1 (2026-10-12, pre-lock, after ChatGPT review).**
1. §0: added the "what a pass lets us say" claim ladder; Phase 1a is the first gate of a two-part program, and a pass supports only transfer of residual-conditioned guidance.
2. §2.3: tasks are stratified by audited minimal functional length \(L^*\), not nominal length. The adjacent-pair filter is acknowledged as incomplete (`mul(c)→fdiv(c)`, `sq→mod(2)`).
3. §6.2, §6.7, App. B: the rule "ENUM verifies 0% or the DSL is too small" is removed. ENUM's outcome on every task is precomputed from the audit; hits are classified by cause; ENUM cannot reach length 4 at N ≤ 60,879.
4. §6.5, §6.6: the ENUM row now points to the cause classification and an ENUM-hard-subset sensitivity analysis before any DSL enlargement.
5. §9: within-run learning split out as Phase 2a, the explicit next gate for part (B).
6. Unchanged after review: greedy acceptance with Phase 1b gated follow-up (§8, §9), and the M, HS and E-vs-M controls (§6.3, §6.4).

**Batch 2 (2026-10-12, pre-lock, after second ChatGPT review).**
1. §6.7: ENUM's outcome is no longer described as readable from the audit. ENUM halts at the first program matching the 8 training anchors, so the precompute walks ENUM's enumeration order against the training anchors, records the first training match and its rank, and classifies it on the 40 verification anchors (verified, overfit or unsolved). This supersedes Batch 1 item 3, and the "roughly \(n_{eq}\times\) coverage" estimate is removed.
2. §6.7: enumeration order is now fixed explicitly. An overfit row is added to the cause table.
3. §2.3: states that \(L^*\) is an audited fact about the task's 48 sampled anchors, not global functional equivalence, and that it does not by itself predict ENUM's outcome.
4. Appendix B item 3 and §6.2 0a′ updated to match.

**Batch 3 (2026-10-12, pre-lock, after third ChatGPT review).**
1. §6.2: Stage 0b is split into an implementation-correctness hard gate (unit tests, exact reproduction of the ENUM precompute, replay verification) and a reported positive-control performance check (0b′). The "R and ENUM must each verify ≥ 90%" rule is removed as a bug trigger: overfits can legitimately halt runs on tasks that have short equivalents, and no task construction guarantees a rate.
2. §2.1: explicit instance indices and a rank formula. §6.7: ENUM evaluates ranks 0 to N−1 with no deduplication, so two independent implementations cannot diverge on traversal order.

**Batch 6 (2026-10-14, pre-lock, Adrian-directed).**
1. Appendix B item 2: replaced the "≥95% of generated tasks pass the distinct-target filter" gate with a documented generator diagnostic (raw draws, accepted tasks, per-reason rejection counts/rates, programmatic validity verification of accepted tasks, generation time, quota fillability). Audit trail: old requirement (≥95%), observed failure (79.3% pass rate on the pre-lock tuning/positive-control run), rationale (mod-collapse is a domain property, not evidence of a broken generator; quotas filled in 52s/42s, so rejection is an efficiency cost; changing the threshold or the sampling would be a redesign). The DSL, sampling procedure and four-distinct-target requirement are unchanged.
2. §6.1: pre-registered confirmatory generation seed `3141592653` (distinct from tuning seeds 1000 and 2000); frozen against post-lock changes for convenience.
3. No design changes to the search skeleton, arms, endpoints or decision rules.

**Batch 5 (2026-10-14, pre-lock, Adrian-directed clarity fix).**
1. §0: added an explicit five-step freeze sequence distinguishing the specification lock (spec document + pre-registered task-generation seed/rules, before any arm runs) from the code lock (code + analysis scripts) and the confirmatory task lock (task set + \(L^*\) audit + ENUM precompute, generated once from the pre-registered seed after code freeze, hashed into a second lock commit). This resolves the ambiguity in §6.1/§6.2 about which "lock commit" the confirmatory artifacts are hashed into.
2. §6.1, Appendix B item 5: "lock commit" wording disambiguated to the code/task lock (freeze step 4); hash recording assigned to its lock step.
3. No design changes; nothing has been run.

**Batch 4 (2026-10-12, pre-lock, after fourth ChatGPT review).**
1. §2.3: added a target-validity rule. A task is rejected if \(g\) is invalid under §2.2 on any of its 48 anchors, with reason-coded rejection logging. Invalid candidates remain part of the search.
2. §6.2 0b′, §6.6: run-level outcomes (verified, overfit, unsolved; mutually exclusive) are reported separately from candidate-level diagnostics (invalid-candidate fraction, proposal-cap rate, inapplicable-proposal rate). Invalid is no longer listed alongside terminal outcomes.
3. §6.1, §6.2 0b, App. B: the ENUM correctness gate covers every ENUM run on every task, confirmatory included, as a post-freeze deterministic check. The confirmatory task set, audit and precompute are generated once after code freeze and hashed into the lock commit.
4. §6.7: the ENUM precompute is run to the maximum budget (10,000) and stores the first-training-match rank and classification, so it does not depend on N, which is only fixed in Stage 0d. Found while checking the Batch 4 freeze ordering.
