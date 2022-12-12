# -*- coding: Utf-8 -*-

from __future__ import annotations

import ast
from os.path import splitext
from typing import Any, Generator


class DunderAll:
    name = "dunder-all"
    version = "0.1.0"

    def __init__(self, tree: ast.Module) -> None:
        self.__tree: ast.Module = tree

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        tree: ast.Module = self.__tree
        misplaced_import_lines: list[tuple[int, int]] = []
        for node in tree.body:
            match node:
                case ast.ImportFrom(module="__future__"):
                    continue
                case ast.Import() | ast.ImportFrom():
                    misplaced_import_lines.append((node.lineno, node.col_offset))
                    continue
                case ast.Assign(targets=[ast.Name(id="__all__")]) | ast.AnnAssign(target=ast.Name(id="__all__")):
                    break
                case _:
                    continue
        else:  # __all__ not found
            return
        for lineno, col_offset in misplaced_import_lines:
            yield (
                lineno,
                col_offset,
                "DAL001 'import' statement before __all__ declaration",
                type(self),
            )


class Stubs:
    name = "stubs-only-checks"
    version = "0.1.0"

    EXT = ".pyi"

    def __init__(self, tree: ast.Module, filename: str) -> None:
        self.__tree: ast.Module | None
        if splitext(filename)[1] == Stubs.EXT:
            self.__tree = tree
        else:
            self.__tree = None

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        tree: ast.Module | None = self.__tree
        if tree is None:
            return

        for node in tree.body:
            match node:
                case ast.ImportFrom(module="__future__"):
                    yield node.lineno, node.col_offset, "STB001 __future__ import in stub file", type(self)
                    break
                case _:
                    continue
