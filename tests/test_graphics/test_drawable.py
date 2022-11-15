# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydiamond.graphics.drawable import Drawable, DrawableGroup, LayeredDrawableGroup

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class _DrawableFixture(Drawable):
    def draw_onto(self, target: Any) -> None:
        raise NotImplementedError("Not meant to be called here")


@pytest.fixture
def drawable_cls() -> type[Drawable]:
    return _DrawableFixture


@pytest.fixture
def drawable(drawable_cls: type[Drawable]) -> Drawable:
    return drawable_cls()


@pytest.fixture
def mock_drawable(mocker: MockerFixture) -> MagicMock:
    return mocker.NonCallableMagicMock(spec_set=_DrawableFixture())


@pytest.fixture
def mock_drawable_list(mocker: MockerFixture) -> list[MagicMock]:
    return [mocker.NonCallableMagicMock(spec_set=_DrawableFixture()) for _ in range(10)]


@pytest.fixture(params=[DrawableGroup, LayeredDrawableGroup])
def drawable_group_cls(request: Any) -> type[DrawableGroup[Any]]:
    group_cls: type[DrawableGroup[Any]] = request.param
    return group_cls


@pytest.fixture
def drawable_group(drawable_group_cls: type[DrawableGroup[Any]]) -> DrawableGroup[Any]:
    return drawable_group_cls()


@pytest.fixture
def mock_drawable_group(mocker: MockerFixture) -> MagicMock:
    return mocker.NonCallableMagicMock(spec_set=DrawableGroup())


@pytest.fixture
def mock_drawable_group_list(mocker: MockerFixture) -> list[MagicMock]:
    return [mocker.NonCallableMagicMock(spec_set=DrawableGroup()) for _ in range(10)]


@pytest.fixture
def layered_drawable_group() -> LayeredDrawableGroup[Any]:
    return LayeredDrawableGroup()


@pytest.fixture
def mock_layered_drawable_group(mocker: MockerFixture) -> MagicMock:
    return mocker.NonCallableMagicMock(spec_set=LayeredDrawableGroup())


@pytest.fixture
def mock_layered_drawable_group_list(mocker: MockerFixture) -> list[MagicMock]:
    return [mocker.NonCallableMagicMock(spec_set=LayeredDrawableGroup()) for _ in range(10)]


