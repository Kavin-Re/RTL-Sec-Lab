"""Fault-injection simulation of the keyed hop engine (hop = SipHash24(key, slot_counter) mod M) at link level.

ORIGIN: copied from FHSS-Link/lab4/silicon/faultsim.py (own design, simulation only). Only change: package-relative import.
SIMULATION ONLY: faults are abstract bit flips / sequencing errors in an RX-side register model; no physical fault mechanism.

Fault sites (one fault event at slot 0 of each trial, RX side):
  ctr : w bit flips in the 32-bit slot counter           (persistent counter offset)
  key : w bit flips in the 128-bit key register          (persistent: hop sequence becomes unrelated)
  fsm : sequencing error in the counter FSM, one event   (counter skips +1/+2 or repeats -1: persistent offset)
  out : upset of the 4-bit hop output register           (one wrong slot, self-healing)
Recovery mechanisms of the link (apply to every scheme, they are part of the link protocol, not the protection):
  * loss-of-lock = L consecutive undelivered packets; an authenticated beacon every B slots (on a fixed rendezvous channel,
    loss prob p_clean) reloads the RX counter if lock is lost.
  * watchdog (optional): if lock is still lost Lw slots after a beacon reload, the key is reloaded from NVM.
Protection schemes (state-only, datapath not modelled):
  none_nowd : no protection, no watchdog       none : no protection, beacon + watchdog
  tmr  : triple copies of key/counter/FSM/output with bitwise majority vote and scrub
  dcp  : duplicate key+counter, parity (1 bit per counter word, 1 per key byte) per copy, A/B compare, parity-select;
         uncorrectable mismatch is DETECTED -> key reloaded from NVM next slot, counter waits for next beacon
Packet loss model: static jammer on channels < kjam, loss prob p_jam on jammed / p_clean otherwise (as in the repo's link_sim).
NOT modelled: TX-side faults, faults inside the SipHash datapath (see the diffusion measurement in lab 5), faults in
voters/comparators/beacon logic, common-mode faults across copies (clock/voltage glitch, laser), spatially adjacent multi-bit upsets,
permanent faults."""
import numpy as np
from .siphash import hop_channels

MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1
SCHEMES = ["none_nowd", "none", "tmr", "dcp"]
SITES = [("ctr", 1), ("ctr", 2), ("ctr", 4), ("key", 1), ("key", 2), ("key", 4), ("fsm", 1), ("out", 1)]


def _parity_groups(site):
    return [(0, 32)] if site == "ctr" else [(8 * i, 8 * i + 8) for i in range(16)]


def _par(x, lo, hi):
    return bin((x >> lo) & ((1 << (hi - lo)) - 1)).count("1") & 1


