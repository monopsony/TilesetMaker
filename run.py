#!/usr/bin/python
import sys, glob, os, pickle, math
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QTreeWidgetItem, QShortcut, QTableWidgetItem
from window import Ui_Form
from PIL.ImageQt import ImageQt
from PIL import Image, ImageDraw, ImageOps
from table import Ui_Form as TableForm
from itertools import chain
import numpy as np

tableStylesheet = """
QTableWidget {background-color: transparent;}
QHeaderView::section {
    background-color: transparent;
    border-style: none; 
}
QHeaderView {background-color: transparent;}
QTableCornerButton::section {background-color: transparent;}
QWidget {border: none;}
QTableView {    
    gridline-color: #BCBCBC;
}
QTableView::item::hover
{
    background-color: #88C8EDFF;
}
QHeaderView::section:horizontal
{
    border-bottom: 1px solid #BCBCBC;
}

QHeaderView::section:vertical
{
    border-right: 1px solid #BCBCBC;
}
"""


#  https://stackoverflow.com/questions/34697559/pil-image-to-qpixmap-conversion-issue
def pil2pixmap(im):
    if im.mode == "RGB":
        r, g, b = im.split()
        im = Image.merge("RGB", (b, g, r))

    elif im.mode == "RGBA":
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (b, g, r, a))

    elif im.mode == "L":
        im = im.convert("RGBA")

    # Bild in RGBA konvertieren, falls nicht bereits passiert
    im2 = im.convert("RGBA")
    data = im2.tobytes("raw", "RGBA")
    qim = QtGui.QImage(data, im.size[0], im.size[1], QtGui.QImage.Format_ARGB32)
    pixmap = QtGui.QPixmap.fromImage(qim)
    return pixmap


def applyTransform(image, rotation=0, flipH=False, flipV=False):
    s = []
    if rotation > 0:
        image = image.rotate(rotation)
        s.append(f"rotation: {rotation}")
    if flipH:
        image = ImageOps.mirror(image)
        s.append("flipH")
    if flipV:
        image = ImageOps.flip(image)
        s.append("flipV")

    return image, "  ".join(s)


class cellEntry:
    def __init__(
        self,
        pos,
        imagePath,
        parent=None,
        width=None,
        height=None,
        rotation=None,
        flipH=None,
        flipV=None,
    ):
        self.parent = parent
        self.position = pos
        self.imagePath = os.path.basename(imagePath)
        self.rotation = rotation
        self.flipH = flipH
        self.flipV = flipV
        self.dependencies = []

        if parent is not None:
            parent.dependencies.append(pos)
        else:
            self.width = width
            self.height = height

    def getAll(self):
        if self.parent:
            return self.parent.getAll()
        else:
            return self, self.dependencies + [self.position]


