# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["main"]

import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from types import MappingProxyType

from .command import AbstractCommand, Configuration
from .piptools import PipCompileCommand, PipSyncCommand, PipUpgradeCommand
from .repo import RepoCommand
from .venv import VenvCommand

COMMANDS: MappingProxyType[str, type[AbstractCommand]] = MappingProxyType(
    {
        "repo": RepoCommand,
        "venv": VenvCommand,
        "pip-compile": PipCompileCommand,
        "pip-sync": PipSyncCommand,
        "pip-upgrade": PipUpgradeCommand,
    }
)


class CustomNamespace(Namespace):
    __slots__ = ("venv_dir", "command")


def main(args: list[str] | None = None) -> int:
    parser = ArgumentParser(prog=__package__, formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "--venv-dir",
        dest="venv_dir",
        type=Path,
        default=Path(".venv"),
        help="virtual env directory",
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

    parsed_args, unparsed_args = parser.parse_known_args(args, namespace=CustomNamespace())

    command_cls: type[AbstractCommand] = COMMANDS[parsed_args.command]

    if not command_cls.accepts_unknown_args() and unparsed_args:
        parser.print_usage(file=sys.stderr)
        print(
            f"{parser.prog}: error: argument {parsed_args.command}: unexpected arguments {', '.join(map(repr, unparsed_args))}",
            file=sys.stderr,
        )
        return 1

    config = Configuration(venv_dir=parsed_args.venv_dir)

    command: AbstractCommand = command_cls(config)

    args_namespace = Namespace(**vars(parsed_args))

    return command.run(args_namespace, unparsed_args)
