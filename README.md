# PyDiamond
PyDiamond engine is a game engine inteded to game developers in Python language.

The framework uses the popular [pygame library](https://github.com/pygame/pygame/).

## Usage
Example with the minimal requirements:
```py
from py_diamond.window.display import Window

def main() -> int:
    w: Window = Window(title="my window", size=(800, 600))
    with w.open():
        while w.is_open():
            for event in w.process_events():
                # do some stuff
                pass
            # draw your object
            w.refresh()
    return 0

if __name__ == "__main__":
    exit(main())
```
This code will open a small window.

## License
This project is licensed under the terms of the [GNU General Public License v3.0](./LICENSE).
