"""Auto-grader for Lab 1 (pure Python + numpy, deterministic seeds).
Usage:  python labs/lab1_lfsr_break/grader.py [path/to/your_script.py]      (default: starter.py next to this file)
Prints PASS/FAIL per task; exit status 0 only if everything passes."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import numpy as np
from rtlseclab.grading import Task, main, seed, load_expected
from rtlseclab.core import lfsr as ref

EXP_ALL = load_expected(HERE)


def t1(m):
    rng = np.random.default_rng(seed(1))
    states = rng.integers(1, 65536, 3000)
    for s in states[:1000]:
        got = m.lfsr_step(int(s))
        assert int(got) == int(ref.lfsr_step(int(s))), "lfsr_step(%d) = %s, expected %d" % (s, got, ref.lfsr_step(int(s)))
    arr = states.astype(np.uint32)
    got = np.asarray(m.lfsr_step(arr))
    assert got.shape == arr.shape and np.array_equal(got.astype(np.uint32), ref.lfsr_step(arr)), "array version differs (does it work on numpy arrays?)"
    assert int(m.lfsr_step(0xACE1)) == int(ref.lfsr_step(0xACE1))
    return True, "3000 states ok"


def t2(m):
    for sd in (0xACE1, 1, 0xFFFF, 12345, 777):
        assert list(m.hop_stream(sd, 64)) == [int(x) for x in ref.lfsr_schedule(64, 13, sd)], "stream differs for seed 0x%X" % sd
    assert list(m.hop_stream(0, 20)) == list(m.hop_stream(1, 20)), "seed 0 must behave like seed 1"
    first = list(m.hop_stream(0xACE1, 10))
    assert first == [2, 9, 11, 12, 6, 4, 8, 10, 0, 8], "reset-state stream wrong: %s" % first
    return True, "first hops from 0xACE1 = %s" % first


def t3(m):
    full = np.arange(1, 65536, dtype=np.uint32)
    e = EXP_ALL["T3"][0]
    got = m.filter_candidates(full, 0)
    n = len(got)
    assert e["lo"] <= n <= e["hi"], "%d survivors after one hop on channel 0, expected %d" % (n, e["expected"])
    rng = np.random.default_rng(seed(3))
    for ch in (0, 5, 12):
        sub = rng.choice(full, 4000, replace=False)
        want = ref.lfsr_step(sub); want = want[want % 13 == ch]
        got = np.asarray(m.filter_candidates(sub, ch))
        assert sorted(got.tolist()) == sorted(want.tolist()), "wrong survivors for channel %d" % ch
    return True, "%d survivors on channel 0" % n


def _truth_state(sd, n):
    s = sd
    for _ in range(n):
        s = int(ref.lfsr_step(s))
    return s


def t4(m):
    e = EXP_ALL["T4"][0]
    rng = np.random.default_rng(seed(4))
    seeds = [int(x) for x in rng.integers(1, 65536, 30)]
    used = []
    for sd in seeds:
        obs = ref.lfsr_schedule(60, 13, sd)
        st, n = m.break_lfsr([int(x) for x in obs])
        assert st is not None, "attack failed for seed %d" % sd
        assert st == _truth_state(sd, n), "recovered state is not the true state after %d hops (seed %d)" % (n, sd)
        pred = m.predict(st, 60 - n)
        assert [int(x) for x in pred] == [int(x) for x in obs[n:]], "prediction of the future hops is wrong"
        used.append(n)
    mean = float(np.mean(used))
    assert e["lo"] <= mean <= e["hi"], "mean hops %.2f outside [%.1f, %.1f]" % (mean, e["lo"], e["hi"])
    assert max(used) <= e["max_hops"], "worst case %d hops" % max(used)
    return True, "mean %.2f hops (min %d max %d), predictions exact" % (mean, min(used), max(used))


def t5(m):
    e1, e2 = EXP_ALL["T5"]
    seeds = list(range(11, 31))
    curve = [float(x) for x in m.survivor_curve(seeds, 8)]
    assert len(curve) == 8
    ratios = [curve[i] / curve[i + 1] for i in range(4)]
    for i, r in enumerate(ratios):
        assert e1["lo"] <= r <= e1["hi"], "ratio hop %d->%d is %.2f, expected about 4" % (i + 1, i + 2, r)
    assert e2["lo"] <= curve[3] <= e2["hi"], "survivors after hop 4 = %.1f" % curve[3]
    return True, "survivors %s ; ratios %s" % ([round(c, 1) for c in curve[:5]], [round(r, 2) for r in ratios])


def t6(m):
    e = EXP_ALL["T6"][0]
    rng = np.random.default_rng(seed(6))
    hops = []
    for _ in range(40):
        key = bytes(rng.integers(0, 256, 16, dtype=np.uint8))
        h = m.attack_keyed(key)
        assert h is not None, "candidate set never emptied on a keyed stream"
        hops.append(int(h))
    mean = float(np.mean(hops))
    assert e["lo"] <= mean <= e["hi"] and max(hops) <= e["max_hops"], "mean %.2f max %d" % (mean, max(hops))
    return True, "empties after %.2f hops on average (max %d)" % (mean, max(hops))


def t7(m):
    full = np.arange(1, 65536, dtype=np.uint32)
    nxt = ref.lfsr_step(full)
    for h in range(13):
        want = sorted(set((nxt[(full % 13) == h] % 13).tolist()))
        got = sorted(int(x) for x in m.successors(h))
        assert got == want, "successors(%d) = %s, brute force says %s" % (h, got, want)
    e = EXP_ALL["T7"][1]
    a = float(m.lfsr_likeness(ref.lfsr_schedule(2000, 13, 0xACE1)))
    b = float(m.lfsr_likeness(ref.keyed_schedule(bytes(range(16)), 0, 2000)))
    assert a == 1.0, "an LFSR stream must score 1.0, got %.3f" % a
    assert e["lo"] <= b <= e["hi"], "keyed stream scored %.3f, expected about 4/13" % b
    return True, "LFSR %.2f, keyed %.3f" % (a, b)


TASKS = [Task("T1", "lfsr_step", t1), Task("T2", "hop_stream", t2), Task("T3", "filter_candidates", t3),
         Task("T4", "break_lfsr + predict", t4), Task("T5", "survivor_curve (4x per hop, not 13x)", t5),
         Task("T6", "attack_keyed", t6), Task("T7", "successors / lfsr_likeness", t7, stretch=True)]

if __name__ == "__main__":
    main("Lab 1 - LFSR break", TASKS, HERE)
