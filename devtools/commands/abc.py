# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["AbstractCommand"]

import os
import shlex
import subprocess
import sys
from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass
class Configuration:
    venv_dir: Path

    def get_script(self, name: str) -> Path:
        if sys.platform == "win32":
            binpath = "Scripts"
        else:
            binpath = "bin"
        return self.venv_dir / binpath / name

    def get_module_exec(self, name: str, *, python_options: Sequence[str] = ()) -> str:
        return shlex.join([os.fspath(self.python_path), *python_options, "-m", name])

    @property
    def python_path(self) -> Path:
        return self.get_script("python")


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

    def exec_command(
        self,
        cmd: str | os.PathLike[str],
        *args: str,
        check: bool = True,
        verbose: bool = True,
        capture_output: bool = False,
    ) -> int:
        if isinstance(cmd, os.PathLike):
            whole_cmd_args = [os.fspath(cmd), *args]
        else:
            whole_cmd_args = [*shlex.split(cmd), *args]
        if verbose:
            self.log(shlex.join(whole_cmd_args))
        return subprocess.run(whole_cmd_args, check=check, capture_output=capture_output).returncode

    def exec_python_script(
        self,
        name: str,
        *args: str,
        check: bool = True,
        verbose: bool = True,
        capture_output: bool = False,
    ) -> int:
        return self.exec_command(self.config.get_script(name), *args, check=check, verbose=verbose, capture_output=capture_output)

    def exec_module(
        self,
        name: str,
        *args: str,
        python_options: Sequence[str] = (),
        check: bool = True,
        verbose: bool = True,
        capture_output: bool = False,
    ) -> int:
        return self.exec_command(
            self.config.get_module_exec(name, python_options=python_options),
            *args,
            check=check,
            verbose=verbose,
            capture_output=capture_output,
        )
