"""Stage 0a: evaluator unit tests. Spec §6.2, Appendix B item 1."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dsl import (N_INSTANCES, canonical_rank, unrank, evaluate, apply_op,
                 instance, describe)

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


# 1. instance table shape
check("39 instances", N_INSTANCES == 39)
check("add(-9) is 0", instance(0) == ("add", -9))
check("add(9) is 17", instance(17) == ("add", 9))
check("mul(-4) is 18", instance(18) == ("mul", -4))
check("sq is 24", instance(24) == ("sq", None))
check("neg is 25", instance(25) == ("neg", None))
check("abs is 26", instance(26) == ("abs", None))
check("mod(2) is 27", instance(27) == ("mod", 2))
check("mod(9) is 34", instance(34) == ("mod", 9))
check("fdiv(2) is 35", instance(35) == ("fdiv", 2))
check("fdiv(5) is 38", instance(38) == ("fdiv", 5))

# 2. rank/unrank roundtrip + spec values
check("rank len1", canonical_rank((0,)) == 0 and canonical_rank((38,)) == 38)
check("rank len2 start", canonical_rank((0, 0)) == 39)
check("rank len2 end", canonical_rank((38, 38)) == 1559)
check("rank len3 start", canonical_rank((0, 0, 0)) == 1560)
check("rank len4 start", canonical_rank((0, 0, 0, 0)) == 60879)
rng = random.Random(0)
for _ in range(2000):
    L = rng.randint(1, 5)
    prog = tuple(rng.randrange(39) for _ in range(L))
    check(f"roundtrip {prog}", unrank(canonical_rank(prog)) == prog)

# 3. hand-built programs recover known targets
# g = add(3), mul(2): x -> (x+3)*2
prog = (12, 20)  # add(3) is idx 12? add(1..9)=9..17 so add(3)=11; check via describe
print("   note: prog (12,20) =", describe((12, 20)))
ok, v = evaluate((11, 20), 5)  # add(3)=idx 11, mul(2)=idx 21? verify
print("   note: prog (11,20) =", describe((11, 20)), "->", evaluate((11, 20), 5))

# find indices properly
def idx_of(op, p):
    for i in range(39):
        if instance(i) == (op, p):
            return i
    raise KeyError

a3 = idx_of("add", 3)
m2 = idx_of("mul", 2)
ok, v = evaluate((a3, m2), 5)
check("hand program (x+3)*2 at x=5", ok and v == 16)
ok, v = evaluate((a3, m2), -4)
check("hand program at x=-4", ok and v == -2)

# sq then add
sq = idx_of("sq", None)
a1 = idx_of("add", 1)
ok, v = evaluate((sq, a1), -3)
check("sq then add(1) at -3", ok and v == 10)

# 4. floor semantics on negatives
fd2 = idx_of("fdiv", 2)
ok, v = evaluate((fd2,), -3)
check("fdiv(2) of -3 is -2 (floor)", ok and v == -2)
mo3 = idx_of("mod", 3)
ok, v = evaluate((mo3,), -4)
check("mod(3) of -4 is 2 (floor)", ok and v == 2)
ok, v = evaluate((mo3,), 5)
check("mod(3) of 5 is 2", ok and v == 2)

# 5. invalid detection
big = (idx_of("mul", 4),) * 25  # 10*4^25 >> 1e12
ok, v = evaluate(big, 10)
check("mul(4)^25 at x=10 invalid", not ok and v is None)
ok, v = evaluate((idx_of("sq", None), idx_of("sq", None)), 10 ** 4)
check("sq(sq(1e4)) invalid", not ok)
ok, v = evaluate((idx_of("sq", None),), 10 ** 3)
check("sq(1e3)=1e6 valid", ok and v == 10 ** 6)

# 6. cross-check vectorized evaluator on random programs/anchors
import numpy as np
from audit import evaluate_programs
rng = random.Random(1)
for trial in range(30):
    L = rng.randint(1, 4)
    prog = tuple(rng.randrange(39) for _ in range(L))
    xs = [rng.randint(-40, 40) for _ in range(12)]
    parr = np.array([prog], dtype=np.int64)
    aarr = np.array(xs, dtype=np.int64)
    valid_v, vals_v = evaluate_programs(parr, aarr)
    ok_all = True
    exp_vals = []
    for x in xs:
        ok, v = evaluate(prog, x)
        if not ok:
            ok_all = False
            break
        exp_vals.append(v)
    check(f"vec-vs-ref trial {trial}",
          bool(valid_v[0]) == ok_all and (not ok_all or list(vals_v[0]) == exp_vals))

print(f"\n0a: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
