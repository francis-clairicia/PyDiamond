# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["VenvCommand"]

import venv
from argparse import ArgumentParser
from typing import Any, Sequence, final

from .command import AbstractCommand, Configuration
from .constants import REQUIREMENTS_FILES


@final
class VenvCommand(AbstractCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config)

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Create and setup the virtual env"}

    @classmethod
    def accepts_unknown_args(cls) -> bool:
        return False

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, __unparsed_args: Sequence[str], /) -> int:
        return self.create(log_if_already_created=True)

    def create(self, log_if_already_created: bool = False) -> int:
        config = self.config

        if config.venv_dir.is_dir():
            if log_if_already_created:
                self.log(f"Nothing to do. Run python3 -m {__package__} pip-sync if you want to be up-to-date with requirements")
            return 0

        venv.create(config.venv_dir, clear=True, with_pip=True)

        self.exec_command(config.get_module_exec("pip"), "install", "--upgrade", "pip")
        self.exec_command(config.get_module_exec("pip"), "install", "pip-tools", *(f"-r{f}" for f in REQUIREMENTS_FILES))
        self.exec_command(config.get_script("flit"), "install", "--pth-file", "--deps=none")

        return 0
