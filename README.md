# PyDiamond
PyDiamond engine is a game engine for Python game developers.

The framework uses the popular [pygame library](https://github.com/pygame/pygame/).

## Usage
Example with the minimal requirements:
```py
from pydiamond.window.display import Window

def main() -> int:
    w: Window = Window(title="my window", size=(800, 600))
    with w.open():
        while w.loop():
            for event in w.process_events():
                # do some stuff
                pass
            w.clear()
            # draw your objects
            w.refresh()
    return 0

if __name__ == "__main__":
    exit(main())
```
This code will open a small window.

### Documentation
Coming soon. :)

## Dependencies
PyDiamond is developed based on pygame and Python (obviously). In addition, some features of pygame are available with a specific version of the SDL.

Dependency version:
- CPython >= 3.10
- pygame == 2.1.2
- SDL >= 2.0.16
- SDL_image >= 2.0.0
- SDL_mixer >= 2.0.0
- Other python dependencies referred by `requirements.txt`

Use the following command to install all the necessary dependencies
```sh
python3 -m pip install -r requirements.txt
```

## Credits
### Vendored-in packages
- [Gradient](https://www.pygame.org/project-gradients-307-.html) module by DR0ID
- [OrderedSet](https://github.com/rspeer/ordered-set) collection by rspeer

## License
This project is licensed under the terms of the [GNU General Public License v3.0](https://github.com/francis-clairicia/PyDiamond/blob/main/LICENSE).
