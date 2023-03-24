""" Updated widget to support filter and other Filesystems """
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from s3path import S3Path
from rich.style import Style
from rich.text import Text, TextType

from textual.message import Message
from textual.widgets._tree import TOGGLE_STYLE, Tree, TreeNode


@dataclass
class DirEntry:
    """Attaches directory information ot a node."""

    path: str
    is_dir: bool
    file_system: str = "local"
    loaded: bool = False


class DirectoryFilterTree(Tree[DirEntry]):
    """A Tree widget that presents files and directories.

    Args:
        path: Path to directory.
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

        Can be handled using `on_directory_tree_file_selected` in a subclass of
        `DirectoryTree` or in a parent widget in the DOM.

        Attributes:
            path: The path of the file that was selected.
        """

        def __init__(self, path: str) -> None:
            self.path: str = path
            super().__init__()

    def __init__(
        self,
        path: str,
        file_filter: list[str],
        *,
        name: str | None = None,
        id: str | None = None,  # pylint: disable=W0622
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:

        # identity file system
        if path[0:5] == "s3://":
            self.file_system = "s3"
            self.path = path[4:]  # replace s3:// with / for S3Path
        else:
            self.path = path
            self.file_system = "local"

        self.file_filter = file_filter

        super().__init__(
            path,
            data=DirEntry(self.path, True, self.file_system),
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def process_label(self, label: TextType):
        """Process a str or Text into a label. Maybe overridden in a subclass to modify
            how labels are rendered.

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
        node_label = node._label.copy()  # pylint: disable=W0212
        node_label.stylize(style)

        if node._allow_expand:  # pylint: disable=W0212
            prefix = ("📂 " if node.is_expanded else "📁 ", base_style + TOGGLE_STYLE)
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--folder", partial=True)
            )
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
                self.get_component_rich_style(
                    "directory-tree--extension", partial=True
                ),
            )

        if node_label.plain.startswith("."):
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--hidden")
            )

        text = Text.assemble(prefix, node_label)
        return text

    def load_directory(self, node: TreeNode[DirEntry]) -> None:
        """Load the selected directory into nodes and show"""
        assert node.data is not None
        node.data.loaded = True

        if self.file_system == "s3":
            dir_path = S3Path(node.data.path)
        else:
            dir_path = Path(node.data.path)

        directory = sorted(
            list(dir_path.iterdir()),
            key=lambda path: (not path.is_dir(), path.name.lower()),
        )
        for path in directory:
            if path.is_dir() or path.suffix.lower() in self.file_filter:
                node.add(
                    path.name,
                    data=DirEntry(str(path), path.is_dir(), self.file_system),
                    allow_expand=path.is_dir(),
                )
        node.expand()

    def on_mount(self) -> None:
        """Load the root directory on startup"""
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
            self.post_message(self.FileSelected(dir_entry.path))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """event: on tree node selected"""
        event.stop()
        dir_entry = event.node.data
        if dir_entry is None:
            return
        if not dir_entry.is_dir:
            if dir_entry.file_system == "s3":
                path = "s3:/" + dir_entry.path
            else:
                path = dir_entry.path
            self.post_message(self.FileSelected(path))
