"""
Data browser example.

Run with:

    python data_browser.py PATH

"""

import pathlib
import sys

import pandas as pd
from rich.syntax import Syntax
from rich.text import Text
from rich.traceback import Traceback
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import var
from textual.widgets import DataTable, Footer, Header, Static
from .widgets import DirectoryFilterTree


class Notification(Static):
    def on_mount(self) -> None:
        self.set_timer(3, self.remove)

    def on_click(self) -> None:
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

    def __load_table(self):
        self.table.clear(columns=True)
        if self.show_dtype:
            show_df = pd.DataFrame(self.df.dtypes.apply(lambda x: x.name).reset_index())
            show_df.columns = ["field", "dtype"]
        else:
            show_df = self.df

        self.table.add_columns(*show_df.columns.to_list())
        self.table.zebra_stripes = True
        for n in range(min(100, len(show_df))):
            self.table.add_row(*show_df.iloc[n])

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
                self.LOADERS.keys(),
                id="tree-view",
            )
            with Vertical(id="data-view"):
                # yield Static(id="data", expand=True)
                yield DataTable(id="data")
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:
        self.query_one(DirectoryFilterTree).focus()

    def on_directory_filter_tree_file_selected(
        self, event: DirectoryFilterTree.FileSelected
    ) -> None:
        """Called when the user click a file in the directory tree."""
        event.stop()
        self.table = self.query_one("#data", DataTable)

        suffix = pathlib.Path(event.path).suffix.lower()

        try:
            if suffix in self.LOADERS:
                self.df = self.LOADERS[suffix](event.path)
                self.__load_table()
            else:
                self.sub_title = f"Unsupported file type:  {suffix}"
        except Exception as exc:
            self.sub_title = f"ERROR {exc} {suffix}"
        else:
            # data_view.update(syntax)
            # self.query_one("#data-view").scroll_home(animate=False)
            self.sub_title = event.path

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree

    def action_toggle_dtype(self) -> None:
        """Called in response to key binding."""
        self.show_dtype = not self.show_dtype
        self.__load_table()

    def action_screenshot(self, filename=None, path: str = "./") -> None:
        """Save an SVG "screenshot". This action will save an SVG file containing the current contents of the screen.

        Args:
            filename: Filename of screenshot, or None to auto-generate. Defaults to None.
            path: Path to directory. Defaults to "./".
        """
        self.bell()
        path = self.save_screenshot(filename, path)
        message = Text.assemble("Screenshot saved to ", (f"'{path}'", "bold green"))
        self.screen.mount(Notification(message))


def run():
    DataBrowser().run()


if __name__ == "__main__":
    run()
