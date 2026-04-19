# Anki Vocab Exporter Agent Guide

This repository is an Anki addon. Keep changes scoped to addon behavior and packaging.

## Primary References

- [README.md](README.md) for installation, usage, and export format examples.

## Setup And Run

- Development link: run `python link.py` from repo root to link [plugin](plugin) into Anki addons as `AnkiVocabExporter`.
- Reload cycle: restart Anki after code changes.
- Formatting: Black line length is 120 (see [pyproject.toml](pyproject.toml)).
- Tests: no automated test suite in this repo.

## Architecture

- Entry hook: [plugin/__init__.py](plugin/__init__.py) registers deck browser context menu action and opens dialog.
- UI/state: [plugin/dialog.py](plugin/dialog.py) builds Qt dialog, loads/saves addon config, and launches export.
- Domain models: [plugin/models.py](plugin/models.py) defines `ExportSettings` and `ExportResult`.
- Core logic: [plugin/exporter.py](plugin/exporter.py) builds Anki queries, groups cards by maturity, and writes output.
- Persistence: [plugin/config.py](plugin/config.py) merges defaults with saved addon config.

## Codebase Conventions

- Use type hints consistently; follow existing Python typing style.
- Keep Anki-dependent access inside runtime methods (use `mw` only when collection is available).
- Preserve existing maturity buckets in [plugin/exporter.py](plugin/exporter.py) unless task explicitly changes export semantics.
- Output files use `.md` extension but content is sectioned CSV; preserve CSV escaping behavior in `escape_csv`.

## Change Map

- Add or change dialog options: [plugin/dialog.py](plugin/dialog.py).
- Add config keys or migrations: [plugin/config.py](plugin/config.py) and dialog apply/save paths.
- Change grouping/query logic: [plugin/exporter.py](plugin/exporter.py) query constants and section builders.
- Change menu entry points: [plugin/__init__.py](plugin/__init__.py).

## Manual Validation Checklist

- Open Anki and verify menu entry appears in deck options.
- Run export with selected fields and confirm output file is generated.
- Validate sections and card counts for selected statuses.
- Confirm config persistence by reopening dialog and checking prior selections.
- If predictive export is enabled, verify multiple dated files are produced.