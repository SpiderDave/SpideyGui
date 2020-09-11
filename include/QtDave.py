import math
from random import randrange
import numpy as np

from PIL.ImageQt import ImageQt

from PyQt5 import QtGui
from PyQt5.QtGui import QIcon, QPainter, QColor, QImage, QBrush, QPixmap, QPen
from PyQt5.QtCore import QDateTime, Qt, QTimer, QCoreApplication, QSize, QRect
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QAction, QMainWindow, QMessageBox, QFileDialog, 
        QInputDialog, QErrorMessage, QFrame
        )

nesPalette=[
[0x74,0x74,0x74],[0x24,0x18,0x8c],[0x00,0x00,0xa8],[0x44,0x00,0x9c],
[0x8c,0x00,0x74],[0xa8,0x00,0x10],[0xa4,0x00,0x00],[0x7c,0x08,0x00],
[0x40,0x2c,0x00],[0x00,0x44,0x00],[0x00,0x50,0x00],[0x00,0x3c,0x14],
[0x18,0x3c,0x5c],[0x00,0x00,0x00],[0x00,0x00,0x00],[0x00,0x00,0x00],
[0xbc,0xbc,0xbc],[0x00,0x70,0xec],[0x20,0x38,0xec],[0x80,0x00,0xf0],
[0xbc,0x00,0xbc],[0xe4,0x00,0x58],[0xd8,0x28,0x00],[0xc8,0x4c,0x0c],
[0x88,0x70,0x00],[0x00,0x94,0x00],[0x00,0xa8,0x00],[0x00,0x90,0x38],
[0x00,0x80,0x88],[0x00,0x00,0x00],[0x00,0x00,0x00],[0x00,0x00,0x00],
[0xfc,0xfc,0xfc],[0x3c,0xbc,0xfc],[0x5c,0x94,0xfc],[0xcc,0x88,0xfc],
[0xf4,0x78,0xfc],[0xfc,0x74,0xb4],[0xfc,0x74,0x60],[0xfc,0x98,0x38],
[0xf0,0xbc,0x3c],[0x80,0xd0,0x10],[0x4c,0xdc,0x48],[0x58,0xf8,0x98],
[0x00,0xe8,0xd8],[0x78,0x78,0x78],[0x00,0x00,0x00],[0x00,0x00,0x00],
[0xfc,0xfc,0xfc],[0xa8,0xe4,0xfc],[0xc4,0xd4,0xfc],[0xd4,0xc8,0xfc],
[0xfc,0xc4,0xfc],[0xfc,0xc4,0xd8],[0xfc,0xbc,0xb0],[0xfc,0xd8,0xa8],
[0xfc,0xe4,0xa0],[0xe0,0xfc,0xa0],[0xa8,0xf0,0xbc],[0xb0,0xfc,0xcc],
[0x9c,0xfc,0xf0],[0xc4,0xc4,0xc4],[0x00,0x00,0x00],[0x00,0x00,0x00],
]

# black, green, red, blue
basePalette = [
    [0,0,0],
    [0,255,0],
    [255,0,0],
    [0,0,255],
    ]

basePens = [QColor(*basePalette[x]) for x in range(4)]


# This is something to reformat lua tables from lupa into 
# lists if needed.  I'd like to avoid importing lupa here
# to keep things reasonably seperate.
def fix(item):
    if item.__class__.__name__ == '_LuaTable':
        return [item[x] for x in list(item)]
    else:
        return item

clamp = lambda value, minv, maxv: max(min(value, maxv), minv)

clip = {}


class App(QApplication):
    def __init__(self, args=[], **kw):
        super().__init__(args, **kw)
    def mainloop(self):
        super().exec_()
    def quit(self):
        QCoreApplication.quit()

