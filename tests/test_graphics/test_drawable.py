from __future__ import annotations

from collections.abc import Callable
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
def mock_drawable_factory(mocker: MockerFixture) -> Callable[[], MagicMock]:
    return lambda: mocker.NonCallableMagicMock(spec_set=_DrawableFixture())


@pytest.fixture
def mock_drawable(mock_drawable_factory: Callable[[], MagicMock]) -> MagicMock:
    return mock_drawable_factory()


@pytest.fixture(params=[DrawableGroup, LayeredDrawableGroup])
def drawable_group_cls(request: Any) -> type[DrawableGroup[Any]]:
    group_cls: type[DrawableGroup[Any]] = request.param
    return group_cls


@pytest.fixture
def drawable_group(drawable_group_cls: type[DrawableGroup[Any]]) -> DrawableGroup[Any]:
    return drawable_group_cls()


@pytest.fixture
def mock_drawable_group_factory(mocker: MockerFixture) -> Callable[[], MagicMock]:
    return lambda: mocker.NonCallableMagicMock(spec_set=DrawableGroup())


@pytest.fixture
def mock_drawable_group(mock_drawable_group_factory: Callable[[], MagicMock]) -> MagicMock:
    return mock_drawable_group_factory()


@pytest.fixture
def layered_drawable_group() -> LayeredDrawableGroup[Any]:
    return LayeredDrawableGroup()


@pytest.fixture
def mock_layered_drawable_group_factory(mocker: MockerFixture) -> Callable[[], MagicMock]:
    return lambda: mocker.NonCallableMagicMock(spec_set=LayeredDrawableGroup())


@pytest.fixture
def mock_layered_drawable_group(mock_layered_drawable_group_factory: Callable[[], MagicMock]) -> MagicMock:
    return mock_layered_drawable_group_factory()


