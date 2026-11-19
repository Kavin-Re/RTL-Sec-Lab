# Lab 1 answer key

1. Consecutive hops are not independent observations of the state. The successor set of every channel has 4 members (task T7: |successors(h)| = 4), and the grader measures a shrink of about 4x per hop, i.e. about 2 bits of state per hop, so about 16/2 = 8 hops (measured 8.33). The naive 13x per hop would give 4.3 hops. (This is the empirical rule behind T5/T7, not a proof.)
2. A keyed stream is not an LFSR trajectory, so after a few hops no LFSR state is consistent with it (2.6 hops on average). An empty candidate set, or low `lfsr_likeness` (about 4/13 for a random stream because it matches only when the next channel is one of the 4 allowed successors), is a cheap test for "this is not an LFSR".
3. Linear generators stay linear: with n state bits an attacker needs about n/2 hops here, and for any LFSR the Berlekamp-Massey algorithm recovers it from 2n output bits. A longer register raises the work only linearly. The attack above (candidate filtering) grows with 2^n, but linear algebra over GF(2) does not, which is Lab 2's point. Fix = a keyed PRF, not a bigger LFSR.

Common mistakes: filtering before stepping (the RTL steps first); returning the state before instead of after the last used hop; Python-int loops on 65535 states (use numpy, the dtype must be wide enough for `<<`).