class Base():
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.control = self # backwards compatability
        self.anonymous = False
        self.data = dict()
    def init(self, t):
        self.name = t.name
        self.tooltip=t.tooltip
        self.move(t.x,t.y)
        self.resize(t.w, t.h)
        self.text = t.text
        self.scale = t.scale or 1
    def move(self, x,y):
        if not x:
            x = 0
        if not y:
            y = 0
        super().move(int(x),int(y))
    def setGeometry(self, x,y,w,h):
        self.move(x,y)
        self.resize(w,h)
    def resize(self, w,h):
        if not w:
            w = self.sizeHint().width()*1.5
        if not h:
            h = self.sizeHint().height()*1.2
        super().resize(int(w),int(h))
    def setFont(self, fontName, size):
        super().setFont(QtGui.QFont(fontName, size))
        self.adjustSize()
    def setCssClass(self, value):
        super().setProperty('class', value.strip())
    def getCssClass(self):
        return super().property('class')
    def addCssClass(self, value):
        value = value.strip()
        #super().setProperty('CssClass', value)
        classes = super().property('class') or ''
        
        if value.lower() in classes.lower().split():
            pass
        else:
            super().setProperty('class', classes+" "+value)
    def removeCssClass(self, value):
        value = value.strip()
        classes = super().property('class') or ''
        
        if value.lower() in classes.lower().split():
            classes = ' '.join([x for x in classes.split() if x.lower()!=value.lower()])
            super().setProperty('class', classes)
    def __getattribute__(self, key):
        if key == 'tooltip':
            return self.toolTip()
        if key == 'width':
            return super().width()
        if key == 'height':
            return super().height()
        return super().__getattribute__(key)
    def __setattr__(self, key, v):
        if key == 'tooltip':
            self.setToolTip(v)
        if key == 'width':
            self.resize(v, super().height())
        if key == 'height':
            self.resize(super().width(), v)
        super().__setattr__(key,v)
    def screenshot(self):
        try:
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow( self.winId() )
            screenshot.save('shot.jpg', 'jpg')
        except: pass

class Button(Base, QPushButton):
    def setIcon(self, f):
        try:
            super().setIcon(QIcon(f))
            self.setIconSize(QSize(64, 64))
            super().setProperty('hasIcon', True)
        except:
            pass


