# -*- coding: Utf-8 -*-

from __future__ import annotations

import pickle
from copy import copy, deepcopy
from typing import Any

from pydiamond.system.collections import SortedDict

import pytest

########################
# Initialization
########################


def test_initialization_from_kwargs() -> None:
    sd: SortedDict[str, int] = SortedDict(c=5, a=2, d=23, b=-4)

    assert sd["c"] == 5
    assert sd["a"] == 2
    assert sd["d"] == 23
    assert sd["b"] == -4


def test_initialization_from_iterable() -> None:
    sd: SortedDict[str, int] = SortedDict([("c", 5), ("a", 2), ("d", 23), ("b", -4)])

    assert sd["c"] == 5
    assert sd["a"] == 2
    assert sd["d"] == 23
    assert sd["b"] == -4


def test_initialization_from_dict() -> None:
    d = {"c": 5, "a": 2, "d": 23, "b": -4}
    sd: SortedDict[str, int] = SortedDict(d)

    assert sd["c"] == 5
    assert sd["a"] == 2
    assert sd["d"] == 23
    assert sd["b"] == -4


def test_initialization_from_another_sorted_dict() -> None:
    d = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})
    sd: SortedDict[str, int] = SortedDict(d)

    assert sd["c"] == 5
    assert sd["a"] == 2
    assert sd["d"] == 23
    assert sd["b"] == -4


def test_from_keys_classmethod() -> None:
    sd: SortedDict[str, int | None] = SortedDict.fromkeys(["c", "a", "d", "b"])

    assert isinstance(sd, SortedDict)
    assert all(sd[key] is None for key in ["c", "a", "d", "b"])


def test_from_keys_classmethod_default_value() -> None:
    sd: SortedDict[str, int] = SortedDict.fromkeys(["c", "a", "d", "b"], 42)

    assert isinstance(sd, SortedDict)
    assert all(sd[key] == 42 for key in ["c", "a", "d", "b"])


########################
# Representation
########################


def test_repr() -> None:
    sd: SortedDict[str, int | None] = SortedDict.fromkeys(["c", "a", "d", "b"])

    assert repr(sd) == "SortedDict({'a': None, 'b': None, 'c': None, 'd': None})"


def test_repr_empty_container() -> None:
    sd: SortedDict[str, int | None] = SortedDict()

    assert repr(sd) == "SortedDict({})"


def test_repr_single_element() -> None:
    sd: SortedDict[str, int | None] = SortedDict(a=None)

    assert repr(sd) == "SortedDict({'a': None})"


def test_recursive_repr() -> None:
    sd: SortedDict[str, Any] = SortedDict()
    sd["sd"] = sd

    assert repr(sd) == "SortedDict({'sd': ...})"


########################
# Iteration
########################


def test_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(sd) == ["a", "b", "c", "d"]


def test_reverse_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(reversed(sd)) == ["d", "c", "b", "a"]


def test_keys_view_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(sd.keys()) == ["a", "b", "c", "d"]


def test_keys_view_reverse_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(reversed(sd.keys())) == ["d", "c", "b", "a"]


def test_values_view_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(sd.values()) == [2, -4, 5, 23]  # List values sorted by keys


def test_values_view_reverse_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(reversed(sd.values())) == [23, 5, -4, 2]


def test_items_view_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(sd.items()) == [("a", 2), ("b", -4), ("c", 5), ("d", 23)]


def test_items_view_reverse_iteration() -> None:
    sd: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    assert list(reversed(sd.items())) == [("d", 23), ("c", 5), ("b", -4), ("a", 2)]


########################
# Item assignment
########################


def test_setitem_successive_assignment() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd["c"] = 12
    sd["a"] = 65

    assert sd["c"] == 12
    assert sd["a"] == 65
    assert list(sd) == ["a", "c", "h", "k", "p", "z"]


def test_setitem_do_not_accept_unhashable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        sd[{}] = None


def test_setitem_do_not_accept_non_comparable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    sd[object()] = None  # The 1st will work because there is no comparison to do
    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd[object()] = None


def test_setitem_non_comparable_do_not_keep_key() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    a = object()
    b = object()

    sd[a] = None
    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd[b] = None

    assert b not in sd
    assert len(sd) == 1


