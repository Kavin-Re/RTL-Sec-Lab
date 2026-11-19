# Lab 2 - The PRNG graveyard (20 min)

Own-link simulation, no radio. The attacker knows the algorithm and sees past channel numbers. Files: `starter.py`, `solution.py`, `grader.py`, `expected.json`.

**Learning goals.** (1) Break three standard generators from partial output. (2) Distinguish "passes statistical tests" from "unpredictable". (3) Measure predictability with a model-free predictor. (4) Know what keyed designs change.

**Generators** (given in `rtlseclab/core/prng.py`): LCG-24 with hop = (x >> 8) mod 13; xorshift32 with hop = x & 15 on 16 channels; MT19937 where full 32-bit outputs leak; HMAC-SHA256 and SipHash-2-4 as keyed references.

**Tasks**
- T1 `lcg_filter` + `break_lcg`: candidate filtering over the 2^24 states (the step is a bijection so every pre-state is covered).
- T2 `untemper` + `mt_clone`: invert MT19937 output tempering and clone the generator from 624 consecutive outputs.
- T3 `solve_gf2` + `break_xorshift`: xorshift is linear over GF(2); each observed hop gives 4 linear equations on the 32 state bits.
- T4 `context_predictor_accuracy`: order-3 context predictor on LFSR, SipHash and HMAC streams. T5 `graveyard_table`.

**Expected results and tolerances**
| Quantity | Expected | Accepted |
|---|---|---|
| hops to break LCG-24 (each of 4 seeds) | 6-9, mean about 7.4 | 5-10 |
| untemper(temper(y)) == y, 2000 values; MT clone predicts 2000 outputs | exact | exact |
| xorshift32 hops until the GF(2) system is unique | 9 | 9 |
| predictor accuracy on the LFSR stream (chance 0.077) | 0.236 | 0.20-0.27 |
| predictor accuracy on SipHash / HMAC | 0.072 | 0.05-0.10 |
| graveyard table: LCG24 / xorshift32 / MT19937 hops | about 7.4 / 9 / 624 | LCG24 5.5-9.5 |

**Discussion questions**
1. Mersenne Twister passes standard statistical suites. Why is that irrelevant for a hop schedule?
2. Why does xorshift need only about 9 observed hops although each reveals just 4 bits?
3. The context predictor is 3x above chance on the LFSR stream but at chance on SipHash. What would you conclude if it scored 0.10 on a new generator?