class TestDrawable:
    @pytest.fixture
    @staticmethod
    def mock_drawable_group_list(mock_drawable_group_factory: Callable[[], MagicMock]) -> list[MagicMock]:
        return [mock_drawable_group_factory() for _ in range(10)]

    @staticmethod
    def _add_mock_to_group(drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        mock_drawable_group.__contains__.return_value = False
        drawable.add_to_group(mock_drawable_group)
        assert drawable.has_group(mock_drawable_group)
        mock_drawable_group.reset_mock()
        mock_drawable_group.__contains__.return_value = True

    @pytest.fixture
    @classmethod
    def add_mock_to_group(cls, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        return cls._add_mock_to_group(drawable, mock_drawable_group)

    @pytest.fixture
    @classmethod
    def add_mock_list_to_group(cls, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        for mock_drawable_group in mock_drawable_group_list:
            TestDrawable._add_mock_to_group(drawable, mock_drawable_group)

    def test____add_to_group____default(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)
        assert drawable.has_group(mock_drawable_group)

    def test____add_to_group____no_duplicate(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.side_effect = [False, True, True]

        # Act
        drawable.add_to_group(mock_drawable_group, mock_drawable_group)
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_called_once_with(drawable)

    def test____add_to_group____already_present_in_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = True

        # Act
        drawable.add_to_group(mock_drawable_group)

        # Assert
        mock_drawable_group.add.assert_not_called()
        assert drawable.has_group(mock_drawable_group)

    @pytest.mark.parametrize("added_in_group", [False, True], ids=lambda b: f"added_in_group=={b}")
    def test____add_to_group____exception_caught(
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
    def test____remove_from_group____default(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange

        # Act
        drawable.remove_from_group(mock_drawable_group)

        # Assert
        mock_drawable_group.remove.assert_called_once_with(drawable)
        assert not drawable.has_group(mock_drawable_group)

    @pytest.mark.usefixtures("add_mock_to_group")
    def test____remove_from_group____already_removed_in_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange
        mock_drawable_group.__contains__.return_value = False

        # Act
        drawable.remove_from_group(mock_drawable_group)

        # Assert
        mock_drawable_group.remove.assert_not_called()
        assert not drawable.has_group(mock_drawable_group)

    def test____remove_from_group____error_if_was_not_registered(
        self, drawable: Drawable, mock_drawable_group: MagicMock
    ) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove from several groups") as exc_info:
            drawable.remove_from_group(mock_drawable_group)
        assert exc_info.value.args[1] == [mock_drawable_group]

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test____remove_from_group____exception_caught(
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
    def test____kill____remove_from_all_groups(self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        drawable.kill()

        # Assert
        for mock_drawable_group in mock_drawable_group_list:
            mock_drawable_group.remove.assert_called_once_with(drawable)
            assert not drawable.has_group(mock_drawable_group)

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test____kill____exception_caught(
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

    def test____is_alive____false_if_there_is_no_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert not drawable.is_alive()

    @pytest.mark.usefixtures("add_mock_to_group")
    def test____is_alive____true_if_there_is_one_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert drawable.is_alive()

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test____is_alive____true_if_there_is_several_groups(self, drawable: Drawable) -> None:
        # Arrange

        # Act

        # Assert
        assert drawable.is_alive()

    def test____get_groups____no_group(self, drawable: Drawable) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == 0

    @pytest.mark.usefixtures("add_mock_to_group")
    def test____get_groups____single_group(self, drawable: Drawable, mock_drawable_group: MagicMock) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == 1
        assert groups == frozenset({mock_drawable_group})

    @pytest.mark.usefixtures("add_mock_list_to_group")
    def test____get_groups____several_groups(self, drawable: Drawable, mock_drawable_group_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        groups = drawable.get_groups()

        # Assert
        assert isinstance(groups, frozenset)
        assert len(groups) == len(mock_drawable_group_list)
        assert groups == frozenset(mock_drawable_group_list)


class TestCommonDrawableGroup:
    @pytest.fixture
    @staticmethod
    def mock_drawable_list(mock_drawable_factory: Callable[[], MagicMock]) -> list[MagicMock]:
        return [mock_drawable_factory() for _ in range(10)]

    @staticmethod
    def _add_mock_to_group(drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        drawable_group.data.append(mock_drawable)
        mock_drawable.has_group.return_value = True

    @pytest.fixture
    @classmethod
    def add_mock_to_group(cls, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        cls._add_mock_to_group(drawable_group, mock_drawable)

    @pytest.fixture
    @classmethod
    def add_mock_list_to_group(cls, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
        for mock_drawable in mock_drawable_list:
            cls._add_mock_to_group(drawable_group, mock_drawable)

    def test____dunder_init____without_items(self, drawable_group_cls: type[DrawableGroup[Any]], mocker: MockerFixture) -> None:
        # Arrange
        mock_add = mocker.patch.object(drawable_group_cls, "add")

        # Act
        _ = drawable_group_cls()

        # Assert
        mock_add.assert_not_called()

    def test____dunder_init____with_items(
        self, drawable_group_cls: type[DrawableGroup[Any]], mocker: MockerFixture, mock_drawable_list: list[MagicMock]
    ) -> None:
        # Arrange
        mock_add = mocker.patch.object(drawable_group_cls, "add")

        # Act
        _ = drawable_group_cls(*mock_drawable_list)

        # Assert
        mock_add.assert_called_once_with(*mock_drawable_list)

    def test____dunder_iter____default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)

        # Act
        _ = iter(drawable_group)

        # Assert
        mock_data.__iter__.assert_called_once()

    def test____dunder_len____default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.__len__.return_value = 472

        # Act
        ret_val = len(drawable_group)

        # Assert
        mock_data.__len__.assert_called_once()
        assert ret_val == 472

    def test____dunder_contains____default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
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
    def test____dunder_bool____default(
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
    def test____dunder_getitem____default(
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

    def test____dunder_delitem____index(
        self, drawable_group_cls: type[DrawableGroup[Any]], drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_pop = mocker.patch.object(drawable_group_cls, "pop")

        # Act
        del drawable_group[123]

        # Assert
        mock_pop.assert_called_once_with(123)

    def test____dunder_delitem____slice(
        self, drawable_group_cls: type[DrawableGroup[Any]], drawable_group: DrawableGroup[Any], mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_remove = mocker.patch.object(drawable_group_cls, "remove")
        drawable_group.data = list(range(10))

        # Act
        del drawable_group[2:9:2]

        # Assert
        mock_remove.assert_called_once_with(2, 4, 6, 8)

    def test____index____default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 0)
        assert ret_val == 472

    def test____index____start(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel, 20)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 20)
        assert ret_val == 472

    def test____index____start_and_stop(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.index.return_value = 472

        # Act
        ret_val = drawable_group.index(sentinel, 20, 80)

        # Assert
        mock_data.index.assert_called_once_with(sentinel, 20, 80)
        assert ret_val == 472

    def test____count____default(self, drawable_group: DrawableGroup[Any], mocker: MockerFixture) -> None:
        # Arrange
        sentinel = mocker.sentinel.object
        mock_data = mocker.patch.object(drawable_group, "data", autospec=True)
        mock_data.count.return_value = 472

        # Act
        ret_val = drawable_group.count(sentinel)

        # Assert
        mock_data.count.assert_called_once_with(sentinel)
        assert ret_val == 472

    def test____draw_onto____default(
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

    def test____add____default(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.add_to_group.assert_called_once_with(drawable_group)
        assert mock_drawable in drawable_group.data

    def test____add____no_duplicate(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.add(mock_drawable, mock_drawable)
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.has_group.assert_called_once_with(drawable_group)
        mock_drawable.add_to_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == 1

    def test____add____already_present(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange
        mock_drawable.has_group.return_value = True

        # Act
        drawable_group.add(mock_drawable)

        # Assert
        mock_drawable.add_to_group.assert_not_called()
        assert drawable_group.data.count(mock_drawable) == 1

    @pytest.mark.parametrize("added_in_group", [False, True], ids=lambda b: f"added_in_group=={b}")
    def test____add____exception_caught(
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
    def test____remove____default(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange

        # Act
        drawable_group.remove(mock_drawable)

        # Assert
        mock_drawable.remove_from_group.assert_called_once_with(drawable_group)
        assert drawable_group.data.count(mock_drawable) == 0

    @pytest.mark.usefixtures("add_mock_to_group")
    def test____remove____already_removed_from_drawable(
        self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock
    ) -> None:
        # Arrange
        mock_drawable.has_group.return_value = False

        # Act
        drawable_group.remove(mock_drawable)

        # Assert
        mock_drawable.remove_from_group.assert_not_called()
        assert drawable_group.data.count(mock_drawable) == 0

    def test____remove____error_if_was_not_registered(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError, match=r"Failed to remove self from several objects") as exc_info:
            drawable_group.remove(mock_drawable)
        assert exc_info.value.args[1] == [mock_drawable]

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test____remove____exception_caught(
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
    def test____pop____default(self, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
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
    def test____pop____index_in_range(
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
    def test____pop____index_out_of_range(self, index: int, drawable_group: DrawableGroup[Any]) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(IndexError):
            drawable_group.pop(index)

    @pytest.mark.usefixtures("add_mock_to_group")
    def test____pop____already_removed_from_drawable(self, drawable_group: DrawableGroup[Any], mock_drawable: MagicMock) -> None:
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
    def test____pop____exception_caught(
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
    def test____clear____default(self, drawable_group: DrawableGroup[Any], mock_drawable_list: list[MagicMock]) -> None:
        # Arrange

        # Act
        drawable_group.clear()

        # Assert
        for mock_drawable in mock_drawable_list:
            mock_drawable.remove_from_group.assert_called_once_with(drawable_group)
            assert drawable_group.data.count(mock_drawable) == 0

    @pytest.mark.usefixtures("add_mock_list_to_group")
    @pytest.mark.parametrize("removed_from_group", [True, False], ids=lambda b: f"removed_from_group=={b}")
    def test____clear____exception_caught(
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


class TestLayeredDrawableGroup:
    @staticmethod
    def _add_mock_to_group(
        drawable_group: LayeredDrawableGroup[Any],
        mock_drawable: MagicMock,
        *mock_drawables: MagicMock,
        layer: int | None = None,
        top_of_layer: bool = True,
    ) -> None:
        mock_drawables = (mock_drawable, *mock_drawables)
        for mock_drawable in mock_drawables:
            mock_drawable.has_group.return_value = False
        drawable_group.add(*mock_drawables, layer=layer, top_of_layer=top_of_layer)
        for mock_drawable in mock_drawables:
            mock_drawable.has_group.return_value = True

    @pytest.fixture(params=[0, 2, -3], ids=lambda layer: f"default_layer==({layer})")
    @staticmethod
    def default_layer(request: Any) -> int:
        return request.param

    def test____dunder_init____default(self) -> None:
        # Arrange

        # Act
        group: LayeredDrawableGroup[Any] = LayeredDrawableGroup()

        # Assert
        assert group.default_layer == 0

    @pytest.mark.parametrize("layer", [0, 12, 2000, -3, -642])
    def test____dunder_init____default_layer(self, layer: int) -> None:
        # Arrange

        # Act
        group: LayeredDrawableGroup[Any] = LayeredDrawableGroup(default_layer=layer)

        # Assert
        assert group.default_layer == layer

    def test____add____default_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        default_layer: int,
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer
        drawable = mock_drawable_factory()
        drawable.has_group.return_value = False

        # Act
        layered_drawable_group.add(drawable)

        # Assert
        assert layered_drawable_group.get_layer(drawable) == default_layer

    @pytest.mark.parametrize("layer", [0, 2000, -3000])
    def test____add____defined_layer(
        self,
        layer: int,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        drawable.has_group.return_value = False

        # Act
        layered_drawable_group.add(drawable, layer=layer)

        # Assert
        assert layered_drawable_group.get_layer(drawable) == layer

    def test____add____layer_greater_than_all(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        for layer in range(10):
            self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=layer)
        assert len(layered_drawable_group.data) == 10
        layer = 272
        drawable = mock_drawable_factory()

        # Act
        layered_drawable_group.add(drawable, layer=layer)

        # Assert
        assert layered_drawable_group.data[10] is drawable

    def test____add____layer_lower_than_all(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        for layer in range(10):
            self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=layer)
        assert len(layered_drawable_group.data) == 10
        layer = -30
        drawable = mock_drawable_factory()

        # Act
        layered_drawable_group.add(drawable, layer=layer)

        # Assert
        assert layered_drawable_group.data[0] is drawable

    def test____add____layer_between_others(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=0)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=2)
        assert len(layered_drawable_group.data) == 2
        drawable = mock_drawable_factory()

        # Act
        layered_drawable_group.add(drawable, layer=1)

        # Assert
        assert layered_drawable_group.data[1] is drawable

    @pytest.mark.parametrize("top_of_layer", [True, False], ids=lambda b: f"top_of_layer=={b}")
    def test____add____same_layer(
        self,
        top_of_layer: bool,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=0)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=1)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=2)
        assert len(layered_drawable_group.data) == 3
        drawable_already_present = layered_drawable_group.data[1]
        drawable_to_add = mock_drawable_factory()

        # Act
        layered_drawable_group.add(drawable_to_add, layer=1, top_of_layer=top_of_layer)

        # Assert
        if top_of_layer:
            assert layered_drawable_group.data[1] is drawable_already_present
            assert layered_drawable_group.data[2] is drawable_to_add
        else:
            assert layered_drawable_group.data[1] is drawable_to_add
            assert layered_drawable_group.data[2] is drawable_already_present

    def test____remove____delete_layer_info(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, drawable, layer=1)
        assert drawable in layered_drawable_group
        assert layered_drawable_group.get_layer(drawable) == 1

        # Act
        layered_drawable_group.remove(drawable)

        # Assert
        with pytest.raises(ValueError, match=r"obj not in group"):
            _ = layered_drawable_group.get_layer(drawable)

    def test____pop____delete_layer_info(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, drawable, layer=1)
        assert drawable in layered_drawable_group
        assert layered_drawable_group.get_layer(drawable) == 1

        # Act
        layered_drawable_group.pop(0)

        # Assert
        with pytest.raises(ValueError, match=r"obj not in group"):
            _ = layered_drawable_group.get_layer(drawable)

    def test____clear____delete_layer_info(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable_list = [mock_drawable_factory() for _ in range(10)]
        self._add_mock_to_group(layered_drawable_group, *drawable_list, layer=1)
        assert all(drawable in layered_drawable_group for drawable in drawable_list)
        assert all(layered_drawable_group.get_layer(drawable) == 1 for drawable in drawable_list)

        # Act
        layered_drawable_group.clear()

        # Assert
        for drawable in drawable_list:
            with pytest.raises(ValueError, match=r"obj not in group"):
                _ = layered_drawable_group.get_layer(drawable)

    def test____get_layers____empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        default_layer: int,
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer

        # Act
        layers = layered_drawable_group.get_layers()

        # Assert
        assert layers == [default_layer]

    def test____get_layers____non_empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        default_layer: int,
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer
        expected_layers_list = list(range(-9, 10))
        for layer in expected_layers_list:
            if layer == default_layer:  # Do not add element in default layer
                continue
            self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=layer)
        assert not any(layered_drawable_group.get_layer(obj) == default_layer for obj in layered_drawable_group)

        # Act
        all_layers = layered_drawable_group.get_layers()

        # Assert
        assert all_layers == expected_layers_list

    def test____change_layer____different_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, drawable, layer=0)
        assert layered_drawable_group.get_layer(drawable) == 0

        # Act
        layered_drawable_group.change_layer(drawable, 2)

        # Assert
        assert layered_drawable_group.get_layer(drawable) == 2

    def test____change_layer____same_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, drawable, layer=2)
        assert layered_drawable_group.get_layer(drawable) == 2

        # Act
        layered_drawable_group.change_layer(drawable, 2)

        # Assert
        assert layered_drawable_group.get_layer(drawable) == 2

    @pytest.mark.parametrize("top_of_layer", [True, False])
    def test____change_layer____top_of_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
        top_of_layer: bool,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        drawable = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, drawable, layer=0)
        mock_insort = mocker.patch(f"{LayeredDrawableGroup.__module__}.insort_{'right' if top_of_layer else 'left'}")
        mock_other_insort = mocker.patch(f"{LayeredDrawableGroup.__module__}.insort_{'left' if top_of_layer else 'right'}")

        # Act
        layered_drawable_group.change_layer(drawable, 0, top_of_layer=top_of_layer)

        # Assert
        mock_insort.assert_called_once()
        mock_other_insort.assert_not_called()

    def test____get_top_layer____empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        default_layer: int,
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer

        # Act
        top_layer = layered_drawable_group.get_top_layer()

        # Assert
        assert top_layer == default_layer

    def test____get_top_layer____non_empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
        default_layer: int,
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer
        for layer in range(-9, 10):
            self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=layer)

        # Act
        top_layer = layered_drawable_group.get_top_layer()

        # Assert
        assert top_layer == 9

    def test____get_bottom_layer____empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        default_layer: int,
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer

        # Act
        bottom_layer = layered_drawable_group.get_bottom_layer()

        # Assert
        assert bottom_layer == default_layer

    def test____get_bottom_layer____non_empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
        default_layer: int,
    ) -> None:
        # Arrange
        layered_drawable_group.default_layer = default_layer
        for layer in range(-9, 10):
            self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=layer)

        # Act
        bottom_layer = layered_drawable_group.get_bottom_layer()

        # Assert
        assert bottom_layer == -9

    def test____get_top____empty_group(self, layered_drawable_group: LayeredDrawableGroup[Any]) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(IndexError):
            _ = layered_drawable_group.get_top()

    def test____get_top____non_empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        expected_top_object = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, expected_top_object, layer=12)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=10)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=12, top_of_layer=False)

        # Act
        top_object = layered_drawable_group.get_top()

        # Assert
        assert top_object is expected_top_object

    def test____get_bottom____empty_group(self, layered_drawable_group: LayeredDrawableGroup[Any]) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(IndexError):
            _ = layered_drawable_group.get_bottom()

    def test____get_bottom____non_empty_group(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        expected_bottom_object = mock_drawable_factory()
        self._add_mock_to_group(layered_drawable_group, expected_bottom_object, layer=12)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=15)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=12, top_of_layer=True)

        # Act
        bottom_object = layered_drawable_group.get_bottom()

        # Assert
        assert bottom_object is expected_bottom_object

    def test____move_to_front____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        mock_get_top_layer = mocker.patch.object(type(layered_drawable_group), "get_top_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer")
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_front(drawable)

        # Assert
        mock_get_top_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4562, top_of_layer=True)

    @pytest.mark.parametrize("top_of_layer", [True, False])
    def test____move_to_front____always_on_top_of_top_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
        top_of_layer: bool,
    ) -> None:
        # Arrange
        mock_get_top_layer = mocker.patch.object(type(layered_drawable_group), "get_top_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer")
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_front(drawable, top_of_layer=top_of_layer)

        # Assert
        mock_get_top_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4562, top_of_layer=True)

    @pytest.mark.parametrize("top_of_layer", [True, False])
    def test____move_to_front____before_first_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
        top_of_layer: bool,
    ) -> None:
        # Arrange
        mock_get_top_layer = mocker.patch.object(type(layered_drawable_group), "get_top_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer")
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_front(drawable, before_first=True, top_of_layer=top_of_layer)

        # Assert
        mock_get_top_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4563, top_of_layer=top_of_layer)

    def test____move_to_back____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        mock_get_bottom_layer = mocker.patch.object(type(layered_drawable_group), "get_bottom_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer")
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_back(drawable)

        # Assert
        mock_get_bottom_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4562, top_of_layer=False)

    @pytest.mark.parametrize("top_of_layer", [True, False])
    def test____move_to_back____always_on_bottom_of_bottom_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
        top_of_layer: bool,
    ) -> None:
        # Arrange
        mock_get_bottom_layer = mocker.patch.object(type(layered_drawable_group), "get_bottom_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer")
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_back(drawable, top_of_layer=top_of_layer)

        # Assert
        mock_get_bottom_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4562, top_of_layer=False)

    @pytest.mark.parametrize("top_of_layer", [True, False])
    def test____move_to_back____after_last_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mocker: MockerFixture,
        top_of_layer: bool,
    ) -> None:
        # Arrange
        mock_get_bottom_layer = mocker.patch.object(type(layered_drawable_group), "get_bottom_layer", return_value=4562)
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer", return_value=None)
        drawable = mocker.sentinel.drawable

        # Act
        layered_drawable_group.move_to_back(drawable, after_last=True, top_of_layer=top_of_layer)

        # Assert
        mock_get_bottom_layer.assert_called_once()
        mock_change_layer.assert_called_once_with(drawable, 4561, top_of_layer=top_of_layer)

    def test____iter_in_layer____empty_group(self, layered_drawable_group: LayeredDrawableGroup[Any]) -> None:
        # Arrange

        # Act
        elements = list(layered_drawable_group.iter_in_layer(layer=3000))

        # Assert
        assert elements == []

    def test____iter_in_layer____empty_layer(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=2999)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=3001)

        # Act
        elements = list(layered_drawable_group.iter_in_layer(layer=3000))

        # Assert
        assert elements == []

    def test____iter_in_layer____with_elements(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        drawable_list = [mock_drawable_factory() for _ in range(5)]
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=2999)
        self._add_mock_to_group(layered_drawable_group, mock_drawable_factory(), layer=3001)
        self._add_mock_to_group(layered_drawable_group, *drawable_list, layer=3000)

        # Act
        elements = list(layered_drawable_group.iter_in_layer(layer=3000))

        # Assert
        assert elements == drawable_list

    @pytest.mark.parametrize("layer", [0, 2000, -3000])
    def test____get_from_layer____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        layer: int,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        expected_elements = [mocker.sentinel.element_1, mocker.sentinel.element_2]
        mock_iter_in_layer = mocker.patch.object(
            type(layered_drawable_group), "iter_in_layer", return_value=iter(expected_elements)
        )

        # Act
        gotten_elements = layered_drawable_group.get_from_layer(layer)

        # Assert
        mock_iter_in_layer.assert_called_once_with(layer)
        assert gotten_elements == expected_elements

    @pytest.mark.parametrize("layer", [0, 2000, -3000])
    def test____remove_layer____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        layer: int,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        expected_elements = [mocker.sentinel.element_1, mocker.sentinel.element_2]
        mock_get_from_layer = mocker.patch.object(
            type(layered_drawable_group), "get_from_layer", return_value=expected_elements[:]
        )
        mock_remove = mocker.patch.object(type(layered_drawable_group), "remove", return_value=None)

        # Act
        removed_elements = layered_drawable_group.remove_layer(layer)

        # Assert
        mock_get_from_layer.assert_called_once_with(layer)
        mock_remove.assert_called_once_with(*expected_elements)
        assert removed_elements == expected_elements

    def test____reset_layer____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
    ) -> None:
        # Arrange
        from random import Random

        random = Random(42)

        drawable_list = [mock_drawable_factory() for _ in range(10)]
        for layer, drawable in enumerate(drawable_list, start=1):
            self._add_mock_to_group(layered_drawable_group, drawable, layer=layer)
        layered_drawable_group.data *= 3
        random.shuffle(layered_drawable_group.data)
        assert all(layered_drawable_group.data.count(d) == 3 for d in drawable_list)

        # Act
        layered_drawable_group.reset_layers()

        # Assert
        assert layered_drawable_group.data == drawable_list

    @pytest.mark.parametrize("layer1", [1, 3])
    @pytest.mark.parametrize("layer2", [3, 1])
    def test____switch_layer____default(
        self,
        layered_drawable_group: LayeredDrawableGroup[Any],
        mock_drawable_factory: Callable[[], MagicMock],
        mocker: MockerFixture,
        layer1: int,
        layer2: int,
    ) -> None:
        # Arrange
        mock_change_layer = mocker.patch.object(type(layered_drawable_group), "change_layer", return_value=None)
        drawable_list_layer1 = [mock_drawable_factory() for _ in range(10)]
        drawable_list_layer2 = [mock_drawable_factory() for _ in range(10)]
        self._add_mock_to_group(layered_drawable_group, *(mock_drawable_factory() for _ in range(10)), layer=0)
        self._add_mock_to_group(layered_drawable_group, *drawable_list_layer1, layer=1)
        self._add_mock_to_group(layered_drawable_group, *(mock_drawable_factory() for _ in range(10)), layer=2)
        self._add_mock_to_group(layered_drawable_group, *drawable_list_layer2, layer=3)

        # Act
        layered_drawable_group.switch_layer(layer1, layer2)

        # Assert
        if layer1 == layer2:
            mock_change_layer.assert_not_called()
        else:
            for drawable in drawable_list_layer1:
                mock_change_layer.assert_any_call(drawable, 3, top_of_layer=True)
            for drawable in drawable_list_layer2:
                mock_change_layer.assert_any_call(drawable, 1, top_of_layer=True)
            assert len(mock_change_layer.mock_calls) == 20
