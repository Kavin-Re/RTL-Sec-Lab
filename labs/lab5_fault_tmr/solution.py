"""Lab 5 - Fault injection and the cost of TMR.  SOLUTION.

Own design, simulation only. Faults are ABSTRACT bit flips / sequencing errors in a model of the receiver's key/counter/FSM registers;
no physical fault mechanism (voltage, clock, laser, EM) is modelled. Area numbers are a gate-equivalent PROXY (rtlseclab/core/ge_model.py),
not a synthesis result. Read rtl/hop_keyed.v for the engine; rtlseclab/core/faultsim.py documents the link model and the schemes.
Run:    python labs/lab5_fault_tmr/solution.py
Grade:  python labs/lab5_fault_tmr/grader.py labs/lab5_fault_tmr/solution.py
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from math import comb
import numpy as np
from rtlseclab.core import faultsim, ge_model


# ---- Task 1 ---------------------------------------------------------------------------------------------
def majority(a, b, c):
    """Bitwise 2-of-3 majority of three Python ints (a TMR voter)."""
    # >>> SOLUTION: (a & b) | (a & c) | (b & c)
    return (a & b) | (a & c) | (b & c)
    # <<< SOLUTION


def parity(x, nbits):
    """Even parity (XOR of all bits) of the low `nbits` bits of x: returns 0 or 1."""
    # >>> SOLUTION: popcount of x masked to nbits, modulo 2
    return bin(x & ((1 << nbits) - 1)).count("1") & 1
    # <<< SOLUTION


# ---- Task 2 ---------------------------------------------------------------------------------------------
def p_tmr_fail_w2(width):
    """Exact probability that TWO random bit flips in the 3*width stored bits (3 copies of a width-bit register, uniformly random
    distinct positions) make the voted value wrong. One flip alone is always out-voted; two flips defeat the vote only when they hit the
    SAME bit index in two different copies."""
    # >>> SOLUTION: count the pairs (bit index, pair of copies) = 3*width and divide by C(3*width, 2)
    return 3 * width / comb(3 * width, 2)
    # <<< SOLUTION


def tmr_fail_mc(width, w, n, seed):
    """Monte Carlo estimate of the same probability for w flips: rng = np.random.default_rng(seed); each trial picks w distinct positions
    from range(3*width) (rng.choice(3*width, w, replace=False)), position p -> copy p // width, bit p % width; start from three copies of
    value 0, flip, vote with majority(); a trial fails if the vote is not 0. Return the failure fraction over n trials."""
    # >>> SOLUTION: loop n times, flip, vote, count
    rng = np.random.default_rng(seed)
    bad = 0
    for _ in range(n):
        cp = [0, 0, 0]
        for p in rng.choice(3 * width, w, replace=False):
            cp[int(p) // width] ^= 1 << (int(p) % width)
        bad += majority(*cp) != 0
    return bad / n
    # <<< SOLUTION


# ---- Task 3 ---------------------------------------------------------------------------------------------
def overheads():
    """Area overhead in percent of the baseline engine for every scheme in ge_model.scheme_costs() (it returns (baseline_GE, {scheme: extra_GE})).
    Return {scheme: percent} without the 'baseline' entry."""
    # >>> SOLUTION: 100 * extra / baseline for each entry
    B, extra = ge_model.scheme_costs()
    return {k: 100.0 * v / B for k, v in extra.items() if k != "baseline"}
    # <<< SOLUTION


# ---- Task 4 ---------------------------------------------------------------------------------------------
CASES = [("ctr", 1), ("ctr", 2), ("key", 1), ("key", 2), ("fsm", 1), ("out", 1)]


def fault_table(n=300, seed=7):
    """Run faultsim.campaign(scheme, site, w, n, seed) for every scheme in faultsim.SCHEMES and every (site, w) in CASES.
    Return {(scheme, site, w): campaign_result_dict}."""
    # >>> SOLUTION: double loop
    return {(sch, site, w): faultsim.campaign(sch, site, w, n, seed) for sch in faultsim.SCHEMES for site, w in CASES}
    # <<< SOLUTION


# ---- Task 5 ---------------------------------------------------------------------------------------------
def cheapest_scheme(table, max_pdesync):
    """Among the schemes TMR ('tmr') and duplicate+parity ('dcp') (state protection only), return the name of the one with the smaller area
    overhead (overheads(): 'TMR_state' for tmr, 'DMR_parity_state' for dcp) whose WORST p_desync over the SINGLE-fault cases
    (ctr,1) (key,1) (fsm,1) (out,1) is <= max_pdesync. Return None if neither qualifies."""
    # >>> SOLUTION: compute worst single-fault p_desync per scheme, filter, take min overhead
    ov = overheads()
    cost = {"tmr": ov["TMR_state"], "dcp": ov["DMR_parity_state"]}
    ok = []
    for sch in ("tmr", "dcp"):
        worst = max(table[(sch, s, w)]["p_desync"] for s, w in (("ctr", 1), ("key", 1), ("fsm", 1), ("out", 1)))
        if worst <= max_pdesync:
            ok.append((cost[sch], sch))
    return min(ok)[1] if ok else None
    # <<< SOLUTION


# ---- Task 6 (stretch) ----------------------------------------------------------------------------------------
def common_mode_vote(value, bit):
    """A clock/voltage glitch can flip the SAME bit in all three copies. Return the voted value after flipping `bit` in every copy."""
    # >>> SOLUTION: flip the bit in all three copies and vote
    c = value ^ (1 << bit)
    return majority(c, c, c)
    # <<< SOLUTION


if __name__ == "__main__":
    print("exact P(TMR fails | 2 flips): ctr(32) %.4f, key(128) %.4f ; Monte Carlo ctr %.4f" % (p_tmr_fail_w2(32), p_tmr_fail_w2(128), tmr_fail_mc(32, 2, 20000, 1)))
    print({k: round(v, 1) for k, v in overheads().items()})
    t = fault_table()
    for site, w in CASES:
        print("%-3s w=%d  p_desync: " % (site, w) + "  ".join("%s %.2f" % (s, t[(s, site, w)]["p_desync"]) for s in faultsim.SCHEMES))
    print("cheapest scheme with p_desync <= 0.05 on single faults:", cheapest_scheme(t, 0.05))
    print("common-mode flip of bit 3 in value 0:", common_mode_vote(0, 3), "(TMR does not help)")
