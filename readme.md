## Installing

While in your python environment, navigate to this directory and run the following commands:

-   `pip install pyqt5 pillow`
-   `python setup.py install`

## Usage

While inside the same python environment, run the following command:

`tsm <directory> <name>`

Here, `<directory>` is the directory within which your assets are found. Only png files are considered. The search is recursive. Finally, <name> is the name you want to give to your sheet. At the moment, sheets have a default width/height because Im lazy.

When you exit, a <name>.p and <name>.png file are saved. If a <name>.p file is detected in the <directory> you gave, this file is automatically loaded.

## Hotkeys:

-   R: rotate selected tile by 90°
-   E: flip selected tile vertically
-   W: flip selected tile horizontally
-   Tab: select next unused tile

## Extras:

-   double click on tile to highlight all tiles in the grid where this tile is present in blue
