# -*- coding: Utf-8 -*-

from __future__ import annotations

from copy import copy, deepcopy
from typing import TYPE_CHECKING, Any, Callable, Iterator

from pydiamond.audio.music import Music, MusicStream

import pygame
import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from ..mock.pygame.event import MockEventModule
    from ..mock.pygame.mixer import MockMixerModule, MockMixerMusicModule


@pytest.fixture(scope="module", autouse=True)
def do_not_encode_filepaths(module_mocker: MockerFixture) -> None:
    """Filepaths are manually encoded via pygame.encode_file_path in order not to have UnicodeEncodeError
    when calling pygame functions

    We do not need it for this test suite
    """
    module_mocker.patch("pydiamond.audio.music.encode_file_path", lambda f: f)


@pytest.fixture(scope="module", autouse=True)
def accept_setattr_on_music_stream(module_mocker: MockerFixture) -> None:
    module_mocker.patch.object(type(MusicStream), "__setattr__", type.__setattr__)


@pytest.fixture
def music_filepath_factory(tmp_path: Path) -> Callable[[str], str]:
    def factory(music_path: str) -> str:
        all_path = (tmp_path / music_path).resolve().absolute()
        all_path.parent.mkdir(exist_ok=True)
        all_path.touch()
        return str(all_path)

    return factory


@pytest.fixture
def music_factory(music_filepath_factory: Callable[[str], str]) -> Callable[[str], Music]:
    def factory(music_path: str) -> Music:
        return Music(music_filepath_factory(music_path))

    return factory


