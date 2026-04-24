# Contributing to Macena CS2 Analyzer

Thank you for your interest in contributing. This document describes how to
propose changes, the standards your code must meet, and the review process.

> **[English](CONTRIBUTING.md)** | **[Italiano](CONTRIBUTING_IT.md)** | **[Portugues](CONTRIBUTING_PT.md)**

## License

By submitting a pull request you agree that your contribution is licensed under
the same dual license as the project (Proprietary / Apache 2.0). See [LICENSE](LICENSE).

## Getting Started

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-fork>/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI-main

# 2. Create and activate a virtual environment (Python 3.10+)
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify everything works
python tools/headless_validator.py   # Must exit 0
python -m pytest Programma_CS2_RENAN/tests/ tests/ --tb=short
```

## Pull Request Process

1. **Branch from `main`** — name your branch `feature/<topic>` or `fix/<topic>`.
2. **One logical change per commit** — keep commits atomic and meaningful.
3. **All pre-commit hooks must pass** — `pre-commit run --all-files`.
4. **All tests must pass** — `python -m pytest Programma_CS2_RENAN/tests/ tests/`.
5. **Headless validator must pass** — `python tools/headless_validator.py` (exit 0).
6. **Coverage must not decrease** — current threshold is 40%, rising incrementally.
7. **Open a PR against `main`** with a clear description of what and why.

## Coding Standards

- **Python 3.10+** with type hints on public interfaces.
- **Black** formatter (line length 100). **isort** for import ordering.
- **No magic numbers** — extract to named constants or config.
- **Structured logging** via `get_logger("cs2analyzer.<module>")`.
- **No silent failures** — errors must surface immediately and explicitly.
- **Every tick is sacred** — tick decimation is strictly forbidden.
- Docstrings only where logic is non-obvious. No boilerplate documentation.

## Commit Messages

- Use semantic, imperative-mood messages (e.g. "Fix stale checkpoint handling").
- Keep the first line under 72 characters.
- Reference issue numbers where applicable (`Fixes #42`).

## What We Accept

- Bug fixes with tests proving the fix.
- Performance improvements with benchmarks.
- New features that align with the project vision (coaching AI for CS2 players).
- Documentation improvements.
- Test coverage improvements.

## What We Do Not Accept

- Changes that break existing tests or the headless validator.
- Cosmetic-only formatting changes outside of the files you are modifying.
- Dependencies without clear justification and license compatibility check.
- Code that introduces security vulnerabilities (see OWASP Top 10).

## Reporting Issues

Use the [GitHub Issues](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/issues)
tracker. Include:

- Steps to reproduce (or a minimal demo file if applicable).
- Expected vs actual behavior.
- Python version, OS, and relevant hardware (GPU model if ML-related).

## Security Vulnerabilities

See [SECURITY.md](SECURITY.md) for responsible disclosure guidelines.

## Questions?

Open a discussion or issue. We value quality over speed.
