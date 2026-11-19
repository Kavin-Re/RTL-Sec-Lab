"""Gate-equivalent (GE) PROXY for the hop engine and its protection schemes.  NOT a synthesis result.

ORIGIN: copied from FHSS-Link/lab4/silicon/ge_model.py (own design, simulation only), unchanged.
1 GE = area of a NAND2.  Per-cell values are typical round numbers for a generic standard-cell library (they vary 20-40 %
between libraries); every number below is an ASSUMPTION so the overheads are only good for relative comparison.
Change CELL to explore sensitivity (see sensitivity())."""

CELL = dict(FF=5.0, MUX2=2.25, XOR2=2.5, AND2=1.25, OR2=1.25, HA=3.5, FA=6.5, MAJ3=4.0)


def engine_breakdown(c=CELL):
    """Compact SipHash-2-4 hop engine: one SipRound per cycle, 128-bit key register, 32-bit slot counter, mod-13 reduction."""
    b = {}
    b["key_reg(128)"] = 128 * (c["FF"] + c["MUX2"])
    b["slot_counter(32)+incrementer"] = 32 * (c["FF"] + c["HA"])
    b["sip_state(4x64 FF)"] = 256 * c["FF"]
    b["sip_adders(4x64b)"] = 4 * 64 * c["FA"]
    b["sip_xor_layers(4x64)"] = 4 * 64 * c["XOR2"]
    b["msg/len/const injection(3x64 XOR)"] = 3 * 64 * c["XOR2"]
    b["state init/load mux(256)"] = 256 * c["MUX2"]
    b["finalise xor(3x64)"] = 3 * 64 * c["XOR2"]
    b["mod-13 reduction + out reg(4)"] = 300 + 4 * c["FF"]
    b["control FSM (~20 FF + logic)"] = 20 * c["FF"] + 150
    return b


def total(b):
    return sum(b.values())


def scheme_costs(c=CELL):
    """Extra GE of each protection scheme relative to the baseline engine."""
    base = engine_breakdown(c)
    B = total(base)
    persistent = base["key_reg(128)"] + base["slot_counter(32)+incrementer"] + base["control FSM (~20 FF + logic)"] + 4 * c["FF"]
    out = {"baseline": 0.0}
    # TMR of persistent state (key reg, counter+incrementer, FSM, output reg); datapath shared. Bitwise majority voters with scrub.
    voters = (128 + 32 + 20 + 4) * c["MAJ3"]
    out["TMR_state"] = 2 * persistent + voters
    # full-engine TMR: three engines + 64->4 bit output voter
    out["TMR_full_engine"] = 2 * B + 4 * c["MAJ3"]
    # duplicated key+counter with parity (1 bit/ctr word, 1 bit/key byte per copy), compare A vs B, parity select mux
    key_dup = base["key_reg(128)"]; ctr_dup = base["slot_counter(32)+incrementer"]
    par_gen = 16 * 7 * c["XOR2"] + 31 * c["XOR2"] + 17 * c["FF"]          # per copy: generators + stored parity flops
    par_chk = 16 * 8 * c["XOR2"] + 32 * c["XOR2"]
    cmp_ = 160 * c["XOR2"] + 160 * c["OR2"]
    sel = 160 * c["MUX2"] + 100
    out["DMR_parity_state"] = key_dup + ctr_dup + 2 * (par_gen + par_chk) + cmp_ + sel
    # lockstep full engine (detect only): second engine + output compare
    out["lockstep_full_engine"] = B + 4 * c["XOR2"] + 3 * c["OR2"]
    return B, out


def trojan_gate_cost(c=CELL, counter_bits=24):
    """Tiny trojan: trigger counter + compare, 8-bit magnitude compare on tapped digest bits, output mux (4 bits)."""
    return counter_bits * (c["FF"] + c["HA"]) + counter_bits * (c["XOR2"] + c["AND2"]) + 8 * (c["XOR2"] + c["AND2"]) + 4 * c["MUX2"]


def sensitivity(scale=(0.7, 1.0, 1.3)):
    """Overhead % when every FF cost is scaled (flops dominate state protection) - crude range."""
    res = {}
    for sc in scale:
        c = dict(CELL); c["FF"] = CELL["FF"] * sc
        B, o = scheme_costs(c)
        res[sc] = {k: 100 * v / B for k, v in o.items()}
    return res


if __name__ == "__main__":
    b = engine_breakdown()
    for k, v in b.items():
        print(f"{k:38s}{v:9.0f}")
    B, o = scheme_costs()
    print("baseline total", round(B))
    for k, v in o.items():
        print(f"{k:24s} +{v:7.0f} GE  ({100*v/B:5.1f} %)")
    print("trojan", round(trojan_gate_cost()), "GE", f"{100*trojan_gate_cost()/B:.1f} %")
