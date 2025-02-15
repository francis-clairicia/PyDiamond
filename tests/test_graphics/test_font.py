from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydiamond.graphics.font import (
    Font,
    FontFactory,
    FontSizeInfo,
    GlyphMetrics,
    SysFont,
    SysFontNotFound,
    get_default_font,
    get_fonts,
    match_font,
)

import pygame.freetype
import pytest
from pygame import Surface

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from ..mock.pygame.freetype import MockFreetypeModule
    from ..mock.pygame.sysfont import MockSysFontModule


def test____get_fonts____uses_pygame_sysfont_getfonts(
    mock_pygame_sysfont_module: MockSysFontModule, mocker: MockerFixture
) -> None:
    # Arrange
    mock_pygame_sysfont_module.get_fonts.return_value = mocker.sentinel.get_fonts

    # Act
    rv = get_fonts()

    # Assert
    mock_pygame_sysfont_module.get_fonts.assert_called_once_with()
    assert rv is mocker.sentinel.get_fonts


def test____match_font____uses_pygame_sysfont_match_font(
    mock_pygame_sysfont_module: MockSysFontModule, mocker: MockerFixture
) -> None:
    # Arrange
    mock_pygame_sysfont_module.match_font.return_value = mocker.sentinel.match_font
    font_name: str = mocker.sentinel.font_name
    font_bold: bool = mocker.sentinel.font_bold
    font_italic: bool = mocker.sentinel.font_italic

    # Act
    rv = match_font(font_name, font_bold, font_italic)

    # Assert
    mock_pygame_sysfont_module.match_font.assert_called_once_with(font_name, bold=font_bold, italic=font_italic)
    assert rv is mocker.sentinel.match_font


def test____get_default_font____uses_pygame_freetype_get_default_font(
    mock_pygame_freetype_module: MockFreetypeModule, mocker: MockerFixture
) -> None:
    # Arrange
    mock_pygame_freetype_module.get_default_font.return_value = mocker.sentinel.get_default_font

    # Act
    rv = get_default_font()

    # Assert
    mock_pygame_freetype_module.get_default_font.assert_called_once_with()
    assert rv is mocker.sentinel.get_default_font