class cellEntries:
    def __init__(self, tileSize, nRow, nCol):
        self.tileSize = tileSize
        self.nRow = nRow
        self.nCol = nCol
        self.usedImagePaths = set()
        self.entries = {}

    def hasCell(self, pos):
        return pos in self.entries

    def checkOverlaps(self, pos, w, h):
        if self.hasCell(pos):
            return True
        nCols, nRows = math.ceil(w / self.tileSize), math.ceil(h / self.tileSize)
        for j in range(nCols):
            for i in range(nRows):
                if self.hasCell((pos[0] + i, pos[1] + j)):
                    return True

        return False

    def getCell(self, pos):
        return self.entries.get(pos, None)

    def deleteCell(self, pos):
        parent, relatedEntries = None, []
        if self.hasCell(pos):
            parent, relatedEntries = self.entries[pos].getAll()
            for x in relatedEntries:
                if x in self.entries:
                    del self.entries[x]
                else:
                    print(
                        f"{x} not found in the cells despite all odds. Something could be wrong. To avoid shit like that make sure to only use images whose dimensions are a multiple of the tilesize"
                    )
            self.updateUsedImagePaths()

        return parent, relatedEntries

    def add(self, pos, imagePath, rotation=None, flipH=None, flipV=None):
        image = Image.open(imagePath)
        w, h = image.size

        if rotation == 90 or rotation == 270:
            w, h = h, w

        parent = cellEntry(
            pos,
            imagePath,
            width=w,
            height=h,
            rotation=rotation,
            flipH=flipH,
            flipV=flipV,
        )
        self.entries[pos] = parent

        nCols, nRows = math.ceil(w / self.tileSize), math.ceil(h / self.tileSize)
        for j in range(nCols):
            for i in range(nRows):
                if i == j == 0:
                    continue
                pos2 = (pos[0] + j, pos[1] + i)
                self.entries[pos2] = cellEntry(pos2, imagePath, parent=parent)
        self.updateUsedImagePaths()

        return parent

    def updateUsedImagePaths(self):
        used = set()
        for k, v in self.entries.items():
            used.add(v.imagePath)
        self.usedImagePaths = used

    def save(self, path):
        with open(path, "wb") as fil:
            pickle.dump(self, fil)

    def drawCell(self, pos, image):
        if not self.hasCell(pos):
            return

        cell = self.getCell(pos)
        if cell.parent:
            return

        img = cell.imagePath
        path = self.content.baseToPath.get(img, None)
        row, col = pos
        if path is None:
            draw = ImageDraw.Draw(image)
            x1, y1, x2, y2 = (
                row * self.tileSize,
                col * self.tileSize,
                (row + 1) * self.tileSize,
                (col + 1) * self.tileSize,
            )
            draw.rectangle((x1, y1, x2, y2), fill="red")
            print(
                f"No image found with basename {img}. Replaced visuals with red tile."
            )
        else:
            img = Image.open(self.content.baseToPath[img])
            img, _ = applyTransform(img, cell.rotation, cell.flipH, cell.flipV)
            image.paste(img, (row * self.tileSize, col * self.tileSize))


class tableOverlay(QtWidgets.QWidget, TableForm):
    def __init__(self, parent=None, content=None):
        super(tableOverlay, self).__init__(parent)

        self.setupUi(self)
        self.content = content

        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)

        self.setPalette(palette)
        self.setStyleSheet(tableStylesheet)

        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setFocusPolicy(Qt.NoFocus)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        # self.tableWidget.clicked.connect(self.content.onClick)

        self.tableWidget.mousePressEvent = self.onClick

        self.tableWidget.horizontalHeader().setSectionsClickable(False)
        self.tableWidget.verticalHeader().setSectionsClickable(False)

    def setDimensions(self, size, nRows, nCols):
        self.size = size
        self.tableWidget.horizontalHeader().setDefaultSectionSize(size)
        self.tableWidget.horizontalHeader().setMinimumSectionSize(size)
        self.tableWidget.horizontalHeader().setMaximumSectionSize(size)
        self.tableWidget.verticalHeader().setDefaultSectionSize(size)
        self.tableWidget.verticalHeader().setMinimumSectionSize(size)
        self.tableWidget.verticalHeader().setMaximumSectionSize(size)

        self.tableWidget.horizontalHeader().setDefaultSectionSize(QHeaderView.Fixed)
        self.tableWidget.verticalHeader().setDefaultSectionSize(QHeaderView.Fixed)

        self.setNRowCols(nRows, nCols)
        self.updateSize()

    def setNRowCols(self, nRows, nCols):
        self.nRows = nRows
        self.nCols = nCols
        self.tableWidget.setColumnCount(nCols)
        self.tableWidget.setRowCount(nRows)

    def updateSize(self):
        self.resize(self.nCols * self.size + 100, self.nRows * self.size + 100)

    def onClick(self, event):
        # https://stackoverflow.com/questions/50681354/how-to-add-a-right-click-action-not-menu-to-qtablewidgets-cells
        pos = event.pos()
        x, y = pos.x(), pos.y()
        row, col = x // self.size, y // self.size

        if event.button() == QtCore.Qt.LeftButton:
            self.content.addTile(row, col)

        elif event.button() == QtCore.Qt.RightButton:
            self.content.removeTile(row, col)


