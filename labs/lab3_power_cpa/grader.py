"""Auto-grader for Lab 3 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab3_power_cpa/grader.py [path/to/your_script.py]      (default: starter.py next to this file)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected
from rtlseclab.core import leakage as L
from rtlseclab.core.siphash import split_key

EXP = load_expected(HERE)


def _keys(n, off):
    rng = np.random.default_rng(seed(off))
    return [bytes(rng.integers(0, 256, 16, dtype=np.uint8)) for _ in range(n)], rng


def t1(m):
    x = np.arange(256, dtype=np.uint8)
    got = np.asarray(m.hw8(x), dtype=float)
    assert got.shape == (256,) and np.array_equal(got, [bin(i).count("1") for i in range(256)]), "hw8 differs from popcount"
    assert np.asarray(m.hw8(x.reshape(16, 16))).shape == (16, 16), "must keep the input shape"
    return True, "popcount table ok"


def t2(m):
    rng = np.random.default_rng(seed(2))
    H = rng.integers(0, 9, (200, 12)).astype(float); H[:, 3] = 4.0           # one constant column
    l = rng.normal(0, 1, 200) + H[:, 5]
    got = np.asarray(m.corr_cols(H, l), dtype=float)
    want = np.array([0.0 if j == 3 else np.corrcoef(H[:, j], l)[0, 1] for j in range(12)])
    d = float(np.abs(got - want).max())
    assert got.shape == (12,) and d < EXP["T2"][0]["hi"], "max abs diff %.2e (constant column must give 0)" % d
    return True, "max abs diff %.1e" % d


def t3(m):
    keys, rng = _keys(5, 3)
    for key in keys:
        msg = L.rand64(rng, 300); T = L.leak_unmasked(key, msg, 1.0, rng)
        k1 = m.recover_k1(T, msg)
        assert k1 == split_key(key)[1], "k1 %016x != %016x (%d of 8 bytes right)" % (k1, split_key(key)[1], L.byte_hits(k1, split_key(key)[1]))
    e = EXP["T3"][1]
    rng = np.random.default_rng(seed(33)); key = bytes(range(16)); msg = L.rand64(rng, 300); T = L.leak_unmasked(key, msg, 2.0, rng)
    sc = np.asarray(m.scores_stage1(T[:, 0], L.bytes_of(msg), 0), dtype=float)
    assert sc.shape == (256,) and int(np.argmax(sc)) == (split_key(key)[1] & 255), "right guess is not the argmax"
    pk = float(sc.max())
    assert e["lo"] <= pk <= e["hi"], "peak correlation %.3f outside [%.2f, %.2f]" % (pk, e["lo"], e["hi"])
    return True, "5/5 keys, peak r = %.3f" % pk


def t4(m):
    keys, rng = _keys(5, 4)
    for key in keys:
        msg = L.rand64(rng, 300); T = L.leak_unmasked(key, msg, 1.0, rng)
        k0t, k1t = split_key(key)
        k0 = m.recover_k0(T, msg, k1t)
        assert k0 == k0t, "k0 %016x != %016x (%d of 8 bytes right; remember carry and low-byte-first)" % (k0, k0t, L.byte_hits(k0, k0t))
    return True, "5/5 keys, k0 recovered given k1"


def t5(m):
    es = EXP["T5"]
    r = [float(m.success_rate(2.0, 50, 20, 7)), float(m.success_rate(2.0, 200, 20, 7)), float(m.success_rate(4.0, 800, 20, 7))]
    for (sg, N), e, v in zip([(2, 50), (2, 200), (4, 800)], es, r):
        assert e["lo"] <= v <= e["hi"], "sigma=%d N=%d: success %.2f outside [%.2f, %.2f]" % (sg, N, v, e["lo"], e["hi"])
    return True, "success: s2/N50 %.2f, s2/N200 %.2f, s4/N800 %.2f" % tuple(r)


def t6(m):
    e1, e2 = EXP["T6"]
    a, b = m.min_traces(2.0), m.min_traces(4.0)
    assert a is not None and b is not None, "no grid point reached the target"
    assert e1["lo"] <= a <= e1["hi"], "min_traces(2) = %s" % a
    assert e2["lo"] <= b / a <= e2["hi"], "ratio %s/%s = %.1f, expected about 4 (noise power scales as sigma^2)" % (b, a, b / a)
    return True, "min traces: sigma 2 -> %d, sigma 4 -> %d (x%.1f)" % (a, b, b / a)


def t7(m):
    keys, rng = _keys(5, 7)
    for key in keys:
        msg = L.rand64(rng, 400); T = L.leak_unmasked(key, msg, 1.0, rng, model2="HD")
        k0t, k1t = split_key(key)
        got = [int(x) for x in m.hd_top2_byte0(T, msg, k1t)]
        want = sorted([k0t & 255, (k0t & 255) ^ 0x80])
        assert got == want, "top-2 %s, expected the true byte and the true byte with bit 7 flipped: %s" % (got, want)
    return True, "HD model: top-2 = {true byte, true ^ 0x80} on 5/5 keys (bit 7 is invisible)"


TASKS = [Task("T1", "hw8", t1), Task("T2", "corr_cols", t2), Task("T3", "stage-1 CPA recovers k1", t3),
         Task("T4", "stage-2 CPA recovers k0 (carry, low byte first)", t4), Task("T5", "success_rate vs noise and N", t5),
         Task("T6", "min_traces scales with sigma^2", t6), Task("T7", "HD model has a 1-bit ambiguity", t7, stretch=True)]

if __name__ == "__main__":
    main("Lab 3 - Power analysis (CPA)", TASKS, HERE)
