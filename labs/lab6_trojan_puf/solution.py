"""Lab 6 - Trojan detection from the hop sequence, and a ring-oscillator PUF as key source.  SOLUTION.

Own design, simulation only. The trojan is an ABSTRACT model of our own engine (rare trigger counter + output mux that biases the channel);
the PUF is a statistical model (Gaussian process variation + read noise + a layout gradient). Nothing here describes a real chip or a real attack.
The observer sees only the channel sequence and does not know the key or the trojan's target channel.
Run:    python labs/lab6_trojan_puf/solution.py
Grade:  python labs/lab6_trojan_puf/grader.py labs/lab6_trojan_puf/solution.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from rtlseclab.core import trojan as T, puf as P
from rtlseclab.core.siphash import split_key

M = 13


def rand_key(rng):
    return split_key(bytes(rng.integers(0, 256, 16, dtype=np.uint8)))


# ---- Task 1 ---------------------------------------------------------------------------------------------
def chi2_stat(counts, W):
    """Pearson chi-square of channel counts (..., 13) against uniform for windows of W hops: sum (c - W/13)^2 / (W/13) over the last axis."""
    # >>> SOLUTION: e = W / 13 ; return ((counts - e) ** 2 / e).sum(-1)
    e = W / M
    return ((np.asarray(counts) - e) ** 2 / e).sum(-1)
    # <<< SOLUTION


def chi2_series(engine, W, nwin):
    """Chi-square statistic of nwin consecutive windows of W hops from engine.hops(0, nwin*W). Use T.window_counts(h, W) -> (nwin, 13)."""
    # >>> SOLUTION: hops -> window_counts -> chi2_stat
    return chi2_stat(T.window_counts(engine.hops(0, nwin * W), W), W)
    # <<< SOLUTION


# ---- Task 2 ---------------------------------------------------------------------------------------------
def alarm_threshold(alpha):
    """Smallest x with P(chi2_12 > x) <= alpha, by bisection on T.chi2_sf_even(x, 12) (12 degrees of freedom = 13 channels - 1)."""
    # >>> SOLUTION: bisection on [0, 200]
    lo, hi = 0.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if T.chi2_sf_even(mid, 12) > alpha:
            lo = mid
        else:
            hi = mid
    return hi
    # <<< SOLUTION


# ---- Task 3 ---------------------------------------------------------------------------------------------
def false_alarm_rate(alpha, W, nwin, seed):
    """Fraction of CLEAN windows above alarm_threshold(alpha). rng = default_rng(seed); key = rand_key(rng); engine = T.HopEngine(key)."""
    # >>> SOLUTION: chi2_series on a clean engine, mean of (X > thr)
    rng = np.random.default_rng(seed)
    X = chi2_series(T.HopEngine(rand_key(rng)), W, nwin)
    return float((X > alarm_threshold(alpha)).mean())
    # <<< SOLUTION


# ---- Task 4 ---------------------------------------------------------------------------------------------
def detect_power(beta_k, W, nwin, alpha, seed, runs=20):
    """Fraction of post-trigger windows that raise the single-window alarm. For each of `runs` runs (rng = default_rng(seed), a fresh key per run):
    engine = T.TrojanEngine(key, trigger=nwin*W, beta_k=beta_k)  (bias beta = beta_k/256 after slot nwin*W, mode 'stuck'), take chi2_series over 2*nwin windows
    and look only at windows nwin..2*nwin-1. Return the mean fraction over runs."""
    # >>> SOLUTION: loop runs, compare the second half of the series with alarm_threshold(alpha)
    rng = np.random.default_rng(seed)
    thr = alarm_threshold(alpha)
    fr = []
    for _ in range(runs):
        eng = T.TrojanEngine(rand_key(rng), trigger=nwin * W, beta_k=beta_k)
        X = chi2_series(eng, W, 2 * nwin)
        fr.append((X[nwin:] > thr).mean())
    return float(np.mean(fr))
    # <<< SOLUTION


# ---- Task 5 ---------------------------------------------------------------------------------------------
def cusum_first(X, k, h):
    """One-sided CUSUM: S_0 = 0, S_t = max(0, S_{t-1} + X_t - k). Return the index of the first t with S_t >= h, or -1."""
    # >>> SOLUTION: running sum with floor at zero
    S = 0.0
    for t, x in enumerate(X):
        S = max(0.0, S + float(x) - k)
        if S >= h:
            return t
    return -1
    # <<< SOLUTION


def calibrate_h(k, W, runs, nwin, target_far, seed, grid=tuple(range(20, 101, 10))):
    """Smallest h in `grid` for which the fraction of CLEAN runs (each: fresh key, chi2_series(HopEngine, W, nwin), rng = default_rng(seed)) that ever alarm is <= target_far."""
    # >>> SOLUTION: simulate the clean series once, scan the grid
    rng = np.random.default_rng(seed)
    Xs = [chi2_series(T.HopEngine(rand_key(rng)), W, nwin) for _ in range(runs)]
    for h in grid:
        if np.mean([cusum_first(X, k, h) >= 0 for X in Xs]) <= target_far:
            return h
    return None
    # <<< SOLUTION


def delay_compare(beta_k, W, k, h, alpha, runs, seed, pre=100, post=300):
    """Mean detection delay in windows after the trigger, for CUSUM (k, h) and for the single-window alarm (alpha). Each run: fresh key, trojan with
    trigger = pre*W, chi2_series over pre+post windows, look at windows from `pre` on. A run that never alarms counts as `post`. Return (cusum, single)."""
    # >>> SOLUTION: delays from cusum_first / first X > thr on X[pre:]
    rng = np.random.default_rng(seed)
    thr = alarm_threshold(alpha)
    dc, ds = [], []
    for _ in range(runs):
        X = chi2_series(T.TrojanEngine(rand_key(rng), trigger=pre * W, beta_k=beta_k), W, pre + post)[pre:]
        c = cusum_first(X, k, h)
        dc.append(post if c < 0 else c)
        idx = np.flatnonzero(X > thr)
        ds.append(post if len(idx) == 0 else int(idx[0]))
    return float(np.mean(dc)), float(np.mean(ds))
    # <<< SOLUTION


# ---- Task 6 ---------------------------------------------------------------------------------------------
def puf_uniqueness(kind, chips=64, seed=3):
    """Mean fractional Hamming distance between the (noise-free-ish) enrolment responses of different chips.
    puf = P.ROArray(chips, rng=np.random.default_rng(seed)); ref = P.enrol_reference(puf, kind). Ideal: 0.5. kind in 'far', 'neighbor', 'far_planefit'."""
    # >>> SOLUTION: all pairwise HDs of the rows of ref, mean over pairs
    puf = P.ROArray(chips, rng=np.random.default_rng(seed))
    ref = P.enrol_reference(puf, kind).astype(float)
    hd = ref @ (1 - ref).T + (1 - ref) @ ref.T
    iu = np.triu_indices(chips, 1)
    return float(hd[iu].mean() / ref.shape[1])
    # <<< SOLUTION


def puf_ber(kind, dT, chips=64, seed=3, reads=5):
    """Mean bit error rate of fresh reads (temperature offset dT) against the enrolment reference (enrol_reference at dT=0), same construction as above."""
    # >>> SOLUTION: average (read != ref) over reads, chips and bits
    puf = P.ROArray(chips, rng=np.random.default_rng(seed))
    ref = P.enrol_reference(puf, kind)
    return float(np.mean([(P.get_response(puf, kind, dT=dT) != ref).mean() for _ in range(reads)]))
    # <<< SOLUTION


# ---- Task 7 ---------------------------------------------------------------------------------------------
def regen_rate(mode, R, dT, chips=200, seed=3):
    """Fraction of chips whose 128-bit key is regenerated exactly. puf = P.ROArray(chips, rng=default_rng(seed)); kind 'far_planefit';
    ref = P.enrol_reference(puf, kind); fe = P.FuzzyExtractor(mode, R=R); helper, secret = fe.enrol(ref, np.random.default_rng(seed + 1));
    resp = P.get_response(puf, kind, dT=dT); out = fe.regenerate(resp, helper). Success = out equals secret in every position of a row.
    Return (rate, fe.n_code) - n_code is how many PUF response bits the scheme consumes."""
    # >>> SOLUTION: as described
    puf = P.ROArray(chips, rng=np.random.default_rng(seed))
    ref = P.enrol_reference(puf, "far_planefit")
    fe = P.FuzzyExtractor(mode, R=R)
    helper, secret = fe.enrol(ref, np.random.default_rng(seed + 1))
    out = fe.regenerate(P.get_response(puf, "far_planefit", dT=dT), helper)
    return float((out == secret).all(1).mean()), int(fe.n_code)
    # <<< SOLUTION


if __name__ == "__main__":
    W = 2000
    print("threshold alpha=1e-3: %.2f ; clean false-alarm rate (alpha=1e-2, W=500): %.4f" % (alarm_threshold(1e-3), false_alarm_rate(1e-2, 500, 3000, 1)))
    for bk in (26, 13, 6):
        print("trojan beta=%.3f: per-window detection %.2f" % (bk / 256, detect_power(bk, W, 40, 1e-3, 2)))
    k = 15.0
    h = calibrate_h(k, 500, 100, 300, 0.05, 3)
    print("CUSUM h for 5%% false-alarm runs: %s ; mean delay (cusum, single window) for beta=8/256: %s" % (h, delay_compare(8, 500, k, h, 1e-3, 40, 4)))
    for kind in ("far", "neighbor", "far_planefit"):
        print("PUF %-13s uniqueness %.3f  BER nominal %.4f  BER +60C %.4f" % (kind, puf_uniqueness(kind), puf_ber(kind, 0.0), puf_ber(kind, 60.0)))
    for mode, R in (("raw", 1), ("rep", 5), ("bch", 1), ("rep+bch", 3)):
        print("key regen %-8s R=%d: nominal %s, +60C %s" % (mode, R, regen_rate(mode, R, 0.0), regen_rate(mode, R, 60.0)))
