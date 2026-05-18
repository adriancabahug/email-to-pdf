"""
Folder filtering with a single recursive collector and two
predicate strategies. Replaces duplicated fast/deep recursion.
"""

from __future__ import annotations

from typing import Callable, List, Protocol, TypeVar

T = TypeVar("T")


class FolderLike(Protocol):
    Name: str
    Folders: List["FolderLike"]


class Predicate(Protocol):
    def __call__(self, name: str) -> bool:
        ...


class FolderResolver:
    """
    One recursive implementation. Strategies are just callables.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_fast_folders(root: T) -> List[T]:
        return _collect(root, _FastPredicate())

    @staticmethod
    def get_deep_folders(root: T) -> List[T]:
        return _collect(root, _DeepPredicate())

    @staticmethod
    def should_skip_folder(name: str) -> bool:
        return not _DeepPredicate()(name)


# ---------------------------------------------------------------------- #
# Shared recursion
# ---------------------------------------------------------------------- #
def _collect(folder: FolderLike, predicate: Predicate) -> List[FolderLike]:
    result: List[FolderLike] = []
    _recurse(folder, predicate, result)
    return result


def _recurse(folder: FolderLike, predicate: Predicate, acc: List[FolderLike]) -> None:
    if predicate(folder.Name):
        acc.append(folder)
    for child in folder.Folders:
        _recurse(child, predicate, acc)


# ---------------------------------------------------------------------- #
# Strategy implementations
# ---------------------------------------------------------------------- #
class _FastPredicate:
    """Skips clutter folders for fast search mode."""
    SKIP: set[str] = {
        "Deleted Items",
        "Junk Email",
        "RSS Feeds",
        "Outbox",
        "Sync Issues",
        "Conflicts",
    }

    def __call__(self, name: str) -> bool:
        return name not in self.SKIP


class _DeepPredicate:
    """Permissive deep search; only skips obviously non-mail folders."""
    SKIP: set[str] = {
        "RSS Feeds",
        "Sync Issues",
    }

    def __call__(self, name: str) -> bool:
        return name not in self.SKIP