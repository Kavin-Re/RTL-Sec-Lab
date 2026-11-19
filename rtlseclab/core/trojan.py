"""Hardware-trojan simulation: a tiny trigger-counter trojan in the hop engine's output stage, plus statistical detectors.

ORIGIN: copied from FHSS-Link/lab4/silicon/trojan.py (own design, simulation only). Only change: package-relative import.
SIMULATION ONLY. The trojan is an abstract model of our own design (24-bit slot counter + compare + output mux).

Trojan: counts slots since reset; once count >= T (rare trigger) it replaces the channel with probability beta = beta_k/256 using
8 tapped digest bits as its private pseudo-random select ('stuck': replace by a fixed target channel; 'narrow': h -> h mod 6,
i.e. squeeze onto the lowest 6 channels). Before the trigger the output is bit-identical to the clean engine.
Detectors (observer sees only the channel sequence, does NOT know the key or the target):
  * single-window chi-square (window W hops, exact chi2 tail for df=12), threshold set for a given false-alarm probability
  * CUSUM on the window chi-square statistic (tuned for a design bias), threshold calibrated by Monte Carlo on clean data
  * golden reference (RX regenerates the expected hops from the key): first mismatch -- only valid if the trojan is on one side."""
import numpy as np
from math import exp, factorial
from .siphash import siphash24_u64

M = 13
U = np.uint64


class HopEngine:
    def __init__(self, key_k0k1, M=13):
        self.k0, self.k1, self.M = key_k0k1[0], key_k0k1[1], M

    def digest(self, slots):
        return siphash24_u64(self.k0, self.k1, np.asarray(slots, dtype=np.uint64))

    def hops(self, start, n):
        d = self.digest(np.arange(start, start + n, dtype=np.uint64))
        return (d % U(self.M)).astype(np.int64)


class TrojanEngine(HopEngine):
    def __init__(self, key_k0k1, trigger=1 << 20, beta_k=26, mode="stuck", target=0, M=13):
        super().__init__(key_k0k1, M)
        self.trigger, self.beta_k, self.mode, self.target = trigger, beta_k, mode, target

    @property
    def beta(self):
        return self.beta_k / 256.0

    def hops(self, start, n):
        slots = np.arange(start, start + n, dtype=np.uint64)
        d = self.digest(slots)
        h = (d % U(self.M)).astype(np.int64)
        hit = (slots >= U(self.trigger)) & (((d >> U(40)) & U(0xFF)) < U(self.beta_k))
        return np.where(hit, self.target if self.mode == "stuck" else h % 6, h)


def bias_pmf(beta, mode="stuck", target=0, M=13):
    """Per-hop channel pmf after the trigger for an ideal (uniform) clean engine."""
    p = np.full(M, 1.0 / M) * (1 - beta)
    if mode == "stuck":
        p[target] += beta
    else:
        for h in range(M):
            p[h % 6] += beta / M
    return p


def chi2_stat(counts, W, M=13):
    e = W / M
    return ((counts - e) ** 2 / e).sum(-1)


def chi2_sf_even(x, df=12):
    """Exact upper tail of chi-square with even df."""
    k = df // 2; s = sum((x / 2) ** j / factorial(j) for j in range(k))
    return exp(-x / 2) * s


def chi2_threshold(alpha, df=12):
    lo, hi = 0.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if chi2_sf_even(mid, df) > alpha: lo = mid
        else: hi = mid
    return hi


def window_counts(h, W, M=13):
    n = len(h) // W
    h = h[: n * W].reshape(n, W)
    return np.stack([(h == c).sum(1) for c in range(M)], 1)


def cusum_run(X, k, hthr):
    """X: (n_windows,) or (runs, n_windows). Returns index of first alarm (or -1) per run, and the S path."""
    X = np.atleast_2d(X); S = np.zeros(X.shape[0]); first = -np.ones(X.shape[0], dtype=int); path = np.zeros(X.shape)
    for t in range(X.shape[1]):
        S = np.maximum(0, S + X[:, t] - k); path[:, t] = S
        newly = (S >= hthr) & (first < 0); first[newly] = t
    return first, path
