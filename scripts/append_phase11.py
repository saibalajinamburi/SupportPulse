"""Append Phase 11 documentation to PROJECT_SUMMARY.md."""

PHASE11 = """
## Phase 11: CI/CD with GitHub Actions

### Why CI/CD Matters for ML Projects

A Continuous Integration pipeline automatically runs your tests every time code is pushed to GitHub. For an ML project, this means:
- No broken imports make it to main -- if someone changes schemas.py and breaks a field name, CI catches it before merge
- Math regressions are caught -- if someone changes the PSI formula and produces negative values, the test fails immediately
- New contributors get instant feedback on whether their changes broke anything

**Interview question:** *"What does your CI pipeline test in an ML project where you cannot run models in CI?"*

Answer: Separate concerns. GPU inference (Ollama, embeddings) cannot run in CI -- they need VRAM and a running Ollama server. Everything else can and should be tested:
- Pure Python logic (PII masker, label normalizer, drift math)
- Database I/O (SQLite logger with a temp DB)
- Schema validation (Pydantic models -- no network needed)
These tests run in 1.87 seconds. GPU tests run in evaluation scripts manually.

### New Unit Tests (25 new, 38 total)

| Test File | What It Tests | Count |
|---|---|---|
| test_label_normaliser.py | Category normalization logic | 7 |
| test_pii_masker.py | Email/IP/phone PII masking | 6 |
| test_request_logger.py | SQLite log/retrieve/stats round-trip | 5 |
| test_drift_detector.py | PSI and KL math invariants | 8 |
| test_schemas.py | Pydantic request/response models | 12 |

**Result: 38/38 tests passed in 1.87 seconds.**

Key pattern: pytest's `tmp_path` fixture + `monkeypatch` to redirect `DB_PATH` to a temp file. Tests never touch the production log, run hermetically, and can run in parallel.

### `.github/workflows/ci.yml` -- GitHub Actions

Two jobs run on every push and pull request to main:

**Job 1: unit-tests**
1. Checkout code
2. Set up Python 3.12 with pip caching
3. pip install -r requirements.txt
4. pytest tests/unit/ -v --junitxml=reports/junit.xml
5. Upload JUnit XML as downloadable artifact

**Job 2: lint**
Runs ruff (Rust-based Python linter, 10-100x faster than flake8) to catch unused imports, undefined names, and style issues.

### Phase 11 -- Interview Questions & Answers

**Q: Why use ruff instead of flake8 or pylint?**
A: ruff is written in Rust and is 10-100x faster than Python-based linters. It also combines the functionality of flake8, isort, and many pylint rules into a single tool. The ML/AI community (Hugging Face, LangChain, FastAPI) has largely switched to ruff as the standard.

**Q: What is a JUnit XML report and why upload it as an artifact?**
A: JUnit XML is a standard format for test results understood by GitHub, GitLab, Jenkins, and all major CI platforms. When you upload it, GitHub shows a visual test results panel in the Actions UI -- you can see which tests passed/failed without reading raw logs. This matters when you have 200+ tests and need to quickly find the failing one.

**Q: How would you add integration tests to this CI pipeline?**
A: Integration tests (that call the real FastAPI server) would run in a separate job triggered only on release tags, not on every push. The job would:
1. Start Ollama as a service container (if small enough models)
2. Start uvicorn in the background
3. Run pytest tests/integration/ --timeout=120
4. Stop both servers
On a GPU-free CI runner, you would mock the Ollama calls with pytest-mock and test the API routing logic only.

### Phase 11 Conclusion
- 38/38 unit tests passing in 1.87 seconds
- GitHub Actions CI workflow active on every push and PR to main
- Two CI jobs: unit-tests + ruff lint
- Zero Ollama/GPU dependency in CI -- hermetic and fast
- GitHub: Pushed (.github/workflows/ci.yml, 3 new test files)
"""

with open('PROJECT_SUMMARY.md', 'a', encoding='utf-8') as f:
    f.write(PHASE11)
print('Phase 11 appended successfully.')
