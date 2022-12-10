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
    venv_dir: Path | None

    def get_exec_bin(self, name: str) -> str:
        venv_dir = self.venv_dir
        if venv_dir is None:
            return name
        if sys.platform == "win32":
            binpath = "Scripts"
        else:
            binpath = "bin"
        return os.fspath(venv_dir / binpath / name)

    @property
    def python_path(self) -> str:
        return self.get_exec_bin("python")


class AbstractCommand(metaclass=ABCMeta):
    def __init__(self, config: Configuration) -> None:
        self.config = config

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return {}

    @classmethod
    @abstractmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        raise NotImplementedError

    @abstractmethod
    def run(self, __args: Any, /) -> int:
        raise NotImplementedError

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
        whole_cmd_args = [os.fspath(cmd), *args]
        if verbose:
            self.log(shlex.join(whole_cmd_args))
        try:
            return subprocess.run(whole_cmd_args, check=check, capture_output=capture_output).returncode
        except subprocess.CalledProcessError as exc:
            if exc.stdout:
                print(exc.stdout, file=sys.stdout)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
            raise

    def exec_bin(
        self,
        name: str,
        *args: str,
        check: bool = True,
        verbose: bool = True,
        capture_output: bool = False,
    ) -> int:
        return self.exec_command(
            self.config.get_exec_bin(name), *args, check=check, verbose=verbose, capture_output=capture_output
        )

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
            self.config.python_path,
            *python_options,
            "-m",
            name,
            *args,
            check=check,
            verbose=verbose,
            capture_output=capture_output,
        )

    def ensure_piptools(self, *, verbose: bool = False, capture_output: bool = True) -> None:
        self.exec_module(
            "pip",
            "install",
            "pip-tools",
            verbose=verbose,
            capture_output=capture_output,
        )
