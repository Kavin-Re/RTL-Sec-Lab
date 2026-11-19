# Lab 1 - Breaking the 16-bit LFSR hop generator (25 min)

Own design, simulation only. Files: `starter.py` (edit), `solution.py` (facilitator), `grader.py`, `expected.json`, `../../rtl/hop_lfsr.v` (the RTL this model matches bit for bit).

**Learning goals.** (1) Write the generator from its RTL. (2) See that an observer who knows the algorithm (Kerckhoffs) but not the seed can recover the full state from a handful of channel numbers. (3) Measure how fast the candidate set shrinks and see why it is not 13x per hop. (4) Contrast with a keyed generator.

**Background.** State is 16 bits, polynomial x^16+x^14+x^13+x^11+1, Fibonacci form, shift right: feedback = s[0]^s[2]^s[3]^s[5], new state = (s >> 1) | (fb << 15). The engine steps first, then outputs `state mod 13`. The attacker sees channel numbers only, so each observation keeps every state whose (stepped) value mod 13 matches. Candidates are stepped in lock-step, so the set is filtered with 65535 states at once using numpy.

**Tasks** (run `python labs/lab1_lfsr_break/grader.py labs/lab1_lfsr_break/starter.py`; each prints PASS/FAIL)
- T1 `lfsr_step` for ints and numpy arrays. T2 `hop_stream` (seed 0 behaves as 1).
- T3 `filter_candidates(cands, ch)`: step, keep those with state mod 13 == ch.
- T4 `break_lfsr(obs)` returns (state after the last used hop, hops used); `predict` the rest.
- T5 `survivor_curve`: mean survivors after 1..8 hops over 20 seeds. T6 `attack_keyed`: run the same attacker on a SipHash-2-4 keyed stream; after how many hops is the candidate set empty? T7 (stretch) successors and `lfsr_likeness`.

**Expected results and tolerances** (also in `expected.json`)
| Quantity | Expected | Accepted |
|---|---|---|
| survivors after hop 1 (channel 0) | 5041 | 5041-5042 |
| mean hops to a single state, 30 seeds | 8.33 | 7.8-9.0 (max 11) |
| survivor ratio between consecutive hops | 4.0 | 3.3-4.8 |
| survivors after hop 4 | 78 | 40-150 |
| keyed stream: hops until the LFSR candidate set empties | 2.6 | 2.0-4.0 |
| keyed stream LFSR-likeness vs LFSR stream | 0.31 vs 1.00 | 0.27-0.35 |

**Discussion questions** (answer keys in `answer_key.md`)
1. The state has 16 bits and a hop is one of 13 values (3.7 bits). Why is the attack not finished after 16/3.7 = 4.3 hops?
2. The attacker's candidate set becomes empty on the keyed stream. Why is that itself a useful distinguisher?
3. Would a 32-bit or 64-bit LFSR with the same structure help? What would you change in this attack?
