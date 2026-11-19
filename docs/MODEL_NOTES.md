# Model notes: how the Python models relate to the RTL in `rtl/`

The kit does not simulate RTL. The two Verilog files are included for reading, so that the labs can point at real
registers and adders. This note states exactly where the Python models in `rtlseclab/core/` match that RTL and where
they do not.

## `rtl/hop_lfsr.v` and `rtlseclab/core/lfsr.py`: same sequence

Both implement x^16 + x^14 + x^13 + x^11 + 1 as a right-shifting Fibonacci LFSR (feedback `s0 ^ s2 ^ s3 ^ s5` enters at
bit 15), step the state first and then output `state mod M`, reset to `0xACE1`, and map seed 0 to 1.
`lfsr_schedule()` is written to produce the same channel sequence as the RTL. That equivalence was established in the
FHSS-Link repository the files were copied from; this kit contains no RTL simulation that re-checks it.

## `rtl/hop_keyed.v` and `rtlseclab/core/siphash.py`: same PRF, different channel mapping

| | RTL (`hop_keyed.v`) | Python model |
|---|---|---|
| PRF | SipHash-2-4, one SipRound per clock | SipHash-2-4 (`siphash24`, `siphash24_u64`) |
| Message | `{retry[7:0], slot[55:0]}`, 8 bytes | 64-bit slot counter, 8 bytes little-endian |
| Digest to channel | Lemire multiply-shift on 32-bit chunks of the digest, with rejection (unbiased); on rejection of all chunks, `retry++` and re-hash | `digest mod 13` |
| Slot counter | 56 bits, auto-increment | 64-bit in the hop models, 32-bit register in the fault model |

Consequences:

- For slots below 2^56 and `retry = 0` the two compute the **same 64-bit digest**. They then map it to a channel
  differently, so the **channel sequences are not equal**. Do not use the Python hops as test vectors for the RTL.
- `digest mod 13` has a modulo bias of at most 13 / 2^64 per channel, far below anything the labs can measure.
  The RTL removes even that by rejection.
- What the labs teach does not depend on the mapping: the leakage points of labs 3 and 4 (`v3 = k1 ^ C3 ^ m` and the
  first addition `v2 + v3`) are before the reduction; the state registers faulted in lab 5 (key, slot counter, FSM,
  output register) exist in both; and the output statistics used in labs 1, 2 and 6 are uniform over 13 channels in both.

## What is modelled, in one table

| Lab | Model | Assumption |
|---|---|---|
| 3, 4 | `core/leakage.py` | Each trace sample is the Hamming weight (or distance) of one byte plus Gaussian noise. No alignment, jitter, glitches or coupling. Masking is at share-byte level. |
| 5 | `core/faultsim.py` | Faults are bit flips or sequencing errors in receiver-side registers. No physical mechanism, no datapath or voter faults. |
| 5 | `core/ge_model.py` | Gate-equivalent proxy from assumed per-cell areas. Not a synthesis result. |
| 6 | `core/trojan.py` | Trigger counter plus output mux, observed only through the channel sequence. |
| 6 | `core/puf.py` | Ring-oscillator frequencies = layout gradient + Gaussian process variation + read noise + linear temperature term. |
