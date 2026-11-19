"""Simulated power side-channel on the SipHash-2-4 hop engine (ASSUMED leakage model, no real device).

ORIGIN: copied and adapted from FHSS-Link/lab4/silicon/sidechannel.py (own design, simulation only).
Changes: package-relative imports; the CPA reference code is unchanged in behaviour.

Leakage points modelled (first SipRound, 8-byte counter message m):
  stage 1:  v3 = k1 ^ C3 ^ m              (key whitening of the message)      -> leaks HW(byte_i(v3))
  stage 2:  s  = v2 + v3, v2 = k0 ^ C2    (first 64-bit modular addition)     -> leaks HW(byte_i(s))  or HD(v2_i -> s_i)
Each trace sample = Hamming weight (or distance) of one byte of the value + N(0, sigma^2). 16 samples per trace.
Attack: divide and conquer CPA. Stage 1 recovers k1 byte by byte (256 hypotheses each), stage 2 then recovers k0 byte by byte,
low byte first, using the recovered k1 and the carry from already-recovered lower bytes.

Masked version: first-order boolean masking with 2 shares and a fresh 64-bit mask per execution. Addition of boolean shares
uses a secure ripple adder built from ISW AND gadgets (Goubin/Coron style). Each share byte leaks separately (own sample).
NOT modelled: glitches/early propagation, routing/coupling, share transitions in registers (except one explicit control),
the ISW internal intermediates, desynchronised/jittered traces, acquisition limits."""
import numpy as np
from .siphash import C2, C3, MASK, split_key

U = np.uint64
HW = np.array([bin(i).count("1") for i in range(256)], dtype=np.float32)


def bytes_of(x):
    """(N,) uint64 -> (N,8) uint8, byte 0 = least significant."""
    return np.ascontiguousarray(np.asarray(x, dtype=np.uint64).astype("<u8")).view(np.uint8).reshape(-1, 8)


def rand64(rng, n):
    return rng.integers(0, 2**63, n, dtype=np.uint64) * U(2) + rng.integers(0, 2, n, dtype=np.uint64)


# ---------------- unmasked leakage ----------------
def leak_unmasked(key, m, sigma, rng, model2="HW"):
    """Returns traces (N,16): cols 0..7 stage-1 bytes, cols 8..15 stage-2 bytes."""
    k0, k1 = split_key(key)
    with np.errstate(over="ignore"):
        v3 = U(k1 ^ C3) ^ m
        v2 = np.full(len(m), U(k0 ^ C2), dtype=np.uint64)
        s = v2 + v3
    L1 = HW[bytes_of(v3)]
    L2 = HW[bytes_of(s)] if model2 == "HW" else HW[bytes_of(v2 ^ s)]
    return np.concatenate([L1, L2], 1) + rng.normal(0, sigma, (len(m), 16)).astype(np.float32)


# ---------------- masked leakage ----------------
def secand(a0, a1, b0, b1, rng):
    """ISW AND gadget on 2 boolean shares (word-wise)."""
    r = rand64(rng, len(a0))
    c0 = (a0 & b0) ^ r
    c1 = (a1 & b1) ^ (r ^ (a0 & b1)) ^ (a1 & b0)
    return c0, c1


def secadd(x0, x1, y0, y1, rng):
    """Secure addition mod 2^64 of boolean-shared x, y. Returns shares of x+y."""
    p0, p1 = x0 ^ y0, x1 ^ y1
    g0, g1 = secand(x0, x1, y0, y1, rng)
    c0 = np.zeros_like(x0); c1 = np.zeros_like(x0)
    for _ in range(64):                      # carry into bit i settles after i iterations
        t0, t1 = secand(p0, p1, c0, c1, rng)
        c0 = (g0 ^ t0) << U(1); c1 = (g1 ^ t1) << U(1)
    return p0 ^ c0, p1 ^ c1


def shares_masked(key, m, rng, mask_on=True):
    """Return (v3 shares), (sum shares) as uint64 arrays. mask_on=False -> r=0 (control: masking disabled)."""
    k0, k1 = split_key(key)
    n = len(m)
    r3 = rand64(rng, n) if mask_on else np.zeros(n, dtype=np.uint64)
    r2 = rand64(rng, n) if mask_on else np.zeros(n, dtype=np.uint64)
    with np.errstate(over="ignore"):
        v3s0 = (U(k1 ^ C3) ^ r3) ^ m          # message is XORed into share 0 only
        v3s1 = r3
        v2s0 = np.full(n, U(k0 ^ C2), dtype=np.uint64) ^ r2
        v2s1 = r2
        s0, s1 = secadd(v2s0, v2s1, v3s0, v3s1, rng)
    return (v3s0, v3s1), (s0, s1)


