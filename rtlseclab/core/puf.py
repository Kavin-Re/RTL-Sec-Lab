"""Ring-oscillator PUF simulation + code-offset fuzzy extractor (repetition + BCH(15,7,t=2) lite) -> 128-bit hop key.

ORIGIN: copied from FHSS-Link/lab4/silicon/puf.py (own design, simulation only), unchanged except this header.
SIMULATION ONLY of our own assumed model: RO frequency = common plane (systematic layout gradient) + per-RO Gaussian process
variation, read noise per measurement, per-RO temperature coefficient (independent part) for hot/cold corners.
Units: process-variation sigma = 1. NOT modelled: aging, voltage, supply noise coupling, RO locking, spatial correlation beyond a plane,
helper-data manipulation / fault attacks, side channels of the PUF, ML modelling, real measurement counters (quantisation)."""
import hashlib
import numpy as np


class ROArray:
    def __init__(self, n_chips, rows=32, cols=64, grad=3.0, sigma_noise=0.05, sigma_slope=0.0025, rng=None):
        self.rng = rng or np.random.default_rng(0)
        self.rows, self.cols, self.n = rows, cols, rows * cols
        self.n_chips, self.sigma_noise = n_chips, sigma_noise
        r, c = np.divmod(np.arange(self.n), cols)
        self.plane = grad * (c / (cols - 1) - 0.5) + 0.3 * grad * (r / (rows - 1) - 0.5)       # same layout gradient on every chip
        self.static = self.plane[None, :] + self.rng.normal(0, 1, (n_chips, self.n))
        self.slope = self.rng.normal(0, sigma_slope, (n_chips, self.n))                        # per-RO temperature coefficient (per deg C)
        self.design = np.stack([np.ones(self.n), c / cols, r / rows], 1)

    def read(self, dT=0.0, sigma_noise=None):
        sn = self.sigma_noise if sigma_noise is None else sigma_noise
        return self.static + self.slope * dT + self.rng.normal(0, sn, self.static.shape)

    def planefit_remove(self, F):
        coef = np.linalg.pinv(self.design) @ F.T            # (3, chips)
        return F - (self.design @ coef).T


