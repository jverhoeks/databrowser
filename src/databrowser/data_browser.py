"""
Data browser example.

Run with:

    python data_browser.py PATH

"""

import pathlib
import sys

import pandas as pd
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import var
from textual.widgets import DataTable, Footer, Header, Static
from .widgets import DirectoryFilterTree


class Notification(Static):
    """Helper class for notications"""

    def on_mount(self) -> None:
        """event: mount"""
        self.set_timer(3, self.remove)

    def on_click(self) -> None:
        """event:click"""
        self.remove()


class DataBrowser(App):
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
        ".parquet": pd.read_parquet,
        ".json": pd.read_json,
    }

    show_tree = var(True)
    show_dtype = var(False)
    dataframe = None

    def _load_table(self, df_in=None):
        """internal function to load the table"""
        table = self.query_one("#data", DataTable)
        table.clear(columns=True)

        if df_in:
            self.dataframe = df_in

        if self.show_dtype:
            show_df = pd.DataFrame(
                self.dataframe.dtypes.apply(lambda x: x.name).reset_index()
            )
            show_df.columns = ["field", "dtype"]
        else:
            show_df = self.dataframe

        table.add_columns(*show_df.columns.to_list())
        table.zebra_stripes = True
        for i in range(min(100, len(show_df))):
            table.add_row(*show_df.iloc[i])

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        path = "./" if len(sys.argv) < 2 else sys.argv[1]
        yield Header()
        with Container():
            yield DirectoryFilterTree(
                path,
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

    def on_directory_filter_tree_file_selected(
        self, event: DirectoryFilterTree.FileSelected
    ) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()

        suffix = pathlib.Path(event.path).suffix.lower()

        try:
            if suffix in self.LOADERS:
                self._load_table(self.LOADERS[suffix](event.path))
            else:
                self.sub_title = f"Unsupported file type:  {suffix}"
        except Exception as exc:  # pylint: disable=W0703
            self.sub_title = f"ERROR {exc} {suffix}"
        else:
            self.sub_title = event.path

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree

    def action_toggle_dtype(self) -> None:
        """Called in response to key binding."""
        self.show_dtype = not self.show_dtype
        self._load_table()

    def action_screenshot(self, filename=None, path: str = "./") -> None:
        """Save an SVG "screenshot". This action will save an SVG file containing
           the current contents of the screen.

        Args:
            filename: Filename of screenshot, or None to auto-generate. Defaults to None.
            path: Path to directory. Defaults to "./".
        """
        self.bell()
        path = self.save_screenshot(filename, path)
        message = Text.assemble("Screenshot saved to ", (f"'{path}'", "bold green"))
        self.screen.mount(Notification(message))


def run():
    """Run helper"""
    DataBrowser().run()


if __name__ == "__main__":
    run()
