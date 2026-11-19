"""Grader tests (unittest, standard library only):  python -m unittest tests.test_graders   or   python tests/test_graders.py
 1. every solution passes every task of its grader
 2. every starter FAILs every task with 'not implemented yet' and never crashes the grader
 3. starters are in sync with the solutions (make_starters --check)
 4. mutation tests: a deliberately broken solution makes the intended task FAIL (the graders do discriminate)
 5. the kit is standalone (no import of FHSS code) and every copied file carries an ORIGIN header
Seed robustness is a separate, slower script: tests/test_robustness.py"""
import glob, importlib.util, os, re, sys, tempfile, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from rtlseclab.grading import run_tasks, load_module

LABS = sorted(glob.glob(os.path.join(ROOT, "labs", "lab*")))


def tasks_of(lab):
    spec = importlib.util.spec_from_file_location("g_" + os.path.basename(lab), os.path.join(lab, "grader.py"))
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    return g.TASKS


MUTANTS = [   # (lab dir prefix, text to find, replacement, task that must FAIL)
    ("lab1", "(s >> 3)", "(s >> 4)", "T1"),
    ("lab2", "for _ in range(3):\n        t = y ^ (t >> 11)", "for _ in range(1):\n        t = y ^ (t >> 11)", "T2"),
    ("lab3", "carry = carry_in(k0, v3, b)\n        k0 |= int(np.argmax(scores_stage2", "carry = np.zeros(len(m), dtype=np.uint8)\n        k0 |= int(np.argmax(scores_stage2", "T4"),
    ("lab4", "np.argmax(-stage1_scores(so_combine(T, b), mb, b))", "np.argmax(stage1_scores(so_combine(T, b), mb, b))", "T4"),
    ("lab5", "return (a & b) | (a & c) | (b & c)", "return (a & b) | (a & c)", "T1"),
    ("lab6", "e = W / M\n    return", "e = W / 12\n    return", "T1"),
]


class Graders(unittest.TestCase):
    def test_solutions_pass(self):
        for lab in LABS:
            res = run_tasks(tasks_of(lab), load_module(os.path.join(lab, "solution.py")), out=lambda s: None)
            self.assertTrue(all(r[1] for r in res), "%s: %s" % (os.path.basename(lab), [(r[0].tid, r[2]) for r in res if not r[1]]))

    def test_starters_fail_cleanly(self):
        for lab in LABS:
            res = run_tasks(tasks_of(lab), load_module(os.path.join(lab, "starter.py")), out=lambda s: None)
            for t, ok, detail, _ in res:
                self.assertFalse(ok, "%s %s passes with an untouched starter" % (os.path.basename(lab), t.tid))
                self.assertIn("not implemented", detail, "%s %s: %s" % (os.path.basename(lab), t.tid, detail))

    def test_starters_in_sync(self):
        from rtlseclab.tools.make_starters import main
        self.assertEqual(main(check=True), 0)

    def test_mutants_are_caught(self):
        for prefix, find, rep, tid in MUTANTS:
            lab = [d for d in LABS if os.path.basename(d).startswith(prefix)][0]
            src = open(os.path.join(lab, "solution.py")).read()
            self.assertIn(find, src, "mutation anchor missing in " + prefix)
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "mutant.py"); open(p, "w").write(src.replace(find, rep, 1))
                res = {r[0].tid: r[1] for r in run_tasks(tasks_of(lab), load_module(p), out=lambda s: None)}
            self.assertFalse(res[tid], "%s mutant survived task %s" % (prefix, tid))

    def test_standalone_and_origin(self):
        for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
            if os.sep + "tests" + os.sep in f:
                continue
            for line in open(f):
                if re.match(r"\s*(import|from)\s", line):
                    self.assertNotRegex(line, r"(?i)fhss|hop_model|sidechannel\b", "%s imports FHSS code: %s" % (f, line.strip()))
        for f in glob.glob(os.path.join(ROOT, "rtlseclab", "core", "*.py")) + glob.glob(os.path.join(ROOT, "rtl", "*.v")):
            if os.path.basename(f) == "__init__.py":
                continue
            self.assertIn("ORIGIN", open(f).read(600), "no ORIGIN header in " + f)

    def test_expected_json_has_every_task(self):
        import json
        for lab in LABS:
            ids = {t.tid for t in tasks_of(lab)}
            got = {e["task"] for e in json.load(open(os.path.join(lab, "expected.json")))["items"]}
            self.assertEqual(ids, got, os.path.basename(lab))


if __name__ == "__main__":
    unittest.main(verbosity=2)
