"""
Data browser example.

Run with:

    python data_browser.py PATH

"""

import argparse
import os
import pathlib
from importlib.metadata import PackageNotFoundError, version

import pandas as pd
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import var
from textual.widgets import DataTable, Footer, Header
from textual.worker import get_current_worker

from .widgets import DirectoryFilterTree


class DataBrowser(App):  # pylint: disable=too-many-instance-attributes
    """Textual data browser app."""

    CSS_PATH = "data_browser.css"
    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("d", "toggle_dtype", "Toggle Dtype"),
        ("s", "screenshot", "Screenshot"),
        ("q", "quit", "Quit"),
    ]

    LOADERS = {
        ".csv": pd.read_csv,
        ".tsv": pd.read_table,  # tab-separated
        ".parquet": pd.read_parquet,
        ".feather": pd.read_feather,
        ".orc": pd.read_orc,
        ".json": pd.read_json,
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".xml": pd.read_xml,
        ".html": pd.read_html,
    }

    # Default number of rows rendered in the preview table (override per instance
    # or via the DATABROWSER_ROWS environment variable).
    ROW_LIMIT = 100
    # Loaders whose pandas reader accepts ``nrows`` so we can avoid reading a whole
    # multi-GB file just to preview the first rows.
    NROWS_LOADERS = {".csv", ".tsv", ".xlsx"}

    show_tree = var(True)
    show_dtype = var(False)

    def __init__(self, path: str = "./", row_limit: int = ROW_LIMIT, **kwargs) -> None:
        super().__init__(**kwargs)
        self.path = path
        self.row_limit = max(1, row_limit)
        self.dataframe = None
        self._filename = ""
        # Whether the last read was capped by ``nrows`` (so the true row count is unknown).
        self._capped = False

    @work(thread=True, exclusive=True)
    def _load_file(self, suffix: str, file_path: str) -> None:
        """Read a data file into a DataFrame off the UI thread.

        pandas readers are blocking, so running them in a worker thread keeps the
        interface responsive while a large file loads. The table is then rendered
        back on the UI thread via ``call_from_thread``.
        """
        worker = get_current_worker()
        try:
            read_kwargs = {"nrows": self.row_limit + 1} if suffix in self.NROWS_LOADERS else {}
            data = self.LOADERS[suffix](file_path, **read_kwargs)
            # pd.read_html returns a list of DataFrames (one per <table>); preview the first.
            dataframe = data[0] if isinstance(data, list) else data
        except Exception as exc:  # pylint: disable=broad-except
            if not worker.is_cancelled:
                self.call_from_thread(self._on_load_error, exc, file_path)
            return

        # A thread read can't be interrupted; if a newer selection superseded this one
        # while we were reading, drop the stale result instead of showing the wrong file.
        if worker.is_cancelled:
            return

        self.dataframe = dataframe
        self._filename = pathlib.Path(file_path).name
        self._capped = suffix in self.NROWS_LOADERS
        self.call_from_thread(self._render_table)

    def _on_load_error(self, exc: Exception, file_path: str) -> None:
        """Surface a load failure to the user (runs on the UI thread)."""
        self.query_one("#data", DataTable).loading = False
        self.notify(f"{type(exc).__name__}: {exc}", title="Failed to load", severity="error")
        self.sub_title = f"ERROR loading {file_path}"

    def _render_table(self) -> None:
        """Render the current DataFrame into the DataTable (UI thread only)."""
        table = self.query_one("#data", DataTable)
        table.loading = False
        table.clear(columns=True)

        if self.dataframe is None:
            return

        if self.show_dtype:
            show_df = pd.DataFrame(self.dataframe.dtypes.apply(lambda x: x.name).reset_index())
            show_df.columns = ["field", "dtype"]
        else:
            show_df = self.dataframe

        table.add_columns(*show_df.columns.to_list())
        table.zebra_stripes = True
        for i in range(min(self.row_limit, len(show_df))):
            table.add_row(*show_df.iloc[i])

        self.sub_title = self._status_text()

    def _status_text(self) -> str:
        """Build the subtitle describing what is currently shown."""
        rows, cols = self.dataframe.shape
        if self.show_dtype:
            return f"{self._filename} — dtypes ({cols} fields)"
        if rows > self.row_limit:
            if self._capped:
                shown = f"showing first {self.row_limit} rows"
            else:
                shown = f"showing {self.row_limit} of {rows} rows"
        else:
            shown = f"{rows} rows"
        return f"{self._filename} — {shown}, {cols} columns"

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header()
        with Container():
            yield DirectoryFilterTree(
                self.path,
                list(self.LOADERS.keys()),
                id="tree-view",
            )
            with Vertical(id="data-view"):
                yield DataTable(id="data")
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:
        """event: mount"""
        del event
        self.query_one(DirectoryFilterTree).focus()

    def on_directory_filter_tree_file_selected(self, event: DirectoryFilterTree.FileSelected) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()

        suffix = pathlib.Path(event.path).suffix.lower()
        if suffix not in self.LOADERS:
            self.notify(f"Unsupported file type: {suffix}", severity="warning")
            self.sub_title = f"Unsupported file type: {suffix}"
            return

        self.query_one("#data", DataTable).loading = True
        self.sub_title = f"Loading {pathlib.Path(event.path).name} …"
        self._load_file(suffix, event.path)

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree

    def action_toggle_dtype(self) -> None:
        """Called in response to key binding."""
        if self.dataframe is None:
            self.notify("Select a data file first", severity="warning")
            return
        self.show_dtype = not self.show_dtype
        self._render_table()

    def action_screenshot(self, filename=None, path: str = "./") -> None:
        """Save an SVG "screenshot". This action will save an SVG file containing
           the current contents of the screen.

        Args:
            filename: Filename of screenshot, or None to auto-generate. Defaults to None.
            path: Path to directory. Defaults to "./".
        """
        self.bell()
        saved = self.save_screenshot(filename, path)
        self.notify(f"Screenshot saved to '{saved}'", title="Screenshot")


def _version() -> str:
    """Installed package version (for ``--version``)."""
    try:
        return version("databrowser")
    except PackageNotFoundError:  # running from a source checkout without metadata
        return "0+unknown"


def run():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="databrowser",
        description="Browse and view data files (csv, tsv, parquet, feather, orc, json, "
        "xlsx, xls, xml, html) from local disk, S3, Hugging Face, or any fsspec filesystem.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="./",
        help="file/directory path or fsspec URL (e.g. s3://bucket/dir/, "
        "hf://datasets/org/name); defaults to the current directory",
    )
    parser.add_argument(
        "--rows",
        type=int,
        metavar="N",
        help=f"max rows to preview (default {DataBrowser.ROW_LIMIT}, or $DATABROWSER_ROWS)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    args = parser.parse_args()

    if args.rows is not None:
        row_limit = args.rows
    else:
        try:
            row_limit = int(os.environ.get("DATABROWSER_ROWS", DataBrowser.ROW_LIMIT))
        except ValueError:
            row_limit = DataBrowser.ROW_LIMIT

    DataBrowser(args.path, row_limit=row_limit).run()


if __name__ == "__main__":
    run()
