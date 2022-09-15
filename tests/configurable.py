# -*- coding: Utf-8 -*-

from __future__ import annotations

from contextlib import contextmanager
from time import monotonic as time
from typing import Any, ClassVar, Iterator

from pydiamond.system.configuration import ConfigurationTemplate, OptionAttribute, initializer


@contextmanager
def benchmark() -> Iterator[None]:
    start_time = time()
    try:
        yield
    finally:
        elapsed = time() - start_time
        print(f"===== Elapsed time: {elapsed:.6f}s =====")


class Configurable:
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("a", "b", "c", "d")

    a: OptionAttribute[int] = OptionAttribute()
    b: OptionAttribute[int] = OptionAttribute()
    c: OptionAttribute[int] = OptionAttribute()
    d: OptionAttribute[dict[str, int]] = OptionAttribute()

    @initializer
    @benchmark()
    def __init__(self) -> None:
        self.a = 42
        self.b = 3
        self.c = 98
        print("END")

    @config.on_update_value_with_key("a")
    @config.on_update_value_with_key("b")
    @config.on_update_value_with_key("c")
    def _on_update_field(self, name: str, val: int) -> None:
        print(f"{self}: {name} set to {val}")

    config.on_update_value_with_key("d", lambda self, name, val: print((self, name, val)), use_override=False)

    @config.add_value_converter_on_set_static("a")
    @config.add_value_converter_on_set_static("b")
    @config.add_value_converter_on_set_static("c")
    @staticmethod
    def __valid_int(val: Any) -> int:
        return max(int(val), 0)

    @config.on_update("a")
    @config.on_update("b")
    @config.on_update("c")
    def __update(self) -> None:
        print("UPDATE CALL")

    config.add_value_validator_static("d", dict)

    @config.add_value_validator_static("d")
    @staticmethod
    def __valid_dict(val: dict[Any, Any]) -> None:
        print(f"Dict is here: {val}")

    @config.add_main_update
    def _update(self) -> None:
        if self.config.has_initialization_context():
            print("Init object")
        else:
            print("Update object")


class SubConfigurable(Configurable):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("e", parent=Configurable.config)
    config.remove_parent_ownership("b")
    e: OptionAttribute[int] = OptionAttribute()

    config.add_value_converter_on_set_static("e", int)

    def _update(self) -> None:
        super()._update()
        print("Override")

    @config.add_main_update
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

    @config.on_update_value_with_key("a")
    def __special_case_a(self, name: str, val: int) -> None:
        print(f"----------Special case for {name}--------")
        # self._on_update_field(name, val)

    # def _update(self) -> None:
    #     super()._update()
    #     print("Subfunction update")


class C:
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("a", "b", "c")

    @initializer
    def __init__(self) -> None:
        self.config.update(a=5, b=6, c=7)

    def __del__(self) -> None:
        print(self)


# class C:
#     config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("a")

#     a: OptionAttribute[int] = OptionAttribute()

#     def __init__(self) -> None:
#         self.__a: int = 5

# class D(C):
#     config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(parent=C.config)

#     config.remove_parent_ownership("a")

#     def __init__(self) -> None:
#         super().__init__()
#         self.__a = 12


# class E(D):
#     config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(parent=D.config)

#     config.remove_parent_ownership("a")

#     def __init__(self) -> None:
#         super().__init__()
#         self.__a = 25


class A:
    __config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("a")

    a: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(self) -> None:
        self.a = 5

    def __del__(self) -> None:
        print(self)


class Rect:
    def __init__(self) -> None:
        self.config.set("size", (4, 5))

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("width", "height", "size")

    @config.add_main_update
    def update(self) -> None:
        print("UPDATE")

    @config.getter("size")
    def get_size(self) -> tuple[Any, Any]:
        return (self.config.get("width"), self.config.get("height"))

    @config.setter("size")
    def set_size(self, size: Any) -> None:
        self.config.update(width=size[0], height=size[1])


class SubRect(Rect):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(parent=Rect.config)


class Klass:
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("a", "b", "c")

    @config.add_main_update
    def update(self) -> None:
        print("UPDATE")

    @config.on_update_with_key("a")
    @config.on_update_with_key("b")
    @config.on_update_with_key("c")
    def __update_field(self, option: str) -> None:
        print(f"{option!r} modified")

    @config.on_update_value_with_key("a")
    @config.on_update_value_with_key("b")
    @config.on_update_value_with_key("c")
    def __update_field_v(self, option: str, value: Any) -> None:
        print(f"{option!r} set to {value}")


def main() -> None:
    # e = E()

    # print(e.config.get("a"))
    # print(super(E, e).config.get("a"))
    # print(super(D, e).config.get("a"))
    # print("====")
    # print(e.a)
    # print(super(E, e).a)
    # print(super(D, e).a)

    rect = SubRect()
    print(rect.config.get("size"))
    # c = Klass()
    c = SubConfigurable()
    print("--------")
    with benchmark():
        c.config["a"] = 4
        c.config.update(a=6, b=5, c=-9)
        print("After")
        c.config.update(a=6, b=5, c=-9)
        print("Close")
        c.config.update(a=6, b=5, c=-5)
        print(c.config.info.options)
        print(c.config["a"])
        c.config.set("a", 6)
        c.config.update(a=6, b=5, c=-12)
        c.a += 2
        print(c.a)
        c.config.set("e", "4")
        assert isinstance(c.e, int)
        c.d = d = {"a": 5}
        print(c.d is d)
        try:
            c.d = 5  # type: ignore[assignment]
        except TypeError as exc:
            print(f"Works as expected: {exc}")
        print(c.config.as_dict())
        print(c.config.as_dict(sorted_keys=True))
        print(vars(c))

    a = A()
    del a
    print("----")


if __name__ == "__main__":
    main()
