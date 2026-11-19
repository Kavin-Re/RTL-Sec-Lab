# Known issues

## Open

1. **Labs 3 and 4 assume uniformly random messages.** The graders and the explorer generate traces with messages drawn
   uniformly from all 64-bit values (`rand64`). The engine's real input is a slot counter. With consecutive slots only
   the low counter bytes change, a constant message byte gives a constant Hamming-weight hypothesis, and the first-round
   CPA cannot rank guesses for that key byte. Measured with `rtlseclab.core.leakage.cpa_attack` at sigma = 2 over 5 keys:
   consecutive slots give 1 of 8 bytes of k1 (and of k0) at N = 300 and N = 5000 (one run reached 2), and 2 of 8 at
   N = 70,000, against 8 of 8 with random messages at every N. The handout and the facilitator guide now say this. A
   lab task on the counter case (and on what an attacker does about it) would close the gap.
2. **The Python hop model is not bit-identical to `rtl/hop_keyed.v`** (same SipHash digest, different digest-to-channel
   mapping). See `docs/MODEL_NOTES.md`. The kit contains no RTL simulation.
3. **Graders are self-check tools, not assessment tools.** The reference models the graders compare against live in
   `rtlseclab/core/` and ship with the student copy.
4. `tests/test_explorer.py` rewrites the committed screenshots in `tests/screens/` every time it runs, so a local run
   leaves the working tree dirty.
5. Plotting is not part of the kit (no matplotlib); the explorer is the only visual.
6. Timing figures in the facilitator guide come from a 2-core cloud machine.

## Fixed

- **Lab 4 T5 band was too tight for one seed stream** (found by `tests/test_robustness.py`, shift 7: second-order attack
  at N = 3000, sigma = 2 returned 5 of 8 bytes against an accepted band of 6-8). The band is now 4-8 in
  `labs/lab4_masking/expected.json` and in the handout table. `tests/robustness_result.txt` is the re-run after the
  change: 20 of 20 seed shifts pass every task.
