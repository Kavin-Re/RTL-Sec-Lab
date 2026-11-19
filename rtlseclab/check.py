"""python -m rtlseclab.check  -- runs every lab's solution.py through its auto-grader and prints the PASS/FAIL lines.
Options:  --starters   also run each starter.py (expected: every task FAIL with 'not implemented yet', never a crash)
          --lab N      only lab N
Exit status 0 only if every solution task passes."""
import glob, importlib.util, os, sys, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _grader(lab_dir):
    spec = importlib.util.spec_from_file_location("_grader_" + os.path.basename(lab_dir), os.path.join(lab_dir, "grader.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    only = argv[argv.index("--lab") + 1] if "--lab" in argv else None
    from rtlseclab.grading import grade
    labs = sorted(glob.glob(os.path.join(ROOT, "labs", "lab*")))
    if only:
        labs = [d for d in labs if os.path.basename(d).startswith("lab" + only + "_")]
    total = passed = 0; bad = []
    for d in labs:
        g = _grader(d)
        res = grade(g.TASKS[0].tid and os.path.basename(d), g.TASKS, os.path.join(d, "solution.py"))
        total += len(res); passed += sum(1 for r in res if r[1])
        bad += ["%s %s" % (os.path.basename(d), r[0].tid) for r in res if not r[1]]
        if "--starters" in argv:
            buf = io.StringIO()
            sres = grade(os.path.basename(d) + " (starter)", g.TASKS, os.path.join(d, "starter.py"), out=lambda s: buf.write(s + "\n"))
            ni = sum(1 for r in sres if (not r[1]) and "not implemented" in r[2])
            print("   starter: %d/%d tasks FAIL as 'not implemented yet' (the rest: %s)" % (ni, len(sres), "none" if ni == len(sres) else "see below"))
            if ni != len(sres):
                print(buf.getvalue()); bad.append(os.path.basename(d) + " starter")
    print("\nKIT CHECK: %d/%d solution tasks PASS across %d labs%s" % (passed, total, len(labs), "" if not bad else "   PROBLEMS: " + ", ".join(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
