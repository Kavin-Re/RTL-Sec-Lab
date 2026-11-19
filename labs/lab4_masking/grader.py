"""Auto-grader for Lab 4 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab4_masking/grader.py [path/to/your_script.py]      (default: starter.py next to this file)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected
from rtlseclab.core import leakage as L

EXP = load_expected(HERE)


def band(e, v, what):
    assert e["lo"] <= v <= e["hi"], "%s = %.2f, expected within [%s, %s]" % (what, v, e["lo"], e["hi"])


def t1(m):
    rng = np.random.default_rng(seed(1))
    x = L.rand64(rng, 2500)
    x0, x1 = m.share(x, np.random.default_rng(seed(11)))
    x0, x1 = np.asarray(x0, dtype=np.uint64), np.asarray(x1, dtype=np.uint64)
    assert np.array_equal(x0 ^ x1, x), "shares do not recombine to x"
    hw = float(L.HW[L.bytes_of(x1)].mean())
    band(EXP["T1"][0], hw, "mean HW of share 1 bytes")
    fixed = np.full(4000, 0xFFFFFFFFFFFFFFFF, dtype=np.uint64)
    f0, f1 = m.share(fixed, np.random.default_rng(seed(12)))
    h0 = float(L.HW[L.bytes_of(np.asarray(f0, dtype=np.uint64))].mean())
    assert 3.8 <= h0 <= 4.2, "share 0 of a constant 0xFF..FF value must look random too (mean HW %.2f, not 8)" % h0
    return True, "recombines; share 1 mean HW %.2f; share 0 of all-ones mean HW %.2f" % (hw, h0)


def t2(m):
    a = m.attack_hits("unmasked", 300, 2.0, seed(2)); b = m.attack_hits("off_fo", 2000, 2.0, seed(22))
    band(EXP["T2"][0], a, "unmasked bytes right"); band(EXP["T2"][1], b, "masks-off control bytes right")
    return True, "unmasked %d/8, masks-off control %d/8" % (a, b)


def t3(m):
    rng = np.random.default_rng(seed(3))
    T = L.leak_masked(bytes(range(16)), L.rand64(rng, 500), 1.0, rng)
    for b in (0, 3, 7):
        got = np.asarray(m.so_combine(T, b), dtype=float)
        a, c = T[:, 0, b].astype(float), T[:, 1, b].astype(float)
        assert got.shape == (500,) and np.allclose(got, (a - a.mean()) * (c - c.mean()), atol=1e-4), "so_combine wrong for byte %d" % b
    return True, "centred product ok"


def t4(m):
    a = m.attack_hits("fo", 10000, 1.0, seed(4)); b = m.attack_hits("so", 10000, 2.0, seed(44))
    band(EXP["T4"][0], a, "first-order on masked: bytes right"); band(EXP["T4"][1], b, "second-order on masked: bytes right")
    return True, "first order %d/8 (chance), second order %d/8" % (a, b)


def t5(m):
    a = m.attack_hits("so", 300, 2.0, seed(5)); b = m.attack_hits("so", 3000, 2.0, seed(55))
    band(EXP["T5"][0], a, "second order, N=300"); band(EXP["T5"][1], b, "second order, N=3000")
    return True, "second order: N=300 -> %d/8, N=3000 -> %d/8 (unmasked needs <300)" % (a, b)


def t6(m):
    v = [float(m.tmax(1, False, 10000, seed(6))), float(m.tmax(1, True, 10000, seed(6))), float(m.tmax(2, True, 10000, seed(6)))]
    for e, x, w in zip(EXP["T6"], v, ("order1/off", "order1/on", "order2/on")):
        band(e, x, "max|t| " + w)
    return True, "max|t|: order1 masks-off %.1f, order1 masks-on %.1f, order2 masks-on %.1f" % tuple(v)


def t7(m):
    a = m.attack_hits("hd_fo", 2000, 2.0, seed(7))
    band(EXP["T7"][0], a, "first order vs recombination leak: bytes right")
    return True, "first-order attack breaks the 'masked' design again: %d/8 bytes" % a


TASKS = [Task("T1", "share", t1), Task("T2", "fo_attack: works unmasked, control", t2), Task("T3", "so_combine", t3),
         Task("T4", "first order fails, second order wins", t4), Task("T5", "masking costs traces", t5),
         Task("T6", "t-test: where does the leakage live?", t6), Task("T7", "recombination leak breaks masking", t7, stretch=True)]

if __name__ == "__main__":
    main("Lab 4 - Masking and its limits", TASKS, HERE)
