"""Generate every labs/*/starter.py from the matching solution.py (single source of truth).

In solution.py a block
        # >>> SOLUTION: <hint shown to the student>
        ...code...
        # <<< SOLUTION
becomes, in starter.py,
        # TODO: <hint shown to the student>
        raise NotImplementedError("TODO")
A line  `# STARTER-ONLY: text` in the solution is dropped; `# >>> STARTER: text` ... `# <<< STARTER` blocks appear only in the starter
(use them for scaffolding such as extra prints). The header docstring line 'SOLUTION' is rewritten to 'STARTER'.
Usage: python -m rtlseclab.tools.make_starters [--check]   (--check exits 1 if a starter is out of date; used by the tests)"""
import os, re, sys, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def convert(src):
    out, skipping, indent = [], False, ""
    for line in src.splitlines():
        m = re.match(r"^(\s*)# >>> SOLUTION:?\s*(.*)$", line)
        if m:
            skipping, indent = True, m.group(1)
            out.append("%s# TODO: %s" % (indent, m.group(2) or "fill in this function"))
            out.append('%sraise NotImplementedError("TODO")' % indent)
            continue
        if re.match(r"^\s*# <<< SOLUTION\s*$", line):
            skipping = False
            continue
        if skipping:
            continue
        out.append(line)
    text = "\n".join(out) + "\n"
    text = text.replace("SOLUTION.", "STARTER (fill in the TODOs).", 1)
    text = text.replace("solution.py", "starter.py")
    return text


def main(check=False):
    bad = 0
    for sol in sorted(glob.glob(os.path.join(ROOT, "labs", "lab*", "solution.py"))):
        dst = os.path.join(os.path.dirname(sol), "starter.py")
        new = convert(open(sol).read())
        old = open(dst).read() if os.path.exists(dst) else None
        if check:
            if old != new:
                print("OUT OF DATE:", os.path.relpath(dst, ROOT)); bad += 1
        else:
            open(dst, "w").write(new); print("wrote", os.path.relpath(dst, ROOT))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
