# Lab 3 - Correlation power analysis of the keyed hop engine (30 min)

Own design, simulation only. The traces come from an **assumed** leakage model (Hamming weight of one byte + Gaussian noise), not from a device. Files: `starter.py`, `solution.py`, `grader.py`, `expected.json`; explorer: `explorer/trace_explorer.html`.

**Learning goals.** (1) Build a Hamming-weight hypothesis and correlate it with traces. (2) Divide and conquer: 8 key bytes with 256 guesses each instead of 2^64. (3) Handle the carry of the modular addition (low byte first). (4) Relate noise, trace count and success: N scales with sigma^2.

**Target.** SipHash-2-4 on an 8-byte counter message m, first SipRound. Stage 1: v3 = k1 ^ C3 ^ m leaks HW of each byte of v3. Stage 2: s = (k0 ^ C2) + v3 leaks HW of each byte of s; with k1 known, v3 is known, and byte b of s depends on k0 byte b, v3 byte b and the carry from bytes 0..b-1. A trace has 16 samples (8 + 8).

**Assumption to keep in mind.** The grader draws every message m uniformly at random from all 64-bit values, so every message byte varies. A real hop engine hashes a slot counter that counts up: over a few hundred hops only its lowest byte changes, and this first-round attack then recovers only the key bytes that line up with changing counter bytes (1 of 8 at 300 consecutive slots). Full-key recovery here is a property of the random-message setting.

**Tasks** (`python labs/lab3_power_cpa/grader.py labs/lab3_power_cpa/starter.py`)
T1 `hw8`. T2 `corr_cols` (Pearson per column, constant column gives 0). T3 `scores_stage1` + `recover_k1`. T4 `scores_stage2` + `recover_k0` (use the given `carry_in`). T5 `success_rate(sigma, N)` = fraction of full 128-bit keys recovered. T6 `min_traces(sigma)`. T7 (stretch) with Hamming-distance leakage, find the two best guesses for k0 byte 0.

**Expected results and tolerances**
| Quantity | Expected | Accepted |
|---|---|---|
| recover k1 / k0, N=300, sigma=1, 5 keys | exact | exact |
| peak r of the right guess, sigma=2, N=300 | 0.54 | 0.42-0.66 |
| full-key success, sigma=2, N=50 / N=200 | 0.0 / 1.0 | <= 0.25 / >= 0.9 |
| full-key success, sigma=4, N=800 | 1.0 | >= 0.9 |
| min traces for 90 % success, sigma=2 | 200 | 100-400 |
| ratio min_traces(4)/min_traces(2) | 4 | 2-8 |
| HD model, k0 byte 0: top-2 guesses | {true, true ^ 0x80} | exact |

**Discussion questions**
1. In the explorer a guess that is the bitwise complement of the true byte has correlation of about -r. Why, and why do you rank by the signed value?
2. Why must k0 be recovered low byte first and why can a wrong low byte break the next one?
3. Doubling sigma needs about 4x the traces. Give the argument, and say what it implies for a countermeasure that adds noise.
