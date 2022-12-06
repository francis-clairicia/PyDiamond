# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["PipCompileCommand", "PipSyncCommand"]

import re
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import Any, Sequence, final

from ..constants import REQUIREMENTS_FILES
from .abc import AbstractCommand, Configuration
from .venv import VenvCommand


class _AbstractPipToolsCommand(AbstractCommand):
    def __init__(self, config: Configuration, piptools_command: str) -> None:
        super().__init__(config)
        self.piptools_command: str = piptools_command

    def exec_piptools_command(
        self,
        *args: str,
        python_options: Sequence[str] = (),
        check: bool = True,
        verbose: bool = True,
        capture_output: bool = False,
    ) -> int:
        python_options = ["-Wignore::UserWarning:_distutils_hack", *python_options]
        return self.exec_module(
            "piptools",
            self.piptools_command,
            *args,
            python_options=python_options,
            check=check,
            verbose=verbose,
            capture_output=capture_output,
        )


@final
class PipCompileCommand(_AbstractPipToolsCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config, "compile")
        self.default_options: Sequence[str] = (
            "--no-allow-unsafe",
            "--resolver=backtracking",
            "--quiet",
            "--no-header",
        )

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "manage requirements.txt files"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            "files", type=cls.validate_filename, nargs="*", default=REQUIREMENTS_FILES, help="requirements.txt files to compile"
        )

    @staticmethod
    def validate_filename(file: str) -> str:
        filename = Path(file).name
        if re.match(r"^requirements(-\w+)?\.txt$", filename) is None:
            raise ArgumentTypeError(f"Invalid filename {filename!r}")
        return file

    def run(self, args: Any, pip_compile_args: Sequence[str]) -> int:
        self.compile_all(args.files, *pip_compile_args)
        return 0

    def compile_all(self, requirement_files: Sequence[str], *options: str) -> None:
        if isinstance(requirement_files, str):
            raise ValueError("Expected a sequence of str, but not a string itself")
        for requirement_file in dict.fromkeys(requirement_files):
            self.compile(requirement_file, *options)

    def compile(self, requirement_file: str, *options: str) -> None:
        extended_options: list[str] = []
        extra: str | None
        if (match := re.match(r"requirements-(\w+)\.txt", Path(requirement_file).name)) is not None:
            extra = str(match.group(1))
        else:
            extra = None
        if extra is not None:
            extended_options.append(f"--extra={extra}")
        extended_options.append(f"--output-file={requirement_file}")
        self.exec_piptools_command(*self.default_options, *options, *extended_options, "pyproject.toml", check=True)


@final
class PipSyncCommand(_AbstractPipToolsCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config, "sync")
        self.default_options: Sequence[str] = ()

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "keep your virtual env up-to-date with requirements.txt directives"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, _: Any, pip_sync_args: Sequence[str]) -> int:
        self.sync(*pip_sync_args)
        return 0

    def sync(self, *options: str) -> None:
        options = tuple(self.validate_args(options, posargs=False))
        VenvCommand(self.config).create()

        self.exec_piptools_command(*self.default_options, *options, *REQUIREMENTS_FILES, check=True)
        self.exec_module("pip", "install", "--no-deps", "--no-build-isolation", "--editable", ".")


@final
class PipUpgradeCommand(AbstractCommand):
    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Upgrade dependencies if possible"}

    @classmethod
    def accepts_unknown_args(cls) -> bool:
        return False

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, __unparsed_args: Sequence[str], /) -> int:
        self.upgrade()
        return 0

    def upgrade(self) -> None:
        config = self.config
        PipCompileCommand(config).compile_all(REQUIREMENTS_FILES, "--upgrade")
        PipSyncCommand(config).sync()
