"""Seed-robustness: run the whole kit check with RTLSECLAB_SEED_SHIFT = each shift and report any task that FAILs (tolerances must not be
tuned to one random stream).   python tests/test_robustness.py [n_shifts=20] [workers=4]"""
import os, sys, subprocess, concurrent.futures as cf
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run(shift):
    env = dict(os.environ, RTLSECLAB_SEED_SHIFT=str(shift), PYTHONPATH=ROOT)
    r = subprocess.run([sys.executable, "-m", "rtlseclab.check"], cwd=ROOT, env=env, capture_output=True, text=True)
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    return shift, r.returncode, fails


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    bad = 0
    with cf.ThreadPoolExecutor(w) as ex:
        for shift, rc, fails in ex.map(run, range(n)):
            print("shift %2d: %s" % (shift, "all PASS" if rc == 0 else "FAILS: " + " | ".join(f[:110] for f in fails)), flush=True)
            bad += rc != 0
    print("ROBUSTNESS: %d/%d shifts all-PASS" % (n - bad, n))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