class Content(QtWidgets.QWidget, Ui_Form):
    scale = 1

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.table = tableOverlay(self.scrollAreaWidgetContents, self)

        self.treeWidget.selectionModel().selectionChanged.connect(
            self.treeSelectionChanged
        )

        self.treeWidget.itemDoubleClicked.connect(self.updateSelectionHighlight)

        self.scaleSlider.valueChanged.connect(self.scaleChanged)

    cellEntries = None

    def scaleChanged(self, scale):
        self.scale = scale
        self.applyScale()
        self.scaleSlider.setValue(scale)
        self.label_2.setText(f"Scale: {scale}")

    def applyScale(self):
        self.table.setDimensions(self.scale * 16, self.table.nRows, self.table.nCols)
        self.updateImage()

    def newImage(self, tileSize, nRows, nCols):
        self.tileSize = tileSize
        self.image = Image.new(
            "RGBA", (tileSize * nCols, tileSize * nRows), (0, 0, 0, 0)
        )
        self.image.baseX, self.image.baseY = self.image.size

        # self.image = Image.open("Bush_prop_0.png")
        self.updateImage()
        self.table.setDimensions(tileSize, nRows, nCols)
        if self.cellEntries is None:
            self.cellEntries = cellEntries(tileSize, nRows, nCols)
        self.draw = ImageDraw.Draw(self.image)

    def load(self, name):
        if name is None:
            sys.exit("???")

        name = name.replace(".p", "")
        name = name.replace(".png", "")

        self.imageSavePath = f"{name}.png"
        self.cellEntriesPath = f"{name}.p"
        self.loadCellEntries(self.cellEntriesPath)
        ce = self.cellEntries
        self.newImage(ce.tileSize, ce.nRow, ce.nCol)

        for k in self.cellEntries.entries:
            ce.drawCell(k, self.image)

        self.updateImage()

    def updateImage(self):
        im = self.image
        qim = ImageQt(im)
        # smaller_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.FastTransformation)
        x, y = self.image.size
        pixmap = QtGui.QPixmap.fromImage(qim).scaled(
            x * self.scale, x * self.scale, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.label.setPixmap(pixmap)

    def clearTreeWidget(self):
        tw = self.treeWidget
        tw.clear()

    items = []
    baseToPath = {}

    def loadDirectory(self, path, parent=None):
        self.items = []
        if parent is None:
            self.rootDir = path
            self.clearTreeWidget()
            parent = self.treeWidget
        for fil in glob.glob(os.path.join(path, "*")):
            if os.path.isdir(fil):
                item = QTreeWidgetItem(parent, [os.path.basename(fil)])
                item.oriPath = None
                self.loadDirectory(fil, item)
            elif fil.endswith(".png"):
                pFile = fil.replace(".png", ".p")
                pDarkFile = pFile.replace("_darkened.png", ".p")
                if os.path.exists(pFile) or os.path.exists(pDarkFile):
                    # if .p file exists, it should mean it's a tilesheet file
                    continue
                item = QTreeWidgetItem(parent, [os.path.basename(fil)])
                item.oriPath = fil
                item.setIcon(0, QtGui.QIcon(QtGui.QPixmap(fil)))
                self.items.append(fil)

                basename = os.path.basename(fil)
                if basename in self.baseToPath:
                    print(
                        f"Duplicate tile name found!:\n- {fil} \n- {self.baseToPath[basename]}"
                    )
                else:
                    self.baseToPath[basename] = fil

    selectedPath = None

    def treeSelectionChanged(self, *args):
        item = self.treeWidget.selectedItems()[0]
        self.selectItem(item.oriPath)

    def selectItem(self, path):
        self.selectedPath = path
        self.rotation = 0
        self.flipH = False
        self.flipV = False
        self.updatePreview()
        self.updateSelectionHighlight(reset=True)

    def updateSelectionHighlight(self, *args, reset=False):
        selected = self.selectedPath
        cells = self.cellEntries.entries

        tw = self.table.tableWidget

        if reset:
            for i in range(tw.rowCount()):
                for j in range(tw.columnCount()):
                    tableItem = tw.item(i, j)
                    if tableItem is not None:
                        tableItem.setBackground(QtGui.QColor(0, 0, 0, 0))
            return

        for pos, cell in cells.items():
            i, j = pos
            tableItem = tw.item(j, i)
            if tableItem is None:
                tableItem = QTableWidgetItem()
                tw.setItem(j, i, tableItem)

            if reset or (cell.imagePath != selected):
                tableItem.setBackground(QtGui.QColor(0, 0, 0, 0))
            else:
                tableItem.setBackground(QtGui.QColor(0, 0, 255, 200))

    def addTile(self, row, col):
        if self.selectedPath is None:
            return

        img = Image.open(self.selectedPath)
        w, h = img.size
        if self.cellEntries.checkOverlaps((row, col), w, h):
            return
        # print(f"Adding {self.selectedPath} to tile {row},{col}")

        # img, _ = applyTransform(img, self.rotation, self.flipH, self.flipV)
        # self.image.paste(img, (row * self.tileSize, col * self.tileSize))
        # self.updateImage()
        parent = self.cellEntries.add(
            (row, col),
            self.selectedPath,
            rotation=self.rotation,
            flipH=self.flipH,
            flipV=self.flipV,
        )

        self.cellEntries.drawCell((row, col), self.image)
        self.updateImage()

    def removeTile(self, row, col):
        if not self.cellEntries.hasCell((row, col)):
            return
        print(f"Removing tile {row},{col}")
        parent, relatedEntries = self.cellEntries.deleteCell((row, col))
        if parent is None:
            print(f"No parent found for tile {row},{col}. Somehow?")
        else:
            s = self.tileSize
            x, y = parent.position
            w, h = parent.width, parent.height
            self.draw.rectangle(
                (x * s, y * s, x * s + w - 1, y * s + h - 1), fill=(0, 0, 0, 0)
            )
            self.updateImage()

    rotation = 0
    flipH = False
    flipV = False

    previewSize = 64

    def updatePreview(self):
        label = ""
        if self.selectedPath is None:
            pix = QtGui.QPixmap()
        else:
            size = self.previewSize
            imPath = self.selectedPath
            im = Image.open(imPath)

            im, s = applyTransform(im, self.rotation, self.flipH, self.flipV)

            w, h = im.size
            label += f"{w}x{h}  "
            label += s
            if w > h:
                im = im.resize((size, int(size * h / w)), Image.NEAREST)
            else:
                im = im.resize((int(size * w / h), size), Image.NEAREST)

            pix = pil2pixmap(im)

        self.previewLabel.setPixmap(pix)
        self.previewText.setText(label)

    def save(self):
        del self.cellEntries.content
        self.cellEntries.save(self.cellEntriesPath)
        self.image.save(self.imageSavePath)

    def loadCellEntries(self, path):
        if os.path.exists(path):
            with open(path, "rb") as fil:
                self.cellEntries = pickle.load(fil)

                for _, entry in self.cellEntries.entries.items():
                    entry.imagePath = os.path.basename(entry.imagePath)
        else:
            self.cellEntries = cellEntries(16, 50, 50)

        self.cellEntries.content = self


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.content = Content()
        self.resize(1150, 950)
        self.setCentralWidget(self.content)

        self.rotateShortcut = QShortcut(QKeySequence("R"), self)
        self.rotateShortcut.activated.connect(self.changeRotation)

        self.flipVShortcut = QShortcut(QKeySequence("W"), self)
        self.flipVShortcut.activated.connect(self.changeFlipV)

        self.flipHShortcut = QShortcut(QKeySequence("E"), self)
        self.flipHShortcut.activated.connect(self.changeFlipH)

        self.nextUnusedShortcut = QShortcut(QKeySequence("tab"), self)
        self.nextUnusedShortcut.activated.connect(self.nextUnused)

        self.scale1Shortcut = QShortcut(QKeySequence("1"), self)
        self.scale1Shortcut.activated.connect(self.setScale1)

        self.scale2Shortcut = QShortcut(QKeySequence("2"), self)
        self.scale2Shortcut.activated.connect(self.setScale2)

        self.scale3Shortcut = QShortcut(QKeySequence("3"), self)
        self.scale3Shortcut.activated.connect(self.setScale3)

        self.scale4Shortcut = QShortcut(QKeySequence("4"), self)
        self.scale4Shortcut.activated.connect(self.setScale4)

        self.scale5Shortcut = QShortcut(QKeySequence("5"), self)
        self.scale5Shortcut.activated.connect(self.setScale5)

    def setScale1(self):
        self.content.scaleChanged(1)

    def setScale2(self):
        self.content.scaleChanged(2)

    def setScale3(self):
        self.content.scaleChanged(3)

    def setScale4(self):
        self.content.scaleChanged(4)

    def setScale5(self):
        self.content.scaleChanged(5)

    def changeRotation(self):
        self.content.rotation = (self.content.rotation + 90) % 360
        self.content.updatePreview()

    def changeFlipV(self):
        self.content.flipV = not self.content.flipV
        self.content.updatePreview()

    def changeFlipH(self):
        self.content.flipH = not self.content.flipH
        self.content.updatePreview()

    def nextUnused(self):
        used = self.content.cellEntries.usedImagePaths
        selected = self.content.selectedPath

        items = self.content.items
        try:
            selectedIndex = items.index(selected)
        except ValueError:
            selectedIndex = 0

        indexList = chain(
            range(selectedIndex + 1, len(items)), range(selectedIndex + 1)
        )
        # for x in self.content.items:
        for i in indexList:
            x = self.content.items[i]
            if x not in used:
                return self.content.selectItem(x)

        return self.content.selectItem(None)


def commandOpen(*args):
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    if len(args) < 3:
        print(
            f"Two arguments need to be given:\n1) a path to the directory from which to load images\n2) a path to (existing/new) save name (without extension!, will be placed inside directory argument"
        )
        sys.exit()
    saveName = args[2]
    window.content.loadDirectory(args[1])
    window.content.load(saveName)
    window.show()
    app.exec_()
    window.content.save()


def commandDarken(*args):
    if len(args) < 6:
        print(
            f"5 arguments need to be given:\n1) a path to sheet to darken\n2-5) RGBA values (0-1) of the filter"
        )
        sys.exit()

    path = args[1]
    r, g, b, a = [float(x) for x in args[2:6]]
    rgb = np.array([r, g, b])

    image = Image.open(path)
    if image.mode == "RGB":
        image.putalpha(255)
    pixels = np.array(image) / 255

    ## looping through it manually instead of using numpy properly
    ## because performance shouldnt matter and I wanna exclude 0-alpha pixels
    ## without having to use np.where and shit like that

    for i in range(pixels.shape[0]):
        for j in range(pixels.shape[1]):
            p = pixels[i, j]

            aij = p[3]
            at = aij + a

            if aij == 0:
                continue

            p[:3] = rgb * a + p[:3] * (1 - a)
            p[3] = a + aij - a * aij

    im = Image.fromarray(np.uint8(pixels * 255))
    darkPath = path.replace(".png", "_darkened.png")
    im.save(darkPath)


def main():

    if len(sys.argv) < 2:
        print("You need to supply a main command (e.g. open/filter")
        sys.exit()

    command = sys.argv[1]
    if command == "open":
        commandOpen(*sys.argv[1:])

    elif command == "darken":
        commandDarken(*sys.argv[1:])

    else:
        print(f"Command {command} not recognised")


if __name__ == "__main__":

    main()

# 1 - p = (1 - p1) * (1-p2)
# p = 1 - (1 - p1) * (1-p2)
# p = 1 - 1 + p2 + p1 - p1*p2
# ==> p = p2 + p1 - p1*p2
