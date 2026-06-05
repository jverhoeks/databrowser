# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`databrowser` is a terminal UI (TUI) application for browsing and viewing data files
(csv, tsv, parquet, feather, orc, json, xlsx, xls, xml, html) from local disk, S3, Hugging Face, or any fsspec filesystem. It is built on
[Textual](https://textual.textualize.io/) and reads files into pandas DataFrames.
Originally derived from Textual's `code_browser` example.

## Commands

This project uses **uv** for packaging and environments (Python >= 3.13, developed on 3.14).

```bash
uv sync                              # create .venv and install package + dev deps from uv.lock
uv run databrowser [path]            # run the app (path optional, defaults to ./)
uv run databrowser s3://bucket/dir/  # browse S3 (uses default AWS credentials from environment)

uv run pytest                        # run the headless smoke tests (tests/test_smoke.py)
uv run pytest tests/test_smoke.py::test_dtype_toggle_switches_view   # run a single test
uv run black src tests               # format (line-length 120, isort black profile)
uv run pylint src                    # lint (max-line-length 120)
uv run bandit -c pyproject.toml -r src   # security scan (matches CI)
uv build                             # build sdist + wheel (version derived from git tag)
```

Dependency bumps go through `uv lock` / `uv add`; `uv.lock` is committed.

## Architecture

Two source files in `src/databrowser/`:

- **`data_browser.py`** — the `DataBrowser(App)` Textual app. The `LOADERS` dict maps
  file suffixes to the pandas reader function used to load them; **adding a new file
  format means adding one entry here** (the same dict drives the tree's file filter via
  `list(self.LOADERS.keys())`). Selecting a file runs `_load_file()`, a
  `@work(thread=True)` worker that reads the file **off the UI thread** (pandas readers
  block) and then calls `_render_table()` back on the UI thread via `call_from_thread`, so
  the interface stays responsive on large files (the DataTable shows a loading indicator,
  `table.loading`, while the worker reads). `_render_table()` is also reused for the
  `d` dtype toggle (no re-read). Rendering is capped at `self.row_limit` (default `ROW_LIMIT`
  100, overridable via the `DATABROWSER_ROWS` env var or `DataBrowser(path, row_limit=...)`);
  loaders in `NROWS_LOADERS` (csv, xlsx) are passed `nrows` so large files aren't read in full just to
  preview, and the subtitle (`_status_text()`) reports row/column counts and whether the
  view is truncated. `pd.read_html` returns a *list* of DataFrames, so the first table is
  taken. Key bindings: `f` toggle file tree, `d` toggle dtype view, `s` SVG screenshot,
  `q` quit. The target directory is passed to `DataBrowser(path)` (the `run()` entry point
  reads `sys.argv`); this keeps `compose()` free of global state and makes the app testable
  via Textual's `run_test()` harness (see `tests/test_smoke.py`).

- **`widgets/_directory_filter_tree.py`** — `DirectoryFilterTree`, a subclass of Textual's
  `Tree` that lazily loads directory contents and filters to directories + filtered
  suffixes. The **filesystem abstraction** lives here: `fsspec.core.url_to_fs(path)`
  resolves the protocol (local, `s3://`, `hf://`, `gs://`, …) to a filesystem and listing uses
  `self.fs.ls(..., detail=True)`, so the same iteration/loading code works for every backend
  (the selected file's URL is rebuilt with `self.fs.unstrip_protocol`). Selecting a file posts a
  `FileSelected` message that bubbles up to `DataBrowser.on_directory_filter_tree_file_selected`.

`data_browser.css` styles the layout (the `-show-tree` class toggles tree visibility).

## Release flow (CI)

Versioning is automated — **do not bump the version manually**. The `version` is dynamic,
derived from the git tag by **hatch-vcs** (`[tool.hatch.version] source = "vcs"`). On every
merge to `main`, `publish.yml` runs one job that bumps + pushes the tag (default patch; put
`#minor`/`#major`/`#none` in the merge commit message to change it), then `uv build` +
`uv publish --trusted-publishing always`, then creates the GitHub release. Doing tag and
publish in a single run avoids the `GITHUB_TOKEN`-pushed-tag-doesn't-trigger-workflows
problem and the old double-publish race. `publish.yml` keeps its filename because the PyPI
trusted-publisher config is keyed on it. `python-pr.yml` (pylint + pytest) and
`bandit-pr.yml` run on PRs via uv.