class TestSysFont:
    @pytest.fixture
    @staticmethod
    def mock_Font(mocker: MockerFixture) -> MagicMock:
        return mocker.patch(f"{Font.__module__}.Font", autospec=True)

    @pytest.fixture
    @staticmethod
    def mock_font_instance(mock_Font: MagicMock) -> MagicMock:
        return mock_Font.return_value

    def test____call____dispatch(self, mock_pygame_sysfont_module: MockSysFontModule, mocker: MockerFixture) -> None:
        # Arrange
        mock_pygame_sysfont_module.SysFont.return_value = mocker.sentinel.font
        font_name: str = mocker.sentinel.font_name
        font_size: int = mocker.sentinel.font_size
        font_bold: bool = mocker.sentinel.font_bold
        font_italic: bool = mocker.sentinel.font_italic

        # Act
        font = SysFont(font_name, font_size, font_bold, font_italic)

        # Assert
        mock_pygame_sysfont_module.SysFont.assert_called_once_with(
            font_name,
            font_size,
            bold=font_bold,
            italic=font_italic,
            constructor=mocker.ANY,
        )
        assert font is mocker.sentinel.font

    def test____constructor____create_our_font(
        self, mock_Font: MagicMock, mock_font_instance: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        from random import Random

        random = Random(42)

        font_size = 42

        # Act
        font = SysFont(random.choice(get_fonts()), font_size)

        # Assert
        mock_Font.assert_called_once_with(mocker.ANY, font_size)
        mock_font_instance.config.update.assert_called_once_with(wide=False, oblique=False)
        assert font is mock_font_instance

    @pytest.mark.parametrize("raise_if_not_found", [True, False], ids=lambda b: f"raise_if_not_found=={b}")
    @pytest.mark.parametrize(
        "font_name", [[], "", "an_impossible_sysfont_name", ["an_impossible_sysfont_name"]], ids=lambda e: f"font_name=={e!r}"
    )
    def test____constructor____no_matching_font(
        self,
        font_name: str | list[str],
        raise_if_not_found: bool,
        mock_Font: MagicMock,
    ) -> None:
        # Arrange
        font_size = 42

        # Act & Assert
        if raise_if_not_found:
            with pytest.raises(SysFontNotFound):
                _ = SysFont(font_name, font_size, raise_if_not_found=raise_if_not_found)

            mock_Font.assert_not_called()
        else:
            _ = SysFont(font_name, font_size, raise_if_not_found=raise_if_not_found)
            mock_Font.assert_called_once_with(None, font_size)


class TestFont:
    @pytest.fixture
    @staticmethod
    def mock_freetype_font(mock_pygame_freetype_module: MockFreetypeModule) -> MagicMock:
        return mock_pygame_freetype_module.Font.return_value

    @pytest.fixture
    def font(self, mock_freetype_font: Any) -> Font:
        return Font(None)

    def test____dunder_init____none_font_name(
        self, mock_pygame_freetype_module: MockFreetypeModule, mocker: MockerFixture
    ) -> None:
        # Arrange

        # Act
        _ = Font(None)

        # Assert
        mock_pygame_freetype_module.Font.assert_called_once_with(None, size=mocker.ANY, resolution=mocker.ANY)

    def test____dunder_init____string_font_name(
        self, mock_pygame_freetype_module: MockFreetypeModule, mocker: MockerFixture
    ) -> None:
        # Arrange

        # Act
        _ = Font("font.ttf")

        # Assert
        mock_pygame_freetype_module.Font.assert_called_once_with("font.ttf", size=mocker.ANY, resolution=mocker.ANY)

    def test____dunder_init____file_io_font(
        self, mock_pygame_freetype_module: MockFreetypeModule, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        # Arrange
        font_filepath = (tmp_path / "font.ttf").absolute()
        font_filepath.touch()

        with font_filepath.open("rb") as file_io:
            # Act
            _ = Font(file_io)

            # Assert
            mock_pygame_freetype_module.Font.assert_called_once_with(file_io, size=mocker.ANY, resolution=mocker.ANY)

    @pytest.mark.parametrize(
        ["given_size", "expected_size"],
        [
            pytest.param(15, 15, id="given_size==15|expected_size==15"),
            pytest.param(0, 1, id="given_size==0|expected_size==1"),
            pytest.param(-15, 1, id="given_size==-15|expected_size==1"),
        ],
    )
    def test____dunder_init____size(
        self, given_size: int, expected_size: int, mock_pygame_freetype_module: MockFreetypeModule, mocker: MockerFixture
    ) -> None:
        # Arrange

        # Act
        _ = Font(None, given_size)

        # Assert
        mock_pygame_freetype_module.Font.assert_called_once_with(mocker.ANY, size=expected_size, resolution=mocker.ANY)

    @pytest.mark.parametrize(
        "property",
        [
            "name",
            "resolution",
            "height",
            "ascender",
            "descender",
            "fixed_width",
            "fixed_sizes",
            "scalable",
        ],
    )
    def test____read_only_property____pass_through(
        self, property: str, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        sentinel_value: Any = getattr(mocker.sentinel, f"pg_freetype_Font_{property}")
        setattr(mock_freetype_font, property, sentinel_value)
        method: Callable[[], Any] = getattr(font, property)

        # Act
        rv = method()

        # Assert
        assert rv is sentinel_value

    def test____get_scale_size____uniform_size(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        font_size = mocker.sentinel.font_size
        mock_freetype_font.size = font_size

        # Act
        scale_size = font.get_scale_size()

        # Assert
        assert scale_size == (font_size, font_size)

    def test____get_scale_size____tuple_size(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        font_width = mocker.sentinel.font_width
        font_height = mocker.sentinel.font_height
        mock_freetype_font.size = (font_width, font_height)

        # Act
        scale_size = font.get_scale_size()

        # Assert
        assert scale_size == (font_width, font_height)

    def test____set_scale_size____width_and_height_are_not_equal(
        self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        font_width = mocker.sentinel.font_width
        font_height = mocker.sentinel.font_height

        # Act
        font.set_scale_size((font_width, font_height))

        # Assert
        assert mock_freetype_font.size == (font_width, font_height)

    def test____set_scale_size____width_and_height_are_equal(
        self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        font_width = mocker.sentinel.font_width
        font_height = font_width

        # Act
        font.set_scale_size((font_width, font_height))

        # Assert
        assert mock_freetype_font.size is font_width

    def test____get_rect____default(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.get_rect.return_value = mocker.sentinel.font_rect

        # Act
        rect = font.get_rect("TEXT")

        # Assert
        mock_freetype_font.get_rect.assert_called_once_with("TEXT", style=pygame.freetype.STYLE_DEFAULT, rotation=0, size=0)
        assert rect is mocker.sentinel.font_rect

    def test____get_rect____with_parameters(self, font: Font, mock_freetype_font: MagicMock) -> None:
        # Arrange

        # Act
        font.get_rect("TEXT", style=1234, rotation=180, size=12)

        # Assert
        mock_freetype_font.get_rect.assert_called_once_with("TEXT", style=1234, rotation=180, size=12)

    def test____get_rect____without_rect_kwargs(self, font: Font, mocker: MockerFixture) -> None:
        # Arrange
        mock_move_rect = mocker.patch(f"{Font.__module__}.move_rect_in_place", autospec=True)

        # Act
        font.get_rect("TEXT")

        # Assert
        mock_move_rect.assert_not_called()

    def test____get_rect____with_rect_kwargs(self, font: Font, mocker: MockerFixture) -> None:
        # Arrange
        mock_move_rect = mocker.patch(f"{Font.__module__}.move_rect_in_place", autospec=True)

        # Act
        rect = font.get_rect("TEXT", x=mocker.sentinel.x, bottom=mocker.sentinel.bottom)

        # Assert
        mock_move_rect.assert_called_once_with(rect, x=mocker.sentinel.x, bottom=mocker.sentinel.bottom)

    def test____get_metrics____default(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.get_metrics.return_value = [(1, 2, 3, 4, 5.6, 7.8)]

        # Act
        metrics = font.get_metrics("TEXT", mocker.sentinel.font_size)

        # Assert
        mock_freetype_font.get_metrics.assert_called_once_with("TEXT", size=mocker.sentinel.font_size)
        assert len(metrics) == 1
        assert isinstance(metrics[0], GlyphMetrics)
        assert metrics[0].min_x == 1
        assert metrics[0].max_x == 2
        assert metrics[0].min_y == 3
        assert metrics[0].max_y == 4
        assert metrics[0].horizontal_advance_x == 5.6
        assert metrics[0].horizontal_advance_y == 7.8

    @pytest.mark.parametrize("info", ["ascender", "descender", "height", "glyph_height"])
    def test____get_sized_info____default(
        self, info: str, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        mock_freetype_font_method: MagicMock = getattr(mock_freetype_font, f"get_sized_{info}")
        mock_freetype_font_method.return_value = mocker.sentinel.size_returned
        font_method: Callable[[Any], Any] = getattr(font, f"get_sized_{info}")

        # Act
        rv = font_method(mocker.sentinel.size_as_parameter)

        # Assert
        mock_freetype_font_method.assert_called_once_with(mocker.sentinel.size_as_parameter)
        assert rv is mocker.sentinel.size_returned

    def test____get_sizes____default(self, font: Font, mock_freetype_font: MagicMock) -> None:
        # Arrange
        mock_freetype_font.get_sizes.return_value = [(1, 2, 3, 4.5, 6.7)]

        # Act
        sizes = font.get_sizes()

        # Assert
        mock_freetype_font.get_sizes.assert_called_once_with()
        assert len(sizes) == 1
        assert isinstance(sizes[0], FontSizeInfo)
        assert sizes[0].point_size == 1
        assert sizes[0].width == 2
        assert sizes[0].height == 3
        assert sizes[0].horizontal_ppem == 4.5
        assert sizes[0].vertical_ppem == 6.7

    def test____render____default(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.render.return_value = mocker.sentinel.render_rect

        # Act
        rv = font.render("TEXT", (255, 255, 255, 255))

        # Assert
        mock_freetype_font.render.assert_called_once_with(
            "TEXT",
            bgcolor=None,
            fgcolor=(255, 255, 255, 255),
            style=pygame.freetype.STYLE_DEFAULT,
            rotation=0,
            size=0,
        )
        assert rv is mocker.sentinel.render_rect

    def test____render____with_parameters(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.render.return_value = mocker.sentinel.render_rect

        # Act
        rv = font.render(
            "TEXT",
            (255, 255, 255, 255),
            bgcolor=mocker.sentinel.bgcolor,
            style=mocker.sentinel.style,
            rotation=180,
            size=mocker.sentinel.size,
        )

        # Assert
        mock_freetype_font.render.assert_called_once_with(
            "TEXT",
            bgcolor=mocker.sentinel.bgcolor,
            fgcolor=(255, 255, 255, 255),
            style=mocker.sentinel.style,
            rotation=180,
            size=mocker.sentinel.size,
        )
        assert rv is mocker.sentinel.render_rect

    def test____render_to____default(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.render_to.return_value = mocker.sentinel.render_rect
        target_surface: Surface = mocker.sentinel.target_surface
        target_dest: tuple[float, float] = mocker.sentinel.target_dest

        # Act
        rv = font.render_to(target_surface, target_dest, "TEXT", (255, 255, 255, 255))

        # Assert
        mock_freetype_font.render_to.assert_called_once_with(
            target_surface,
            target_dest,
            "TEXT",
            bgcolor=None,
            fgcolor=(255, 255, 255, 255),
            style=pygame.freetype.STYLE_DEFAULT,
            rotation=0,
            size=0,
        )
        assert rv is mocker.sentinel.render_rect

    def test____render_to____with_parameters(self, font: Font, mock_freetype_font: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_freetype_font.render_to.return_value = mocker.sentinel.render_rect
        target_surface: Surface = mocker.sentinel.target_surface
        target_dest: tuple[float, float] = mocker.sentinel.target_dest

        # Act
        rv = font.render_to(
            target_surface,
            target_dest,
            "TEXT",
            (255, 255, 255, 255),
            bgcolor=mocker.sentinel.bgcolor,
            style=mocker.sentinel.style,
            rotation=180,
            size=mocker.sentinel.size,
        )

        # Assert
        mock_freetype_font.render_to.assert_called_once_with(
            target_surface,
            target_dest,
            "TEXT",
            bgcolor=mocker.sentinel.bgcolor,
            fgcolor=(255, 255, 255, 255),
            style=mocker.sentinel.style,
            rotation=180,
            size=mocker.sentinel.size,
        )
        assert rv is mocker.sentinel.render_rect


class TestFontFactory:
    @pytest.fixture(autouse=True)
    @staticmethod
    def mock_Font(mocker: MockerFixture) -> MagicMock:
        return mocker.patch(f"{Font.__module__}.Font", autospec=True)

    @pytest.fixture(autouse=True)
    @staticmethod
    def mock_SysFont(mocker: MockerFixture, mock_Font_instance: MagicMock) -> MagicMock:
        return mocker.patch(f"{Font.__module__}.SysFont", autospec=True, return_value=mock_Font_instance)

    @pytest.fixture
    @staticmethod
    def mock_Font_instance(mock_Font: MagicMock) -> MagicMock:
        return mock_Font.return_value

    @pytest.fixture(autouse=True)
    @staticmethod
    def mock_isinstance(mocker: MockerFixture, mock_Font: MagicMock, mock_Font_instance: MagicMock) -> None:
        from builtins import isinstance

        def mock_isinstance(obj: object, class_or_tuple: Any) -> bool:
            if class_or_tuple is mock_Font:
                return obj is mock_Font_instance
            return isinstance(obj, class_or_tuple)

        mocker.patch(f"{Font.__module__}.isinstance", mock_isinstance)

    def test____create_font____from_none(
        self,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange

        # Act
        font = FontFactory.create_font(None)

        # Assert
        mock_SysFont.assert_not_called()
        mock_Font.assert_called_once_with(None, mocker.ANY)
        assert font is mock_Font_instance

    @pytest.mark.parametrize(
        "filename",
        [
            None,
            "font.ttf",
            "/path/to/font",
            b"font.ttf",
            b"/path/to/font",
            Path("font"),
        ],
        ids=repr,
    )
    def test____create_font____from_tuple_with_filename(
        self,
        filename: str | bytes | Path | None,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange

        # Act
        font = FontFactory.create_font((filename, mocker.sentinel.font_size))

        # Assert
        mock_SysFont.assert_not_called()
        mock_Font.assert_called_once_with(filename, mocker.sentinel.font_size)
        assert font is mock_Font_instance

    def test____create_font____from_tuple_with_sysfont_name(
        self,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange

        # Act
        font = FontFactory.create_font(("a_random_sysfont", mocker.sentinel.font_size))

        # Assert
        mock_Font.assert_not_called()
        mock_SysFont.assert_called_once_with(
            "a_random_sysfont",
            mocker.sentinel.font_size,
            bold=mocker.ANY,
            italic=mocker.ANY,
            raise_if_not_found=False,
        )
        assert font is mock_Font_instance

    def test____create_font____from_font(
        self,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
    ) -> None:
        # Arrange

        # Act
        font = FontFactory.create_font(mock_Font_instance)

        # Assert
        mock_Font.assert_not_called()
        mock_SysFont.assert_not_called()
        assert font is mock_Font_instance

    def test____create_font____bold_italic_underline_parameters_applied_for_Font_instance(
        self,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        filename = Path("font")

        # Act
        _ = FontFactory.create_font(
            (filename, mocker.sentinel.font_size),
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )

        # Assert
        mock_SysFont.assert_not_called()
        mock_Font.assert_called_once()
        mock_Font_instance.config.update.assert_called_once_with(
            wide=mocker.sentinel.font_bold,
            oblique=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )

    def test____create_font____bold_italic_underline_parameters_applied_for_SysFont_instance(
        self,
        mock_Font: MagicMock,
        mock_Font_instance: MagicMock,
        mock_SysFont: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        filename = "sysfont"

        # Act
        _ = FontFactory.create_font(
            (filename, mocker.sentinel.font_size),
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )

        # Assert
        mock_Font.assert_not_called()
        mock_SysFont.assert_called_once_with(
            "sysfont",
            mocker.sentinel.font_size,
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            raise_if_not_found=False,
        )
        mock_Font_instance.config.update.assert_called_once_with(
            underline=mocker.sentinel.font_underline,
        )

    def test____factory____from_path(self, mock_Font: MagicMock, mock_Font_instance: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        mock_create_font = mocker.patch.object(FontFactory, "create_font", return_value=mock_Font_instance)
        factory = FontFactory("path")

        # Act
        font = factory(
            mocker.sentinel.font_size,
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )

        # Assert
        mock_Font.assert_not_called()
        mock_create_font.assert_called_once_with(
            ("path", mocker.sentinel.font_size),
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )
        assert font is mock_Font_instance

    def test____factory____from_resource(
        self, mock_Font: MagicMock, mock_Font_instance: MagicMock, mocker: MockerFixture
    ) -> None:
        # Arrange
        from io import BytesIO
        from typing import BinaryIO, ContextManager

        class MockResource:
            name: str = "MockResource"

            def as_file(self) -> ContextManager[Path]:
                raise NotImplementedError

            def open(self) -> BinaryIO:
                return BytesIO(b"data")

        mock_create_font = mocker.patch.object(FontFactory, "create_font", return_value=mock_Font_instance)
        factory = FontFactory(MockResource())

        # Act
        font = factory(
            mocker.sentinel.font_size,
            bold=mocker.sentinel.font_bold,
            italic=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )

        # Assert
        mock_create_font.assert_not_called()
        mock_Font.assert_called_once_with(
            mocker.ANY,
            mocker.sentinel.font_size,
        )
        assert font is mock_Font_instance
        mock_Font_instance.config.update.assert_called_once_with(
            wide=mocker.sentinel.font_bold,
            oblique=mocker.sentinel.font_italic,
            underline=mocker.sentinel.font_underline,
        )
