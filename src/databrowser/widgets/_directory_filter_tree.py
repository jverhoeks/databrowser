"""Tree widget that browses any fsspec filesystem (local, s3, hf, gs, …) with a suffix filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import fsspec
from rich.style import Style
from rich.text import Text, TextType
from textual.message import Message
from textual.widgets._tree import TOGGLE_STYLE, Tree, TreeNode


@dataclass
class DirEntry:
    """Attaches directory information to a node."""

    path: str  # path within the filesystem (no protocol prefix)
    is_dir: bool
    loaded: bool = False


class DirectoryFilterTree(Tree[DirEntry]):
    """A Tree widget that presents files and directories from any fsspec filesystem.

    The target may be a local path (``./data``) or any fsspec URL — ``s3://bucket/dir/``,
    ``hf://datasets/org/name`` (needs ``huggingface_hub``), ``gs://…``, etc. The protocol is
    resolved with ``fsspec.core.url_to_fs`` and listing uses the resulting filesystem, so the
    same code works for every backend.

    Args:
        path: Path or fsspec URL to browse.
        file_filter: File suffixes to show (e.g. ``[".csv", ".parquet"]``); directories
            are always shown.
        name: The name of the widget, or None for no name. Defaults to None.
        id: The ID of the widget in the DOM, or None for no ID. Defaults to None.
        classes: A space-separated list of classes, or None for no classes. Defaults to None.
        disabled: Whether the directory tree is disabled or not.
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "directory-tree--folder",
        "directory-tree--file",
        "directory-tree--extension",
        "directory-tree--hidden",
    }
    """
    | Class | Description |
    | :- | :- |
    | `directory-tree--extension` | Target the extension of a file name. |
    | `directory-tree--file` | Target files in the directory structure. |
    | `directory-tree--folder` | Target folders in the directory structure. |
    | `directory-tree--hidden` | Target hidden items in the directory structure. |

    See also the [component classes for `Tree`][textual.widgets.Tree.COMPONENT_CLASSES].
    """

    DEFAULT_CSS = """
    DirectoryTree > .directory-tree--folder {
        text-style: bold;
    }

    DirectoryTree > .directory-tree--file {

    }

    DirectoryTree > .directory-tree--extension {
        text-style: italic;
    }

    DirectoryTree > .directory-tree--hidden {
        color: $text 50%;
    }
    """

    class FileSelected(Message, bubble=True):
        """Posted when a file is selected.

        Attributes:
            path: The full path/URL of the file that was selected (with protocol for
                remote filesystems), ready to be handed to a pandas reader.
        """

        def __init__(self, path: str) -> None:
            self.path: str = path
            super().__init__()

    def __init__(  # pylint: disable=too-many-arguments
        self,
        path: str,
        file_filter: list[str],
        *,
        name: str | None = None,
        id: str | None = None,  # pylint: disable=W0622
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        # Resolve the protocol once; `self.fs` then drives all listing/loading.
        self.fs, self.root_path = fsspec.core.url_to_fs(path)
        protocols = self.fs.protocol if isinstance(self.fs.protocol, tuple) else (self.fs.protocol,)
        self.is_local = bool({"file", "local"} & set(protocols))
        self.file_filter = file_filter

        super().__init__(
            path,
            data=DirEntry(self.root_path, True),
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    @staticmethod
    def _basename(path: str) -> str:
        """Last path segment, protocol-agnostic."""
        return path.rstrip("/").rsplit("/", 1)[-1]

    def _suffix(self, path: str) -> str:
        """Lower-cased file extension (including the dot), or '' if none."""
        base = self._basename(path)
        return "." + base.rsplit(".", 1)[-1].lower() if "." in base else ""

    def _file_url(self, path: str) -> str:
        """Full URL to hand to a loader: plain path locally, protocol-prefixed remotely."""
        return path if self.is_local else self.fs.unstrip_protocol(path)

    def process_label(self, label: TextType):
        """Process a str or Text into a label.

        Args:
            label: Label.

        Returns:
            A Rich Text object.
        """
        if isinstance(label, str):
            text_label = Text(label)
        else:
            text_label = label
        first_line = text_label.split()[0]
        return first_line

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style):
        node_label = node.label.copy()
        node_label.stylize(style)

        if node.allow_expand:
            prefix = ("📂 " if node.is_expanded else "📁 ", base_style + TOGGLE_STYLE)
            node_label.stylize_before(self.get_component_rich_style("directory-tree--folder", partial=True))
        else:
            prefix = (
                "📄 ",
                base_style,
            )
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--file", partial=True),
            )
            node_label.highlight_regex(
                r"\..+$",
                self.get_component_rich_style("directory-tree--extension", partial=True),
            )

        if node_label.plain.startswith("."):
            node_label.stylize_before(self.get_component_rich_style("directory-tree--hidden"))

        text = Text.assemble(prefix, node_label)
        return text

    def load_directory(self, node: TreeNode[DirEntry]) -> None:
        """Load the selected directory into nodes and show."""
        assert node.data is not None
        node.data.loaded = True

        entries = self.fs.ls(node.data.path, detail=True)
        # directories first, then case-insensitive by name
        entries.sort(key=lambda e: (e.get("type") != "directory", self._basename(e["name"]).lower()))
        for entry in entries:
            name = entry["name"]
            is_dir = entry.get("type") == "directory"
            if is_dir or self._suffix(name) in self.file_filter:
                node.add(
                    self._basename(name),
                    data=DirEntry(name, is_dir),
                    allow_expand=is_dir,
                )
        node.expand()

    def on_mount(self) -> None:
        """Load the root directory on startup."""
        self.load_directory(self.root)

    def on_tree_node_expanded(self, event: Tree.NodeSelected) -> None:
        """event: on tree node expansion"""
        event.stop()
        dir_entry = event.node.data
        if dir_entry is None:
            return
        if dir_entry.is_dir:
            if not dir_entry.loaded:
                self.load_directory(event.node)
        else:
            self.post_message(self.FileSelected(self._file_url(dir_entry.path)))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """event: on tree node selected"""
        event.stop()
        dir_entry = event.node.data
        if dir_entry is None:
            return
        if not dir_entry.is_dir:
            self.post_message(self.FileSelected(self._file_url(dir_entry.path)))
