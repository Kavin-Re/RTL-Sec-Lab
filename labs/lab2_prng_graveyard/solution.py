"""Lab 2 - The PRNG graveyard: why a hop schedule must not come from an ordinary PRNG.  SOLUTION.

Own-link simulation, no radio. Kerckhoffs: the attacker knows the algorithm, not the seed. Observed = channel numbers of past hops.
Generators: LCG-24 (hop = (x >> 8) mod 13), xorshift32 (hop = x & 15 on 16 channels), MT19937 (full 32-bit outputs leaked), HMAC-SHA256.
Run:    python labs/lab2_prng_graveyard/solution.py
Grade:  python labs/lab2_prng_graveyard/grader.py labs/lab2_prng_graveyard/solution.py
"""
import os, sys, random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from rtlseclab.core.prng import (A24, C24, M24, lcg_stream, lcg_hop, xs32, temper, hmac_hop)   # generators are given
from rtlseclab.core.lfsr import lfsr_schedule, keyed_schedule


# ---- Task 1: LCG-24 by candidate elimination ------------------------------------------------------------
def lcg_filter(cand, ch):
    """cand: uint64 array of candidate states BEFORE the hop. Step each candidate (x -> (A24*x + C24) mod 2^24), then keep the
    ones whose hop ((x >> 8) % 13) equals ch. Return the surviving candidates (states AFTER the hop)."""
    # >>> SOLUTION: vectorised with numpy.uint64 (a python loop over 16.7 M states is far too slow)
    nxt = (np.uint64(A24) * cand + np.uint64(C24)) % np.uint64(M24)
    return nxt[((nxt >> np.uint64(8)) % np.uint64(13)) == ch]
    # <<< SOLUTION


def break_lcg(obs):
    """Return (state after the last used hop, hops used) from observed hops h1.. (h1 is the hop of the FIRST stepped state).
    Start from all 2^24 states, filter once per hop, stop when exactly one candidate is left."""
    # >>> SOLUTION: cand = np.arange(2**24, dtype=np.uint64); loop lcg_filter over obs until len(cand) == 1
    cand = np.arange(M24, dtype=np.uint64)
    for i, ch in enumerate(obs):
        cand = lcg_filter(cand, int(ch))
        if len(cand) == 1:
            return int(cand[0]), i + 1
        if len(cand) == 0:
            return None, i + 1
    return None, len(obs)
    # <<< SOLUTION


# NOTE: lcg_filter steps BEFORE it tests, so the first filter call needs the state *before* h1. Starting from every state
# in 0..2^24-1 covers that, because the step is a bijection on 2^24 values.


# ---- Task 2: Mersenne Twister state cloning -------------------------------------------------------------
def untemper(y):
    """Invert MT19937's output tempering (core.prng.temper is the forward function; read it first).
    The four steps are y ^= y >> 11 ; y ^= (y << 7) & 0x9D2C5680 ; y ^= (y << 15) & 0xEFC60000 ; y ^= y >> 18."""
    # >>> SOLUTION: undo them in reverse order; a shift by >= 16 undoes itself, the others need an iteration (5x for <<7, 3x for >>11)
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
    # <<< SOLUTION


def mt_clone(outputs624):
    """From 624 consecutive FULL 32-bit outputs of a Python `random.Random`, return a Random that continues the same stream.
    random.Random.setstate takes (3, tuple_of_624_state_words + (index,), None) ; after 624 outputs the index is 624."""
    # >>> SOLUTION: state words = untemper of every output; index 624 means 'generate a new block before the next output'
    r = random.Random()
    r.setstate((3, tuple(untemper(o) for o in outputs624) + (624,), None))
    return r
    # <<< SOLUTION


# ---- Task 3: xorshift32 is linear over GF(2) --------------------------------------------------------------
def xorshift_equations(obs):
    """GIVEN. obs = low 4 bits of successive xorshift32 outputs. Every output bit is an XOR of initial-state bits, so each observed
    bit gives one equation  (mask over the 32 unknown bits) . x0 = bit.  Returns a list of (mask, bit)."""
    Tm = [xs32(1 << j) for j in range(32)]
    rows = [1 << i for i in range(32)]            # state bit i expressed as a mask over x0 bits
    eqs = []
    for o in obs:
        new = [0] * 32
        for j in range(32):
            for i in range(32):
                if (Tm[j] >> i) & 1:
                    new[i] ^= rows[j]
        rows = new
        for b in range(4):
            eqs.append((rows[b], (o >> b) & 1))
    return eqs


