# -*- coding: Utf-8 -*

from sys import path as SYS_PATH
from os.path import dirname
from typing import Any, Dict, Tuple

SYS_PATH.append(dirname(dirname(__file__)))

from my_pygame.configuration import ConfigAttribute, Configuration, initializer


class Configurable:
    config = Configuration("a", "b", "c", "d", autocopy=True)
    config.set_autocopy("d", copy_on_get=False, copy_on_set=False)

    a: ConfigAttribute[int] = ConfigAttribute()
    b: ConfigAttribute[int] = ConfigAttribute()
    c: ConfigAttribute[int] = ConfigAttribute()
    d: ConfigAttribute[Dict[str, int]] = ConfigAttribute()

    @initializer
    def __init__(self) -> None:
        self.a = 42
        self.b = 3
        self.c = 98
        print("END")

    @config.value_updater("a")
    @config.value_updater("b")
    @config.value_updater("c")
    def _on_update_field(self, name: str, val: int) -> None:
        print(f"{self}: {name} set to {val}")

    config.value_updater("d", lambda self, name, val: print((self, name, val)))

    @config.validator("a")
    @config.validator("b")
    @config.validator("c")
    @staticmethod
    def __valid_int(val: Any) -> int:
        return max(int(val), 0)

    @config.updater("a")
    @config.updater("b")
    @config.updater("c")
    @staticmethod
    def __update() -> None:
        print("UPDATE CALL")

    config.validator("d", dict)

    @config.updater
    def _update(self) -> None:
        if self.config.has_initialization_context():
            print("Init object")
        else:
            print("Update object")


class SubConfigurable(Configurable):
    config = Configuration("e", parent=Configurable.config)
    config.remove_parent_ownership("b")
    e: ConfigAttribute[int] = ConfigAttribute()

    config.validator("e", int, convert=True)

    @config.updater
    def _custom_update(self) -> None:
        print("After parent update")
        print("-----")

    @config.updater("a")
    def _custom_a_updater(self) -> None:
        print("AAAAAAAAA")
        print("----------")

    def _custom_b_updater(self) -> None:
        print("BBBBBBBBBBB")
        print("----------")

    config.updater("b", _custom_b_updater)

    @config.value_updater("a")
    def __special_case_a(self, name: str, val: int) -> None:
        print(f"----------Special case for {name}--------")
        # self._on_update_field(name, val)

    # def _update(self) -> None:
    #     super()._update()
    #     print("Subfunction update")


class C:
    config: Configuration = Configuration("a", "b", "c")

    @initializer
    def __init__(self) -> None:
        self.config(a=5, b=6, c=7)

    def __del__(self) -> None:
        print(self)


class A:
    __config: Configuration = Configuration("a")

    a: ConfigAttribute[int] = ConfigAttribute()

    @initializer
    def __init__(self) -> None:
        self.a = 5

    def __del__(self) -> None:
        print(self)


class Rect:
    def __init__(self) -> None:
        self.config.set("size", (4, 5))

    config = Configuration("width", "height", "size")

    @config.updater
    def update(self) -> None:
        print("UPDATE")

    @config.getter("size")
    def get_size(self) -> Tuple[Any, Any]:
        return (self.config.get("width"), self.config.get("height"))

    @config.setter_property("size")
    def set_size(self, size: Any) -> None:
        self.config(width=size[0], height=size[1])


class SubRect(Rect):
    config = Configuration(parent=Rect.config)


def main() -> None:
    rect = SubRect()
    c = SubConfigurable()
    print("--------")
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
