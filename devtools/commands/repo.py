from __future__ import annotations

__all__ = ["RepoCommand"]

from argparse import ArgumentParser
from typing import Any, final

from ..constants import REQUIREMENTS_FILES
from .abc import AbstractCommand, Configuration
from .piptools import PipCompileCommand, PipSyncCommand
from .venv import VenvCommand


@final
class RepoCommand(AbstractCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config)

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Setup the repository for development"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        parser.add_argument("-s", "--no-sync", dest="pip_sync", action="store_false", help="Do not run 'pip-sync'")
        parser.add_argument(
            "-p", "--no-pre-commit-install", dest="pre_commit", action="store_false", help="Do not run 'pre-commit install'"
        )

    def run(self, args: Any, /) -> int:
        self.setup(pip_sync=args.pip_sync, pre_commit_install=args.pre_commit)
        return 0

    def setup(self, pip_sync: bool = True, pre_commit_install: bool = True) -> None:
        config: Configuration = self.config

        if config.venv_dir is not None:
            VenvCommand(config).create()
        self.ensure_piptools()
        PipCompileCommand(config).compile_all(REQUIREMENTS_FILES)
        if pip_sync:
            PipSyncCommand(config).sync()

        if pre_commit_install:
            self.exec_bin("pre-commit", "install")
