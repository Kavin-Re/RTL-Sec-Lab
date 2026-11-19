"""Lab 4 - Masking and its limits.  STARTER (fill in the TODOs).

Own design, simulation only. Traces come from an ASSUMED model: 2-share boolean masking of the first SipRound, every share byte leaks
its Hamming weight in its OWN time sample, plus Gaussian noise. T has shape (N, S, 16): axis 1 = share sample (0, 1, optionally a
third 'recombination' sample), axis 2 = byte (0..7 leak v3 = k1^C3^m, 8..15 leak the sum).
Run:    python labs/lab4_masking/starter.py
Grade:  python labs/lab4_masking/grader.py labs/lab4_masking/starter.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from rtlseclab.core import leakage as L
from rtlseclab.core.leakage import rand64, bytes_of, stage1_scores, byte_hits, welch_t, leak_masked, leak_unmasked
from rtlseclab.core.siphash import split_key

KEY = bytes(range(16))
K1 = split_key(KEY)[1]


# ---- Task 1 ---------------------------------------------------------------------------------------------
def share(x, rng):
    """Split a uint64 array x into two boolean shares (x0, x1) with x0 ^ x1 == x, x1 uniformly random (use rand64)."""
    # TODO: x1 = rand64(rng, len(x)); x0 = x ^ x1
    raise NotImplementedError("TODO")


# ---- Task 2 ---------------------------------------------------------------------------------------------
def fo_attack(T, m):
    """First-order CPA on stage 1. For every key byte try every share sample s in range(T.shape[1]) with stage1_scores(T[:, s, b], mb, b)
    (stage1_scores is the Lab 3 hypothesis+correlation, provided). Keep the guess with the largest peak correlation over all samples.
    Return k1 as an int."""
    # TODO: for each byte b: loop over s, remember the best peak and its argmax
    raise NotImplementedError("TODO")


# ---- Task 3 ---------------------------------------------------------------------------------------------
def so_combine(T, byte):
    """Second-order pre-processing: the centred product of the two share samples of one byte, (a - mean(a)) * (c - mean(c)), shape (N,).
    Why it works: E[(HW(x^r)-4)(HW(r)-4)] = -(HW(x)-4)/2, so the product correlates NEGATIVELY with HW of the unmasked byte."""
    # TODO: a = T[:, 0, byte], c = T[:, 1, byte]; return (a - a.mean()) * (c - c.mean())
    raise NotImplementedError("TODO")


def so_attack(T, m):
    """Second-order CPA on stage 1: for each byte correlate so_combine(T, b) with the hypotheses via stage1_scores, but take the argmax of the
    NEGATED scores (the correlation is negative). Return k1."""
    # TODO: sc = -stage1_scores(so_combine(T, b), mb, b); argmax
    raise NotImplementedError("TODO")


# ---- Task 4 ---------------------------------------------------------------------------------------------
def attack_hits(kind, N, sigma, seed):
    """Run one experiment and return how many of the 8 bytes of k1 are right. rng = np.random.default_rng(seed); m = rand64(rng, N);
    traces by `kind` (key = KEY):
      'unmasked'   leak_unmasked(KEY, m, sigma, rng)                      attacked with fo_attack on T[:, None, :]
      'off_fo'     leak_masked(KEY, m, sigma, rng, mask_on=False)         fo_attack   (control: masks switched off)
      'fo'         leak_masked(KEY, m, sigma, rng)                        fo_attack
      'so'         leak_masked(KEY, m, sigma, rng)                        so_attack
      'hd_fo'      leak_masked(KEY, m, sigma, rng, extra_hd=True)         fo_attack   (a register leaks HW(share0 ^ share1))"""
    # TODO: build the traces for `kind`, run the attack, return byte_hits(k1_est, K1)
    raise NotImplementedError("TODO")


# ---- Task 5 ---------------------------------------------------------------------------------------------
def tmax(order, mask_on, N, seed, sigma=1.0):
    """Fixed-vs-random Welch t-test (leakage detection, no key needed). Fixed set: N copies of one message; random set: N random messages
    (rng = default_rng(seed), traces from leak_masked(KEY, ., sigma, rng, mask_on=mask_on), fixed set first). Use only the 8 stage-1 byte
    columns. order=1: t-test each (share sample, byte) column on its own (welch_t) ; order=2: t-test so_combine of every byte (that is 8 columns).
    Return the largest |t|. Rule of thumb: |t| > 4.5 means leakage."""
    # TODO: build Tf, Tr; order 1 -> welch_t on T[:, :, :8].reshape(N, -1); order 2 -> welch_t on the stacked so_combine columns
    raise NotImplementedError("TODO")


if __name__ == "__main__":
    for kind, N, sg in (("unmasked", 300, 2), ("off_fo", 2000, 2), ("fo", 10000, 1), ("so", 300, 2), ("so", 3000, 2), ("so", 10000, 2), ("hd_fo", 2000, 2)):
        print("%-9s N=%-6d sigma=%d : %d/8 bytes of k1" % (kind, N, sg, attack_hits(kind, N, sg, 1)))
    for order, on in ((1, False), (1, True), (2, True)):
        print("t-test order %d, masks %s: max|t| = %.1f" % (order, "on" if on else "off", tmax(order, on, 10000, 1)))
