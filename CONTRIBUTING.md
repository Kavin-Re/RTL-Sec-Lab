# Contributing to RTL-Sec-Lab

Thanks for your interest. RTL-Sec-Lab is a simulation-only workshop kit on the hardware security of a small keyed hop/PRF engine. Read `docs/facilitator_guide.md` first.

## Getting started

Python 3 and numpy; no network access is needed.

```
python -m rtlseclab.check                      # all solutions through all graders
python -m rtlseclab.check --starters           # every starter must FAIL cleanly
python labs/lab3_power_cpa/grader.py labs/lab3_power_cpa/starter.py
```

## Testing

```
python -m unittest tests.test_graders
python tests/test_explorer.py                  # needs Playwright; skipped otherwise
```

Starters are generated from solutions (see the README); edit the solution, then regenerate. Copied code must carry an ORIGIN header.

## Pull requests

- Open an issue first for larger changes.
- Keep PRs focused and fill in the pull request template.
- Follow `.editorconfig` and match the style of surrounding code.
- Say which simulator and tool versions you used for RTL changes.

## Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
