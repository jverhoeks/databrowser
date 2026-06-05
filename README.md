# databrowser

[![PyPI version](https://img.shields.io/pypi/v/databrowser.svg)](https://pypi.org/project/databrowser/)
[![Python versions](https://img.shields.io/pypi/pyversions/databrowser.svg)](https://pypi.org/project/databrowser/)

A terminal file browser for quickly viewing data files, from local disk or S3.

Supports csv, tsv, parquet, feather, orc, json, xlsx, xls, xml and html — read into pandas DataFrames
and shown in a scrollable table (with a dtype view). Built on
[Textual](https://textual.textualize.io/).

_Originally based on the example code_browser from Textual._

## install

The package is published on pypi <https://pypi.org/project/databrowser/>

run `pip install databrowser`  (`pip install databrowser --upgrade` to get latest version)

Then just execute `databrowser`

## Build

This project uses [uv](https://docs.astral.sh/uv/) (Python >= 3.13).

Execute `uv sync` to create the virtual env and install the package and its dependencies.

Run `uv run databrowser` to execute in the virtual env
(or `uv run python src/databrowser/data_browser.py`).

## Usage

`databrowser [optional path]` (defaults to the current directory)

_Remote filesystems_

Any [fsspec](https://filesystem-spec.readthedocs.io/) URL works, not just local paths:

* `databrowser s3://bucket/path/` — S3 (uses the default AWS credentials in the environment)
* `databrowser hf://datasets/org/name` — Hugging Face datasets (set `HF_TOKEN` for private ones)
* `databrowser gs://bucket/path/` — Google Cloud Storage (needs `gcsfs` installed)

The protocol is resolved automatically, so the same browsing works for every backend.

Select a data file to view

* press F to hide the filebrowser
* press D to show the dtypes
* press S to save a screenshot in svg

* press Q to quit

By default the preview shows the first 100 rows. Set `DATABROWSER_ROWS` to change it,
e.g. `DATABROWSER_ROWS=500 databrowser data/`.

## examples

![Screenshot data](https://raw.githubusercontent.com/jverhoeks/databrowser/main/images/screenshot_data.svg)

![Screenshot dtype](https://raw.githubusercontent.com/jverhoeks/databrowser/main/images/screenshot_dtype.svg)
