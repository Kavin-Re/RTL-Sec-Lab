"""Auto-grader for Lab 6 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab6_trojan_puf/grader.py [path/to/your_script.py]      (default: starter.py next to this file)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected

EXP = load_expected(HERE)


def band(e, v, what):
    assert e["lo"] <= v <= e["hi"], "%s = %.4g, expected within [%s, %s]" % (what, v, e["lo"], e["hi"])


def t1(m):
    rng = np.random.default_rng(seed(1))
    c = rng.multinomial(500, [1 / 13] * 13, size=50)
    want = ((c - 500 / 13) ** 2 / (500 / 13)).sum(1)
    got = np.asarray(m.chi2_stat(c, 500), dtype=float)
    assert got.shape == (50,) and np.allclose(got, want), "chi2_stat differs from sum((c-E)^2/E)"
    assert abs(float(m.chi2_stat(np.full(13, 100), 1300))) < 1e-9, "uniform counts must give 0"
    from rtlseclab.core import trojan as T
    from rtlseclab.core.siphash import split_key
    X = np.asarray(m.chi2_series(T.HopEngine(split_key(bytes(range(16)))), 500, 20), dtype=float)
    assert X.shape == (20,) and 3 < X.mean() < 25, "chi2_series: shape %s mean %.1f" % (X.shape, X.mean())
    return True, "formula exact; clean series mean %.1f (df = 12)" % X.mean()


def t2(m):
    a, b = float(m.alarm_threshold(1e-3)), float(m.alarm_threshold(0.05))
    band(EXP["T2"][0], a, "threshold(1e-3)"); band(EXP["T2"][1], b, "threshold(0.05)")
    return True, "thresholds %.2f and %.2f" % (a, b)


def t3(m):
    f = float(m.false_alarm_rate(1e-2, 500, 3000, seed(3)))
    band(EXP["T3"][0], f, "false-alarm rate")
    return True, "clean windows above the alpha=1e-2 threshold: %.4f" % f


def t4(m):
    v = [float(m.detect_power(bk, 2000, 40, 1e-3, seed(4))) for bk in (26, 13, 6)]
    for e, x, n in zip(EXP["T4"], v, ("beta 10 %", "beta 5 %", "beta 2.3 %")):
        band(e, x, "detection " + n)
    return True, "per-window detection: 10 %% -> %.2f, 5 %% -> %.2f, 2.3 %% -> %.2f" % tuple(v)


def t5(m):
    seq = [10, 20, 5, 30, 40]
    assert m.cusum_first(seq, 12, 25) == 4 and m.cusum_first(seq, 12, 1000) == -1 and m.cusum_first([0, 0, 40], 12, 20) == 2, "cusum_first wrong (S floors at 0)"
    e = EXP["T5"]
    h = m.calibrate_h(15.0, 500, 100, 300, 0.05, seed(5))
    assert h is not None; band(e[1], h, "calibrated h")
    dc, ds = m.delay_compare(8, 500, 15.0, 40, 1e-3, 100, seed(55))
    band(e[2], dc, "CUSUM delay"); band(e[3], ds / dc, "single/CUSUM delay ratio")
    return True, "h=%s ; delay CUSUM %.1f windows, single window %.1f (x%.1f)" % (h, dc, ds, ds / dc)


def t6(m):
    e = EXP["T6"]
    u = {k: float(m.puf_uniqueness(k)) for k in ("far", "neighbor", "far_planefit")}
    band(e[0], u["far"], "uniqueness far"); band(e[1], u["neighbor"], "uniqueness neighbor"); band(e[1], u["far_planefit"], "uniqueness far_planefit")
    b0, b1 = float(m.puf_ber("far_planefit", 0.0)), float(m.puf_ber("far_planefit", 60.0))
    band(e[2], b0, "BER nominal"); band(e[3], b1, "BER +60C")
    return True, "uniqueness far %.3f / neighbor %.3f / far_planefit %.3f ; BER %.4f nominal, %.3f at +60C" % (u["far"], u["neighbor"], u["far_planefit"], b0, b1)


def t7(m):
    e = EXP["T7"]
    raw, _ = m.regen_rate("raw", 1, 60.0)
    bch, nb = m.regen_rate("bch", 1, 60.0)
    rb, n = m.regen_rate("rep+bch", 3, 60.0)
    band(e[0], raw, "raw rate"); band(e[1], bch, "BCH-only rate"); band(e[2], rb, "rep3+BCH rate")
    assert n == 855, "rep3+BCH should consume 855 response bits, got %s" % n
    return True, "key regenerated at +60C: raw %.2f, BCH %.2f (%d bits), rep3+BCH %.2f (%d bits)" % (raw, bch, nb, rb, n)


TASKS = [Task("T1", "chi2_stat + chi2_series", t1), Task("T2", "alarm_threshold", t2), Task("T3", "false-alarm rate on clean engines", t3),
         Task("T4", "single-window detection power", t4), Task("T5", "CUSUM: calibration and delay", t5),
         Task("T6", "PUF uniqueness and reliability", t6), Task("T7", "fuzzy extractor: key regeneration", t7, stretch=True)]

if __name__ == "__main__":
    main("Lab 6 - Trojan detection and PUF", TASKS, HERE)
