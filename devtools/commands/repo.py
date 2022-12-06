from __future__ import annotations

__all__ = ["RepoCommand"]

from argparse import ArgumentParser
from typing import Any, Sequence, final

from .abc import AbstractCommand, Configuration
from .piptools import PipSyncCommand
from .venv import VenvCommand


@final
class RepoCommand(AbstractCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config)

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Setup the repository for development"}

    @classmethod
    def accepts_unknown_args(cls) -> bool:
        return False

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, __unparsed_args: Sequence[str], /) -> int:
        self.setup()
        return 0

    def setup(self) -> None:
        config: Configuration = self.config

        VenvCommand(config).create()
        PipSyncCommand(config).sync()

        self.exec_python_script("pre-commit", "install")
