"""Hop-schedule generators of the 'PRNG graveyard' and the attacks on them (own-link simulation, no radio).

ORIGIN: copied and adapted from FHSS-Link/lab6/exp5_prng_graveyard.py (own design, simulation only). Plotting and the
experiment driver were removed; `untemper`/`mt_clone` are kept as REFERENCE solutions for lab 2 (the student starter has them blanked).
Kerckhoffs: the attacker knows the algorithm, not the seed/key. Observed = the channel numbers of past hops.
 - LCG 24-bit (a=1140671485, c=12820163, m=2^24), hop = (x>>8) mod 13. Attack: candidate-set filtering over all 2^24 states.
 - xorshift32, hop = x & 15 on a 16-channel plan (4 bits/hop). Attack: GF(2)-linear, solve a linear system for the 32 state bits.
 - MT19937, 624 consecutive FULL 32-bit outputs leaked: untemper, clone the state, predict (checked against Python's random).
 - HMAC-SHA256 (keyed PRF): attacker uses a generic predictor; accuracy stays at chance 1/13."""
import hmac, hashlib, random
import numpy as np

A24, C24, M24 = 1140671485, 12820163, 1 << 24


def lcg_step(x):
    return (A24 * x + C24) % M24


def lcg_hop(x):
    return (x >> 8) % 13


def lcg_stream(x, n):
    out = []
    for _ in range(n):
        x = lcg_step(x)
        out.append(lcg_hop(x))
    return out


def lcg_attack(obs):
    """obs = hops h1..hn where h_i = hop(x_i), x_i = step(x_{i-1}). Returns (candidates for x_k, k = hops used)."""
    cand = np.arange(M24, dtype=np.uint64)
    cand = cand[((cand >> np.uint64(8)) % np.uint64(13)) == obs[0]]
    used = 1
    for i in range(1, len(obs)):
        if len(cand) == 1:
            break
        cand = (np.uint64(A24) * cand + np.uint64(C24)) % np.uint64(M24)
        cand = cand[((cand >> np.uint64(8)) % np.uint64(13)) == obs[i]]
        used = i + 1
    return cand, used


def xs32(x):
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


def xorshift_attack(obs):
    """obs = low 4 bits of successive outputs o_1..o_n (o_i = state after i steps). Unknown x0 (32 bits). Output bits are
    linear in x0 over GF(2). Returns (x0 or None, rank)."""
    Tm = [xs32(1 << j) for j in range(32)]                 # Tm[j] = T(e_j) as int

    def apply(vec):                                         # vec[i] = bitmask over x0 bits that equal state bit i
        new = [0] * 32
        for j in range(32):
            tj = Tm[j]
            for i in range(32):
                if (tj >> i) & 1:
                    new[i] ^= vec[j]
        return new
    rows = [1 << i for i in range(32)]
    eqs = []
    for o in obs:
        rows = apply(rows)
        for b in range(4):
            eqs.append((rows[b], (o >> b) & 1))
    piv = {}
    for m, v in eqs:
        for p, (pm, pv) in sorted(piv.items(), reverse=True):
            if (m >> p) & 1:
                m ^= pm; v ^= pv
        if m:
            p = m.bit_length() - 1
            piv[p] = (m, v)
    if len(piv) < 32:
        return None, len(piv)
    sol = 0
    for p in sorted(piv):
        m, v = piv[p]
        rest = m & ~(1 << p)
        val = v ^ (bin(rest & sol).count("1") & 1)
        if val:
            sol |= 1 << p
    return sol, 32


def temper(y):
    """MT19937 output tempering (forward)."""
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    return y & 0xFFFFFFFF


def untemper(y):
    """Inverse of `temper` (reference solution)."""
    y ^= y >> 18
    y ^= (y << 15) & 0xEFC60000
    t = y
    for _ in range(5):
        t = y ^ ((t << 7) & 0x9D2C5680)
    y = t
    t = y
    for _ in range(3):
        t = y ^ (t >> 11)
    return t & 0xFFFFFFFF


def mt_clone(outputs624, untemper_fn=untemper):
    """Build a random.Random whose future outputs equal those of the generator that produced `outputs624`."""
    r = random.Random()
    r.setstate((3, tuple(untemper_fn(o) for o in outputs624) + (624,), None))
    return r


def hmac_hop(key, n):
    return int.from_bytes(hmac.new(key, n.to_bytes(8, "big"), hashlib.sha256).digest()[:4], "big") % 13
