# Repository Guidelines

## Project Structure & Module Organization
- Core simulation lives in `core/` (physics, nodes, environment, quantization) and `controller/` (RIS controller, pathfinding, beamforming, ML sweep helpers). Web UI and REST API sit in `app/` (`web/`, `api/`, `static/` with thread-safe wrappers in `thread_safe_network.py`). The interactive shell is in `cli/`, while the packaged CLI wrapper is under `risnet/` with the `risnet` entry point. Example scripts and notebooks are under `examples/`; tests are in `tests/`; configuration helpers are in `config/`; utility scripts live in `tools/` and `bin/`.

## Build, Test, and Development Commands
- Create a virtualenv and install dev deps: `python -m venv .venv && .venv\Scripts\activate` then `pip install -e .[dev]`. For runtime only, use `pip install -e .`.
- Run the CLI locally: `python main.py --cli` (interactive) or `risnet testall --exec-only` to run a command then exit. Start the web UI: `python main.py --web --host 0.0.0.0 --port 5000` (served by Waitress).
- Execute examples: `python examples/script/example_waveform_level.py` or `python examples/aruco_marker_generation_example.py` as needed.
- Test suite: `pytest tests` or `pytest --cov=core --cov=controller tests` for coverage focus on simulation logic.

## Coding Style & Naming Conventions
- Python 3.7+ with 4-space indentation. Auto-format with Black (line length 100) and keep imports isort/Black compatible; flake8 and mypy are available via the `dev` extra. Use snake_case for modules/functions, CamelCase for classes, and keep CLI commands lowercase with hyphen-free verbs (mirroring existing commands).
- Prefer type hints in new code, avoid global state in controllers, and keep algorithms pluggable (follow registry patterns in `controller/pathfinding` and `core/quantization`).

## Testing Guidelines
- Place new tests in `tests/` with `test_*.py` naming. Use pytest fixtures over ad-hoc globals; set deterministic seeds when randomness is involved (existing ML sweep tests demonstrate patterns).
- Cover both core physics (loss, beam calculations) and controller behaviors (pathfinding, beamforming decisions). Include regression assertions for angles/SNRs when adding new algorithms or quantizers. Keep tests headless (no GUI or network).

## Commit & Pull Request Guidelines
- Follow the short, imperative style used in history (e.g., "Implement DE localization sweep", "fix connect and sweep"). Keep subjects under ~72 chars and prefer a single focused change per commit.
- PRs should describe motivation, key changes, and test results (`pytest ...`). Link issues when applicable. Include CLI transcripts or screenshots for UI changes (web dashboard) and note config impacts (`config/`, `.risnet_network.json`). Request review when new APIs or commands are added.
