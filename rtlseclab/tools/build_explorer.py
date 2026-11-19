"""Build explorer/trace_explorer.html: ONE self-contained offline file (no CDN, no network). Simulated data (ASSUMED Hamming-weight leakage)
is generated here with the kit's own simulator and embedded as JSON; the page does the CPA itself in JavaScript.
Usage: python -m rtlseclab.tools.build_explorer"""
import os, json
import numpy as np
from rtlseclab.core.leakage import rand64, bytes_of, HW
from rtlseclab.core.siphash import C3, split_key

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
N = 3000


def data():
    key = bytes(range(16)); k1 = split_key(key)[1]
    rng = np.random.default_rng(2026)
    m = rand64(rng, N); mb = bytes_of(m)                                   # (N,8)
    k1b = np.array([(k1 >> (8 * i)) & 255 for i in range(8)], dtype=np.uint8)
    c3b = np.array([(C3 >> (8 * i)) & 255 for i in range(8)], dtype=np.uint8)
    v3 = mb ^ k1b[None, :] ^ c3b[None, :]
    r = bytes_of(rand64(rng, N))                                           # fresh mask byte per trace and byte position
    z = rng.normal(0, 1, (N, 3, 8))                                        # unit noise for: unmasked, share0, share1
    return dict(N=N, m=mb.reshape(-1).tolist(), r=r.reshape(-1).tolist(), c3=c3b.tolist(), k1=k1b.tolist(),
                z=np.round(z, 3).reshape(-1).tolist())


def build():
    tpl = open(os.path.join(ROOT, "explorer", "template.html")).read()
    out = tpl.replace("/*__DATA__*/null", json.dumps(data(), separators=(",", ":")))
    dst = os.path.join(ROOT, "explorer", "trace_explorer.html")
    open(dst, "w").write(out)
    return dst, len(out)


if __name__ == "__main__":
    print(build())
