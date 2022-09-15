# -*- coding: Utf-8 -*-

from __future__ import annotations

from pydiamond.system.collections import OrderedWeakSet

import pytest


class Dummy:
    """
    Dummy class which is weakly referenceable
    """


def test_dummy_add() -> None:
    d1 = Dummy()
    d2 = Dummy()
    d3 = Dummy()
    d4 = Dummy()
    d5 = Dummy()

    dset = OrderedWeakSet([d1, d2, d4, d1, d3, d5, d5, d2, d3])

    assert len(dset) == 5
    assert list(dset) == [d1, d2, d4, d3, d5]

    del d2
    assert len(dset) == 4
    assert list(dset) == [d1, d4, d3, d5]

    del d1, d3, d4, d5

    assert len(dset) == 0
    assert list(dset) == []


def test_type_subscription() -> None:
    d1 = Dummy()
    d2 = Dummy()

    dset = OrderedWeakSet[Dummy]([d1, d2])

    assert list(dset) == [d1, d2]


def test_get_item() -> None:
    d1 = Dummy()
    d2 = Dummy()
    d3 = Dummy()
    d4 = Dummy()
    d5 = Dummy()

    dset = OrderedWeakSet([d1, d2, d3, d4, d5])

    assert dset[0] is d1
    assert dset[1] is d2
    assert dset[2] is d3
    assert dset[3] is d4
    assert dset[4] is d5

    with pytest.raises(IndexError):
        dset[5]

    assert dset[-1] is d5


def test_get_item_deleted_item() -> None:
    d1 = Dummy()
    d2 = Dummy()
    d3 = Dummy()
    d4 = Dummy()
    d5 = Dummy()

    dset = OrderedWeakSet([d1, d2, d3, d4, d5])

    assert dset[0] is d1
    assert dset[1] is d2
    assert dset[2] is d3

    del d1, d2, d3

    assert dset[0] is d4
    assert dset[1] is d5


def test_get_item_type_error() -> None:
    d1 = Dummy()
    dset = OrderedWeakSet([d1])
    with pytest.raises(TypeError):
        dset["0"]  # type: ignore[call-overload]


def test_reverse_iterator() -> None:
    d1 = Dummy()
    d2 = Dummy()
    d3 = Dummy()
    d4 = Dummy()
    d5 = Dummy()

    dset = OrderedWeakSet([d1, d2, d3, d4, d5])

    assert list(reversed(dset)) == [d5, d4, d3, d2, d1]


def test_index() -> None:
    d1 = Dummy()
    d2 = Dummy()
    d3 = Dummy()
    d4 = Dummy()
    d5 = Dummy()

    dset = OrderedWeakSet([d1, d2, d3, d4, d5])

    assert dset.index(d1) == 0
    assert dset.index(d2) == 1
    assert dset.index(d3) == 2
    assert dset.index(d4) == 3
    assert dset.index(d5) == 4

    del d4

    assert dset.index(d5) == 3