class TestMusicObject:
    @pytest.fixture
    @staticmethod
    def mock_music_stream(mocker: MockerFixture) -> MagicMock:
        return mocker.patch("pydiamond.audio.music.MusicStream", spec=MusicStream)

    def test__init__absolute_filepath(self, music_filepath_factory: Callable[[str], str]) -> None:
        # Arrange
        expected_filepath = music_filepath_factory("music.wav")

        # Act
        music = Music(expected_filepath)

        # Assert
        assert music.filepath == expected_filepath

    def test__init__relative_filepath(
        self,
        tmp_path: Path,
        music_filepath_factory: Callable[[str], str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        subdirectory = tmp_path / "subdirectory"
        subdirectory.mkdir()
        monkeypatch.chdir(subdirectory)
        relative_filepath = "../music.wav"
        expected_filepath = music_filepath_factory("music.wav")

        # Act
        music = Music(relative_filepath)

        # Assert
        assert music.filepath == expected_filepath

    def test__play__calls_MusicStream_play_method(
        self,
        music_factory: Callable[[str], Music],
        mock_music_stream: MagicMock,
        sentinel: Any,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        mock_music_stream_play: MagicMock = mock_music_stream.play

        # Act
        music_wav.play(repeat=sentinel.Music_play_repeat, fade_ms=sentinel.Music_play_fade_ms)

        # Assert
        mock_music_stream_play.assert_called_once_with(
            music_wav,
            repeat=sentinel.Music_play_repeat,
            fade_ms=sentinel.Music_play_fade_ms,
        )

    def test__queue__calls_MusicStream_queue_method(
        self,
        music_factory: Callable[[str], Music],
        mock_music_stream: MagicMock,
        sentinel: Any,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        mock_music_stream_queue: MagicMock = mock_music_stream.queue

        # Act
        music_wav.queue(repeat=sentinel.Music_queue_repeat)

        # Assert
        mock_music_stream_queue.assert_called_once_with(music_wav, repeat=sentinel.Music_queue_repeat)

    def test__object__cache(self, music_filepath_factory: Callable[[str], str]) -> None:
        # Arrange
        music_wav_filepath = music_filepath_factory("music.wav")

        # Act
        music_1 = Music(music_wav_filepath)
        music_2 = Music(music_wav_filepath)

        # Assert
        assert music_1 is music_2

    @pytest.mark.parametrize("copy_func", [copy, deepcopy])
    def test__object__is_not_copyable(self, copy_func: Callable[[Any], Any], music_factory: Callable[[str], Music]) -> None:
        # Arrange
        music_wav = music_factory("music.wav")

        # Act & Assert
        with pytest.raises(TypeError):
            _ = copy_func(music_wav)

    def test__object__is_not_picklable(self, music_factory: Callable[[str], Music]) -> None:
        # Arrange
        import pickle

        music_wav = music_factory("music.wav")

        # Act & Assert
        with pytest.raises(TypeError, match=r"cannot pickle .+"):
            _ = pickle.dumps(music_wav)


@pytest.mark.usefixtures("mock_pygame_mixer_music_module")
class TestMusicStream:
    @pytest.fixture(autouse=True)
    @staticmethod
    def call_musicstream_stop_at_end(mock_pygame_event_module: Any) -> Iterator[None]:
        stop = MusicStream.stop  # Prevent broken mocks...
        yield
        stop(unload=True)

    def test__play__calls_pygame_mixer_music_load_and_play(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")

        # Act
        MusicStream.play(music_wav, repeat=10, fade_ms=30)

        # Assert
        mock_pygame_mixer_music_module.load.assert_called_once_with(music_wav.filepath)
        mock_pygame_mixer_music_module.play.assert_called_once_with(loops=10, fade_ms=30)

    def test__play__ensure_to_stop_playback_before(
        self,
        music_factory: Callable[[str], Music],
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        mock_musicstream_stop = mocker.patch.object(MusicStream, "stop")

        # Act
        MusicStream.play(music_wav, repeat=10, fade_ms=10)

        # Assert
        mock_musicstream_stop.assert_called_once()

    def test__stop__calls_pygame_mixer_music_stop(
        self,
        mock_pygame_mixer_module: MockMixerModule,
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = (44100, -16, 2)  # Simulate default initialization

        # Act
        MusicStream.stop(unload=False)

        # Assert
        mock_pygame_mixer_music_module.stop.assert_called_once()
        mock_pygame_mixer_music_module.unload.assert_not_called()

    def test__stop__calls_pygame_mixer_music_stop_and_unload(
        self,
        mock_pygame_mixer_module: MockMixerModule,
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = (44100, -16, 2)  # Simulate default initialization

        # Act
        MusicStream.stop(unload=True)

        # Assert
        mock_pygame_mixer_music_module.stop.assert_called_once()
        mock_pygame_mixer_music_module.unload.assert_called_once()

    def test__stop__does_not_call_stop_and_unload_if_mixer_is_not_initialized(
        self,
        mock_pygame_mixer_module: MockMixerModule,
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = None  # Simulate no initialization

        # Act
        MusicStream.stop(unload=True)

        # Assert
        mock_pygame_mixer_music_module.stop.assert_not_called()
        mock_pygame_mixer_music_module.unload.assert_not_called()

    @pytest.mark.parametrize(
        ["cls_method_name", "pygame_music_function_name", "args"],
        [
            pytest.param("is_busy", "get_busy", None, id="is_busy"),
            pytest.param("pause", "pause", None, id="pause"),
            pytest.param("unpause", "unpause", None, id="unpause"),
            pytest.param("fadeout", "fadeout", (5,), id="fadeout(5)"),
            pytest.param("get_volume", "get_volume", None, id="get_volume"),
            pytest.param("set_volume", "set_volume", (0.36,), id="set_volume(0.36)"),
        ],
    )
    def test__method__pass_through(
        self,
        cls_method_name: str,
        pygame_music_function_name: str,
        args: tuple[Any, ...] | None,
        mock_pygame_mixer_music_module: MockMixerMusicModule,
        sentinel: Any,
    ) -> None:
        # Arrange
        mock_func: MagicMock = getattr(mock_pygame_mixer_music_module, pygame_music_function_name)
        sentinel_value: Any = getattr(sentinel, f"MusicStream_{cls_method_name}")
        mock_func.return_value = sentinel_value
        cls_method: Callable[..., Any] = getattr(MusicStream, cls_method_name)
        if args is None:
            args = ()

        # Act
        actual_value: Any = cls_method(*args)

        # Assert
        mock_func.assert_called_once_with(*args)
        assert actual_value is sentinel_value

    def test__queue__calls_pygame_mixer_music_queue(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        music2_wav = music_factory("music2.wav")
        MusicStream.play(music_wav)

        # Act
        MusicStream.queue(music2_wav, repeat=123)

        # Assert
        mock_pygame_mixer_music_module.queue.assert_called_once_with(music2_wav.filepath, loops=123)

    def test__queue__calls_MusicStream_play_if_not_busy(
        self,
        music_factory: Callable[[str], Music],
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        mock_musicstream_play = mocker.patch.object(MusicStream, "play")

        # Act
        MusicStream.queue(music_wav, repeat=123)

        # Assert
        mock_musicstream_play.assert_called_once_with(music_wav, repeat=123)

    def test__queue__raises_error_for_infinite_loop(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        music2_wav = music_factory("music2.wav")
        MusicStream.play(music_wav)

        # Act & Assert
        with pytest.raises(ValueError, match=r"Cannot set infinite loop for queued musics"):
            MusicStream.queue(music2_wav, repeat=-1)

        # Assert
        mock_pygame_mixer_music_module.queue.assert_not_called()

    def test__queue__raises_error_if_queue_after_infinite_loop_playback_running(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
    ) -> None:
        # Arrange
        music_wav = music_factory("music.wav")
        music2_wav = music_factory("music2.wav")
        MusicStream.play(music_wav, repeat=-1)  # Infinite loop

        # Act & Assert
        with pytest.raises(ValueError, match=r"The playing music loops infinitely, queued musics will not be set"):
            MusicStream.queue(music2_wav, repeat=123)

        # Assert
        mock_pygame_mixer_music_module.queue.assert_not_called()


@pytest.mark.functional
@pytest.mark.usefixtures("mock_pygame_event_module", "mock_pygame_mixer_module")
class TestMusicStreamFunctional:
    @pytest.fixture(autouse=True)
    @staticmethod
    def call_musicstream_stop_at_end(
        mock_pygame_event_module: Any,  # Used only for explicit fixture dependency, forcing it to be called before this fixture
        mock_pygame_mixer_module: MockMixerModule,
    ) -> Iterator[None]:
        mock_pygame_mixer_module.get_init.return_value = None
        stop = MusicStream.stop  # Prevent broken mocks...
        yield
        stop(unload=True)

    @pytest.fixture
    @staticmethod
    def mixer_music_endevent() -> pygame.event.Event:
        return pygame.event.Event(pygame.mixer.music.get_endevent())

    def test__play__replay_music_if_it_is_the_actual_running_playback(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
        mocker: MockerFixture,
    ) -> None:
        music_wav = music_factory("music.wav")
        MusicStream.play(music_wav)

        mock_musicstream_stop = mocker.patch.object(MusicStream, "stop")
        mock_pygame_mixer_music_module.load.reset_mock()
        mock_pygame_mixer_music_module.play.reset_mock()

        MusicStream.play(music_wav, repeat=123, fade_ms=456)

        mock_musicstream_stop.assert_not_called()
        mock_pygame_mixer_music_module.load.assert_not_called()
        mock_pygame_mixer_music_module.play.assert_called_once_with(loops=123, fade_ms=456)

    def test__stop__without_unload_and_replay_does_not_reload_music(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
        mocker: MockerFixture,
    ) -> None:
        music_wav = music_factory("music.wav")
        MusicStream.play(music_wav)
        MusicStream.stop(unload=False)

        mock_musicstream_stop = mocker.patch.object(MusicStream, "stop")
        mock_pygame_mixer_music_module.load.reset_mock()
        mock_pygame_mixer_music_module.play.reset_mock()

        MusicStream.play(music_wav, repeat=123, fade_ms=456)

        mock_musicstream_stop.assert_not_called()
        mock_pygame_mixer_music_module.load.assert_not_called()
        mock_pygame_mixer_music_module.play.assert_called_once_with(loops=123, fade_ms=456)

    def test__stop__does_not_post_if_there_was_no_playbacks(
        self,
        mock_pygame_event_module: MockEventModule,
    ) -> None:
        MusicStream.stop()

        mock_pygame_event_module.post.assert_not_called()

    @pytest.mark.usefixtures("mock_pygame_mixer_music_module")
    def test__get_music__get_running_music_object(self, music_factory: Callable[[str], Music]) -> None:
        music_wav = music_factory("music.wav")

        assert MusicStream.get_music() is None

        MusicStream.play(music_wav)

        assert MusicStream.get_music() is music_wav

        MusicStream.stop()

        assert MusicStream.get_music() is None

    @pytest.mark.usefixtures("mock_pygame_mixer_music_module")
    def test__fadeout__post_event_for_stopped_playback(
        self,
        music_factory: Callable[[str], Music],
        mixer_music_endevent: pygame.event.Event,
    ) -> None:
        music_wav = music_factory("music.wav")

        MusicStream.play(music_wav)
        # fadeout() will trigger mixer_music_endevent
        MusicStream.fadeout(500)

        assert MusicStream._handle_event(mixer_music_endevent)

        assert mixer_music_endevent.finished is music_wav
        assert mixer_music_endevent.next is None

    def test__queue__scenario_mutiple_calls(
        self,
        music_factory: Callable[[str], Music],
        mock_pygame_mixer_music_module: MockMixerMusicModule,
        mixer_music_endevent: pygame.event.Event,
    ) -> None:
        """Senario: Playlist and events"""

        music1_wav = music_factory("music1.wav")
        music2_wav = music_factory("music2.wav")
        music3_wav = music_factory("music3.wav")
        music4_wav = music_factory("music4.wav")

        music1_wav.play(repeat=3)
        music2_wav.queue(repeat=2)
        music3_wav.queue(repeat=4)
        music4_wav.queue()  # repeat == 0
        mock_pygame_mixer_music_module.queue.assert_called_once_with(music2_wav.filepath, loops=2)

        assert MusicStream.get_music() is music1_wav
        assert MusicStream.get_queue() == [music2_wav, music3_wav, music4_wav]
        assert MusicStream.get_playlist() == [music1_wav, music2_wav, music3_wav, music4_wav]

        mock_pygame_mixer_music_module.load.reset_mock()  # Reset call made by music1_wav.play()
        mock_pygame_mixer_music_module.play.reset_mock()  # Reset call made by music1_wav.play()
        mock_pygame_mixer_music_module.queue.reset_mock()  # Needed to use assert_called_once()

        # A few moments later...
        # music1_wav ends playing (all loops consumed)
        # queued music2_wav automatically starts playing and pygame.mixer.music post the mixer_music_endevent
        # this event will be caught by Window and sent to MusicStream...
        assert MusicStream._handle_event(mixer_music_endevent)
        # We can then queue the next song in the mixer.music stream
        mock_pygame_mixer_music_module.queue.assert_called_once_with(music3_wav.filepath, loops=4)
        assert mixer_music_endevent.finished is music1_wav
        assert mixer_music_endevent.next is music2_wav
        # Load/play the next is performed by pygame.mixer.music module, so there is no need to call load and play
        mock_pygame_mixer_music_module.load.assert_not_called()
        mock_pygame_mixer_music_module.play.assert_not_called()
        assert MusicStream.get_music() is music2_wav
        assert MusicStream.get_queue() == [music3_wav, music4_wav]
        assert MusicStream.get_playlist() == [music2_wav, music3_wav, music4_wav]

        mock_pygame_mixer_music_module.queue.reset_mock()  # Needed to use assert_called_once()

        # music2_wav ends playing, same scenario:
        assert MusicStream._handle_event(mixer_music_endevent)
        mock_pygame_mixer_music_module.queue.assert_called_once_with(music4_wav.filepath, loops=0)
        assert mixer_music_endevent.finished is music2_wav
        assert mixer_music_endevent.next is music3_wav
        mock_pygame_mixer_music_module.load.assert_not_called()
        mock_pygame_mixer_music_module.play.assert_not_called()
        assert MusicStream.get_music() is music3_wav
        assert MusicStream.get_queue() == [music4_wav]
        assert MusicStream.get_playlist() == [music3_wav, music4_wav]

        mock_pygame_mixer_music_module.queue.reset_mock()  # Needed to use assert_not_called() in the next step

        # music3_wav ends playing, same scenario (except for one thing: there is no following musics after music4_wav):
        assert MusicStream._handle_event(mixer_music_endevent)
        mock_pygame_mixer_music_module.queue.assert_not_called()
        assert mixer_music_endevent.finished is music3_wav
        assert mixer_music_endevent.next is music4_wav
        mock_pygame_mixer_music_module.load.assert_not_called()
        mock_pygame_mixer_music_module.play.assert_not_called()
        assert MusicStream.get_music() is music4_wav
        assert MusicStream.get_queue() == []
        assert MusicStream.get_playlist() == [music4_wav]

        mock_pygame_mixer_music_module.queue.reset_mock()  # Needed to use assert_not_called() in the next step

        # music4_wav ends playing, simply notify user
        assert MusicStream._handle_event(mixer_music_endevent)
        mock_pygame_mixer_music_module.queue.assert_not_called()
        assert mixer_music_endevent.finished is music4_wav
        assert mixer_music_endevent.next is None
        assert MusicStream.get_music() is None
        assert MusicStream.get_queue() == []
        assert MusicStream.get_playlist() == []


@pytest.mark.functional
class TestPygameMixerMusicModuleAlteration:
    def test__get_endevent__returns_custom_userevent(self) -> None:
        assert pygame.mixer.music.get_endevent() != pygame.NOEVENT
        assert pygame.USEREVENT < pygame.mixer.music.get_endevent() < pygame.NUMEVENTS

        # Just to be sure...
        from pydiamond.window.event import BuiltinEventType

        assert pygame.mixer.music.get_endevent() == BuiltinEventType.MUSICEND

    def test__set_endevent__cannot_be_called_anymore(self) -> None:
        with pytest.raises(TypeError, match=r"Call to function [\w\.]+ is forbidden"):
            pygame.mixer.music.set_endevent(pygame.NOEVENT)
