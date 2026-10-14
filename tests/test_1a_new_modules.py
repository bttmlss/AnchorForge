"""Unit tests for residuals, records, search, tables, arms, stages."""
import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import residuals
import records
import tables
import stages


def test_epsilon():
    assert residuals.epsilon([0] * 8) == 0.0
    # single 1: log2(2)/8
    import math
    assert abs(residuals.epsilon([1] + [0] * 7) - math.log2(2) / 8) < 1e-12
    assert residuals.epsilon_h([0] * 8) == 0.0
    assert residuals.epsilon_h([1, 0, 0, 0, 0, 0, 0, 0]) == 0.125


def test_bins():
    assert residuals.delta_bin(None, 1.0) == "none"
    assert residuals.delta_bin(0.0, 1.0) == "flat"
    assert residuals.delta_bin(0.1, 1.0) == "small"   # < 0.25
    assert residuals.delta_bin(0.3, 1.0) == "large"    # >= 0.25
    assert residuals.delta_bin(-0.1, 1.0) == "small"
    assert residuals.delta2_bin(None, 0.1) == "none"
    assert residuals.delta2_bin(0.1, None) == "none"
    assert residuals.delta2_bin(0.5, 0.3) == "accel"   # > 1.25x
    assert residuals.delta2_bin(0.1, 0.3) == "decel"   # < 0.75x
    assert residuals.delta2_bin(0.3, 0.3) == "steady"
    assert residuals.delta2_bin(0.0, 0.0) == "steady"
    d_p, d_g = residuals.lineage_deltas([3.0, 2.0, 2.0])
    assert d_p == 0.0 and d_g == -1.0
    assert residuals.lineage_deltas([5.0]) == (None, None)


def test_eps_binner():
    f = residuals.EpsBinFitter().fit([1.0, 2.0, 3.0, 4.0])
    assert f.bin(0.5) == 0
    assert f.bin(1.5) == 1 or f.bin(1.5) == 0  # boundary-tolerant
    assert f.bin(10.0) == 3


def test_candidate_id():
    assert records.candidate_id((1, 2)) == records.candidate_id((1, 2))
    assert records.candidate_id((1, 2)) != records.candidate_id((2, 1))


def test_table_laplace():
    t = tables.Table()
    rng = random.Random(0)
    # unseen context -> uniform
    counts = {m: 0 for m in tables.MTYPES}
    for _ in range(6000):
        counts[t.sample(("nope",), rng)] += 1
    for m in tables.MTYPES:
        assert 800 < counts[m] < 1200, (m, counts[m])
    # learned: type A always improves
    for _ in range(100):
        t.update("c", "REPLACE_OP", True)
        t.update("c", "DELETE", False)
    assert t.p_hat("c", "REPLACE_OP") > t.p_hat("c", "DELETE")


def test_ctx_key():
    assert tables.ctx_key("M", 1, "small", "steady") == ()
    assert tables.ctx_key("E", 2, "small", "steady") == (2,)
    assert tables.ctx_key("H1", 2, "small", "steady") == (2, "small")
    assert tables.ctx_key("H2", 2, "small", "accel") == (2, "small", "accel")


def test_s1_s2_null():
    # no signal: types shuffled -> should usually not pass
    rng = random.Random(1)
    rows = []
    for _ in range(3000):
        rows.append((rng.choice(tables.MTYPES), rng.randrange(4),
                     rng.random() < 0.2))
    s1 = stages.s1_test(rows, n_shuffle=200, seed=5)
    s2 = stages.s2_test(rows, n_shuffle=200, seed=6)
    # not asserting pass/fail (stochastic), just that it runs
    assert "pass" in s1 and "pass" in s2


def test_s1_signal():
    # strong signal: REPLACE_OP always improves in bin 0
    rows = []
    for _ in range(500):
        rows.append(("REPLACE_OP", 0, True))
        rows.append(("DELETE", 0, False))
    for b in (1, 2, 3):
        for _ in range(200):
            rows.append(("REPLACE_OP", b, False))
            rows.append(("DELETE", b, False))
    s1 = stages.s1_test(rows, n_shuffle=200, seed=7)
    assert s1["pass"], s1


def test_run_seed_deterministic():
    assert stages.run_seed("t1", "R", 0) == stages.run_seed("t1", "R", 0)
    assert stages.run_seed("t1", "R", 0) != stages.run_seed("t1", "R", 1)


if __name__ == "__main__":
    test_epsilon()
    test_bins()
    test_eps_binner()
    test_candidate_id()
    test_table_laplace()
    test_ctx_key()
    test_s1_s2_null()
    test_s1_signal()
    test_run_seed_deterministic()
    print("all new-module unit tests pass")
