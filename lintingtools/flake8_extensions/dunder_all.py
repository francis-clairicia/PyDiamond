# -*- coding: Utf-8 -*-

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import ClassVar, Generator

from ._common import Error


@dataclass
class DunderAll:
    name: ClassVar[str] = "dunder-all"
    version: ClassVar[str] = "0.1.0"

    tree: ast.Module

    def run(self) -> Generator[Error, None, None]:
        tree: ast.Module = self.tree
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
            yield Error(
                lineno,
                col_offset,
                "DAL001 'import' statement before __all__ declaration",
                type(self),
            )
