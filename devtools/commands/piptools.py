# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["EnsurePipToolsInstalledCommand", "PipCompileCommand", "PipSyncCommand"]

import re
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import Any, Sequence, final

from ..constants import REQUIREMENTS_FILES, REQUIREMENTS_FILES_EXTRA_REQUIRES, REQUIREMENTS_FILES_INPUT
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

    @staticmethod
    def validate_posarg(arg: str) -> str:
        arg = arg.strip()
        if not arg.startswith("-") or not arg.lstrip("-"):
            raise ArgumentTypeError("Non-option arguments are forbidden")
        return arg


@final
class PipCompileCommand(_AbstractPipToolsCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config, "compile")
        self.default_options: Sequence[str] = (
            "--no-allow-unsafe",
            "--resolver=backtracking",
            "--quiet",
            "--no-header",
            "--newline=LF",
        )

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "manage requirements.txt files"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--files", type=cls.validate_filename, nargs="*", default=REQUIREMENTS_FILES, help="requirements.txt files to compile"
        )
        parser.add_argument(
            "pip_compile_args", type=cls.validate_posarg, default=[], nargs="*", metavar="OPTION", help="pip-compile options"
        )

    @staticmethod
    def validate_filename(file: str) -> str:
        filename = Path(file).name
        if re.match(r"^requirements(-\w+)?\.txt$", filename) is None:
            raise ArgumentTypeError(f"Invalid filename {filename!r}")
        if filename not in REQUIREMENTS_FILES_INPUT:
            raise ArgumentTypeError(f"Unknown filename {filename!r}")
        return file

    def run(self, args: Any) -> int:
        pip_compile_args: Sequence[str] = args.pip_compile_args
        self.compile_all(args.files, *pip_compile_args)
        return 0

    def compile_all(self, requirement_files: Sequence[str], *options: str) -> None:
        if isinstance(requirement_files, str):
            raise ValueError("Expected a sequence of str, but not a string itself")
        for requirement_file in dict.fromkeys(requirement_files):
            self.compile(requirement_file, *options)

    def compile(self, requirement_file: str, *options: str) -> None:
        extended_options: list[str] = []
        requirement_filename = Path(requirement_file).name
        requirement_input: str = REQUIREMENTS_FILES_INPUT[requirement_filename]
        if requirement_filename in REQUIREMENTS_FILES_EXTRA_REQUIRES:
            extra_requires: tuple[str, ...] | None = REQUIREMENTS_FILES_EXTRA_REQUIRES[requirement_filename]
            if extra_requires is None:
                extended_options.append("--all-extras")
            else:
                extended_options.extend(f"--extra={extra}" for extra in extra_requires)
        extended_options.append(f"--output-file={requirement_file}")
        self.exec_piptools_command(*self.default_options, *options, *extended_options, requirement_input, check=True)


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
        parser.add_argument("-c", "--compile", action="store_true", help="Call pip-compile before sync")
        parser.add_argument(
            "pip_sync_args", type=cls.validate_posarg, default=[], nargs="*", metavar="OPTION", help="pip-sync options"
        )

    def run(self, args: Any) -> int:
        pip_sync_args: Sequence[str] = args.pip_sync_args
        self.sync(*pip_sync_args, compile_before=args.compile)
        return 0

    def sync(self, *options: str, compile_before: bool = False) -> None:
        VenvCommand(self.config).create()

        if compile_before:
            PipCompileCommand(self.config).compile_all(REQUIREMENTS_FILES)

        self.exec_piptools_command(*self.default_options, *options, *REQUIREMENTS_FILES, check=True)
        self.exec_module("pip", "install", "--no-deps", "--no-build-isolation", "--editable", ".")


@final
class PipUpgradeCommand(AbstractCommand):
    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Upgrade dependencies if possible"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, /) -> int:
        self.upgrade()
        return 0

    def upgrade(self) -> None:
        config = self.config
        PipCompileCommand(config).compile_all(REQUIREMENTS_FILES, "--upgrade")
        PipSyncCommand(config).sync()


@final
class EnsurePipToolsInstalledCommand(AbstractCommand):
    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Install pip-tools package if unavailable"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, /) -> int:
        self.ensure_piptools(capture_output=False)
        return 0
