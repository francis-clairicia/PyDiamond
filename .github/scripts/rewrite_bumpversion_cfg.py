#!/usr/bin/env python3
# -*- coding: Utf-8 -*-

from __future__ import annotations

import re
import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from configparser import ConfigParser
from contextlib import nullcontext

MAJOR_MINOR_VERSION_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.\d+)?$")
BUMPVERSION_PART_SECTION_PATTERN = re.compile(r"^bumpversion:part:.+")


def rewrite_bumpversion_cfg(filepath: str, *, dry_run: bool = False) -> None:
    config = ConfigParser(interpolation=None)  # Note: interpolation should not be disabled for setup.cfg (but we don't care here)
    # don't transform keys to lowercase (which would be the default)
    config.optionxform = lambda option: option  # type: ignore[assignment]
    config.read(filepath)

    version: str = config.get("bumpversion", "current_version")
    version_match = MAJOR_MINOR_VERSION_PATTERN.match(version)
    if version_match is None:
        raise ValueError(f"Invalid version in file: {version}")

    major, minor = map(str, version_match.group("major", "minor"))

    config.set("bumpversion", "parse", r"{major}\.{minor}\.(?P<patch>\d+)".format(major=major, minor=minor))
    config.set("bumpversion", "serialize", f"{major}.{minor}.{{patch}}")

    for section in filter(BUMPVERSION_PART_SECTION_PATTERN.match, config.sections()):
        config.remove_section(section)

    with (open(filepath, "wt") if not dry_run else nullcontext(sys.stdout)) as output:  # type: ignore[attr-defined]
        config.write(output)


def main() -> None:
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("filepath", nargs="?", default=".bumpversion.cfg", help="bumpversion config filepath")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="If true, prints the result to stdout instead of rewrite the file",
    )

    args = parser.parse_args()

    filepath: str = args.filepath
    dry_run: bool = args.dry_run

    return rewrite_bumpversion_cfg(filepath, dry_run=dry_run)


if __name__ == "__main__":
    main()