def solve_gf2(eqs, nvars=32):
    """Solve a linear system over GF(2). eqs = list of (mask, rhs): bit j of mask says 'variable j appears', rhs is 0/1.
    Return the solution as an int (bit j = variable j) if the system has a UNIQUE solution, else None."""
    # >>> SOLUTION: Gaussian elimination with python ints as bit-vectors: keep one pivot row per leading bit, reduce each new row
    piv = {}                                       # leading bit -> (mask, rhs)
    for m, v in eqs:
        for p in sorted(piv, reverse=True):
            if (m >> p) & 1:
                m ^= piv[p][0]; v ^= piv[p][1]
        if m:
            piv[m.bit_length() - 1] = (m, v)
        elif v:
            return None                            # 0 = 1: inconsistent
    if len(piv) < nvars:
        return None
    sol = 0
    for p in sorted(piv):                          # ascending: lower variables are known when a row is back-substituted
        m, v = piv[p]
        if v ^ (bin((m & ~(1 << p)) & sol).count("1") & 1):
            sol |= 1 << p
    return sol
    # <<< SOLUTION


def break_xorshift(obs):
    """GIVEN glue: grow the observation window until the system has a unique solution. Returns (x0, hops_used) or (None, len(obs))."""
    for n in range(1, len(obs) + 1):
        x0 = solve_gf2(xorshift_equations(obs[:n]))
        if x0 is not None:
            return x0, n
    return None, len(obs)


# ---- Task 4: a generic predictor as an unpredictability detector ------------------------------------------
def context_predictor_accuracy(seq, order=3, M=13):
    """Adaptive order-`order` context predictor: for every position i >= order, look at the previous `order` hops, predict the hop
    that most often followed this context so far (only if the context was seen before; otherwise count a miss), then update the
    counts. Return hits / (len(seq) - order). Chance level is 1/M."""
    # >>> SOLUTION: dict from context tuple -> np.zeros(M) counts ; predict argmax if counts.max() > 0
    ctx = {}
    hits = 0
    for i in range(order, len(seq)):
        c = ctx.setdefault(tuple(seq[i - order:i]), np.zeros(M))
        if c.max() > 0 and int(c.argmax()) == seq[i]:
            hits += 1
        c[seq[i]] += 1
    return hits / (len(seq) - order)
    # <<< SOLUTION


# ---- Task 5: the graveyard table -------------------------------------------------------------------------
def graveyard_table(seed=0):
    """Hops an attacker must observe before every future hop is predicted (mean over a few random seeds), using your functions."""
    rng = random.Random(seed)
    lcg, xs = [], []
    for _ in range(3):
        st = lcg_stream(rng.randrange(M24), 20)
        lcg.append(break_lcg(st)[1])
    for _ in range(3):
        x = rng.randrange(1, 1 << 32); o = []
        for _ in range(30):
            x = xs32(x); o.append(x & 15)
        xs.append(break_xorshift(o)[1])
    return {"LCG24": float(np.mean(lcg)), "xorshift32": float(np.mean(xs)), "MT19937 (32-bit leak)": 624,
            "SipHash / HMAC": None}


def demo():
    print("LCG24: break a 20-hop stream")
    st = lcg_stream(1234567, 20)
    s, used = break_lcg(st)
    x = s
    print("  state after hop %d = %s ; next 5 predicted %s ; true %s" % (used, s, [lcg_hop(x := (A24 * x + C24) % M24) for _ in range(5)], lcg_stream(1234567, used + 5)[used:]))
    r = random.Random(42); outs = [r.getrandbits(32) for _ in range(624)]
    c = mt_clone(outs)
    print("MT19937: clone predicts next 3 outputs", [c.getrandbits(32) for _ in range(3)], "true", [r.getrandbits(32) for _ in range(3)])
    x0 = 0xDEADBEEF; x = x0; o = []
    for _ in range(20):
        x = xs32(x); o.append(x & 15)
    print("xorshift32: recovered x0 = %s after %s hops (true %#x)" % (hex(break_xorshift(o)[0]), break_xorshift(o)[1], x0))
    for name, seq in (("LFSR16", [int(v) for v in lfsr_schedule(20000)]), ("SipHash", [int(v) for v in keyed_schedule(bytes(range(16)), 0, 20000)])):
        print("order-3 context predictor on %-8s accuracy %.3f (chance %.3f)" % (name, context_predictor_accuracy(seq), 1 / 13))
    print("graveyard table:", graveyard_table())


if __name__ == "__main__":
    try:
        demo()
    except NotImplementedError:
        print("A TODO is not finished yet. Grade what you have:  python labs/lab2_prng_graveyard/grader.py")
