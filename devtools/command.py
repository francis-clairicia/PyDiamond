# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["AbstractCommand"]

import os
import shlex
import subprocess
from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass
class Configuration:
    venv_dir: Path

    def get_script(self, name: str) -> Path:
        return self.venv_dir / "bin" / name

    def get_module_exec(self, name: str, *, python_args: Sequence[str] = ()) -> str:
        return shlex.join([os.fspath(self.python_path), *python_args, "-m", name])

    @property
    def python_path(self) -> Path:
        return self.get_script("python3")


class AbstractCommand(metaclass=ABCMeta):
    def __init__(self, config: Configuration) -> None:
        self.config = config

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return {}

    @classmethod
    def accepts_unknown_args(cls) -> bool:
        return True

    @classmethod
    @abstractmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        raise NotImplementedError

    @abstractmethod
    def run(self, __args: Any, __unparsed_args: Sequence[str], /) -> int:
        raise NotImplementedError

    def validate_args(self, unparsed_args: Sequence[str], *, posargs: bool = False) -> Sequence[str]:
        unparsed_args = tuple(arg.strip() for arg in unparsed_args)
        if not posargs and any(not arg.startswith("-") or not arg.lstrip("-") for arg in unparsed_args):
            raise ValueError("Positional arguments are forbidden")
        return unparsed_args

    def log(self, *args: object, sep: str | None = None, end: str | None = None) -> None:
        if sep is None:
            sep = " "
        if end is None:
            end = "\n"
        print(*args, sep=sep, end=end)

    def exec_command(self, cmd: str | bytes | os.PathLike[str] | os.PathLike[bytes], *args: str, check: bool = True) -> int:
        whole_cmd_args = [*shlex.split(os.fsdecode(cmd)), *args]
        self.log(shlex.join(whole_cmd_args))
        return subprocess.run(whole_cmd_args, check=check).returncode