def inject(scheme, site, w, key_int, ctr, rng):
    """Returns (key_eff, ctr_eff, detected, out_bad)."""
    if site == "out":
        if scheme == "tmr":
            return key_int, ctr, False, False
        return key_int, ctr, scheme == "dcp", True
    if site == "fsm":
        off = int(rng.choice([1, -1, 2]))
        if scheme == "tmr":
            return key_int, ctr, False, False
        if scheme == "dcp":    # one of the two counter copies is off, parity regenerated -> valid parity, copies differ
            faulty_is_A = rng.random() < 0.5
            return key_int, (ctr + off) & MASK32 if faulty_is_A else ctr, True, False   # uncorrectable: default to copy A
        return key_int, (ctr + off) & MASK32, False, False
    width = 32 if site == "ctr" else 128
    val = ctr if site == "ctr" else key_int
    if scheme in ("none", "none_nowd"):
        mask = 0
        for p in rng.choice(width, w, replace=False):
            mask |= 1 << int(p)
        val ^= mask
    elif scheme == "tmr":
        copies = [val, val, val]
        for p in rng.choice(3 * width, w, replace=False):
            copies[int(p) // width] ^= 1 << (int(p) % width)
        a, b, c = copies
        val = (a & b) | (a & c) | (b & c)
    elif scheme == "dcp":
        groups = _parity_groups(site); pw = len(groups)
        data = [val, val]; par = [[_par(val, lo, hi) for lo, hi in groups] for _ in range(2)]
        for p in rng.choice(2 * (width + pw), w, replace=False):
            cp, q = divmod(int(p), width + pw)
            if q < width: data[cp] ^= 1 << q
            else: par[cp][q - width] ^= 1
        ok = [all(_par(data[c], lo, hi) == par[c][g] for g, (lo, hi) in enumerate(groups)) for c in range(2)]
        detected = False
        if ok[0] and not ok[1]: val = data[0]
        elif ok[1] and not ok[0]: val = data[1]
        elif ok[0] and ok[1] and data[0] == data[1]: val = data[0]
        else: val = data[0]; detected = True
        return (key_int, val, detected, False) if site == "ctr" else (val, ctr, detected, False)
    return (key_int, val, False, False) if site == "ctr" else (val, ctr, False, False)


def run_trial(scheme, site, w, rng, H=256, M=13, kjam=1, p_jam=0.95, p_clean=0.01, B=32, L=3, Lw=4):
    key_int = int(rng.integers(0, 2**63)) << 65 | int(rng.integers(0, 2**63)) << 2 | int(rng.integers(0, 4))
    ctr0 = int(rng.integers(0, 2**32))
    true_ctr = (ctr0 + np.arange(H, dtype=np.uint64)) & np.uint64(MASK32)
    kt = (key_int & MASK64, key_int >> 64)
    hop_tx = hop_channels(kt, true_ctr, M)
    key_eff, ctr_eff, detected, out_bad = inject(scheme, site, w, key_int, ctr0, rng)
    kk = (key_eff & MASK64, key_eff >> 64); d = (ctr_eff - ctr0) & MASK32
    hop_rx = np.empty(H, dtype=np.int64)

    def recompute(t0):
        if t0 < H:
            hop_rx[t0:] = hop_channels(kk, (true_ctr[t0:] + np.uint64(d)) & np.uint64(MASK32), M)
    recompute(0)
    if out_bad:
        hop_rx[0] = (hop_tx[0] + 1 + int(rng.integers(M - 1))) % M
    u, ub = rng.random(H), rng.random(H)
    phase = int(rng.integers(B))
    wd = scheme != "none_nowd"
    miss = 0; since_rl = None; key_reload_at = 1 if (detected and site == "key") else -1
    detected_ctr = detected and site in ("ctr", "fsm")
    bad_slots = 0; rec = 0; ever_bad = False; lost = 0; lost_clean = 0
    for t in range(H):
        if key_reload_at == t:
            kk = kt; recompute(t); key_reload_at = -1
        bad = (kk != kt) or d != 0 or (t == 0 and out_bad)
        if bad:
            ever_bad = True; rec = t + 1
        jam = hop_tx[t] < kjam
        thr = p_jam if jam else p_clean
        if u[t] <= thr: lost_clean += 1
        if hop_rx[t] == hop_tx[t] and u[t] > thr:
            miss = 0
        else:
            miss += 1; lost += 1
        lock_lost = miss >= L
        if (t + phase) % B == 0 and ub[t] > p_clean and (lock_lost or detected_ctr):
            if d != 0:
                d = 0; recompute(t + 1)
            since_rl = 0; detected_ctr = False
        elif wd and since_rl is not None:
            if lock_lost:
                since_rl += 1
                if since_rl >= Lw:
                    key_reload_at = t + 1; since_rl = None
            else:
                since_rl = None
    still_bad = (kk != kt) or d != 0
    return dict(desync=ever_bad, unrecovered=still_bad, rec=(H if still_bad else rec), excess_lost=lost - lost_clean,
                lost=lost, lost_clean=lost_clean)


def campaign(scheme, site, w, n, seed, **kw):
    rng = np.random.default_rng(seed)
    rs = [run_trial(scheme, site, w, rng, **kw) for _ in range(n)]
    ds = [r for r in rs if r["desync"]]
    recs = np.array([r["rec"] for r in ds]) if ds else np.array([0])
    return dict(scheme=scheme, site=site, w=w, n=n, p_desync=len(ds) / n, p_unrecovered=float(np.mean([r["unrecovered"] for r in rs])),
                mean_rec=float(recs.mean()) if ds else 0.0, p95_rec=float(np.percentile(recs, 95)) if ds else 0.0,
                mean_excess_lost=float(np.mean([r["excess_lost"] for r in rs])), pdr=1 - float(np.mean([r["lost"] for r in rs])) / kw.get("H", 256))
