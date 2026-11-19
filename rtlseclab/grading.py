"""Tiny pure-Python grading harness shared by all six graders (no dependencies beyond numpy being importable by the labs).

A grader defines TASKS = [Task(id, title, fn), ...]. fn(mod) receives the imported student/solution module and returns
(ok: bool, detail: str); raising AssertionError / NotImplementedError / any other exception is reported as FAIL (never a crash).
Output: one line per task, "PASS" or "FAIL", then a summary. Exit status 0 only if every task passes.

Determinism: every grader derives all random draws from `seed(offset)`. The base seed is fixed (1000); the environment variable
RTLSECLAB_SEED_SHIFT adds an integer to it, which the robustness test uses to check that tolerances are not tuned to one stream.
"""
import importlib.util, json, os, sys, traceback, time

KIT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def seed(offset=0):
    return 1000 + int(os.environ.get("RTLSECLAB_SEED_SHIFT", "0")) + offset


class Task:
    def __init__(self, tid, title, fn, stretch=False):
        self.tid, self.title, self.fn, self.stretch = tid, title, fn, stretch


def load_module(path):
    path = os.path.abspath(path)
    if KIT_ROOT not in sys.path:
        sys.path.insert(0, KIT_ROOT)
    name = "_student_" + os.path.basename(os.path.dirname(path)) + "_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_expected(lab_dir):
    """expected.json -> {task id: [item, ...]} ; items carry the tolerance band (lo, hi) the grader enforces."""
    out = {}
    with open(os.path.join(lab_dir, "expected.json")) as f:
        for e in json.load(f)["items"]:
            out.setdefault(e["task"], []).append(e)
    return out


def in_band(x, lo, hi):
    return lo <= x <= hi


def run_tasks(tasks, mod, out=print):
    results = []
    for t in tasks:
        t0 = time.time()
        try:
            ok, detail = t.fn(mod)
            ok = bool(ok)
        except NotImplementedError as e:
            ok, detail = False, "not implemented yet: %s" % (e or "TODO")
        except AssertionError as e:
            ok, detail = False, "assertion: %s" % (e or "failed")
        except Exception as e:                      # never crash the grader on student code
            tb = traceback.extract_tb(e.__traceback__)[-1]
            ok, detail = False, "%s: %s (line %d)" % (type(e).__name__, e, tb.lineno)
        results.append((t, ok, detail, time.time() - t0))
        out("%s  %s %s%s  [%s]  (%.1fs)" % ("PASS" if ok else "FAIL", t.tid, t.title, " (stretch)" if t.stretch else "", detail, time.time() - t0))
    return results


def grade(title, tasks, path, out=print):
    out("== %s : grading %s" % (title, os.path.relpath(path)))
    mod = load_module(path)
    res = run_tasks(tasks, mod, out)
    npass = sum(1 for r in res if r[1])
    out("SUMMARY: %d/%d PASS%s" % (npass, len(res), "" if npass == len(res) else "  (%d FAIL)" % (len(res) - npass)))
    return res


def main(title, tasks, lab_dir, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else os.path.join(lab_dir, "starter.py")
    res = grade(title, tasks, path)
    sys.exit(0 if all(r[1] for r in res) else 1)