def test_setitem_no_duplicate() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    sd["a"] = 1
    sd["a"] = 3

    assert sd["a"] == 3
    assert list(sd) == ["a"]
    assert len(sd) == 1


def test_setdefault_successive_assignment() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd.setdefault("c", 12)
    sd.setdefault("a", 65)

    assert sd["c"] == 12
    assert sd["a"] == 65
    assert list(sd) == ["a", "c", "h", "k", "p", "z"]


def test_setdefault_do_not_accept_unhashable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        sd.setdefault({}, None)


def test_setdefault_do_not_accept_non_comparable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    sd[object()] = None  # The 1st will work because there is no comparison to do
    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd.setdefault(object(), None)


def test_setdefault_non_comparable_do_not_keep_key() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    a = object()
    b = object()

    sd[a] = None
    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd.setdefault(b, None)

    assert b not in sd
    assert len(sd) == 1


def test_setdefault_no_duplicate() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    sd.setdefault("a", 1)
    sd.setdefault("a", 3)

    assert sd["a"] == 1
    assert list(sd) == ["a"]
    assert len(sd) == 1


########################
# Massive assigment
########################


def test_update_no_elements() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd.update()

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_with_only_kwargs() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.update(z=5, p=2, h=23, k=-4)

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_from_dict_only() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.update({"z": 5, "p": 2, "h": 23, "k": -4})

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_with_iterable_only() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.update([("z", 5), ("p", 2), ("h", 23), ("k", -4)])

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_from_dict_and_kwargs() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.update({"z": 5, "p": 2}, h=23, k=-4)

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_from_iterable_and_kwargs() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.update([("z", 5), ("p", 2)], h=23, k=-4)

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", 2), ("z", 5)]
    assert len(sd) == 4


def test_update_with_already_present_pairs() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd.update({"z": 456, "p": -240})

    assert list(sd.items()) == [("h", 23), ("k", -4), ("p", -240), ("z", 456)]
    assert len(sd) == 4


def test_update_do_not_accept_unhashable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()
    payload: list[tuple[Any, Any]] = [("a", 2), ({}, None)]

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        sd.update(payload)

    assert "a" not in sd


def test_update_do_not_accept_non_comparable_keys() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd.update({object(): None, object(): None})


def test_update_non_comparable_do_not_keep_key() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    a = object()
    b = object()

    with pytest.raises(TypeError, match=r"'[<>]' not supported between instances of 'object' and 'object'"):
        sd.update({a: None, b: None})

    assert a not in sd
    assert b not in sd
    assert len(sd) == 0


########################
# Item deletion
########################


def test_delitem_successive_deletion() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    del sd["p"], sd["h"]

    assert list(sd) == ["k", "z"]
    assert len(sd) == 2


def test_delitem_unknown_key() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    with pytest.raises(KeyError):
        del sd["i"]

    assert list(sd) == ["h", "k", "p", "z"]
    assert len(sd) == 4


def test_delitem_do_not_accept_unhashable_key() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        del sd[{}]


def test_pop_successive_deletion() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    assert sd.pop("p") == 2
    assert sd.pop("h") == 23

    assert "p" not in sd
    assert "h" not in sd
    assert list(sd) == ["k", "z"]
    assert len(sd) == 2


def test_pop_unhashable_key_raise_keyerror_for_empty_container() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(KeyError):
        sd.pop({})


def test_pop_unhashable_key_raise_typeerror_for_non_empty_container() -> None:
    sd: SortedDict[Any, Any] = SortedDict({"a": 2})

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        sd.pop({})


def test_pop_default_with_known_key() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    assert sd.pop("h", 42) == 23

    assert list(sd) == ["k", "p", "z"]
    assert len(sd) == 3


def test_pop_default_with_unknown_key() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    assert sd.pop("i", 54) == 54

    assert list(sd) == ["h", "k", "p", "z"]
    assert len(sd) == 4


def test_pop_default_accept_unhashable_key_for_empty_container() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    assert sd.pop({}, 54) == 54


def test_pop_default_do_not_accept_unhashable_key_for_non_empty_container() -> None:
    sd: SortedDict[Any, Any] = SortedDict({"z": 5})

    with pytest.raises(TypeError, match=r"unhashable type: 'dict'"):
        sd.pop({}, 54)