def leak_masked(key, m, sigma, rng, mask_on=True, extra_hd=False):
    """traces (N,S,16): axis1 = share index (own time sample each); cols 0..7 v3 bytes, 8..15 sum bytes.
    extra_hd=True adds a third row = HW(s0^s1 byte), i.e. a register that is overwritten share-by-share (HD leak)."""
    (a0, a1), (b0, b1) = shares_masked(key, m, rng, mask_on)
    rows = [np.concatenate([HW[bytes_of(a)], HW[bytes_of(b)]], 1) for a, b in ((a0, b0), (a1, b1))]
    if extra_hd:
        rows.append(np.concatenate([HW[bytes_of(a0 ^ a1)], HW[bytes_of(b0 ^ b1)]], 1))
    T = np.stack(rows, 1)
    return T + rng.normal(0, sigma, T.shape).astype(np.float32)


# ---------------- CPA reference ----------------
def corr_scores(H, l):
    """Pearson correlation of each column of H (N,K) with vector l (N,). Zero-variance -> 0."""
    Hc = H - H.mean(0, keepdims=True)
    lc = l - l.mean()
    den = np.sqrt((Hc ** 2).sum(0)) * np.sqrt((lc ** 2).sum())
    num = Hc.T @ lc
    return np.where(den > 1e-9, num / np.maximum(den, 1e-9), 0.0)


HYP = np.arange(256, dtype=np.uint8)


def stage1_scores(l, mb, byte):
    return corr_scores(HW[mb[:, byte][:, None] ^ HYP[None, :] ^ np.uint8((C3 >> (8 * byte)) & 255)], l)


def carry_in(k0_known_low, v3, byte):
    """carry into byte position `byte` of (v2 + v3) given the recovered low bytes of k0 (python int)."""
    if byte == 0:
        return np.zeros(len(v3), dtype=np.uint8)
    mask = (1 << (8 * byte)) - 1
    lo2 = (k0_known_low ^ C2) & mask
    with np.errstate(over="ignore"):
        tot = U(lo2) + (v3 & U(mask))
    return ((tot >> U(8 * byte)) & U(1)).astype(np.uint8)


def stage2_scores(l, v3b_byte, carry, byte, model="HW"):
    old = HYP ^ np.uint8((C2 >> (8 * byte)) & 255)                       # (256,)
    s = (old[None, :].astype(np.uint16) + v3b_byte[:, None] + carry[:, None]) & 255
    H = HW[s] if model == "HW" else HW[(old[None, :] ^ s).astype(np.uint8)]
    return corr_scores(H, l)


def cpa_attack(traces, m, model2="HW", k1_oracle=None, sign=+1):
    """Reference two-stage first-order CPA on traces (N,16). Returns (k0_est, k1_est) python ints."""
    mb = bytes_of(m)
    k1 = 0
    for b in range(8):
        sc = sign * stage1_scores(traces[:, b], mb, b)
        k1 |= int(np.argmax(sc)) << (8 * b)
    k1u = k1 if k1_oracle is None else k1_oracle
    with np.errstate(over="ignore"):
        v3 = U(k1u ^ C3) ^ m
    v3b = bytes_of(v3)
    k0 = 0
    for b in range(8):
        carry = carry_in(k0, v3, b)
        sc = sign * stage2_scores(traces[:, 8 + b], v3b[:, b], carry, b, model2)
        k0 |= int(np.argmax(sc)) << (8 * b)
    return k0, k1


def cpa_firstorder_masked(T, m):
    """First-order attacker on masked traces T (N,S,16), stage 1: tries every share-sample as the leakage point and keeps the
    candidate whose peak |correlation| is largest. Returns k1 estimate."""
    mb = bytes_of(m)
    S = T.shape[1]
    k1 = 0
    for b in range(8):
        best, arg = -1, 0
        for s in range(S):
            sc = stage1_scores(T[:, s, b], mb, b)
            if sc.max() > best:
                best, arg = sc.max(), int(np.argmax(sc))
        k1 |= arg << (8 * b)
    return k1


def cpa_secondorder_masked(T, m):
    """Second-order attack on stage 1 of the 2-share masked traces: centred product of the two share samples,
    correlated (negatively; E[(HW(x^r)-4)(HW(r)-4)] = -(HW(x)-4)/2) with HW(hypothesis)."""
    mb = bytes_of(m); k1 = 0
    for b in range(8):
        a, c = T[:, 0, b], T[:, 1, b]
        prod = (a - a.mean()) * (c - c.mean())
        sc = -stage1_scores(prod, mb, b)
        k1 |= int(np.argmax(sc)) << (8 * b)
    return k1


def byte_hits(est, true, nbytes=8):
    return sum(((est >> (8 * i)) & 255) == ((true >> (8 * i)) & 255) for i in range(nbytes))


def welch_t(a, b):
    ma, mb_ = a.mean(0), b.mean(0); va, vb = a.var(0, ddof=1), b.var(0, ddof=1)
    return (ma - mb_) / np.sqrt(va / len(a) + vb / len(b) + 1e-12)
