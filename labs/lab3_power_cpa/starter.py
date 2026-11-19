"""Lab 3 - Correlation power analysis (CPA) of the keyed hop engine.  STARTER (fill in the TODOs).

Own design, simulation only: traces come from an ASSUMED leakage model (Hamming weight of one byte + Gaussian noise), not from a device.
Target: first SipRound of SipHash-2-4 on an 8-byte counter message m.   v3 = k1 ^ C3 ^ m   (stage 1),   s = (k0 ^ C2) + v3  (stage 2).
Run:    python labs/lab3_power_cpa/starter.py
Grade:  python labs/lab3_power_cpa/grader.py labs/lab3_power_cpa/starter.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from rtlseclab.core.siphash import C2, C3, split_key
from rtlseclab.core.leakage import leak_unmasked, rand64, bytes_of, carry_in, HW   # simulator + message bytes + carry helper

U = np.uint64
HYP = np.arange(256, dtype=np.uint8)               # the 256 guesses for one key byte


# ---- Task 1 ---------------------------------------------------------------------------------------------
def hw8(x):
    """Hamming weight of every element of a uint8 array (returns float array of the same shape)."""
    # TODO: look the weights up in a 256-entry table (HW is provided) or count bits
    raise NotImplementedError("TODO")


# ---- Task 2 ---------------------------------------------------------------------------------------------
def corr_cols(H, l):
    """Pearson correlation between every column of H (N,K) and the vector l (N,). Return shape (K,). A constant column gives 0."""
    # TODO: centre both, num = Hc.T @ lc, den = sqrt(sum Hc^2) * sqrt(sum lc^2); guard den == 0
    raise NotImplementedError("TODO")


# ---- Task 3 ---------------------------------------------------------------------------------------------
def scores_stage1(l, mb, byte):
    """Correlation of the samples l (N,) with the model for each of the 256 guesses g of key byte `byte` of k1.
    mb: (N,8) message bytes. The leaking value is the byte  m_byte ^ g ^ C3_byte  (C3_byte = (C3 >> 8*byte) & 255)."""
    # TODO: H[n, g] = HW(mb[n, byte] ^ g ^ c3byte); return corr_cols(H, l)
    raise NotImplementedError("TODO")


def recover_k1(traces, m):
    """traces (N,16): columns 0..7 leak the bytes of v3 (stage 1). m: (N,) uint64 messages. Return k1 as a Python int (byte b = argmax of scores)."""
    # TODO: for each byte b take argmax of scores_stage1(traces[:, b], mb, b) and assemble k1 (byte 0 least significant)
    raise NotImplementedError("TODO")


# ---- Task 4 ---------------------------------------------------------------------------------------------
def scores_stage2(l, v3b_byte, carry, byte):
    """Stage 2 leaks the byte of s = (k0 ^ C2) + v3. For guess g of key byte `byte` of k0:  s_byte = ((g ^ C2_byte) + v3_byte + carry) & 255.
    v3b_byte: (N,) byte `byte` of v3 (computable once k1 is known), carry: (N,) carry into this byte from the lower bytes."""
    # TODO: H[n, g] = HW(((g ^ c2byte) + v3b_byte[n] + carry[n]) & 255); return corr_cols(H, l)
    raise NotImplementedError("TODO")


def recover_k0(traces, m, k1):
    """Given k1, recover k0 byte by byte, LOW byte first (the carry into byte b depends on bytes 0..b-1 of k0).
    Use carry_in(k0_so_far, v3, b) for the carry. v3 = (k1 ^ C3) ^ m."""
    # TODO: v3 = U(k1 ^ C3) ^ m ; for b in 0..7: carry = carry_in(k0, v3, b); argmax of scores_stage2(traces[:, 8+b], v3_bytes[:, b], carry, b)
    raise NotImplementedError("TODO")


# ---- Task 5 ---------------------------------------------------------------------------------------------
def success_rate(sigma, N, trials=20, seed=0):
    """Fraction of `trials` random 128-bit keys fully recovered (k0 AND k1 correct) from N traces at noise sigma.
    Per trial t use rng = np.random.default_rng(seed * 1000 + t): key bytes first (16 bytes), then messages m = rand64(rng, N),
    then traces = leak_unmasked(key, m, sigma, rng)."""
    # TODO: loop over trials, generate, call recover_k1 then recover_k0, count exact matches with split_key(key)
    raise NotImplementedError("TODO")


# ---- Task 6 ---------------------------------------------------------------------------------------------
def min_traces(sigma, grid=(25, 50, 100, 200, 400, 800, 1600), target=0.9, trials=20, seed=1):
    """Smallest N in `grid` whose success_rate(sigma, N, trials, seed) >= target (None if none)."""
    # TODO: scan the grid in increasing order
    raise NotImplementedError("TODO")


# ---- Task 7 (stretch) -------------------------------------------------------------------------------------
def hd_top2_byte0(traces, m, k1):
    """Stage-2 samples can leak the Hamming DISTANCE HW(old ^ s) between the register's old byte (g ^ C2 byte) and the new byte s
    (traces from leak_unmasked(..., model2="HD")). For key byte 0 (no carry in) return the two best guesses, sorted ascending.
    Observe what they have in common: bit 7 of old cancels in old ^ (old + v3), so the model cannot tell g from g ^ 0x80."""
    # TODO: H[n, g] = HW(old_g ^ s_g[n]) with old_g = g ^ c2byte, s = (old_g + v3_byte0) & 255 ; return sorted top two by correlation
    raise NotImplementedError("TODO")


if __name__ == "__main__":
    key = bytes(range(16)); k0, k1 = split_key(key)
    rng = np.random.default_rng(0); m = rand64(rng, 300)
    T = leak_unmasked(key, m, 2.0, rng)
    mb = bytes_of(m)
    sc = scores_stage1(T[:, 0], mb, 0)
    order = np.argsort(-np.abs(sc))
    print("stage 1, key byte 0: true 0x%02X ; best guess 0x%02X (r=%.3f), runner-up 0x%02X (r=%.3f)" % (k1 & 255, order[0], sc[order[0]], order[1], sc[order[1]]))
    est1 = recover_k1(T, m); est0 = recover_k0(T, m, est1)
    print("k1 %016x (true %016x)   k0 %016x (true %016x)" % (est1, k1, est0, k0))
    for s in (1, 2, 4):
        print("sigma", s, "min traces for 90%% full-key success:", min_traces(s))