def test_popitem_always_return_the_greatest_key() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    assert sd.popitem() == ("z", 5)
    assert sd.popitem() == ("p", 2)
    assert sd.popitem() == ("k", -4)
    assert sd.popitem() == ("h", 23)

    assert all(key not in sd for key in ["h", "k", "p", "z"])
    assert list(sd) == []
    assert len(sd) == 0


def test_popitem_error_for_empty_container() -> None:
    sd: SortedDict[Any, Any] = SortedDict()

    with pytest.raises(KeyError):
        sd.popitem()


########################
# Massive deletion
########################


def test_clear_non_empty_container() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd.clear()

    assert all(key not in sd for key in ["h", "k", "p", "z"])
    assert list(sd) == []
    assert len(sd) == 0


def test_clear_empty_container() -> None:
    sd: SortedDict[str, int] = SortedDict()

    sd.clear()

    assert list(sd) == []
    assert len(sd) == 0


########################
# Operator
########################


def test_eq_other_sorted_dict() -> None:
    assert SortedDict() == SortedDict()
    assert SortedDict({"c": 5, "a": 2}) == SortedDict({"a": 2, "c": 5})

    assert SortedDict({"c": 5, "a": 2}) != SortedDict({"a": 2, "b": 5})
    assert SortedDict({"c": 5, "a": 2}) != SortedDict({"a": 2, "c": 12})


def test_eq_builtin_dict() -> None:
    assert SortedDict() == {}
    assert SortedDict({"c": 5, "a": 2}) == {"a": 2, "c": 5}

    assert SortedDict({"c": 5, "a": 2}) != {"a": 2, "b": 5}
    assert SortedDict({"c": 5, "a": 2}) != {"a": 2, "c": 12}


def test_or_return_builtin_dict() -> None:  # See PEP-584
    sd1: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})
    sd2: SortedDict[str, int] = SortedDict({"c": 5, "a": 2, "d": 23, "b": -4})

    d: dict[str, int] = sd1 | sd2

    assert type(d) is dict
    assert d == {"z": 5, "p": 2, "h": 23, "k": -4, "c": 5, "a": 2, "d": 23, "b": -4}


def test_ior_act_as_update() -> None:
    sd: SortedDict[str, int] = SortedDict({"z": 5, "p": 2, "h": 23, "k": -4})

    sd |= {"c": 5, "a": 2, "d": 23, "b": -4}

    assert sd == {"z": 5, "p": 2, "h": 23, "k": -4, "c": 5, "a": 2, "d": 23, "b": -4}
    assert list(sd) == ["a", "b", "c", "d", "h", "k", "p", "z"]
    assert len(sd) == 8


########################
# Copy/Pickle
########################


def test_copy_method() -> None:
    sd: SortedDict[str, Any] = SortedDict({"z": [], "p": {}})

    copy_sd = sd.copy()

    assert type(copy_sd) is type(sd)
    assert copy_sd == sd
    assert copy_sd is not sd

    assert sd["z"] is copy_sd["z"]
    assert sd["p"] is copy_sd["p"]


def test_copy_module_compatiblity() -> None:
    sd: SortedDict[str, Any] = SortedDict({"z": [], "p": {}})

    copy_sd = copy(sd)

    assert type(copy_sd) is type(sd)
    assert copy_sd == sd
    assert copy_sd is not sd

    assert sd["z"] is copy_sd["z"]
    assert sd["p"] is copy_sd["p"]


def test_deepcopy() -> None:
    sd: SortedDict[str, Any] = SortedDict({"z": [], "p": {}})

    copy_sd = deepcopy(sd)

    assert type(copy_sd) is type(sd)
    assert copy_sd == sd
    assert copy_sd is not sd

    assert sd["z"] is not copy_sd["z"]
    assert sd["p"] is not copy_sd["p"]


def test_deepcopy_circular_reference() -> None:
    sd: SortedDict[str, Any] = SortedDict()
    sd["sd"] = sd

    copy_sd = deepcopy(sd)

    assert sd["sd"] is not copy_sd["sd"]
    assert copy_sd["sd"] is copy_sd


def test_pickle() -> None:
    sd: SortedDict[str, Any] = SortedDict({"z": [], "p": {}})

    reconstructed_sd: SortedDict[str, Any] = pickle.loads(pickle.dumps(sd))

    assert type(reconstructed_sd) is type(sd)
    assert reconstructed_sd == sd
