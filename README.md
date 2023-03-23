# databrowser

A easy file browser to view data files.

Currently supports parquet,json and csv with the Pandas library

_Based on the example code_browser from Textual._

## install

The package is published on pypi <https://pypi.org/project/databrowser/>

run `pip install databrowser`  (`pip install databrowser --upgrade` to get latest version)

Then just execute `databrowser`

## Build

Execute `poetry install` to install the package and the dependencies

Run `python3 src/databrowser/data_browser.py`
or run `poetry run databrowser` to execute in virtual env

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

## examples

![Screenshot data](images/screenshot_data.svg)

![Screenshot dtype](images/screenshot_dtype.svg)
