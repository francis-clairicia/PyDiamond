# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["VenvCommand"]

import venv
from argparse import ArgumentParser
from typing import Any, final

from .abc import AbstractCommand, Configuration


@final
class VenvCommand(AbstractCommand):
    def __init__(self, config: Configuration) -> None:
        super().__init__(config)

    @classmethod
    def get_parser_kwargs(cls) -> dict[str, Any]:
        return super().get_parser_kwargs() | {"help": "Create and setup the virtual env"}

    @classmethod
    def register_to_parser(cls, parser: ArgumentParser) -> None:
        pass

    def run(self, __args: Any, /) -> int:
        return self.create(log_if_already_created=True)

    def create(self, log_if_already_created: bool = False) -> int:
        config = self.config

        if config.venv_dir is None:
            self.log("ERROR: Non venv directory given, abort.")
            return 1

        if config.venv_dir.is_dir():
            if log_if_already_created:
                self.log(
                    f"Nothing to do. Run python -m {__package__.rpartition('.')[0]} pip-sync if you want to be up-to-date with requirements"
                )
            return 0

        venv.create(config.venv_dir, clear=True, with_pip=True)

        self.exec_module("pip", "install", "--upgrade", "pip")
        self.ensure_piptools()

        return 0