class Label(Base, QLabel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.autoSize = True
    def setText(self, txt, autoSize = False):
        super().setText(txt)
        if autoSize or self.autoSize:
            self.adjustSize()
    def __getattribute__(self, key):
        if key == 'text':
            return self.getText()
        return super().__getattribute__(key)
    def __setattr__(self, key, v):
        if key == 'text':
            self.setText(v, autoSize=self.autoSize)
        else:
            super().__setattr__(key,v)

class Link(Label):
    def init(self, t):
        super().init(t)
        # There's no reason for a font tag in 2020, except it just doesn't
        # let me style this properly with the qss or even setStyleSheet.
        self.setText('<a href="{0}"><font color="white">{1}</font></a>'.format(t.url,t.text))
        self.addCssClass("link")
        self.setOpenExternalLinks(True)
        self.linkHovered.connect(self._linkHovered)
        self.linkActivated.connect(self._linkClicked)
        #self.setStyleSheet("color: blue;border:1px solid blue;")
    def _linkHovered(self):
        #print('hover')
        #self.text = self.text.replace("white","blue")
        #self.setStyleSheet("color: blue;border:1px solid red;")
        pass
    def _linkClicked(self):
        #print('click')
        pass

class CheckBox(Base, QCheckBox): pass

class LauncherIcon(Base, QFrame):
    def init(self, t):
        super().init(t)
        
        self.addCssClass("launcherFrame")
        
        l = Label(self)
        l.addCssClass("launcherText")
        l.init(t)
        l.move(0,self.height-l.height-8)
        
        self.label = l
        
        ctrl = Label("", self)
        t.text = ""
        ctrl.init(t)
        ctrl.resize(self.width, self.height-l.height-8)
        ctrl.move(0,0)
        ctrl.addCssClass("launcherIcon")
        self.iconCtrl = ctrl
        
        # This is very hacky but it fixes an issue where 
        # the labels are initially cut off.
        QTimer.singleShot(400, self.label.adjustSize)
    def setText(self, text):
        self.label.text = text

class TabWidget(Base, QTabWidget):
    def init(self, t):
        super().init(t)
        self.width = 1000
        self.height = 1000

class Widget(Base, QWidget): pass
QWidget = QWidget

class MainWindow(Base, QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.tabParent = False
        self.name = "MainQt"
        self.tabs = dict()
        self.menus = dict()
        self.loaded = False
        self.onClose = False
        
        #exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        #exitAct.setShortcut('Ctrl+Q')
        #exitAct.setStatusTip('Exit application')
        #exitAct.triggered.connect(app.quit)
        #exitAct.triggered.connect(lambda x:print("hi"))
        
        #menubar = self.menuBar()
        #fileMenu = menubar.addMenu('&File')
        
        #fileMenu.addAction(QAction('Menu Item', self))
        
        #fileMenu.addAction(exitAct)
        QTimer.singleShot(1,self.onDisplay)
    def onDisplay(self):
        self.loaded = True
        print('display')
    def addMenu(self, menuName, menuText, menuItems):
        if not self.menus.get(menuName, False):
            self.menus.update({menuName:self.menuBar().addMenu(menuText)})
        
        m = self.menus.get(menuName)
        
        for i, item in enumerate(menuItems):
            name = item.get('name', str(i))
            txt = item.get('text', "?")
            
            # check if text is any number of -
            if txt.startswith('-') and txt == txt[0]*len(txt):
                m.addSeparator()
            else:
                action = QAction(item.get('text'), self)
                if item.get('action', False):
                    action.triggered.connect(item.get('action'))
                m.addAction(action)
        return m
    def setIcon(self, filename):
        self.setWindowIcon(QtGui.QIcon(filename))
        
    def initUI(self):
        self.setGeometry(300, 300, 300, 220)
        #self.setWindowTitle("Window title")
    def closeEvent(self, event):
        print("User has clicked the red x on the main window")
        if self.onClose:
            if self.onClose():
                event.accept()
            else:
                event.ignore()
            return
        event.accept()




class Dialog():
    def askYesNo(self, title="", message=""):
        m = QMessageBox()
        reply = m.question(m, title, message, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            return True
        else:
            return False
    def askYesNoCancel(self, title="", message=""):
        m = QMessageBox()
        reply = m.question(m, title, message, QMessageBox.Yes | QMessageBox.No |QMessageBox.Cancel , QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            return True
        elif reply == QMessageBox.No:
            return False
        else:
            return
    def openFolder(self, title="Select Folder", initial=None):
        d = QFileDialog()
        return str(d.getExistingDirectory(None, title, initial)) 
    def openFile(self, filetypes=None, initial=None, title="Select File", filter="All Files (*.*)"):
        d = QFileDialog()
        
        types = list()
        if filetypes:
            for t in filetypes:
                types.append([filetypes[t][1],filetypes[t][2]])
            types.append(["All files","*.*"])
        
            filter = ";;".join([x+" ("+y+")" for x,y in types])
            filter=filter.replace("(.","(*.")
        
        #print(filter)
        
        #"Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)"
        file, _ = d.getOpenFileName(None, title, initial, filter)
        return file
    def saveFile(self, filetypes=None, initial=None, title="Save As...", filter="All Files (*.*)"):
        d = QFileDialog()
        
        types = list()
        if filetypes:
            for t in filetypes:
                types.append([filetypes[t][1],filetypes[t][2]])
            types.append(["All files","*.*"])
        
            filter = ";;".join([x+" ("+y+")" for x,y in types])
            filter=filter.replace("(.","(*.")
        
        file, _ = d.getSaveFileName(None, title, initial, filter)
        return file
    def askText(self, title="Enter Text", label=None):
        # trims whitespace and returns false on the empty string.
        
        d = QInputDialog(None, Qt.WindowCloseButtonHint)
        
        text, okPressed = d.getText(None, title, label, QLineEdit.Normal, "")
        if okPressed and text != '':
            return text.strip()
        else:
            return False
    def showError(self, text=None):
        d = QMessageBox()
        d.setText(text)
        
        d.setIcon(3)
        #d.setInformativeText("Some message")
        d.setStyleSheet(".QLabel {padding:1em;}")
        d.setWindowTitle("Error")
        d.exec_()
        
        
class Painter(QPainter):
    def test(self):
        self.setPen(QColor(168, 34, 3))
    def test2(self):
        for i in range(20000):
            self.setPen(QColor(randrange(0,255), randrange(0,255), randrange(0,255)))
            self.drawLine(randrange(0,255), randrange(0,255), randrange(0,255), randrange(0,255))
    def test3(self):
        for x in range(256):
            for y in range(256):
                self.setPen(QColor(randrange(0,255), randrange(0,255), randrange(0,255)))
                self.drawPoint(x, y)

QPixmap = QPixmap


class ClipOperations():
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
    def copy(self):
        """
        Copy pixmap to a "clipboard" type thing to later be
        pasted.  Also returns the pixmap to use directly.
        """
        return clip.update(pix=self.pixmap())
    def paste(self, pix=False):
        """
        Sets a pixmap with automatic resizing.  The pixmap
        can be supplied via parameter or use the one stored
        from a "copy" operation above.
        """
        if not pix:
            pix = clip.get('pix')
        self.setPixmap(pix.scaled(self.size()))



class Canvas(ClipOperations, Base, QLabel):
    def init(self, t):
        self.mask = False
        super().init(t)
        canvas=QPixmap(self.width,self.height)
        self.setPixmap(canvas)
        painter = Painter(self.pixmap())
        painter.setPen(QColor(0, 0, 0))
        painter.brushColor = QColor(Qt.black)
        painter.fillRect(0,0,self.width,self.height,QBrush(Qt.black))
        painter.end()

        columns = (self.width/self.scale)/8
        rows = (self.height/self.scale)/8
    def paintTest(self):
        painter = Painter(self.pixmap())
        painter.test3()
        painter.end()
    def drawLine(self, x,y,x2,y2):
        # needs work
        painter = Painter(self.pixmap())
        painter.scale(self.scale, self.scale)
        pen = QPen()
        pen.width=0
        pen.color='white'
        #painter.setPen(QColor('white'))
        painter.setPen(pen)
        painter.drawLine(x,y,x2,y2)
        painter.end()
    def setPixel(self, x,y):
        painter = Painter(self.pixmap())
        painter.scale(self.scale, self.scale)
        #painter.setPen(QColor(168, 34, 3))
        painter.fillRect(x,y,1,1,QBrush(Qt.white))
        painter.end()
    def test(self, chr):
        pix = NESPixmap(8*16,8*16)
        pix.loadCHR(chr)
        p=Painter(self.pixmap())
        #p.drawPixmap(pix.rect(), pix)
        p.drawPixmap(QRect(0,0,self.width,self.height), pix)
        p.end()
        self.repaint()
    def changeColor(self):
        pix = self.pixmap()
        if not self.mask:
            self.mask = pix.createMaskFromColor(QColor(0, 0, 0), Qt.MaskOutColor)
        
        mask = self.mask
        
        p = Painter(pix)
        p.setPen(QColor(randrange(0,255),randrange(0,255),randrange(0,255)))
        p.drawPixmap(pix.rect(), mask, mask.rect())
        p.end()
        self.repaint()
    def drawTile(self, x,y, tile, imageData, colors=None, columns=16, rows=16):
        painter = Painter(self.pixmap())
        
        if not colors:
            colors=[0x0f,0x21,0x11,0x01]
        else:
            colors = fix(colors)
        
        imageData = fix(imageData)
        
        originX=x*self.scale
        originY=y*self.scale
        
        a = np.zeros((8,8,3))
        
        for y in range(8):
            for x in range(8):
                c=0
                x1=(tile % columns)*8+(7-x)
                y1=math.floor(tile/columns)*8+y
                if (imageData[tile*16+y] & (1<<x)):
                    c=c+1
                if (imageData[tile*16+y+8] & (1<<x)):
                    c=c+2
                a[y][(7-x)] = nesPalette[colors[c]]
                brushColor = QColor(nesPalette[colors[c]][0], nesPalette[colors[c]][1], nesPalette[colors[c]][2])
                painter.fillRect(originX+(7-x)*self.scale,originY+y*self.scale,self.scale,self.scale,QBrush(brushColor))
        painter.end()
        #self.update()


class PaletteButton(Label):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.autoSize = False
    def init(self, t, width=30, height=30):
        super().init(t)
        self.addCssClass('paletteCell')
        self.resize(width, height)
        
# todo: always use indexed palettes
class PaletteControl(Base, QFrame):
    upperHex = False
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__class__.cls = self.__class__
    
    def init(self, t):
        super().init(t)
        
        if t.upperHex in (True, False):
            self.upperHex = self.cls.upperHex = t.upperHex
        else:
            self.upperHex = t.upperHex = self.cls.upperHex
        
        self.addCssClass('paletteControl')
        pw=len(t.palette) %0x10+1
        ph=math.floor(len(t.palette) /0x10)+1
        self.width = pw * 26+2
        self.height = ph * 26+2
        self.cells = []
        for y in range(0,ph):
            for x in range(0,pw):
                ctrl = PaletteButton("00", self)
                ctrl.init(t, width=26, height=26)
                ctrl.name = "{0}_Cell{1:02x}".format(t.name,y*pw+x)
                ctrl.cellNum = y*pw+x
                ctrl.move(1+x*ctrl.width,1+y*ctrl.height)
                
                i=y*0x10+x
                if self.cls.upperHex:
                    ctrl.setText("{0:02X}".format(i), autoSize=False)
                else:
                    ctrl.setText("{0:02x}".format(i), autoSize=False)
                bg = "#{0:02x}{1:02x}{2:02x}".format(t.palette[i][1],t.palette[i][2],t.palette[i][3])
                fg = 'white' if x>=(0x00,0x01,0x0d,0x0e)[y] else 'black'
                ctrl.setStyleSheet("""
                background-color :{0};
                color :{1};
                """.format(bg, fg))
                
                self.cells.append(ctrl)
    def setAll(self, colors):
        colors = [x for _,x in colors.items()]
        for i, c in enumerate(colors):
            self.set(index=i, c=c)
    
    def set(self, index=0, c=0x0f):
        cell = self.cells[index]
        
        bg = "#{0:02x}{1:02x}{2:02x}".format(nesPalette[c][0],nesPalette[c][1],nesPalette[c][2])
        x,y = c%0x10, c>>4
        fg = 'white' if x>=(0x00,0x01,0x0d,0x0e)[y] else 'black'
        cell.setStyleSheet("""
        background-color :{0};
        color :{1};
        """.format(bg, fg))
        #cell.setText("{0:02x}".format(c), autoSize=False)
        if self.cls.upperHex:
            cell.setText("{0:02X}".format(c), autoSize=False)
        else:
            cell.setText("{0:02x}".format(c), autoSize=False)

        
class SideSpin(Base, QFrame):
    def init(self, t):
        super().init(t)
        self._value = 0
        self.min = 0
        self.max = 255
        self.onChange = False
        #self.leftButton = l = Button(u"\u25C0", self)
        self.leftButton = l = Button("-", self)
        l.init(t)
        l.move(0,0)
        l.resize(self.height, self.height)
        l.clicked.connect(self._onLeft)
        self.label = m = Label(self)
        self.label.autoSize = False
        m.init(t)
        m.text="00"
        m.setFont("Verdana",12)
        m.move(l.width,0)
        m.resize(self.width/3, self.height)
        m.addCssClass("sideSpinLabel")
        #self.rightButton = r = Button(u"\u25B6", self)
        self.rightButton = r = Button("+", self)
        r.init(t)
        r.resize(self.height, self.height)
        r.move(self.width-r.width,0)
        r.clicked.connect(self._onRight)
        self.addCssClass('sideSpin')
        QTimer.singleShot(400, self.refresh)
    def _onLeft(self):
        self._value = v = self._value - 1
        self.refresh()
        if self.onChange and (self._value ==v):
            self.onChange()
    def _onRight(self):
        self._value = v = self._value + 1
        self.refresh()
        if self.onChange and (self._value ==v):
            self.onChange()
    def refresh(self):
        self._value = clamp(self._value, self.min, self.max)
        self.label.text = "{0:02x}".format(self._value)
    
    def _changed(self):
        if self.onChange:
            self.onChange()
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        if self._value != v:
            self._value = v
            self.refresh()
            # no idea why this crashes if i dont use a timer here
            QTimer.singleShot(1, self._changed)

class NESPixmap(ClipOperations, Base, QPixmap):
    """
    An off-screen image representation and drawing surface with
    NES-specific things.
    """
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        
        # This is just to give it a pixmap function so it works with 
        # ClipOperations
        self.pixmap = lambda:self

    def loadCHR(self, imageData, columns=16, rows=16):
        """Loads CHR data using 4 preset base colors."""
        painter = Painter(self)
        
        if not imageData:
            imageData = [0] * (16*columns*rows)
        
        imageData = fix(imageData)
        
        #a = np.zeros((8,8,3))
        for tile in range(math.floor(len(imageData)/16)):
            for y in range(8):
                for x in range(8):
                    tileX=(tile % columns)
                    tileY=math.floor(tile/columns)
                    c=0
                    x1=tileX * 8 + (7-x)
                    y1=tileY * 8 + y
                    if (imageData[tile*16+y] & (1<<x)):
                        c=c+1
                    if (imageData[tile*16+y+8] & (1<<x)):
                        c=c+2
                    #a[y][(7-x)] = basePalette[c]
                    painter.setPen(basePens[c])
                    painter.drawPoint(tileX*8+(7-x),tileY*8+y)
        painter.end()
#        palette = [
#            nesPalette[0x0f],
#            nesPalette[0x21],
#            nesPalette[0x11],
#            nesPalette[0x01],
#        ]
#        self.applyPalette(palette=palette)

    def applyPalette(self, palette=False):
        painter = Painter(self)

        # black, green, red, blue
        colors = [
            [0,0,0],
            [0,255,0],
            [255,0,0],
            [0,0,255],
            ]
        
        palette = fix(palette)
        palette = [nesPalette[x] for x in palette]
#        palette = [
#            nesPalette[0x0f],
#            nesPalette[0x21],
#            nesPalette[0x11],
#            nesPalette[0x01],
#        ]
        
        pens = [QColor(*palette[x]) for x in range(4)]
        
#        rndPens = [
#            [QColor(*nesPalette[randrange(0x40)]) for x in range(4)],
#            [QColor(*nesPalette[randrange(0x40)]) for x in range(4)],
#            [QColor(*nesPalette[randrange(0x40)]) for x in range(4)],
#            [QColor(*nesPalette[randrange(0x40)]) for x in range(4)],
#        ]
        
        masks = []
        for i, c in enumerate(colors):
            masks.append(self.createMaskFromColor(QColor(*colors[i]), Qt.MaskOutColor))
        
        for x in range(8):
            for y in range(8):
        
                for i, mask in enumerate(masks):
                    #painter.setPen(QColor(*palette[i]))
                    painter.setPen(pens[i])
                    #painter.setPen(QColor(randrange(0,255), randrange(0,255), randrange(0,255)))
                    #painter.setPen(rndPens[randrange(4)][i])
                    #p.drawPixmap(self.rect(), mask, mask.rect())
                    #p.drawPixmap(QRect(0,0,self.width*2,self.height*2), mask, mask.rect())
                    
                    r = QRect(x*16,y*16,16,16)
                    painter.drawPixmap(r, mask, r)
        painter.end()
