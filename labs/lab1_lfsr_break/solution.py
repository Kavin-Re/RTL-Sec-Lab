"""Lab 1 - Breaking the 16-bit LFSR hop generator.  SOLUTION.

Own design, simulation only. The generator is bit-exact with rtl/hop_lfsr.v (x^16+x^14+x^13+x^11+1, Fibonacci, shift right,
hop = state mod 13, state stepped BEFORE it is output).
Run:    python labs/lab1_lfsr_break/solution.py
Grade:  python labs/lab1_lfsr_break/grader.py labs/lab1_lfsr_break/solution.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from rtlseclab.core.lfsr import keyed_schedule            # SipHash-2-4 keyed schedule, used as the 'good' generator


# ---- Task 1 ---------------------------------------------------------------------------------------------
def lfsr_step(s):
    """One LFSR step. Feedback bit = s[0] ^ s[2] ^ s[3] ^ s[5]; new state = (s >> 1) with the feedback bit placed at bit 15.
    Must work for a Python int AND for a numpy integer array (the attack steps 65535 candidates at once)."""
    # >>> SOLUTION: compute the feedback bit from bits 0, 2, 3, 5 and return (s >> 1) | (fb << 15)
    fb = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 5)) & 1
    return (s >> 1) | (fb << 15)
    # <<< SOLUTION


# ---- Task 2 ---------------------------------------------------------------------------------------------
def hop_stream(seed, n, M=13):
    """The n channels the engine outputs after loading `seed` (seed 0 is mapped to 1, as in the RTL).
    Step first, then output state % M."""
    # >>> SOLUTION: loop n times: step the state, append state % M
    s = seed or 1
    out = []
    for _ in range(n):
        s = int(lfsr_step(s))
        out.append(s % M)
    return out
    # <<< SOLUTION


# ---- Task 3 ---------------------------------------------------------------------------------------------
def filter_candidates(cands, ch, M=13):
    """cands: numpy array of candidate states BEFORE the hop. Return the array of candidate states AFTER the hop
    (i.e. stepped once) that are consistent with the observed channel `ch`."""
    # >>> SOLUTION: step every candidate, keep those whose (state % M) equals ch
    nxt = lfsr_step(cands)
    return nxt[(nxt % M) == ch]
    # <<< SOLUTION


# ---- Task 4 ---------------------------------------------------------------------------------------------
def break_lfsr(observed, M=13):
    """Recover the LFSR state from observed channels (Kerckhoffs: you know the algorithm, not the seed).
    Start with all 65535 non-zero states, filter after every observed hop, stop as soon as ONE candidate is left.
    Return (state_after_last_used_hop, hops_used). If the set empties or never shrinks to 1, return (None, hops_used)."""
    # >>> SOLUTION: cands = np.arange(1, 65536, dtype=np.uint32); filter per hop; stop at 1 (or 0) candidates
    cands = np.arange(1, 65536, dtype=np.uint32)
    for i, ch in enumerate(observed):
        cands = filter_candidates(cands, int(ch), M)
        if len(cands) == 1:
            return int(cands[0]), i + 1
        if len(cands) == 0:
            return None, i + 1
    return None, len(observed)
    # <<< SOLUTION


def predict(state, n, M=13):
    """The next n channels after a known `state` (the state that produced the last observed hop)."""
    out = []
    for _ in range(n):
        state = int(lfsr_step(state))
        out.append(state % M)
    return out


# ---- Task 5 ---------------------------------------------------------------------------------------------
def survivor_curve(seeds, k, M=13):
    """Average number of surviving candidates after hop 1..k, over the given seeds (list of ints). Returns a list of k floats.
    Compare it with the 'independent observations' estimate 65535 / 13**j and explain the gap (Discussion question 1)."""
    # >>> SOLUTION: for every seed generate k hops, filter step by step, add len(cands) to a running sum, divide by len(seeds)
    tot = np.zeros(k)
    for sd in seeds:
        cands = np.arange(1, 65536, dtype=np.uint32)
        for j, ch in enumerate(hop_stream(sd, k, M)):
            cands = filter_candidates(cands, ch, M)
            tot[j] += len(cands)
    return [float(x) for x in tot / len(seeds)]
    # <<< SOLUTION


# ---- Task 6 ---------------------------------------------------------------------------------------------
def attack_keyed(key16, n=40, M=13):
    """Run the same attacker against the SipHash keyed schedule (slots 0..n-1). Return the number of hops after which the
    candidate set became EMPTY (the LFSR model does not explain the stream), or None if it never emptied within n hops."""
    # >>> SOLUTION: same loop as break_lfsr but on keyed_schedule(key16, 0, n, M); report when len(cands) == 0
    cands = np.arange(1, 65536, dtype=np.uint32)
    for i, ch in enumerate(keyed_schedule(key16, 0, n, M)):
        cands = filter_candidates(cands, int(ch), M)
        if len(cands) == 0:
            return i + 1
    return None
    # <<< SOLUTION


# ---- Task 7 (stretch) -----------------------------------------------------------------------------------
def successors(h, M=13):
    """The set of channels that can follow channel h in an LFSR stream (any state s with s % M == h).
    Hint: s' = (s >> 1) + fb * 2^15, so s' mod M depends only on h, the dropped low bit b0 and the feedback bit fb.
    Use the modular inverse of 2 (for M = 13 it is 7; pow(2, -1, M) in Python 3.8+). Return a sorted list."""
    # >>> SOLUTION: s = 2*q + b0 so q = inv2*(h - b0) mod M; add fb * 2**15; collect the values for b0, fb in {0,1}
    inv2 = pow(2, -1, M)
    return sorted({(inv2 * (h - b0) + fb * (1 << 15)) % M for b0 in (0, 1) for fb in (0, 1)})
    # <<< SOLUTION


def lfsr_likeness(stream, M=13):
    """Fraction of consecutive pairs (h_i, h_i+1) in `stream` that an LFSR could have produced."""
    # >>> SOLUTION: count pairs where the second channel is in successors(first)
    ok = sum(int(b) in successors(int(a), M) for a, b in zip(stream[:-1], stream[1:]))
    return ok / (len(stream) - 1)
    # <<< SOLUTION


def demo():
    seed = 0xACE1
    obs = hop_stream(seed, 40)
    print("first 10 hops from seed 0xACE1:", obs[:10])
    st, used = break_lfsr(obs)
    print("recovered state %s after %d hops; next 10 predicted: %s" % (st, used, predict(st, 10)))
    print("true hops %d..%d:                              %s" % (used + 1, used + 10, hop_stream(seed, used + 10)[used:]))
    print("survivors after hops 1..10 (avg of 20 seeds):", [round(x, 1) for x in survivor_curve(range(1, 21), 10)])
    print("independent-observation estimate 65535/13^k: ", [round(65535 / 13 ** k, 2) for k in range(1, 11)])
    print("keyed stream: candidate set empty after", attack_keyed(bytes(range(16))), "hops")
    print("successors of channel 5:", successors(5), "| LFSR-likeness: lfsr %.2f, keyed %.2f"
          % (lfsr_likeness(hop_stream(0xACE1, 400)), lfsr_likeness(keyed_schedule(bytes(range(16)), 0, 400))))


if __name__ == "__main__":
    try:
        demo()
    except NotImplementedError:
        print("A TODO is not finished yet. Grade what you have:  python labs/lab1_lfsr_break/grader.py")
