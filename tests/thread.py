# -*- coding: Utf-8 -*

from os.path import dirname
from sys import path as SYS_PATH

SYS_PATH.append(dirname(dirname(__file__)))

from py_diamond.system.threading import RThread, rthread


@rthread
def my_add(a: int, b: int) -> int:
    return a + b


def main() -> None:
    t: RThread[int] = my_add(5, 8)
    print(t.join())


if __name__ == "__main__":
    main()
