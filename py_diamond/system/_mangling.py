# -*- coding: Utf-8 -*

__all__ = ["mangle_private_attribute"]


def mangle_private_attribute(cls: type, attribute: str) -> str:
    return f"_{cls.__name__}__{attribute}"