def pairings(n, cols, kind):
    idx = np.arange(n)
    if kind in ("far", "far_planefit"):
        a = idx[(idx % cols) < cols // 2]; return a, a + cols // 2
    if kind == "neighbor":
        a = idx[0::2]; return a, a + 1
    raise ValueError(kind)


def response(F, pair):
    a, b = pair
    return (F[:, a] > F[:, b]).astype(np.uint8)


def get_response(puf, kind, dT=0.0, sigma_noise=None):
    F = puf.read(dT, sigma_noise)
    if kind.endswith("planefit"): F = puf.planefit_remove(F)
    return response(F, pairings(puf.n, puf.cols, kind))


def enrol_reference(puf, kind, reads=15):
    s = sum(get_response(puf, kind).astype(int) for _ in range(reads))
    return (s * 2 > reads).astype(np.uint8)


def ber_theory(sigma_noise, sigma_proc=1.0):
    """P(a pair bit flips between the ideal and one noisy read): Pr[sign change] = arctan(sn/sp)/pi (independent Gaussian pair diff)."""
    return float(np.arctan(sigma_noise / sigma_proc) / np.pi)


def metrics(ref, reads_by_cond):
    """ref: (chips, bits) enrolment bits; reads_by_cond: {name: (R, chips, bits)}"""
    nch = ref.shape[0]
    ones = ref.astype(np.float64)
    hd = ones @ (1 - ones).T + (1 - ones) @ ones.T
    iu = np.triu_indices(nch, 1)
    inter = hd[iu] / ref.shape[1]
    p = ref.mean(0)
    Hb = -(np.where(p > 0, p * np.log2(np.maximum(p, 1e-12)), 0) + np.where(p < 1, (1 - p) * np.log2(np.maximum(1 - p, 1e-12)), 0))
    out = dict(uniqueness_mean=float(inter.mean()), uniqueness_std=float(inter.std()), uniqueness_min=float(inter.min()), uniqueness_max=float(inter.max()),
               bit_aliasing_mean_abs_dev=float(np.abs(p - 0.5).mean()), bit_aliasing_max_abs_dev=float(np.abs(p - 0.5).max()),
               frac_bits_stuck_gt90pct=float(((p < 0.1) | (p > 0.9)).mean()), uniformity_mean=float(ref.mean()),
               entropy_sum_indep_upper_bound_bits=float(Hb.sum()), n_bits=int(ref.shape[1]), n_chips=int(nch))
    for name, rd in reads_by_cond.items():
        ber = (rd != ref[None]).mean(2)                     # (R, chips)
        out[f"ber_{name}_mean"] = float(ber.mean()); out[f"ber_{name}_worst_chip"] = float(ber.mean(0).max())
        out[f"reliability_{name}_pct"] = float(100 * (1 - ber.mean()))
    return out, inter, p


# -------------------- BCH(15,7,t=2), systematic, syndrome-table decoding --------------------
G = 0x1D1       # x^8+x^7+x^6+x^4+1


def _polymod(x, g=G):
    gd = g.bit_length() - 1
    while x.bit_length() - 1 >= gd:
        x ^= g << (x.bit_length() - 1 - gd)
    return x


_G_ROWS = np.array([[((1 << (8 + i)) | _polymod(1 << (8 + i))) >> j & 1 for j in range(15)] for i in range(7)], dtype=np.uint8)
_SYN_POS = [_polymod(1 << j) for j in range(15)]
_SYNMAT = np.array([[(s >> b) & 1 for b in range(8)] for s in _SYN_POS], dtype=np.uint8)
_ERR = -np.ones(256, dtype=np.int64); _ERR[0] = 0
for _i in range(15):
    s = _SYN_POS[_i]; assert _ERR[s] == -1; _ERR[s] = 1 << _i
for _i in range(15):
    for _j in range(_i + 1, 15):
        s = _SYN_POS[_i] ^ _SYN_POS[_j]; assert _ERR[s] == -1, "t=2 syndromes must be unique"; _ERR[s] = (1 << _i) | (1 << _j)


def bch_encode(msg):
    """msg (N,7) bits -> codeword (N,15)."""
    return (msg.astype(np.int64) @ _G_ROWS % 2).astype(np.uint8)


def bch_decode(r):
    """r (N,15) -> (msg (N,7), ok_mask (N,)) ; ok False if syndrome is uncorrectable (>2 errors detected)."""
    syn = (r.astype(np.int64) @ _SYNMAT % 2) @ (1 << np.arange(8))
    e = _ERR[syn]
    ok = e >= 0
    ebits = ((np.where(ok, e, 0)[:, None] >> np.arange(15)[None, :]) & 1).astype(np.uint8)
    c = r ^ ebits
    return c[:, 8:15], ok


class FuzzyExtractor:
    """Code-offset construction. mode: 'raw' (no ECC), 'rep' (R-fold repetition, majority), 'bch', 'rep+bch'."""
    def __init__(self, mode, R=1, nblocks=19, key_bits=128):
        self.mode, self.R, self.nb, self.kb = mode, R, nblocks, key_bits
        self.k_secret = key_bits if mode in ("raw", "rep") else 7 * nblocks
        self.n_code = (key_bits * R if mode == "rep" else key_bits if mode == "raw" else 15 * nblocks * (R if mode == "rep+bch" else 1))

    def encode(self, s):
        if self.mode == "raw": return s
        if self.mode == "rep": return np.repeat(s, self.R, axis=1)
        c = bch_encode(s.reshape(len(s), self.nb, 7).reshape(-1, 7)).reshape(len(s), -1)
        return np.repeat(c, self.R, axis=1) if self.mode == "rep+bch" else c

    def decode(self, c):
        n = len(c)
        if self.mode == "raw": return c
        if self.mode in ("rep", "rep+bch"):
            c = (c.reshape(n, -1, self.R).sum(2) * 2 > self.R).astype(np.uint8)
            if self.mode == "rep": return c
        m, _ = bch_decode(c.reshape(-1, 15))
        return m.reshape(n, -1)

    @staticmethod
    def key_from_secret(s_row):
        return hashlib.sha256(np.packbits(s_row).tobytes()).digest()[:16]

    def enrol(self, ref_resp, rng):
        """ref_resp (chips, bits>=n_code). Returns helper (chips,n_code), secrets (chips,k)."""
        s = rng.integers(0, 2, (ref_resp.shape[0], self.k_secret), dtype=np.uint8)     # secret from an on-chip TRNG (assumed)
        helper = self.encode(s) ^ ref_resp[:, : self.n_code]
        return helper, s

    def regenerate(self, resp, helper):
        return self.decode(helper ^ resp[:, : self.n_code])
