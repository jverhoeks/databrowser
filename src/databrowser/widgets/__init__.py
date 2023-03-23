# from __future__ import annotations

import typing
# from importlib import import_module

# from textual.case import camel_to_snake

# For any new built-in Widget we create, not only do we have to import them here and add them to `__all__`,
# but also to the `__init__.pyi` file in this same folder - otherwise text editors and type checkers won't
# be able to "see" them.
# if typing.TYPE_CHECKING:
#     from ._directory_filter_tree import DirectoryFilterTree


from ._directory_filter_tree import DirectoryFilterTree

__all__ = [
    "DirectoryFilterTree",
]

# _WIDGETS_LAZY_LOADING_CACHE: dict[str, type[Widget]] = {}


# # Let's decrease startup time by lazy loading our Widgets:
# def __getattr__(widget_class: str) -> type[Widget]:
#     try:
#         return _WIDGETS_LAZY_LOADING_CACHE[widget_class]
#     except KeyError:
#         pass

#     if widget_class not in __all__:
#         raise ImportError(f"Package 'textual.widgets' has no class '{widget_class}'")

#     widget_module_path = f"._{camel_to_snake(widget_class)}"
#     module = import_module(widget_module_path, package="widgets")
#     class_ = getattr(module, widget_class)

#     _WIDGETS_LAZY_LOADING_CACHE[widget_class] = class_
#     return class_
