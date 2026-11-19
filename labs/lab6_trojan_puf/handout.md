# Lab 6 - Trojan detection from the hop sequence, and a PUF key (25 min)

Own design, simulation only. The trojan is an **abstract** model of our own engine: after a rare trigger (slot count) it replaces the channel with a fixed target with probability beta = beta_k/256, otherwise the output is bit-identical to the clean engine. The PUF is a statistical ring-oscillator model (Gaussian process variation + read noise + a layout gradient) with a code-offset fuzzy extractor. No real chip, no real exploit. Files: `starter.py`, `solution.py`, `grader.py`, `expected.json`.

**Learning goals.** (1) Detect a biased channel distribution without the key: chi-square on windows, threshold from a false-alarm target. (2) Single-window test versus CUSUM for a small bias. (3) PUF metrics: uniqueness, reliability, and why a layout gradient ruins uniqueness. (4) Why raw PUF bits are not a key and what error correction costs.

**Tasks.** T1 `chi2_stat`, `chi2_series`. T2 `alarm_threshold(alpha)` (12 degrees of freedom, bisection on the exact tail). T3 `false_alarm_rate` on clean engines. T4 `detect_power` for beta = 10 %, 5 %, 2.3 %. T5 `cusum_first`, `calibrate_h`, `delay_compare`. T6 `puf_uniqueness`, `puf_ber` for pairings far / neighbour / far with plane removal. T7 (stretch) `regen_rate` of the 128-bit key for raw, BCH(15,7,t=2), repetition, repetition+BCH at 0 and +60 C.

**Expected results and tolerances**
| Quantity | Expected | Accepted |
|---|---|---|
| threshold, alpha=1e-3 / 0.05 (df 12) | 32.91 / 21.03 | +-0.1 / +-0.08 |
| clean false-alarm rate at alpha=1e-2 | 0.010 | 0.005-0.017 |
| per-window detection, W=2000, alpha=1e-3: beta 10 % / 5 % / 2.3 % | 1.0 / 0.99 / 0.20 | >=0.95 / >=0.9 / 0.05-0.45 |
| CUSUM threshold h (k=15, W=500, 5 % false-alarm runs) | 40 | 30-60 |
| CUSUM delay, beta 3.1 %, W=500 (windows) | about 14 | 5-25 |
| single-window delay / CUSUM delay | about 1.7 | 1.15-6 |
| uniqueness: far pairing / neighbour or plane-removed | 0.244 / 0.50 | 0.15-0.35 / 0.47-0.53 |
| BER nominal / +60 C (plane removed; theory 0.0159 nominal) | 0.0165 / 0.051 | 0.010-0.025 / 0.035-0.07 |
| key regeneration at +60 C: raw / BCH only / rep3+BCH | 0 / 0.53 / 1.0 | <=0.05 / 0.3-0.8 / >=0.95 |

**Discussion questions**
1. Why must the CUSUM threshold be calibrated on clean data, and what goes wrong if you tune it on the trojan runs?
2. The detector sees only channel numbers. Name one trojan behaviour it cannot see, and one extra check.
3. rep3+BCH uses 855 response bits for a 128-bit key and BCH alone 285. Why pay for the repetition?
