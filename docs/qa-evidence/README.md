# QA evidence package

This package supports `QA_DEBUGGING_REPORT.pdf`, a portfolio case study of the
NextTech AI Support Bot. It contains real command output captured locally on
29 September 2026. No production credentials or customer records are included.

## Evidence index

- `environment.json`: timestamp, tested commit, baseline commit and runtime versions.
- `pytest.txt`: 62 passing Python tests and 81.66% coverage of CI-selected modules.
- `dashboard.txt`: passing simulated-DOM dashboard regression test.
- `before.txt` / `after.txt`: configuration and greeting behavior at the original
  baseline and the fixed revision. Exit code zero means the measurement ran;
  inspect the final JSON booleans for the defect observations.
- `dashboard-comparison.txt`: before/after raw HTML and status-element observations.
- `ruff.txt`: syntax and undefined-name checks.
- `bandit.txt`: high-severity application source scan; quiet success has no findings
  printed. This is not a full dependency audit or penetration test.
- `migrations.txt`: seven migrations applied to an empty SQLite database.

The Python test duration is suite execution time, not application latency or a
load-test measurement. Existing deprecation warnings are retained as a count.
Docker and local HTTP smoke checks in the report refer to the earlier project
review, not new checks captured in these files.

## Reproduce

From the repository, install `requirements-dev.txt` in a virtual environment,
make Node.js available, and run:

```sh
python scripts/capture_qa_evidence.py
```

The baseline is pinned to `c595d48fbd286864f1d429b256256d0ec67ce802`; the recorded
fixed code is `f38ca9d255066c81d613f732adee569152dee4b4`. A new capture measures the
current checkout and records its commit. Tests use offline providers and synthetic
fixtures. The scripts do not send the HTML injection payload to a live service.

The PDF and editable HTML accompany the raw results. The fix diff is available at
https://github.com/alaamadii/Chat-Bot/pull/32.
