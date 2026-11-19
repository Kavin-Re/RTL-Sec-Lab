# Known issues

1. **Lab 4 T5 band is too tight for one seed stream (found by tests/test_robustness.py, shift 7).** `second-order, N=3000, sigma=2` returned 5 of 8 bytes at `RTLSECLAB_SEED_SHIFT=7`; the accepted band is 6-8. With the default seeds (shift 0) and 19 of 20 shifts every task passes (`tests/robustness_result.txt`). Fix (not applied in this delivered copy because delivered files were write-protected): in `labs/lab4_masking/expected.json` change the T5 item `"lo": 6` to `"lo": 4`, and the same number in the `expected` text of the handout table (`6-8` -> `4-8`). Re-run `python tests/test_robustness.py 20 2`.
2. Plotting is not part of the kit (no matplotlib); the explorer is the only visual.
3. Timing figures in the facilitator guide come from a 2-core cloud machine; a laptop is similar.
