# Lab 4 - Masking and its limits (25 min)

Own design, simulation only. Model: 2-share boolean masking of the first SipRound (ISW-style AND gadget in the adder), each share byte leaks its Hamming weight in its own time sample, plus noise. Not modelled: glitches/early propagation, coupling, jitter. Files: `starter.py`, `solution.py`, `grader.py`, `expected.json`; `explorer/trace_explorer.html` (modes unmasked / masked first / masked second order).

**Learning goals.** (1) Why each single share is independent of the secret. (2) Why a first-order attack fails and a second-order attack (combine two samples) works. (3) What masking costs in traces. (4) Use a fixed-vs-random t-test to see where leakage lives. (5) See that a single recombination leak undoes the protection.

**Tasks** (`python labs/lab4_masking/grader.py labs/lab4_masking/starter.py`)
T1 `share`. T2 `fo_attack` (all share samples, best peak) - works unmasked and with masks switched off. T3 `so_combine` (centred product) and `so_attack` (note the sign). T4 `attack_hits` for each kind. T5 trace cost. T6 `tmax`: order-1 and order-2 Welch t-tests, threshold |t| > 4.5. T7 (stretch) first-order attack on a design where a register leaks HW(share0 ^ share1).

**Expected results and tolerances**
| Quantity | Expected | Accepted |
|---|---|---|
| unmasked, N=300, sigma=2: bytes of k1 right (of 8) | 8 | 8 |
| first-order on masked, N=10000, sigma=1 (chance 0.03) | 0 | 0-2 |
| second-order on masked, N=10000, sigma=2 | 8 | 7-8 |
| second-order, N=300 / N=3000, sigma=2 | 0 / 7 | 0-3 / 4-8 |
| max abs t: order 1 masks off / order 1 masks on / order 2 masks on | about 100-150 / 1.8 / 23-34 | 20-400 / <= 4.5 / 8-60 |
| recombination leak, first-order attack, N=2000, sigma=2 | 8 | 7-8 |

**Discussion questions**
1. Why does the centred product of two share samples correlate with the secret byte, while each sample alone does not?
2. The t-test "passes" at order 1 and fails at order 2. What would you report to a customer?
3. Name two physical effects not in this model that can make a masked implementation behave like a lower-order one.
