"""Auto-grader for Lab 5 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab5_fault_tmr/grader.py [path/to/your_script.py]      (default: starter.py next to this file)"""
import os, sys, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected
from rtlseclab.core import faultsim

EXP = load_expected(HERE)
_TABLE = {}


def band(e, v, what):
    assert e["lo"] <= v <= e["hi"], "%s = %.4g, expected within [%s, %s]" % (what, v, e["lo"], e["hi"])


def table(m):
    if id(m) not in _TABLE:
        _TABLE[id(m)] = m.fault_table(300, seed(7))
    return _TABLE[id(m)]


def t1(m):
    for a, b, c in itertools.product(range(8), repeat=3):
        assert m.majority(a, b, c) == (1 if (a & 1) + (b & 1) + (c & 1) >= 2 else 0) | (2 if ((a >> 1) & 1) + ((b >> 1) & 1) + ((c >> 1) & 1) >= 2 else 0) | (4 if ((a >> 2) & 1) + ((b >> 2) & 1) + ((c >> 2) & 1) >= 2 else 0), "majority(%d,%d,%d) wrong" % (a, b, c)
    rng = np.random.default_rng(seed(1))
    for _ in range(300):
        x = int(rng.integers(0, 2**63)); n = int(rng.integers(1, 64))
        assert m.parity(x, n) == bin(x & ((1 << n) - 1)).count("1") % 2, "parity(%d, %d) wrong" % (x, n)
    assert m.majority(0xF0F0, 0xFF00, 0x0FF0) == 0xFFF0
    return True, "majority and parity exact"


def t2(m):
    a, b = float(m.p_tmr_fail_w2(32)), float(m.p_tmr_fail_w2(128))
    band(EXP["T2"][0], a, "exact P (32 bit)"); band(EXP["T2"][1], b, "exact P (128 bit)")
    mc = float(m.tmr_fail_mc(32, 2, 40000, seed(2)))
    band(EXP["T2"][2], mc, "Monte Carlo")
    assert m.tmr_fail_mc(32, 1, 3000, seed(2)) == 0.0, "a single flip must always be out-voted"
    return True, "exact %.5f / %.5f ; Monte Carlo %.4f ; 1 flip never fails" % (a, b, mc)


def t3(m):
    ov = m.overheads()
    for e, k in zip(EXP["T3"], ("TMR_state", "DMR_parity_state", "TMR_full_engine", "lockstep_full_engine")):
        band(e, ov[k], "overhead " + k)
    assert "baseline" not in ov
    return True, "overheads %s" % {k: round(v, 1) for k, v in ov.items()}


def t4(m):
    t = table(m); e = EXP["T4"]
    band(e[0], t[("none", "ctr", 1)]["p_desync"], "none ctr1 p_desync")
    band(e[1], t[("none_nowd", "key", 1)]["p_unrecovered"], "none_nowd key1 p_unrecovered")
    band(e[2], t[("none", "key", 1)]["mean_rec"], "none key1 mean recovery slots")
    for site, w in (("ctr", 1), ("key", 1), ("fsm", 1), ("out", 1)):
        assert t[("tmr", site, w)]["p_desync"] == e[3]["hi"], "tmr must absorb a single %s fault, p_desync=%.3f" % (site, t[("tmr", site, w)]["p_desync"])
    band(e[4], t[("tmr", "ctr", 2)]["p_desync"], "tmr ctr2 p_desync")
    band(e[5], t[("dcp", "ctr", 2)]["p_desync"], "dcp ctr2 p_desync")
    band(e[6], t[("dcp", "fsm", 1)]["p_desync"], "dcp fsm1 p_desync")
    return True, "none ctr1 %.2f; none_nowd key1 unrecovered %.2f; none key1 recovery %.0f slots; tmr ctr2 %.3f; dcp ctr2 %.2f; dcp fsm1 %.2f" % (
        t[("none", "ctr", 1)]["p_desync"], t[("none_nowd", "key", 1)]["p_unrecovered"], t[("none", "key", 1)]["mean_rec"],
        t[("tmr", "ctr", 2)]["p_desync"], t[("dcp", "ctr", 2)]["p_desync"], t[("dcp", "fsm", 1)]["p_desync"])


def t5(m):
    t = table(m)
    a, b = m.cheapest_scheme(t, 0.05), m.cheapest_scheme(t, 0.6)
    assert a == "tmr", "max 0.05: expected 'tmr' (dcp's output-register case is never corrected), got %r" % (a,)
    assert b == "tmr", "max 0.6: dcp still fails the 'out' case (p_desync 1.0), expected 'tmr', got %r" % (b,)
    assert m.cheapest_scheme(t, 1.0) == "tmr", "with the limit at 1.0 both qualify and TMR_state (53.4 %) is cheaper than DMR_parity_state (57.3 %)"
    return True, "cheapest qualifying scheme: %s (TMR_state is also the cheaper of the two)" % a


def t6(m):
    for v, b in ((0, 3), (0xFFFF, 15), (0x1234, 0)):
        assert m.common_mode_vote(v, b) == v ^ (1 << b), "the vote should return the flipped value %d" % (v ^ (1 << b))
    return True, "same-bit flip in all copies passes the voter"


TASKS = [Task("T1", "majority + parity", t1), Task("T2", "exact and Monte Carlo TMR failure", t2), Task("T3", "area overheads from the GE proxy", t3),
         Task("T4", "link-level fault table", t4), Task("T5", "cheapest scheme meeting a target", t5),
         Task("T6", "common-mode faults beat TMR", t6, stretch=True)]

if __name__ == "__main__":
    main("Lab 5 - Fault injection and TMR cost", TASKS, HERE)
