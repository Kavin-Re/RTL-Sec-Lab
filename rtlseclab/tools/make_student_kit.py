"""Export the student hand-out copy of the kit: everything a participant needs, without solution.py, answer_key.md,
the facilitator guide, the kit self-tests or the generator tools.

Usage: python -m rtlseclab.tools.make_student_kit [out_dir=dist/rtl-sec-lab-student]

This keeps honest students from tripping over the answers; it is not an anti-cheating measure. The graders compare
against reference models in rtlseclab/core/, so those models necessarily ship with the student copy (see README)."""
import glob, os, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB_FILES = ("handout.md", "starter.py", "grader.py", "expected.json")
PKG_SKIP = {"check.py", "tools", "__pycache__"}

STUDENT_README = """# RTL-Sec-Lab - student copy

Simulation only: every trace, fault, trojan and PUF in this kit comes from a simple assumed model, not from a device.

Needs Python 3 and numpy. For each lab read `labs/labN_*/handout.md`, fill in the TODOs in `starter.py`, then grade yourself:

    python labs/lab1_lfsr_break/grader.py labs/lab1_lfsr_break/starter.py

The grader prints PASS or FAIL per task. `explorer/trace_explorer.html` (open it in a browser, works offline) goes with
labs 3 and 4. `rtl/` holds the Verilog of the two hop engines for reading; the kit does not simulate RTL.
"""


def build(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    n = 0
    for lab in sorted(glob.glob(os.path.join(ROOT, "labs", "lab*"))):
        dst = os.path.join(out, "labs", os.path.basename(lab)); os.makedirs(dst)
        for f in LAB_FILES:
            shutil.copy2(os.path.join(lab, f), dst); n += 1
    shutil.copytree(os.path.join(ROOT, "rtlseclab"), os.path.join(out, "rtlseclab"),
                    ignore=lambda d, names: [x for x in names if x in PKG_SKIP or x.endswith(".pyc")])
    shutil.copytree(os.path.join(ROOT, "rtl"), os.path.join(out, "rtl"))
    os.makedirs(os.path.join(out, "explorer"))
    shutil.copy2(os.path.join(ROOT, "explorer", "trace_explorer.html"), os.path.join(out, "explorer"))
    with open(os.path.join(out, "README.md"), "w") as f:
        f.write(STUDENT_README)
    leaked = [p for p in glob.glob(os.path.join(out, "**", "*"), recursive=True)
              if os.path.basename(p) in ("solution.py", "answer_key.md", "facilitator_guide.md")]
    assert not leaked, leaked
    return n


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "dist", "rtl-sec-lab-student")
    if out == ROOT or ROOT.startswith(out + os.sep):
        sys.exit("refusing to export over the kit itself: " + out)
    n = build(out)
    print("student kit: %d lab files + rtlseclab/ + rtl/ + explorer -> %s" % (n, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
