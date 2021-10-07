## Installing

While in your python environment, navigate to this directory and run the following commands:

-   `pip install pyqt5 pillow numpy`
-   `python setup.py install`

## Usage

While inside the same python environment, run the following command:

`tsm <command> <arg1> <arg2> <...>`

The first argument <command> decides which part of tsm to use. Each command has their own subarguments:

### open

Full command: `tsm open <directory> <picklePath>`

Here, `<directory>` is the directory within which your assets are found. Only png files are considered. The search is recursive. Finally, <picklePath> is the path you want to give to your sheet. At the moment, sheets have a default width/height because Im lazy.

When you exit, a `<picklePath>.p` and `<picklePath>.png` file are saved. If a `<picklePath>.p` file already exists, this file is automatically loaded.

### darken

Full command: `tsm darken <imagePath> <r> <g> <b> <a>`

Here, `<imagePath>` is a path to the image you want to darken. Arguments `<r>, <g>, <b>, <a>` are the color and alpha values of the filter to be applied (from 0-1). Output will be saved at `<imagePath>_darkened.png`.

## Hotkeys:

-   R: rotate selected tile by 90°
-   E: flip selected tile vertically
-   W: flip selected tile horizontally
-   Tab: select next unused tile
-   1-5: Select zoom level

## Extras:

-   double click on tile to highlight all tiles in the grid where this tile is present in blue
