# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["main"]

import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from types import MappingProxyType

from .commands.abc import AbstractCommand, Configuration
from .commands.piptools import EnsurePipToolsInstalledCommand, PipCompileCommand, PipSyncCommand, PipUpgradeCommand
from .commands.repo import RepoCommand
from .commands.venv import VenvCommand

COMMANDS: MappingProxyType[str, type[AbstractCommand]] = MappingProxyType(
    {
        "repo": RepoCommand,
        "venv": VenvCommand,
        "ensure-piptools": EnsurePipToolsInstalledCommand,
        "pip-compile": PipCompileCommand,
        "pip-sync": PipSyncCommand,
        "pip-upgrade": PipUpgradeCommand,
    }
)


class CustomNamespace(Namespace):
    __slots__ = ("venv_dir", "command")


def main(args: list[str] | None = None) -> int:
    parser = ArgumentParser(prog=__package__, formatter_class=ArgumentDefaultsHelpFormatter)

    default_venv_dir = Path(os.environ.get("VIRTUAL_ENV", ".venv"))
    venv_option_group = parser.add_mutually_exclusive_group()
    venv_option_group.add_argument(
        "--venv-dir",
        dest="venv_dir",
        type=Path,
        default=default_venv_dir,
        help="virtual env directory",
    )
    venv_option_group.add_argument(
        "--no-venv",
        dest="venv_dir",
        action="store_const",
        const=None,
        default="Use venv_dir",
        help="Do not try to use a virtualenv",
    )

    commands_subparser = parser.add_subparsers(
        title="commands",
        dest="command",
        description="useful commands for development",
        required=True,
    )

    for command_name, command_hander in COMMANDS.items():
        command_hander.register_to_parser(
            commands_subparser.add_parser(
                command_name,
                formatter_class=ArgumentDefaultsHelpFormatter,
                **command_hander.get_parser_kwargs(),
            )
        )

    parsed_args = parser.parse_args(args, namespace=CustomNamespace())

    command_cls: type[AbstractCommand] = COMMANDS[parsed_args.command]

    config = Configuration(venv_dir=parsed_args.venv_dir)

    command: AbstractCommand = command_cls(config)

    args_namespace = Namespace(**vars(parsed_args))

    return command.run(args_namespace)
