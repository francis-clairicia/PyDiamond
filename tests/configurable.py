# -*- coding: Utf-8 -*

from os.path import dirname
from sys import path as SYS_PATH
from typing import Any, Dict, Tuple

SYS_PATH.append(dirname(dirname(__file__)))

from py_diamond.system.configuration import Configuration, OptionAttribute, initializer


class Configurable:
    config = Configuration("a", "b", "c", "d", autocopy=True)
    config.set_autocopy("d", copy_on_get=False, copy_on_set=False)

    a: OptionAttribute[int] = OptionAttribute()
    b: OptionAttribute[int] = OptionAttribute()
    c: OptionAttribute[int] = OptionAttribute()
    d: OptionAttribute[Dict[str, int]] = OptionAttribute()

    @initializer
    def __init__(self) -> None:
        self.a = 42
        self.b = 3
        self.c = 98
        print("END")

    @config.on_update_key_value("a")
    @config.on_update_key_value("b")
    @config.on_update_key_value("c")
    def _on_update_field(self, name: str, val: int) -> None:
        print(f"{self}: {name} set to {val}")

    config.on_update_key_value("d", lambda self, name, val: print((self, name, val)))

    @config.value_converter_static("a")
    @config.value_converter_static("b")
    @config.value_converter_static("c")
    @staticmethod
    def __valid_int(val: Any) -> int:
        return max(int(val), 0)

    @config.on_update("a")
    @config.on_update("b")
    @config.on_update("c")
    def __update(self) -> None:
        print("UPDATE CALL")

    config.value_validator_static("d", dict)

    @config.main_update
    def _update(self) -> None:
        if self.config.has_initialization_context():
            print("Init object")
        else:
            print("Update object")


class SubConfigurable(Configurable):
    config = Configuration("e", parent=Configurable.config)
    config.remove_parent_ownership("b")
    e: OptionAttribute[int] = OptionAttribute()

    config.value_converter_static("e", int)

    @config.main_update
    def _custom_update(self) -> None:
        print("After parent update")
        print("-----")

    @config.on_update("a")
    def _custom_a_updater(self) -> None:
        print("AAAAAAAAA")
        print("----------")

    def _custom_b_updater(self) -> None:
        print("BBBBBBBBBBB")
        print("----------")

    config.on_update("b", _custom_b_updater)

    @config.on_update_key_value("a")
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

    a: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(self) -> None:
        self.a = 5

    def __del__(self) -> None:
        print(self)


class Rect:
    def __init__(self) -> None:
        self.config.set("size", (4, 5))

    config = Configuration("width", "height", "size")

    @config.main_update
    def update(self) -> None:
        print("UPDATE")

    @config.getter("size")
    def get_size(self) -> Tuple[Any, Any]:
        return (self.config.get("width"), self.config.get("height"))

    @config.setter("size")
    def set_size(self, size: Any) -> None:
        self.config(width=size[0], height=size[1])


class SubRect(Rect):
    config = Configuration(parent=Rect.config)


class Klass:
    config = Configuration("a", "b", "c")

    @config.main_update
    def update(self) -> None:
        print("UPDATE")

    @config.on_update_key("a")
    @config.on_update_key("b")
    @config.on_update_key("c")
    def __update_field(self, option: str) -> None:
        print(f"{option!r} modified")

    @config.on_update_key_value("a")
    @config.on_update_key_value("b")
    @config.on_update_key_value("c")
    def __update_field_v(self, option: str, value: Any) -> None:
        print(f"{option!r} set to {value}")


def main() -> None:
    # rect = SubRect()
    c = Klass()
    # print("--------")
    # c.config["a"] = 4
    c.config(a=6, b=5, c=-9)
    print("After")
    c.config(a=6, b=5, c=-9)
    print("Close")
    c.config(a=6, b=5, c=-5)
    # print(c.config.known_options())
    # print(c.config["a"])
    # c.config.set("a", 6)
    # c.config(a=6, b=5, c=-12)

    # c.a += 2
    # print(c.a)

    # c.config.set("e", "4")
    # assert isinstance(c.e, int)

    # c.d = d = {"a": 5}
    # print(c.d is d)
    # print(vars(c))


if __name__ == "__main__":
    main()
