"""Auto-grader for Lab 2 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab2_prng_graveyard/grader.py [path/to/your_script.py]      (default: starter.py next to this file)"""
import os, sys, random, hmac
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected
from rtlseclab.core import prng as ref
from rtlseclab.core.lfsr import lfsr_schedule, keyed_schedule

EXP = load_expected(HERE)


def t1(m):
    e = EXP["T1"][0]
    rng = np.random.default_rng(seed(1))
    sub = rng.integers(0, ref.M24, 5000).astype(np.uint64)
    for ch in (0, 7, 12):
        want = sorted(x for x in ((ref.A24 * int(s) + ref.C24) % ref.M24 for s in sub) if (x >> 8) % 13 == ch)
        got = sorted(int(x) for x in m.lcg_filter(sub, ch))
        assert got == want, "lcg_filter wrong for channel %d" % ch
    pyr = random.Random(seed(1))
    used = []
    for _ in range(4):
        x0 = pyr.randrange(ref.M24)
        st = ref.lcg_stream(x0, 20)
        s, n = m.break_lcg(st)
        assert s is not None, "attack failed"
        x = x0
        for _ in range(n):
            x = ref.lcg_step(x)
        assert int(s) == x, "returned state is not the state after hop %d" % n
        assert e["lo"] <= n <= e["hi"], "needed %d hops" % n
        used.append(n)
    return True, "hops used %s" % used


def t2(m):
    pyr = random.Random(seed(2))
    for y in [0, 1, 0xFFFFFFFF, 0x80000000] + [pyr.getrandbits(32) for _ in range(2000)]:
        assert m.untemper(ref.temper(y)) == y, "untemper(temper(%#x)) != y" % y
        assert ref.temper(m.untemper(y)) == y, "temper(untemper(%#x)) != y" % y
    r = random.Random(seed(2))
    outs = [r.getrandbits(32) for _ in range(624)]
    c = m.mt_clone(outs)
    for i in range(2000):
        assert c.getrandbits(32) == r.getrandbits(32), "clone diverges at output %d" % i
    return True, "untemper exact, clone predicted 2000 outputs"


def t3(m):
    e = EXP["T3"][0]
    rng = np.random.default_rng(seed(3))
    # solver on random systems
    for trial in range(20):
        x = int(rng.integers(0, 1 << 32))
        eqs = []
        for _ in range(60):
            mask = int(rng.integers(0, 1 << 32))
            eqs.append((mask, bin(mask & x).count("1") & 1))
        sol = m.solve_gf2(eqs)
        assert sol == x, "solver returned %r, planted solution %#x" % (sol, x)
    # rank-deficient -> None
    eqs = [(1 << j, 0) for j in range(31)]
    assert m.solve_gf2(eqs) is None, "31 independent equations in 32 unknowns must give None"
    # inconsistent -> None
    assert m.solve_gf2([(1, 0), (1, 1)] + [(1 << j, 0) for j in range(1, 32)]) is None, "inconsistent system must give None"
    pyr = random.Random(seed(3))
    for _ in range(4):
        x0 = pyr.randrange(1, 1 << 32); x = x0; o = []
        for _ in range(30):
            x = ref.xs32(x); o.append(x & 15)
        s, n = m.break_xorshift(o)
        assert s == x0, "break_xorshift recovered %r, expected %#x" % (s, x0)
        assert e["lo"] <= n <= e["hi"], "used %d hops, expected %d" % (n, e["expected"])
    return True, "solver exact; xorshift state recovered from %d hops" % n


def t4(m):
    e_l, e_k = EXP["T4"]
    a = float(m.context_predictor_accuracy([int(v) for v in lfsr_schedule(20000)]))
    assert e_l["lo"] <= a <= e_l["hi"], "LFSR16 accuracy %.3f outside [%.2f, %.2f]" % (a, e_l["lo"], e_l["hi"])
    b = float(m.context_predictor_accuracy([int(v) for v in keyed_schedule(bytes(range(16)), 0, 20000)]))
    c = float(m.context_predictor_accuracy([ref.hmac_hop(b"k" * 16, i) for i in range(20000)]))
    for nm, v in (("SipHash", b), ("HMAC", c)):
        assert e_k["lo"] <= v <= e_k["hi"], "%s accuracy %.3f is not near chance 0.077" % (nm, v)
    return True, "LFSR %.3f, SipHash %.3f, HMAC %.3f (chance 0.077)" % (a, b, c)


def t5(m):
    e = EXP["T5"][0]
    t = m.graveyard_table(seed=seed(5))
    assert e["lo"] <= t["LCG24"] <= e["hi"], "LCG24 %.2f" % t["LCG24"]
    assert t["xorshift32"] == 9, "xorshift32 %.2f" % t["xorshift32"]
    assert t["MT19937 (32-bit leak)"] == 624 and t["SipHash / HMAC"] is None
    return True, "LCG24 %.1f, xorshift32 %.0f, MT19937 624, keyed: not predicted" % (t["LCG24"], t["xorshift32"])


TASKS = [Task("T1", "lcg_filter + break_lcg", t1), Task("T2", "untemper + mt_clone", t2), Task("T3", "solve_gf2 + break_xorshift", t3),
         Task("T4", "context_predictor_accuracy", t4), Task("T5", "graveyard_table", t5)]

if __name__ == "__main__":
    main("Lab 2 - PRNG graveyard", TASKS, HERE)
