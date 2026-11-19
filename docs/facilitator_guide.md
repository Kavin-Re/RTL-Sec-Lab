# Facilitator guide - RTL-Sec-Lab (3-hour workshop)

A self-contained kit on the hardware security of a small keyed hop/PRF engine (own design). **Everything is simulation**: no device, no radio, no real exploit; leakage, fault, trojan and PUF models are simple assumed models and every handout says so.

## Setup (10 minutes, once)
- Python 3.8+ and numpy only (checked here with Python 3.10 and numpy 2.x; no pip installs beyond numpy, no network at run time).
- Copy the kit folder, `cd` into it, run `python -m rtlseclab.check`. Expected last line: `KIT CHECK: 39/39 solution tasks PASS across 6 labs` (about 30-60 s on a laptop).
- Students work in `labs/labN_*/starter.py`; grade with `python labs/labN_*/grader.py labs/labN_*/starter.py`. Each grader prints PASS/FAIL per task and exits non-zero on any FAIL. Graders are deterministic (fixed seeds); `RTLSECLAB_SEED_SHIFT=k` shifts all seeds if you suspect a student hard-coded outputs.
- Open `explorer/trace_explorer.html` in any browser (single file, offline) for Labs 3-4.
- Hand out each `handout.md`; keep `solution.py` and `answer_key.md` back. `python -m rtlseclab.tools.make_student_kit` writes a copy of the kit without them to `dist/rtl-sec-lab-student/`. The repository itself contains the solutions, so point students at that export, not at the repository.

## Timing (180 minutes)
| Time | Block | Notes |
|---|---|---|
| 0:00-0:10 | Intro and setup | threat model: attacker knows the design (Kerckhoffs), not the key; read `rtl/hop_lfsr.v` and `rtl/hop_keyed.v` together |
| 0:10-0:35 | Lab 1 LFSR break | T1-T6 core, T7 stretch |
| 0:35-0:55 | Lab 2 PRNG graveyard | T3 (GF(2) solver) is the longest; give the equation setup if behind |
| 0:55-1:05 | Break | |
| 1:05-1:35 | Lab 3 CPA | show the explorer (unmasked, then N=40 sigma=4) before T3 |
| 1:35-2:00 | Lab 4 masking | explorer: masked first order fails, second order works at N=3000 |
| 2:00-2:20 | Lab 5 faults and TMR | T4 takes about 15 s to run: tell students to run it once |
| 2:20-2:45 | Lab 6 trojan and PUF | T5 and T7 are slower (5-10 s each) |
| 2:45-3:00 | Wrap-up | 3 discussion questions per lab are in each handout; answer keys in `labs/*/answer_key.md` |

If time runs short drop the stretch tasks (marked "(stretch)" in the grader output), then Lab 6 T7, then Lab 2 T4.

## Common mistakes (details in each answer key)
- Lab 1: filtering before stepping; expecting 13x shrink per hop (it is about 4x).
- Lab 2: wrong inverse order in `untemper`; integer overflow with numpy dtypes; reading "chance-level predictor" as proof of security.
- Lab 3: forgetting constants C3/C2; ranking by |r| instead of the signed value; carry computed from all of k0.
- Lab 4: not centring or not negating in the second-order attack; attacking one share sample only.
- Lab 5: comparing tmr to `none_nowd` instead of `none`; using the 32-bit formula for the key; treating GE percentages as synthesis.
- Lab 6: 13 instead of 12 degrees of freedom; calibrating CUSUM on trojan runs; ignoring the PUF layout gradient.

## What the kit does not do (say this out loud)
- Leakage is an assumed Hamming-weight/Hamming-distance model with Gaussian noise; no alignment, jitter, or real measurement. Masking is modelled at the share-byte level only (no glitches, coupling or routing).
- Labs 3 and 4 attack traces taken with uniformly random 64-bit messages. The engine's real input is a slot counter; with consecutive slots the first-round CPA of Lab 3 recovers only the key bytes aligned with counter bytes that change (1 of 8 bytes of each key half at 300 traces, 2 of 8 at 70,000; see `docs/known_issues.md`). The labs teach the method, not an end-to-end break of a counter-mode engine.
- Faults are abstract bit flips in a receiver model; TX-side faults, datapath faults, voter faults and common-mode faults are outside the model except the T6 demonstration.
- Area numbers are a proxy with assumed cell areas, not synthesis results.
- Trojan and PUF models are our own abstractions; the kit proves nothing about any real chip.
- No citations are included beyond named classic ideas (SipHash, Mersenne Twister, ISW masking, CPA, t-test leakage assessment, fuzzy extractors); look them up before quoting.

## Files
`rtlseclab/core/` models (each file has an ORIGIN header naming the file it was copied from), `rtlseclab/check.py` runner, `labs/` (starter, solution, grader, expected.json, handout, answer key per lab), `explorer/trace_explorer.html`, `tests/` (grader tests, explorer test, seed-robustness script).
