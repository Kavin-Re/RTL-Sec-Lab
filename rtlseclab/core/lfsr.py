"""16-bit LFSR hop engine (reference), the keyed SipHash schedule, and the candidate-elimination LFSR breaker.

ORIGIN: lfsr_step / lfsr_schedule are copied from FHSS-Link/rtl/hop_engine/model/hop_model.py (bit-exact with rtl/hop_lfsr.v);
LfsrBreaker is copied (verbatim logic) from FHSS-Link/rtl/hop_engine/model/randcheck.py, which itself reproduces sim/attack.py.
Own design, simulation only."""
import numpy as np
from .siphash import hop_channels


def lfsr_step(s):
    """x^16 + x^14 + x^13 + x^11 + 1, Fibonacci, shift right: feedback = s0 ^ s2 ^ s3 ^ s5 enters at bit 15. Works on ints and arrays."""
    bit = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 5)) & 1
    return (s >> 1) | (bit << 15)


def lfsr_schedule(n, M=13, seed=0xACE1):
    """hop_i = state_i mod M, where the state is stepped BEFORE it is output (matches the RTL). Seed 0 is mapped to 1 (lock-up state)."""
    s = seed or 1
    out = []
    for _ in range(n):
        s = lfsr_step(s)
        out.append(s % M)
    return np.array(out)


def keyed_schedule(key16, start, n, M=13):
    """SipHash-2-4(key, slot) mod M for slots start..start+n-1 (key: 16 bytes)."""
    return hop_channels(key16, np.arange(start, start + n, dtype=np.uint64), M)


class LfsrBreaker:
    """Candidate elimination over all 65535 nonzero states. After observe(h_1..h_n), `cand` holds every state x_n
    (the state that produced h_n) consistent with the observations."""
    def __init__(self, M=13):
        self.M = M
        self.cand = np.arange(1, 65536, dtype=np.uint32)
        self.seen = 0

    def observe(self, ch):
        self.cand = lfsr_step(self.cand)
        self.cand = self.cand[(self.cand % self.M) == ch]
        self.seen += 1

    def identified(self):
        return len(self.cand) == 1


def hops_to_identify(stream, M=13, limit=200):
    """(hops used, success). success False when the candidate set empties (model mismatch) or the limit is hit."""
    a = LfsrBreaker(M)
    for h in stream[:limit]:
        a.observe(int(h))
        if a.identified():
            return a.seen, True
        if len(a.cand) == 0:
            return a.seen, False
    return min(limit, len(stream)), False
