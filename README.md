# databrowser

A easy file browser to view data files.

Currently supports parquet,json and csv with the Pandas library

_Based on the example code_browser from Textual._

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

`python3 data_browser.py [optional path]`

_S3 Support_

with the help of S3Path and S3fs the browser now supports s3.

use `databrowser s3://` to start browsing buckets

or `databrowser s3://bucket/path/subdir/` to browse a specific directory.

it uses the default aws credentials in the environment

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
