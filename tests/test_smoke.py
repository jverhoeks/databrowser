"""Headless smoke tests for the DataBrowser TUI.

These drive the app through Textual's stable ``run_test()`` / Pilot harness so they
survive dependency upgrades and act as a regression tripwire for the data-load path
and the dtype toggle.
"""

import pandas as pd
import pytest

from databrowser.data_browser import DataBrowser
from databrowser.widgets import DirectoryFilterTree
from textual.widgets import DataTable


@pytest.fixture()
def data_dir(tmp_path):
    """A directory containing one file per supported tabular format."""
    df = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
    df.to_csv(tmp_path / "sample.csv", index=False)
    df.to_json(tmp_path / "sample.json")
    df.to_parquet(tmp_path / "sample.parquet")
    df.to_feather(tmp_path / "sample.feather")
    df.to_orc(tmp_path / "sample.orc")
    df.to_csv(tmp_path / "sample.tsv", sep="\t", index=False)
    df.to_excel(tmp_path / "sample.xlsx", index=False)
    (tmp_path / "sample.html").write_text(df.to_html(index=False))
    # A frame larger than ROW_LIMIT to exercise truncation reporting.
    pd.DataFrame({"n": range(250)}).to_csv(tmp_path / "big.csv", index=False)
    return tmp_path


async def _select(app, pilot, path):
    """Select a file in the tree and wait for the background load + render."""
    tree = app.query_one(DirectoryFilterTree)
    tree.post_message(DirectoryFilterTree.FileSelected(str(path)))
    await pilot.pause()
    await app.workers.wait_for_complete()  # the read runs in a thread worker
    await pilot.pause()


async def test_tree_loads_supported_files(data_dir):
    """The tree mounts and lists the supported files in the target directory."""
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        tree = app.query_one(DirectoryFilterTree)
        labels = {str(node.label) for node in tree.root.children}
        assert "sample.csv" in labels
        assert "sample.parquet" in labels
        assert "sample.json" in labels


@pytest.mark.parametrize(
    "filename",
    [
        "sample.csv",
        "sample.tsv",
        "sample.parquet",
        "sample.feather",
        "sample.orc",
        "sample.json",
        "sample.xlsx",
        "sample.html",
    ],
)
async def test_selecting_file_populates_table(data_dir, filename):
    """Selecting a data file loads it into the DataTable with rows and columns."""
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / filename)
        table = app.query_one("#data", DataTable)
        assert len(table.columns) > 0
        assert table.row_count > 0


async def test_dtype_toggle_switches_view(data_dir):
    """Pressing 'd' switches the table to the field/dtype summary view."""
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / "sample.csv")

        await pilot.press("d")
        await pilot.pause()
        table = app.query_one("#data", DataTable)
        headers = [str(col.label) for col in table.columns.values()]
        assert headers == ["field", "dtype"]


async def test_row_limit_and_status(data_dir):
    """A file larger than ROW_LIMIT is capped to ROW_LIMIT rows and reports truncation."""
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / "big.csv")
        table = app.query_one("#data", DataTable)
        assert table.row_count == DataBrowser.ROW_LIMIT
        assert "showing first" in app.sub_title


async def test_configurable_row_limit(data_dir):
    """A custom row_limit caps the rendered rows and is reflected in the status."""
    app = DataBrowser(str(data_dir), row_limit=5)
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / "big.csv")
        table = app.query_one("#data", DataTable)
        assert table.row_count == 5
        assert "showing first 5 rows" in app.sub_title


async def test_corrupt_file_reports_error(data_dir):
    """A file that fails to parse surfaces an error and leaves the table empty."""
    (data_dir / "broken.parquet").write_bytes(b"not a real parquet file")
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / "broken.parquet")
        table = app.query_one("#data", DataTable)
        assert table.row_count == 0
        assert "ERROR" in app.sub_title


async def test_unsupported_file_is_rejected(data_dir):
    """Selecting an unsupported file type does not populate the table."""
    (data_dir / "notes.txt").write_text("hello")
    app = DataBrowser(str(data_dir))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _select(app, pilot, data_dir / "notes.txt")
        table = app.query_one("#data", DataTable)
        assert table.row_count == 0
        assert "Unsupported" in app.sub_title
