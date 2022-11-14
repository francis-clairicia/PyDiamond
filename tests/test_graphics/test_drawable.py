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
def drawable() -> Drawable:
    return _DrawableFixture()


@pytest.fixture
def mock_drawable(mocker: MockerFixture) -> MagicMock:
    return mocker.NonCallableMagicMock(spec_set=_DrawableFixture())


@pytest.fixture
def mock_drawable_list(mocker: MockerFixture) -> list[MagicMock]:
    return [mocker.NonCallableMagicMock(spec_set=_DrawableFixture()) for _ in range(10)]


@pytest.fixture
def drawable_group() -> DrawableGroup[Any]:
    return DrawableGroup()


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
    @pytest.fixture
    @staticmethod
    def add_mock_to_group(drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        mock_drawable_group.__contains__.return_value = False
        drawable.add_to_group(mock_drawable_group)
        assert drawable.has_group(mock_drawable_group)
        mock_drawable_group.reset_mock()
        mock_drawable_group.__contains__.return_value = True

    @pytest.fixture
    @staticmethod
    def add_mock_list_to_group(drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        for mock_drawable_group in mock_drawable_group_list:
            mock_drawable_group.__contains__.return_value = False
        drawable.add_to_group(*mock_drawable_group_list)
        assert all(drawable.has_group(mock_drawable_group) for mock_drawable_group in mock_drawable_group_list)
        for mock_drawable_group in mock_drawable_group_list:
            mock_drawable_group.reset_mock()
            mock_drawable_group.__contains__.return_value = True

    def test__add_to_group__default(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)
        assert drawable.has_group(mock_drawable_group)

    def test__add_to_group__already_present_in_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = True

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_not_called()
        assert drawable.has_group(mock_drawable_group)

    def test__add_to_group__do_not_add_in_case_of_exception(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False
        mock_drawable_group.add.side_effect = UnboundLocalError  # Why not ?

        # Act
        with pytest.raises(UnboundLocalError):
            drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)
        assert not drawable.has_group(mock_drawable_group)

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
    def test__remove_from_group__error_in_case_of_exception(
        self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]
    ) -> None:
        # Arrange
        valid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 0]
        invalid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 1]
        for mock_drawable_group in invalid_groups:
            mock_drawable_group.remove.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.remove_from_group(*mock_drawable_group_list)
        assert exc_info.value.args[1] == invalid_groups
        assert all(drawable.has_group(g) for g in invalid_groups)
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
    def test__kill__error_in_case_of_exception(self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        # Arrange
        valid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 0]
        invalid_groups = [g for i, g in enumerate(mock_drawable_group_list) if i % 2 == 1]
        for mock_drawable_group in invalid_groups:
            mock_drawable_group.remove.side_effect = UnboundLocalError

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.kill()
        assert sorted(exc_info.value.args[1], key=id) == sorted(invalid_groups, key=id)
        assert all(drawable.has_group(g) for g in invalid_groups)
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
    def test__dunder_init__without_items(self, mocker: MockerFixture) -> None:
        # Arrange
        mock_add = mocker.patch.object(DrawableGroup, "add")

        # Act
        _ = DrawableGroup()

        # Assert
        mock_add.assert_not_called()

    def test__dunder_init__with_items(self, mocker: MockerFixture, mock_drawable_list: list[MagicMock]) -> None:
        # Arrange
        mock_add = mocker.patch.object(DrawableGroup, "add")

        # Act
        _ = DrawableGroup(*mock_drawable_list)

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

    @pytest.mark.parametrize("expected_return", [False, True])
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

    def test__dunder_delitem__index(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_pop = mocker.patch.object(DrawableGroup, "pop")

        # Act
        del drawable_group[123]

        # Assert
        mock_pop.assert_called_once_with(123)

    def test__dunder_delitem__slice(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_remove = mocker.patch.object(DrawableGroup, "remove")
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
