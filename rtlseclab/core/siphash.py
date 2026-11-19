"""SipHash-2-4 (Aumasson & Bernstein) in pure Python plus a numpy-vectorised 8-byte-message version.

ORIGIN: copied and lightly adapted from FHSS-Link/lab4/silicon/siphash.py (own design of the kit author; simulation only).
Changes vs the original: added `popcount64` (numpy < 2.0 has no np.bitwise_count); added a docstring header; no functional change.
Used as the keyed PRF of the hop engine:  hop = SipHash24(key128, slot_counter_64) mod M.
The scalar version has a fault/probe hook used by the fault-injection lab."""
import numpy as np

MASK = (1 << 64) - 1
C0, C1, C2, C3 = 0x736f6d6570736575, 0x646f72616e646f6d, 0x6c7967656e657261, 0x7465646279746573


def rotl(x, b):
    return ((x << b) | (x >> (64 - b))) & MASK


def sipround(v, probe=None):
    v0, v1, v2, v3 = v
    v0 = (v0 + v1) & MASK; v1 = rotl(v1, 13); v1 ^= v0; v0 = rotl(v0, 32)
    v2 = (v2 + v3) & MASK
    if probe is not None:
        probe["v2_after_add"] = v2
    v3 = rotl(v3, 16); v3 ^= v2
    v0 = (v0 + v3) & MASK; v3 = rotl(v3, 21); v3 ^= v0
    v2 = (v2 + v1) & MASK; v1 = rotl(v1, 17); v1 ^= v2; v2 = rotl(v2, 32)
    return [v0, v1, v2, v3]


def split_key(key):
    assert len(key) == 16
    return int.from_bytes(key[:8], "little"), int.from_bytes(key[8:], "little")


def siphash24(key, msg, fault=None, probe=None):
    """key: 16 bytes, msg: bytes -> 64-bit int.
    fault = (round_index 0..7 for an 8-byte msg, word 0..3, xor_mask): XOR mask into v[word] just before that round.
    probe: dict that receives 'v3_after_xor' and 'v2_after_add' of the first block / first round."""
    k0, k1 = split_key(key)
    v = [k0 ^ C0, k1 ^ C1, k0 ^ C2, k1 ^ C3]
    n = len(msg)
    nfull = n // 8
    blocks = [int.from_bytes(msg[8 * i:8 * i + 8], "little") for i in range(nfull)]
    blocks.append((int.from_bytes(msg[8 * nfull:], "little") | ((n & 0xFF) << 56)) & MASK)
    rnd = 0

    def do_rounds(cnt, first=False):
        nonlocal v, rnd
        for j in range(cnt):
            if fault is not None and fault[0] == rnd:
                v[fault[1]] ^= fault[2]
            v = sipround(v, probe if (first and j == 0 and probe is not None and "v2_after_add" not in probe) else None)
            rnd += 1

    for bi, m in enumerate(blocks):
        v[3] ^= m
        if probe is not None and bi == 0:
            probe["v3_after_xor"] = v[3]
        do_rounds(2, first=(bi == 0))
        v[0] ^= m
    v[2] ^= 0xFF
    do_rounds(4)
    return v[0] ^ v[1] ^ v[2] ^ v[3]


# ---------------- numpy vectorised (8-byte little-endian message) ----------------
_U = np.uint64


def _rotl(x, b):
    return (x << _U(b)) | (x >> _U(64 - b))


def _round(v0, v1, v2, v3):
    v0 = v0 + v1; v1 = _rotl(v1, 13); v1 = v1 ^ v0; v0 = _rotl(v0, 32)
    v2 = v2 + v3; v3 = _rotl(v3, 16); v3 = v3 ^ v2
    v0 = v0 + v3; v3 = _rotl(v3, 21); v3 = v3 ^ v0
    v2 = v2 + v1; v1 = _rotl(v1, 17); v1 = v1 ^ v2; v2 = _rotl(v2, 32)
    return v0, v1, v2, v3


def siphash24_u64(k0, k1, m, fault=None):
    """Vectorised SipHash-2-4 of 8-byte messages m (uint64 array). k0,k1: python ints or uint64 arrays (broadcast).
    fault = (round_index, word, mask): same meaning as the scalar version (applied to all elements)."""
    with np.errstate(over="ignore"):
        m = np.asarray(m, dtype=np.uint64)
        k0 = np.asarray(k0, dtype=np.uint64); k1 = np.asarray(k1, dtype=np.uint64)
        v = [k0 ^ _U(C0), k1 ^ _U(C1), k0 ^ _U(C2), k1 ^ _U(C3)]
        v = [np.broadcast_to(x, np.broadcast(m, x).shape).copy() for x in v]
        rnd = 0

        def rounds(cnt):
            nonlocal v, rnd
            for _ in range(cnt):
                if fault is not None and fault[0] == rnd:
                    v[fault[1]] = v[fault[1]] ^ _U(fault[2])
                v = list(_round(*v))
                rnd += 1
        v[3] = v[3] ^ m
        rounds(2)
        v[0] = v[0] ^ m
        b = _U(8 << 56)
        v[3] = v[3] ^ b
        rounds(2)
        v[0] = v[0] ^ b
        v[2] = v[2] ^ _U(0xFF)
        rounds(4)
        return v[0] ^ v[1] ^ v[2] ^ v[3]


def hop_channels(key_or_k0k1, counters, M=13):
    """Hop engine output: SipHash24(key, counter as 8-byte LE) mod M. key_or_k0k1: bytes(16) or (k0,k1)."""
    k0, k1 = split_key(key_or_k0k1) if isinstance(key_or_k0k1, (bytes, bytearray)) else key_or_k0k1
    d = siphash24_u64(k0, k1, np.asarray(counters, dtype=np.uint64))
    return (d % _U(M)).astype(np.int64)


_POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)


def popcount64(x):
    """Hamming weight of each element of a uint64 array (works on every numpy version)."""
    b = np.ascontiguousarray(np.asarray(x, dtype="<u8")).view(np.uint8).reshape(np.shape(x) + (8,))
    return _POP8[b].sum(-1)
