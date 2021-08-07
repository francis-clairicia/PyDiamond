# -*- coding: Utf-8 -*

from sys import path as SYS_PATH
from os.path import dirname
from typing import Any, Dict

SYS_PATH.append(dirname(dirname(__file__)))

from my_pygame.configuration import ConfigAttribute, Configuration


class Configurable:
    config = Configuration("a", "b", "c", "d", autocopy=True)
    config.set_autocopy("d", copy_on_get=False, copy_on_set=False)

    a: ConfigAttribute[int] = ConfigAttribute(config)
    b: ConfigAttribute[int] = ConfigAttribute(config)
    c: ConfigAttribute[int] = ConfigAttribute(config)
    d: ConfigAttribute[Dict[str, int]] = ConfigAttribute(config)

    @config.initializer
    def __init__(self) -> None:
        self.a = 42
        self.b = 3
        self.c = 98

    @config.updater("a")
    @config.updater("b")
    @config.updater("c")
    def _on_update_field(self, name: str, val: int) -> None:
        print(f"{self}: {name} set to {val}")

    config.updater("d", lambda self, name, val: print((self, name, val)))

    @config.validator("a")
    @config.validator("b")
    @config.validator("c")
    @staticmethod
    def __valid_int(val: Any) -> int:
        return max(int(val), 0)

    config.validator("d", dict)

    @config.updater
    def _update(self) -> None:
        print("Update object")


class SubConfigurable(Configurable):
    config = Configuration("e", parent=Configurable.config)
    config.remove_parent_ownership("b")
    e: ConfigAttribute[int] = ConfigAttribute(config)

    config.validator("e", int, convert=True)

    # @config.updater("a")
    # def __special_case_a(self, name: str, val: int) -> None:
    #     print(f"----------Special case for {name}--------")
    #     self._on_update_field(name, val)

    # def _update(self) -> None:
    #     super()._update()
    #     print("Subfunction update")


def main() -> None:
    c = SubConfigurable()
    c.config["a"] = 4
    c.config(a=6, b=5, c=-9)
    print(c.config.known_options())
    print(c.config["a"])
    c.config.set("a", 6)
    c.config(a=6, b=5, c=-12)

    c.a += 2
    print(c.a)

    c.config.set("e", "4")
    assert isinstance(c.e, int)

    c.d = d = {"a": 5}
    print(c.d is d)
    print(vars(c))


if __name__ == "__main__":

    main()
