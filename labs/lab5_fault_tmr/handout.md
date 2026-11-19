# Lab 5 - Fault injection and the cost of TMR (20 min)

Own design, simulation only. Faults are **abstract** bit flips or sequencing errors in a model of the receiver's key (128 bit), slot counter (32 bit), counter FSM and 4-bit output register. No physical fault mechanism is modelled, and nothing here tells you how to induce a fault. Areas come from a gate-equivalent PROXY (`rtlseclab/core/ge_model.py`, assumed cell areas), not from synthesis. Files: `starter.py`, `solution.py`, `grader.py`, `expected.json`, `../../rtl/hop_keyed.v`.

**Learning goals.** (1) Why one flipped key or counter bit desynchronises a keyed hop link, and how long recovery takes. (2) TMR with a bitwise voter versus duplication with parity: what each corrects, detects or misses. (3) Compute failure probability exactly and by Monte Carlo. (4) Read overhead in percent and pick the cheapest scheme for a target. (5) Know what TMR cannot do.

**Link model.** hop = SipHash24(key, slot counter) mod 13. Recovery: loss-of-lock after 3 missed packets; an authenticated beacon every 32 slots reloads the counter; an optional watchdog reloads the key from NVM. Schemes: `none_nowd`, `none` (beacon + watchdog), `tmr` (3 copies of state, bitwise vote, scrub), `dcp` (2 copies + parity, A/B compare). Single fault event at slot 0 over 256 slots.

**Tasks.** T1 `majority`, `parity`. T2 `p_tmr_fail_w2` (exact) and `tmr_fail_mc`. T3 `overheads`. T4 `fault_table` (6 fault cases x 4 schemes, 300 trials each). T5 `cheapest_scheme`. T6 (stretch) `common_mode_vote`.

**Expected results and tolerances**
| Quantity | Expected | Accepted |
|---|---|---|
| P(TMR wrong \| 2 random flips), 32-bit / 128-bit register | 0.02105 / 0.00522 | 4 digits |
| Monte Carlo, 32 bit, 40000 trials | 0.021 | 0.0165-0.026 |
| overhead of TMR_state / DMR_parity_state / lockstep / TMR_full_engine (%) | 53.4 / 57.3 / 100.2 / 200.2 | each +-1.0 |
| unprotected, 1 counter flip: p_desync | 1.0 | exact |
| `none` (watchdog), 1 key flip: mean recovery (slots) | about 45 | 30-60 |
| `none_nowd`, 1 key flip: never recovers | 1.0 | 0.95-1.0 |
| tmr, any single fault: p_desync | 0 | exact |
| tmr / dcp, 2 counter flips: p_desync | 0.03 / 0.73 | 0-0.10 / 0.55-0.90 |

**Discussion questions**
1. A single flip is always out-voted by TMR, two flips fail with probability 3W / C(3W,2). Derive it and say why the 128-bit key is safer than the 32-bit counter.
2. Duplication with parity is only 4 points of area more than TMR_state in this proxy. Why does the table still favour TMR?
3. Name a fault class this model does not cover that defeats TMR, and one cheaper-than-TMR measure that would address it.