class TestDrawable:
    @staticmethod
    def _add_mock_to_group(drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        mock_drawable_group.__contains__.return_value = False
        drawable.add_to_group(mock_drawable_group)
        assert drawable.has_group(mock_drawable_group)
        mock_drawable_group.reset_mock()
        mock_drawable_group.__contains__.return_value = True

    @pytest.fixture
    @staticmethod
    def add_mock_to_group(drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        return TestDrawable._add_mock_to_group(drawable, mock_drawable_group)

    @pytest.fixture
    @staticmethod
    def add_mock_list_to_group(drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        for mock_drawable_group in mock_drawable_group_list:
            TestDrawable._add_mock_to_group(drawable, mock_drawable_group)

    def test__add_to_group__default(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)
        assert drawable.has_group(mock_drawable_group)

    def test__add_to_group__no_duplicate(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.side_effect = [False, True, True]

        # Act
        drawable.add_to_group(mock_drawable_group, mock_drawable_group)
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)

    def test__add_to_group__already_present_in_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = True

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_not_called()
        assert drawable.has_group(mock_drawable_group)

    @pytest.mark.parametrize("added_in_group", [False, True], ids=lambda b: f"added_in_group=={b}")
    def test__add_to_group__exception_caught(
        self, added_in_group: bool, drawable: Drawable, mock_drawable_group: MagicMock
    ) -> None:
        # Arrange
        mock_drawable_group.__contains__.side_effect = [False, added_in_group]
        mock_drawable_group.add.side_effect = UnboundLocalError  # Why not ?

        # Act
        with pytest.raises(UnboundLocalError):
            drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)
        assert drawable.has_group(mock_drawable_group) is added_in_group

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__remove_from_group__default(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange

        # Act
        drawable.remove_from_group(mock_drawable_group)

        # Assert
        mock_drawable_group.remove.assert_called_once_with(drawable)
        assert not drawable.has_group(mock_drawable_group)

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__remove_from_group__already_removed_in_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False

        # Act
        drawable.remove_from_group(mock_drawable_group)

        # Assert
        mock_drawable_group.remove.assert_not_called()
        assert not drawable.has_group(mock_drawable_group)

    def test__remove_from_group__error_if_was_not_registered(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.remove_from_group(mock_drawable_group)
        assert exc_info.value.args[1] == [mock_drawable_group]

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test__remove_from_group__exception_caught(
        self, removed_from_group: bool, drawable: Drawable, mock_drawable_group_list: list[MagicMock]
    ) -> None:
        # Arrange
        valid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 0]
        invalid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 1]
        for mock_drawable_group in invalid_groups:
            mock_drawable_group.__contains__.side_effect = [True, not removed_from_group]
            mock_drawable_group.remove.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.remove_from_group(*mock_drawable_group_list)
        assert exc_info.value.args[1] == invalid_groups
        if not removed_from_group:
            assert all(drawable.has_group(g) for g in invalid_groups)
        else:
            assert all(not drawable.has_group(g) for g in invalid_groups)
        assert all(not drawable.has_group(g) for g in valid_groups)

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test__kill__remove_from_all_groups(self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        drawable.kill()

        # Assert
        for mock_drawable_group in mock_drawable_group_list:
            mock_drawable_group.remove.assert_called_once_with(drawable)
            assert not drawable.has_group(mock_drawable_group)

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test__kill__exception_caught(
        self, removed_from_group: bool, drawable: Drawable, mock_drawable_group_list: list[MagicMock]
    ) -> None:
        # Arrange
        valid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 0]
        invalid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 1]
        for mock_drawable_group in invalid_groups:
            mock_drawable_group.__contains__.side_effect = [True, not removed_from_group]
            mock_drawable_group.remove.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.kill()
        assert sorted(exc_info.value.args[1], key=id) == sorted(invalid_groups, key=id)
        if not removed_from_group:
            assert all(drawable.has_group(g) for g in invalid_groups)
        else:
            assert all(not drawable.has_group(g) for g in invalid_groups)
        assert all(not drawable.has_group(g) for g in valid_groups)

    def test__is_alive__false_if_there_is_no_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert not drawable.is_alive()

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__is_alive__true_if_there_is_one_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert drawable.is_alive()

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test__is_alive__true_if_there_is_several_groups(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert drawable.is_alive()

    def test__get_groups__no_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == 0

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__get_groups__single_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == 1
        assert groups == frozenset({mock_drawable_group})

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test__get_groups__several_groups(self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == len(mock_drawable_group_list)
        assert groups == frozenset(mock_drawable_group_list)


class TestDrawableGroup:
    @pytest.fixture
    @staticmethod
    def add_mock_to_group(drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        drawable_group.data.append(mock_drawable)
        mock_drawable.has_group.return_value = True

    @pytest.fixture
    @staticmethod
    def add_mock_list_to_group(drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
        drawable_group.data.extend(mock_drawable_list)
        for mock_drawable in mock_drawable_list:
            mock_drawable.has_group.return_value = True

    def test__dunder_init__without_items(self, drawable_group_cls: type[DrawableGroup[Any]], mocker: MockerFixture) -> None:
        # Arrange
        mock_add = mocker.patch.object(drawable_group_cls, "add")

        # Act
        _ = drawable_group_cls()

        # Assert
        mock_add.assert_not_called()

    def test__dunder_init__with_items(
        self, drawable_group_cls: type[DrawableGroup[Any]], mocker: MockerFixture, mock_drawable_list: list[MagicMock]
    ) -> None:
        # Arrange
        mock_add = mocker.patch.object(drawable_group_cls, "add")

        # Act
        _ = drawable_group_cls(*mock_drawable_list)

        # Assert
        mock_add.assert_called_once_with(*mock_drawable_list)

    def test__dunder_iter__default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)

        # Act
        _ = iter(drawable_group)

        # Assert
        mock_data.__iter__.assert_called_once()

    def test__dunder_len__default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.__len__.return_value = 472

        # Act
        ret_val = len(drawable_group)

        # Assert
        mock_data.__len__.assert_called_once()
        assert ret_val == 472

    def test__dunder_contains__default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.__contains__.return_value = True
        sentinel = mocker.sentinel.object

        # Act
        ret_val = sentinel in drawable_group

        # Assert
        mock_data.__contains__.assert_called_once_with(sentinel)
        assert ret_val is True

    @pytest.mark.parametrize("expected_return", [False, True], ids=lambda b: f"expected_return=={b}")
    def test__dunder_bool__default(
        self, expected_return: bool, drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.__len__.return_value = 10 if expected_return is True else 0

        # Act
        ret_val = bool(drawable_group)

        # Assert
        mock_data.__len__.assert_called_once()
        assert ret_val is expected_return

    @pytest.mark.parametrize("index", [0, slice(10, None)])
    def test__dunder_getitem__default(
        self, index: int | slice, drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.__getitem__.return_value = sentinel

        # Act
        ret_val = drawable_group[index]

        # Assert
        mock_data.__getitem__.assert_called_once_with(index)
        assert ret_val is sentinel

    def test__dunder_delitem__index(
        self, drawable_group_cls: type[DrawableGroup[Any]], drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_pop = mocker.patch.object(drawable_group_cls, "pop")

        # Act
        del drawable_group[123]

        # Assert
        mock_pop.assert_called_once_with(123)

    def test__dunder_delitem__slice(
        self, drawable_group_cls: type[DrawableGroup[Any]], drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_remove = mocker.patch.object(drawable_group_cls, "remove")
        drawable_group.data = list(range(10))

        # Act
        del drawable_group[2:9:2]

        # Assert
        mock_remove.assert_called_once_with(2, 4, 6, 8)

    def test__index__default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 0)
        assert ret_val == 472

    def test__index__start(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel, 20)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 20)
        assert ret_val == 472

    def test__index__start_and_stop(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel, 20, 80)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 20, 80)
        assert ret_val == 472

    def test__count__default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.count.return_value = 472

        # Act
        ret_val = drawable_group.count(sentinel)

        # Assert
        mock_data.count.assert_called_once_with(sentinel)
        assert ret_val == 472

    def test__draw_onto__default(
        self, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock], mocker: MockerFixture
    ) -> None:
        # Arrange
        drawable_group.data = mock_drawable_list
        renderer = mocker.sentinel.renderer

        # Act
        drawable_group.draw_onto(renderer)

        # Assert
        for mock_drawable in mock_drawable_list:
            mock_drawable.draw_onto.assert_called_once_with(renderer)

    def test__add__default(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.add_to_group.assert_called_once_with(drawable_group)
        assert mock_drawable in drawable_group.data

    def test__add__no_duplicate(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.add(mock_drawable, mock_drawable)
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.has_group.assert_called_once_with(drawable_group)
        mock_drawable.add_to_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == 1

    def test__add__already_present(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = True

        # Act
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.add_to_group.assert_not_called()
        assert drawable_group.data.count(mock_drawable) == 1

    @pytest.mark.parametrize("added_in_group", [False, True], ids=lambda b: f"added_in_group=={b}")
    def test__add__exception_caught(
        self, added_in_group: bool, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock
    ) -> None:
        # Arrange
        mock_drawable.has_group.side_effect = [False, added_in_group]
        mock_drawable.add_to_group.side_effect = UnboundLocalError

        # Act
        with pytest.raises(UnboundLocalError):
            drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.add_to_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == (1 if added_in_group else 0)

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__remove__default(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange

        # Act
        drawable_group.remove(mock_drawable)

        # Assert
        mock_drawable.remove_from_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == 0

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__remove__already_removed_from_drawable(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.remove(mock_drawable)

        # Assert
        mock_drawable.remove_from_group.assert_not_called()
        assert drawable_group.data.count(mock_drawable) == 0

    def test__remove__error_if_was_not_registered(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove self from several objects") as exc_info:
            drawable_group.remove(mock_drawable)
        assert exc_info.value.args[1] == [mock_drawable]

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test__remove__exception_caught(
        self, removed_from_group: bool, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]
    ) -> None:
        # Arrange
        valid_objects = [g for i, g in enumerate(mock_drawable_list) if i % 2 == 0]
        invalid_objects = [g for i, g in enumerate(mock_drawable_list) if i % 2 == 1]
        for mock_drawable in invalid_objects:
            mock_drawable.has_group.side_effect = [True, not removed_from_group]
            mock_drawable.remove_from_group.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove self from several objects") as exc_info:
            drawable_group.remove(*mock_drawable_list)
        assert exc_info.value.args[1] == invalid_objects
        if not removed_from_group:
            assert all(d in drawable_group.data for d in invalid_objects)
        else:
            assert all(d not in drawable_group.data for d in invalid_objects)
        assert all(d not in drawable_group.data for d in valid_objects)

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test__pop__default(self, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
        # Arrange
        expected_removed_obj = mock_drawable_list[-1]

        # Act
        removed_obj = drawable_group.pop()

        # Assert
        expected_removed_obj.remove_from_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(expected_removed_obj) == 0
        assert removed_obj is expected_removed_obj

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("index", [0, 8, -1, -5], ids=lambda i: f"({i})")
    def test__pop__index_in_range(
        self, index: int, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]
    ) -> None:
        # Arrange
        expected_removed_obj = mock_drawable_list[index]

        # Act
        removed_obj = drawable_group.pop(index)

        # Assert
        expected_removed_obj.remove_from_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(expected_removed_obj) == 0
        assert removed_obj is expected_removed_obj

    @pytest.mark.parametrize("index", [21321, -3000], ids=lambda i: f"({i})")
    def test__pop__index_out_of_range(self, index: int, drawable_group: DrawableGroup[Any]) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(IndexError):
            drawable_group.pop(index)

    @pytest.mark.usefixtures("add_mock_to_group")
    def test__pop__already_removed_from_drawable(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        removed_obj = drawable_group.pop()

        # Assert
        mock_drawable.remove_from_group.assert_not_called()
        assert drawable_group.data.count(mock_drawable) == 0
        assert removed_obj is mock_drawable

    @pytest.mark.usefixtures("add_mock_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test__pop__exception_caught(
        self, removed_from_group: bool, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock
    ) -> None:
        # Arrange
        mock_drawable.has_group.side_effect = [True, not removed_from_group]
        mock_drawable.remove_from_group.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(UnboundLocalError):
            drawable_group.pop()

        mock_drawable.remove_from_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == (1 if not removed_from_group else 0)

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test__clear__default(self, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        drawable_group.clear()

        # Assert
        for mock_drawable in mock_drawable_list:
            mock_drawable.remove_from_group.assert_called_once_with(drawable_group)
            assert drawable_group.data.count(mock_drawable) == 0

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test__clear__exception_caught(
        self, removed_from_group: bool, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]
    ) -> None:
        # Arrange
        valid_objects = [g for i, g in enumerate(mock_drawable_list) if i % 2 == 0]
        invalid_objects = [g for i, g in enumerate(mock_drawable_list) if i % 2 == 1]
        for mock_drawable in invalid_objects:
            mock_drawable.has_group.side_effect = [True, not removed_from_group]
            mock_drawable.remove_from_group.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove self from several objects") as exc_info:
            drawable_group.clear()
        assert exc_info.value.args[1] == invalid_objects
        if not removed_from_group:
            assert all(d in drawable_group.data for d in invalid_objects)
        else:
            assert all(d not in drawable_group.data for d in invalid_objects)
        assert all(d not in drawable_group.data for d in valid_objects)
