# needs lupa, pyinstaller, pillow, pyqt5, numpy
'''
ToDo:
    * move to pyQt5!
    * make return value of control generating methods more consistant
    * makeCanvas method
    * clean up color variable names, add more
    * phase out controls and use controlsNew, then rename controlsNew
    * per-project plugins
'''

import os, sys, time

def badImport(m):
    print('Error: Could not import {0}.  Please run "install dependencies.bat".'.format(m))
    sys.exit(1)



try: import lupa
except: badImport('lupa')
from lupa import LuaRuntime
from lupa import LuaError
lua = LuaRuntime(unpack_returned_tuples=True)
try: import PyQt5.QtWidgets
except: badImport('PyQt5')
try: from PIL import ImageTk, Image, ImageDraw
except: badImport('pillow')
from PIL import ImageOps
from PIL import ImageGrab
from collections import deque
import re

from random import randrange

from io import BytesIO

import textwrap

try: import numpy as np
except: badImport('numpy')

from shutil import copyfile
import subprocess
import traceback

from tempfile import NamedTemporaryFile
#from textwrap import dedent

import math
import webbrowser

from binascii import hexlify, unhexlify

import importlib, pkgutil
from zipfile import ZipFile

# import our include folder
import include 

# This helps make things work in the frozen version
# All that python imports here is an empty init file.
try:    import icons
except: pass
try:    import cursors
except: pass

# import with convenient names
from include import *

app = QtDave.App()
main = QtDave.MainWindow()

import configparser, atexit

# Handle exporting some stuff from python scripts to lua
include.init(lua)

true, false = True, False

script_path = os.path.dirname(os.path.abspath( __file__ ))
initialFolder = os.getcwd()

frozen = (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'))

application_path = False
if frozen:
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

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

def pathToFolder(p):
    return fixPath2(os.path.split(p)[0])

def fixPath2(p):
    if ":" not in p:
        p = script_path+"/"+p
    return p.replace("/",os.sep).replace('\\',os.sep)
    
def fixPath(p):
    return p.replace("/",os.sep).replace('\\',os.sep)


# create our config parser
cfg = Cfg(filename=fixPath2("config.ini"))

# read config file if it exists
cfg.load()

cfg.setDefault('main', 'stylemenus', 1)
cfg.setDefault('main', 'project', "newProject")
cfg.setDefault('main', 'upperhex', 0)
cfg.setDefault('main', 'alphawarning', 1)
cfg.setDefault('main', 'loadplugins', 1)
cfg.setDefault('main', 'breakonpythonerrors', 0)
cfg.setDefault('main', 'breakonluaerrors', 0)
cfg.setDefault('main', 'autosave', 1)
cfg.setDefault('main', 'autosaveinterval', 1000 * 60 * 5) # 5 minutes

# make cfg available to lua
lua_func = lua.eval('function(o) {0} = o return o end'.format('cfg'))
lua_func(cfg)

controls={}
controlsNew={}

controlsNew.update({"main":main})

# have to manually define hotspots
cursorData = dict(
    pencil=dict(hotspot=[0,31]),
)
for k,v in cursorData.items():
    if v:
        cursorName = "cursors\\"+k
        folder, file = os.path.split(cursorName)
        d = os.path.dirname(sys.modules[folder].__file__)
        cursorData[k].update(filename = os.path.join(d, file))

QtDave.loadCursors(cursorData)

# set up our lua function
#lua_func = lua.eval('function(o) {0} = o return o end'.format('tkConstants'))
# get all the constants from tk.constants but leave out builtins, etc.
#d= dict(enumerate([x for x in dir(tk.constants) if not x.startswith('_')]))
# flip keys and values
#d = {v:k for k,v in d.items()}
# export to lua.  the values will still be python
#lua_func(lua.table_from(d))

def fancy(text):
    return "*"*60+"\n"+text+"\n"+"*"*60


class Stack(deque):
    def push(self, *args):
        for arg in args:
            self.append(arg)
    def pop(self, n=0):
        if n > 0:
            ret = []
            for i in range(n):
                ret.append(super().pop())
            return tuple(ret)
        else:
            return super().pop()
    def remove(self,value):
        try:
            super().remove(value)
            return True
        except:
            return False
    def asList(self):
        return list(self)

# Make stuff in this class available to lua
# so we can do Python stuff rom lua.
class ForLua:
    x=0
    y=0
    w=16
    h=16
    direction="v"
    window="Main"
    canvas=False
    images={}
    images2=[]
    config = cfg
    anonCounter = 1
    loading = 0
    windowQt = main
    tabQt = main
    Qt = True
    
    def QtWrapper(func):
        def inner(self, t=None):
            return t
        return inner
    # decorator
    def makeControl(func):
        def addStandardProp(t):
            def _config(cfg):
                t.control.config(dict(cfg))
            def update():
                t.control.update()
                t.height = t.control.winfo_height()
                t.width = t.control.winfo_width()
            t.config = _config
            t.update = update
            t.plugin = lua.eval("_getPlugin and _getPlugin() or false")
            return t
        def inner(self, t=None):
            # This is some patchwork stuff for methods
            # that lack the self argument
            if self!=ForLua:
                t=self
                self=ForLua
                #print("Warning: created {0} without : syntax.".format(t.name))
            
            # This is used in makeWindow to avoid
            # creating the same window over and over.
            if t.alreadyCreated: return t
            
            if self.direction.lower() in ("v","vertical"):
                x=coalesce(t.x, self.x, 0)
                y=coalesce(t.y, self.y+self.h, 0)
            else:
                x=coalesce(t.x, self.x+self.w, 0)
                y=coalesce(t.y, self.y, 0)
            w=coalesce(t.w, self.w, 16)
            h=coalesce(t.h, self.h, 16)
            self.x=x
            self.y=y
            self.w=w
            self.h=h
            
            index = t.index
            
            anonymous = False
            if not t.name:
                anonymous = True
            
            t = func(self, t, (x,y,w,h))
            t = addStandardProp(t)
            if t.control:
                t.control.update()
                t.height=t.control.winfo_height()
                t.width=t.control.winfo_width()
            
            t.index = index
            
            if not t.name:
                t.name = "anonymous{0}".format(ForLua.anonCounter)
                ForLua.anonCounter = ForLua.anonCounter + 1
                t.anonymous=True

            return t
        return inner
    def decorate(self):
        decorator = lupa.unpacks_lua_table_method
        for method_name in dir(self):
            m = getattr(self, method_name)
            if m.__class__.__name__ == 'function':
                # these are control creation functions
                # makedir maketab
                makers = ['makeButton', 'makeCanvas', 'makeEntry', 'makeLabel', "makeTree",
                          'makeMenu', 'makePaletteControl', 'makePopupMenu',
                          'makeText', 'makeWindow', 'makeSpinBox',
                          ]
                QtWidgets = ['makeButtonQt', 'makeLabelQt', 'makeTabQt', 'makeCanvasQt', 'makeSideSpin', 'makeCheckbox', 'makeLink', 'makeTextEdit', 'makeList']
                
                if method_name in makers:
                    attr = getattr(self, method_name)
                    wrapped = self.makeControl(attr)
                    setattr(self, method_name, wrapped)
                elif method_name in QtWidgets:
                    attr = getattr(self, method_name)
                    wrapped = self.QtWrapper(attr)
                    setattr(self, method_name, wrapped)
                elif method_name in ['getNESColors', 'makeControl', 'getLen', 'makeMenuQt','makeNESPixmap','listToTable','tableToList']:
                    # getNESColors: excluded because it may have a table as its first parameter
                    # makeControl: excluded because it's a decorator
                    pass
                else:
                    #print(method_name, m.__class__)
                    if method_name.startswith('make') and method_name not in ['makeDir', 'makeTab', 'makeIps']:
                        print("possible function to exclude from decorator: ", method_name, m.__class__)
                    attr = getattr(self, method_name)
                    wrapped = decorator(attr)
                    setattr(self, method_name, wrapped)
    
    # can't figure out item access from lua with cfg,
    # so we'll define some methods here too.
    def cfgLoad(self, filename = "config.ini"):
        return cfg.load(filename)
    def cfgSoad(self):
        return cfg.save()
    def cfgMakeSections(self, *sections):
        return cfg.makeSections(*sections)
    def cfgGetValue(self, section, key, default=None):
        return cfg.getValue(section, key, default)
    def cfgSetValue(self, section, key, value):
        return cfg.setValue(section, key, value)
    def cfgSetDefault(self, section,key,value):
        return cfg.setDefault(section,key,value)
    def repr(self, item):
        return repr(item)
    def type(self, item):
        return item.__class__.__name__
    def calc(self, s):
        calc = Calculator()
        return calc(s)
    def getPrintable(self, item):
        if type(item) is str: return item
        if repr(item).startswith("<"):
            return repr(item)
        else:
            return str(item)
    def printNoPrefix(self, item):
        if repr(item).startswith("<"):
            print(repr(item))
        else:
            print(item)
    def print(self, prefix, item):
        print(prefix, end="")
        if repr(item).startswith("<"):
            print(repr(item))
        else:
            print(item)
    def fileExists(self, f):
        f = fixPath(script_path+"/"+f)
        return os.path.isfile(f)
    def pathToFolder(self, path):
        return pathToFolder(path)
    def pathExists(self, f):
        f = fixPath(script_path+"/"+f)
        return os.path.exists(f)
    def setWorkingFolder(self, f=""):
        workingFolder = fixPath2(f)
        os.chdir(workingFolder)
    def getWorkingFolder(self):
        return os.getcwd()
    def extractAll(self, file, folder):
        file = fixPath2(file)
        #if self.fileExists(self, file):
        if True:
            folder = fixPath2(folder)
            print(file, folder)
            with ZipFile(file, mode='r') as zip:
                zip.extractall(folder)
            return True
        else:
            print("File does not exist: {}".format(file))
            return False
    def sleep(self, t):
        time.sleep(t)
    def delete(self, filename):
        filename = fixPath(script_path+"/"+filename)
        try:
            if os.path.exists(filename):
                os.remove(filename)
            return True
        except:
            print("Could not delete "+filename)
            return False
    def run(self, workingFolder, cmd, args):
        try:
            cmd = fixPath(script_path+"/"+cmd)
            workingFolder = fixPath(script_path+"/"+workingFolder)
            os.chdir(workingFolder)
            subprocess.run([cmd]+ args.split())
            print()
            return True
        except:
            print("could not run " + cmd)
            return False
    def shellOpen(self, workingFolder, cmd):
        cmd = fixPath2(cmd)
        workingFolder = pathToFolder(workingFolder)
        try:
            os.chdir(workingFolder)
            os.startfile(cmd, 'open')
            return True
        except:
            print("could not open " + cmd)
            return False
    def numberToBitArray(self, n):
        return [int(x) for x in "{:08b}".format(n)]
    def bitArrayToNumber(self, l):
        return int("".join(str(x) for x in l), 2) 
    def showError(self, title="Error", text=""):
        d = QtDave.Dialog()
        d.showError(text)
    def askText(self, title, text):
        d = QtDave.Dialog()
        return d.askText(title, text)
    def isAlphaNumeric(self, txt):
        return txt.isalnum()
    def regexMatch(self,reString, txt):
        if re.match(reString, txt):
            return True
        else:
            return None
    def askyesnocancel(self, title="NESBuilder", message=""):
        print("WARNING: deprecated; use askYesNoCancel instead of askyesnocancel.")
        m = QtDave.Dialog()
        return m.askYesNo(title, message)
    def askYesNoCancel(self, title="NESBuilder", message=""):
        m = QtDave.Dialog()
        return m.askYesNoCancel(title, message)
    def incLua(self, n):
        filedata = pkgutil.get_data( 'include', n+'.lua' )
        return lua.execute(filedata)
    def setDirection(self, d):
        self.direction=d
    def getWindow(self, window=None):
        return windows.get(coalesce(window, ForLua.window))
    def setWindow(self, window):
        self.window=window
    def getWindowQt(self, name=None):
        # needs an upgrade to get only windows not controls
        if name:
            return controlsNew[name]
        return self.windowQt
    def getTabQt(self, name=None):
        # todo: add parameter to get tab by name
        return self.tabQt
    def setTab(self, tab):
        window = controls[self.window]
        window.tab = tab
        self.tab=tab
    def setContainer(self, widget=None):
        window = self.windowQt
        if widget == None:
            self.tabQt = window
            return
        self.tabQt = widget
    def setTabQt(self, tab=None):
        window = self.windowQt
        if tab == None:
            self.tabQt = window
            return
        self.tabQt = window.tabs.get(tab)
    def switchTab(self, tab):
        window = self.windowQt
        window.tabParent.setCurrentWidget(window.tabs.get(tab))
    def setWindowQt(self, window):
        if type(window)==str:
            window = controlsNew[window]
        
        self.windowQt=window
    def getCanvas(self, canvas=None):
        return controlsNew[coalesce(canvas, self.canvas)]
    def setCanvas(self, canvas):
        self.canvas = canvas
    def makeDir(self,dir):
        dir = fixPath(script_path + "/" + dir)
        print(dir)
        if not os.path.exists(dir):
            os.makedirs(dir)
    def openFolder(self, initial=None):
        initial = fixPath(script_path + "/" + initial)
        m = QtDave.Dialog()
        foldername =  m.openFolder(initial=initial)
        return foldername, os.path.split(foldername)[1]
    def openFile(self, filetypes, initial=None, parent=None):
        initial = fixPath(script_path + "/" + coalesce(initial,''))
        m = QtDave.Dialog()
        return coalesce(m.openFile(filetypes=filetypes, initial=initial), '')
    def saveFileAs(self, filetypes, initial=None):
        initial = fixPath(script_path + "/" + coalesce(initial,''))
        m = QtDave.Dialog()
        file, ext, filter = m.saveFile(filetypes=filetypes, initial=initial)
        file = coalesce(file, '')
        ext = coalesce(ext, '')
        return (file, ext, filter)
    def lift(self, window=None):
        window = self.getWindow(self, window)
        window.control.lift()
        window.control.focus_force()
    def importFunction(self, mod, f):
        m = importlib.import_module(mod)
        setattr(self, f, getattr(m, f))
        
        return getattr(m,f)
    def copyfile(self, src,dst):
        copyfile(src,dst)
    def canvasPaint(self, x,y, c):
        canvas = self.getCanvas(self)
        c = "#{0:02x}{1:02x}{2:02x}".format(nesPalette[c][0],nesPalette[c][1],nesPalette[c][2])
        canvas.control.create_rectangle(x*canvas.scale, y*canvas.scale, x*canvas.scale+canvas.scale-1, y*canvas.scale+canvas.scale-1,
                           width=1, outline=c, fill=c,
                           )

#    def saveCanvasImage(self, f='test.png'):
#        canvas = self.getCanvas(self).control
#        grabcanvas=ImageGrab.grab(bbox=canvas)
#        ttk.grabcanvas.save(f)
#    def loadImageToCanvas(self, f):
#        c = self.getCanvas(self).control
#        canvas = c.control
#        print("loadImageToCanvas: {0}".format(f))
#        try:
#            with Image.open(f) as im:
#                px = im.load()
            
#            displayImage = ImageOps.scale(im, c.scale, resample=Image.NEAREST)
#            canvas.image = ImageTk.PhotoImage(displayImage)
            
#            canvas.create_image(0, 0, image=canvas.image, anchor=tk.NW)
#            canvas.configure(highlightthickness=0, borderwidth=0)
#        except:
#            print("error loading image")
    def newStack(self, arg=[], maxlen=None):
        stack = Stack(arg, maxlen)
        t = lua.table(
                        stack=stack,
                        push=stack.push,
                        pop=stack.pop,
                        remove=stack.remove,
                        asList=stack.asList,
                     )
        return t, stack.push, stack.pop
    def getNESmakerColors(self):
        return [
            [0,0,0],
            [0,255,0],
            [255,0,0],
            [0,0,255],
            ]
    def getNESColors(self, c):
        if type(c) is str:
            c=c.replace(' ','').strip()
            c = [nesPalette[x] for x in unhexlify(c)]
            if len(c) == 1:
                return c[0]
            return c
        else:
            c = [nesPalette[v] for i,v in sorted(c.items())]
            if len(c) == 1:
                return c[0]
            return c
    def getAttribute(self, attrTable, tileX,tileY):
        attrIndex = math.floor(tileY / 4) * 8 + math.floor(tileX / 4)
        return math.floor(attrTable[attrIndex]/(2**(((math.floor(tileY/2) % 2)*2 + math.floor(tileX/2) % 2)*2))) % 4
        #return (attrTable[attrIndex]>>(tileY%2*2+tileX)*2)%4
    def setAttribute(self, attrTable, tileX,tileY, pal):
        
        attrIndex = math.floor(tileY / 4) * 8 + math.floor(tileX / 4)
        
        b=lambda x:"{0:08b}".format(x)
        before = attrTable[attrIndex]
        #attrTable[attrIndex] = attrTable[attrIndex] & 0xff^(3<<(tileY%2*2+tileX%2)*2) | pal<<(tileY%2*2+tileX%2)*2
        
        masks = [0b11111100, 0b11110011, 0b11001111, 0b00111111]
        mTileMap = [0,1,2,3]
        
        
        
        attr = attrTable[attrIndex]
        i = math.floor(tileY/2)%2*2+math.floor(tileX/2)%2
        
        attr = (attr & masks[i]) | (pal<<mTileMap[i]*2)
        
        attrTable[attrIndex] = attr
        after = attr
        
        #print(' tilexy=({},{}) attrIndex={} i={} pal={} {}-->{}'.format(attrTable[0], tileX,tileY, attrIndex,i, pal,b(before),b(after)))
        
        return attrIndex, attrTable[attrIndex]
    def imageToCHR(self, f, outputfile="output.chr", colors=False):
        print('imageToCHR')
        data = self.imageToCHRData(self, f, colors)
        
        print('Tile data written to {0}.'.format(outputfile))
        f=open(outputfile,"wb")
        f.write(bytes(data))
        f.close()
    def getLen(self, item):
        # todo: make work for lua stuff
        if not item:
            return 0
        return len(item)
    def tableToList(self, t,base=1):
        if t.__class__.__name__ == '_LuaTable':
            ret = [t[x] for x in list(t)]
            if base==1:
                ret = [None]+ret
            return ret
        else:
            return t
    def hexToList(self, s, base=1):
        return list(bytearray.fromhex(s))
    def listToTable(self, l, base=1):
        if lupa.lua_type(l)=='table': return l
        if l==None: return l
        if type(l) is int: return None
        
        if base==0:
            t = lua.table()
            for i, item in enumerate(l):
                t[i] = item
            return t
        
        return lua.table_from(l)
#    def test(self, x=0,y=0):
#        canvas = self.getCanvas(self, 'tsaTileCanvas')
#        f = r"J:\svn\NESBuilder\mtile.png"
#        img = Image.open(f)
#        photo = ImageTk.PhotoImage(ImageOps.scale(img, 2, resample=Image.NEAREST))
#        self.images2.append(photo)
#        canvas = self.getCanvas(self, 'testCanvas')
#        canvas.control.create_image(x, y, image=photo, anchor=tk.NW)
    def imageToCHRData(self, f, colors=False):
        print('imageToCHRData')
        
        # convert and re-index lua table
        if lupa.lua_type(colors)=="table":
            colors = [colors[x] for x in colors]
        
        try:
            with Image.open(f) as im:
                px = im.load()
        except:
            print("error loading image")
            return
        
        width, height = im.size
        
        w = math.floor(width/8)*8
        h = math.floor(height/8)*8
        nTiles = int(w/8 * h/8)
        
        out = []
        for t in range(nTiles):
            tile = [[]]*16
            for y in range(8):
                tile[y] = 0
                tile[y+8] = 0
                for x in range(8):
                    for i in range(4):
                        if list(px[x+(t*8) % w, y + math.floor(t/(w/8))*8]) == colors[i]:
                            tile[y] += (2**(7-x)) * (i%2)
                            tile[y+8] += (2**(7-x)) * (math.floor(i/2))
            
            for i in range(16):
                out.append(tile[i])
        
        ret = lua.table_from(out)
        
        return ret
    def screenshotTest(self):
        main.screenshot(main)
    def updateApp(self):
        app.processEvents()
    def getFileData(self, f=None):
        file=open(f,"rb")
        #file.seek(0x1000)
        fileData = file.read()
        file.close()
        return list(fileData)
    def getFileAsArray(self, f):
        file=open(f,"rb")
        fileData = file.read()
        file.close()
        fileData = list(fileData)
        return fileData
    def saveArrayToFile(self, f, fileData):
        fileData = self.tableToList(self, fileData, base=0)
        f = fixPath2(f)
        file=open(f,"wb")
        file.write(bytes(fileData))
        file.close()
        return True
    def writeToFile(self, f, fileData):
        f = fixPath2(f)
        file=open(f,"w")
        file.write(fileData)
        file.close()
        return True
    def unHex(self, s):
        return unhexlify(str(s))
    def hexStringToList(self, s):
        return list(unhexlify(s))
    def getFileContents(self, f, start=0):
        # returns a list
        file=open(f,"rb")
        file.seek(start)
        fileData = file.read()
        file.close()
        
        return list(fileData)
    def loadCHRFile(self, f='chr.chr', colors=(0x0f,0x21,0x11,0x01), start=0):
        file=open(f,"rb")
        file.seek(start)
        fileData = file.read()
        file.close()
        fileData = list(fileData)
        
        ret = self.loadCHRData(self,fileData,colors)
        return ret
#    def newCHRData(self, nTiles=16*16):
#        return lua.table_from("\x00" * (nTiles * 16))
    def newCHRData(self, columns=16,rows=16):
        imageData = lua.table()
        for i in range(0, 16*columns*rows):
            imageData[i+1] = 0
        return imageData
    def loadCHRData(self, fileData=False, colors=(0x0f,0x21,0x11,0x01), columns=16, rows=16, fromHexString=False):
        print('DEPRECIATED: loadCHRData')
        control = self.getCanvas(self)
        
        canvas = control.control
        
        if fromHexString:
            fileData = list(unhexlify(fileData))
        
        if not fileData:
            fileData = "\x00" * (16 * columns * rows)
        
        if type(fileData) is str:
            fileData = [ord(x) for x in fileData]
        elif lupa.lua_type(fileData)=="table":
            fileData = [fileData[x] for x in fileData]
        
        # convert and re-index lua table
        if lupa.lua_type(colors)=="table":
            colors = [colors[x] for x in colors]
        
        img=Image.new("RGB", size=(columns*8,rows*8))
        
        a = np.asarray(img).copy()
        
        for tile in range(math.floor(len(fileData)/16)):
            if tile >= (columns * rows):
                break
            for y in range(8):
                for x in range(8):
                    c=0
                    x1=(tile % columns)*8+(7-x)
                    y1=math.floor(tile/columns)*8+y
                    if (fileData[tile*16+y] & (1<<x)):
                        c=c+1
                    if (fileData[tile*16+y+8] & (1<<x)):
                        c=c+2
                    a[y1][x1] = nesPalette[colors[c]]
        
        img = Image.fromarray(a)
        
        #img = img.crop((0,0,50,50))
        
        ret = lua.table_from(fileData)
        
        photo = ImageTk.PhotoImage(ImageOps.scale(img, control.scale, resample=Image.NEAREST))
        
        canvas.chrImage = photo # keep a reference
        
        canvas.create_image(0,0, image=photo, state="normal", anchor=tk.NW)
        canvas.configure(highlightthickness=0, borderwidth=0)
        
        control.chrData = lua.table_from(fileData)
        
        return ret
    def exportCHRDataToImage(self, filename="export.png", fileData=False, colors=(0x0f,0x21,0x11,0x01)):
        colors=(0x0f,0x21,0x11,0x01)
        
        if not fileData:
            print('no filedata')
            fileData = "\x00" * 0x1000
        
        if type(fileData) is str:
            fileData = [ord(x) for x in fileData]
        elif lupa.lua_type(fileData)=="table":
            #fileData = [fileData[x] for x in fileData]
            fileData = list([fileData[x] for x in fileData])
            
        # convert and re-index lua table
        if lupa.lua_type(colors)=="table":
            colors = [colors[x] for x in colors]
        
        img=Image.new("RGB", size=(128,128))
        
        a = np.asarray(img).copy()
        
        for tile in range(256):
            for y in range(8):
                for x in range(8):
                    c=0
                    x1=tile%16*8+(7-x)
                    y1=math.floor(tile/16)*8+y
                    if (fileData[tile*16+y] & (1<<x)):
                        c=c+1
                    if (fileData[tile*16+y+8] & (1<<x)):
                        c=c+2
                    a[y1][x1] = nesPalette[colors[c]]
        
        img = Image.fromarray(a)
        img.save(filename)
    def Quit(self):
#        app.quit()
#        main.destroy()
        #onExit()
        print("Quit selected")
        main.close()
    def switch(self):
        if qt:
            app.quit()
            main.destroy()
        else:
            self.restart(self)
    def exec(self, s):
        exec(s)
    def eval(s):
        # store the eval return value so we can pass return value to lua space.
        exec('ForLua.execRet = {0}'.format(s))
        return ForLua.execRet
    def embedTest(self):
        import subprocess
        import time
        import win32gui
        
        print('embed test')

        # create a process
        #exePath = "C:\\Windows\\system32\\calc.exe"
        exePath = r"J:\Games\Nes\fceux-2.2.3-win32\fceux.exe"
        subprocess.Popen(exePath)
        #hwnd = win32gui.FindWindowEx(0, 0, "CalcFrame", "Calculator")
        #hwnd = win32gui.FindWindowEx(0, 0, 0, "FCEUX 2.2.3-interim git9cd4b59cb3e02f911e9a96ba8f01fa0a95bc2f0c")
        hwnd = win32gui.FindWindow(0, "FCEUX 2.2.3-interim git9cd4b59cb3e02f911e9a96ba8f01fa0a95bc2f0c")
        #hwnd = win32gui.FindWindowEx(0, 0, "CalcFrame", None)
        #hwnd = win32gui.FindWindow(0, "Calculator")
        time.sleep(0.05)
        #time.sleep(0.15)
        #time.sleep(2)
        m = QtDave.QWidget()
        layout = QtDave.QVBoxLayout(m)
        #layout = main.layout()
        
        window = QtDave.QWindow.fromWinId(hwnd)
        window.setFlags(QtDave.Qt.FramelessWindowHint)
        #widget = QtDave.QWidget.createWindowContainer(window, controlsNew.get('testTab'))
        widget = QtDave.QWidget.createWindowContainer(window)
        #widget = QtDave.QWidget.createWindowContainer(window, main)
        #widget = main.createWindowContainer(window, main)
        #widget.show()
        #widget.resize(800,800)
        #main.addWidget(widget, 'test')
        #layout.addWidget(widget)
        #main.layout().addWidget(widget)
        #layout = QtDave.QVBoxLayout()
        #main.setCentralWidget(widget)
        layout.addWidget(widget)
        #widget.setLayout(layout)
        #main.setLayout(layout)
        m.show()
        
#        self.setGeometry(500, 500, 450, 400)
#        self.setWindowTitle('File dialog')
#        self.show()
    def getControlNew(self, n):
        if not n:
            return controlsNew
        else:
            if n in controlsNew:
                return controlsNew[n]
            elif "_"+n in controlsNew:
                return controlsNew["_"+n]
    def getControl(self, n):
        if not n:
            return controls
        else:
            if n in controls:
                return controls[n]
            elif "_"+n in controls:
                return controls["_"+n]
        return self.getControlNew(self, n)
    def removeControl(c):
        controls[c].destroy()
    def hideControl(c):
        x = controls[c].winfo_x()
        if x<0:
            x=x+1000
        else:
            x=x-1000
        controls[c].place(x=x)
    def makeNESPixmap(self, width=128,height=128):
        return QtDave.NESPixmap(width, height)
    @lupa.unpacks_lua_table
    def makeCanvasQt(self, t):
        t.scale = t.scale or 3
        t.w=t.w*t.scale
        t.h=t.h*t.scale
        
        ctrl = QtDave.Canvas(self.tabQt)
        ctrl.init(t)
        t.control = ctrl
        
        #ctrl.mousePressEvent = makeCmdNew(t)
        #ctrl.mouseReleaseEvent = makeCmdNew(t)
        #ctrl.mouseMoveEvent = makeCmdNew(t)
        ctrl.onMouseMove = makeCmdNew(t)
        ctrl.onMousePress = makeCmdNew(t)
        ctrl.onMouseRelease = makeCmdNew(t)
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeTabQt(self, t):
        window = self.windowQt
        
        #if t.name in self.windowQt.tabs:
        if self.windowQt.tabs.get(t.name):
            print('Not creating tab "{}" (already exists).'.format(t.name))
            return self.getControlNew(self, t.name)
        
        ctrl = QtDave.Widget()
        window.tabParent.addTab(ctrl, t.text)
        window.repaint()
        ctrl.init(t)
        
        window.tabs.update({t.name:ctrl})
        
        ctrl.mousePressEvent = makeCmdNew(t)
        
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeButton2(self, t):
        
        if t.w:
            t.w=t.w*7.5
        
        if t.h:
            t.h=t.h*7.5
        
        return self.makeButtonQt(self, t)
    @lupa.unpacks_lua_table
    def makeTable(self, t):
        ctrl = QtDave.Table(self.tabQt)
        ctrl.init(t)
        
        ctrl.setRowCount(t.rows)
        ctrl.setColumnCount(t.columns)
        ctrl.verticalHeader().hide()
        
        t.control = ctrl
        #ctrl.onChange = makeCmdNoEvent(t)
        
        ctrl.clicked.connect(makeCmdNew(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeSideSpin(self, t):
        ctrl = QtDave.SideSpin(self.tabQt)
        ctrl.init(t)
        
        #ctrl.onChange = lambda:print('test')
        t.control = ctrl
        ctrl.onChange = makeCmdNoEvent(t)
        
        #ctrl.clicked.connect(makeCmdNew(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeButtonQt(self, t):
        ctrl = QtDave.Button(t.text, self.tabQt)
        ctrl.init(t)
        
#        if t.image:
            #image = Image.open(t.image.replace(".png", "_white.png"))
            #t.image = t.image.replace(".png", "_white.png")
#            image = Image.open(t.image)
#            print(ctrl.setIcon(image))
        
        if t.image:
            folder, file = os.path.split(t.image)
            #print(folder,file)
            d = os.path.dirname(sys.modules[folder].__file__)
            #print(d)
            filename = os.path.join(d, file)
            #print(filename)
            ctrl.setIcon(filename)
        
        ctrl.clicked.connect(makeCmdNew(t))
        #ctrl.onMouseRelease = makeCmdNew(t)
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    def getCursorFile(self, cursorName):
        
        cursorName = "cursors\\"+cursorName
        folder, file = os.path.split(cursorName)
        d = os.path.dirname(sys.modules[folder].__file__)
        filename = os.path.join(d, file)
        return filename
    @lupa.unpacks_lua_table
    def makeLineEdit(self, t):
        ctrl = QtDave.LineEdit(self.tabQt)
        t.text = coalesce(t.text, '')
        t.control = ctrl
        ctrl.init(t)
        
        #ctrl.clicked.connect(makeCmdNew(t))
        #ctrl.textChanged.connect(makeCmdNew(t))
        ctrl.textChanged.connect(makeCmdNoEvent(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeTextEdit(self, t):
        ctrl = QtDave.TextEdit(t.text, self.tabQt)
        ctrl.init(t)
        #ctrl.clicked.connect(makeCmdNew(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeFrame(self, t):
        ctrl = QtDave.Frame(self.tabQt)
        ctrl.init(t)
        #ctrl.clicked.connect(makeCmdNew(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeList(self, t):
        ctrl = QtDave.ListWidget(self.tabQt)
        ctrl.setSortingEnabled(False)
        ctrl.init(t)
        
        #t.currentItem = lambda: ctrl.currentItem().text()
        t.getIndex = ctrl.currentRow
        t.getItem = lambda: ctrl.currentItem().text()
        
        
        if t.list:
            ctrl.setList(t.list)
        t.control = ctrl
        #ctrl.clicked.connect(makeCmdNew(t))
        #ctrl.clicked.connect(makeCmdNoEvent(t))
        #ctrl.itemClicked.connect(makeCmdNoEvent(t))
        #ctrl.itemClicked.connect(makeCmdNew(t))
        ctrl.currentItemChanged.connect(makeCmdNew(t))
        
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeCheckbox(self, t):
        ctrl = QtDave.CheckBox(t.text, self.tabQt)
        ctrl.init(t)
        
        t.control = ctrl
        t.isChecked = ctrl.isChecked
        t.setChecked = ctrl.setChecked
        
        if t.value: ctrl.setChecked(True)
        
        if t.image:
            try:
                # the frozen version will still try to load it manually first
                ctrl.setIcon(fixPath2(t.image))
            except:
                folder, file = os.path.split(t.image)
                ctrl.setIcon(BytesIO(pkgutil.get_data(folder, file)))
        
        ctrl.clicked.connect(makeCmdNoEvent(t))
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeLauncherIcon(self, t):
        ctrl = QtDave.LauncherIcon(self.tabQt)
        ctrl.init(t)
        ctrl.mousePressEvent = makeCmdNew(t)
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeLink(self, t):
        ctrl = QtDave.Link(t.text, self.tabQt)
        ctrl.init(t)
        ctrl.mousePressEvent = makeCmdNew(t)
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeLabelQt(self, t):
        ctrl = QtDave.Label(t.text, self.tabQt)
        ctrl.init(t)
        ctrl.mousePressEvent = makeCmdNew(t)
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    @lupa.unpacks_lua_table
    def makeMenuQt(self, t):
        window = self.getWindowQt(self)
        
        # We'll turn this into a dictionary so our little class library
        # doesn't have to handle any lua.
        menuItems = [dict(x) for _,x in t.menuItems.items()]
        for i, item in enumerate(menuItems):
            if item.get('name', False):
                if not item.get('action',False):
                    
                    
                    t2 = lua.table()
                    
                    if t.prefix:
                        t2.name = t.name + "_" + item.get('name', str(i))
                    else:
                        t2.name = item.get('name', "_"+str(i))
                    
                    menuItems[i].update(action = makeCmdNew(t2))
        
        return window.addMenu(t.name, t.text, menuItems)
    def setText(c,txt):
        c.setText(txt)
    def makeMenu(self, t, variables):
        x,y,w,h = variables
        
        window = self.getWindow(self)
        if not window.menu:
            menubar = tk.Menu(window.control)
            window.menu = menubar
            window.control.config(menu = menubar)
        
        tab = self.getTab(self)
        
        menu = False
        control = False
        
        if controls.get(t.name):
            # menu already exists, add to it instead.
            menu = controls.get(t.name)
            control = menu
            
            t=lua.table(name=t.name,
                        control=control,
                        items=t['items'],
                        prefix=t.prefix,
                        )
        else:
            # create menu
            menu = tk.Menu(tab, tearoff=0)
            
            if cfg.getValue("main","styleMenus"):
                menu.config(bg=config.colors.bk2,fg=config.colors.fg, activebackground=config.colors.bk_menu_highlight)
            
            window.menu.add_cascade(label=t.text, menu=menu)

            control = menu
            controls.update({t.name:control})

            t=lua.table(name=t.name,
                        control=control,
                        items=t['items'],
                        prefix=t.prefix,
                        )

        for i, item in t['items'].items():
            name = item.name or str(i)
            t2=lua.table(name=t.name+"_"+name,
                        control=control,
                        items=t['items'],
                        )
            if not t.prefix:
                if item.name:
                    t2.name = name
                else:
                    t2.name = "_"+name
            
            entry = dict(index=i, entry = item)
            if item.text == "-":
                menu.add_separator()
            else:
                menu.add_command(label=item.text, command=makeCmdNoEvent(t2, extra=entry))
        
        return t
    def makeWindow(self, t, variables):
        x,y,w,h = variables
        
        if controls.get(t.name):
            if controls.get(t.name).exists():
                # If the window already exists, bring it to the front
                # and return its table.
                t = controls.get(t.name)
                t.alreadyCreated = True
                t.control.deiconify()
                t.control.lift()
                return t
        
        window = tk.Toplevel(root)
        window.title(t.title or "Window")
        window.geometry("{0}x{1}".format(w,h))
        
        def close():
            del controls[t.name]
            window.destroy()
        def front():
            window.focus_force()
        def exists():
            return window.winfo_exists()
            #return window.winfo_ismapped()
        window.protocol( "WM_DELETE_WINDOW", close)
        
        tabParent = ttk.Notebook(window)
        tabs={}
        
        window.configure(bg=config.colors.bk)
        
        # Set the window icon and override when applicable in this order:
        # 1. executable icon 
        # 2. external icon if not frozen
        # 3. custom icon
        # 4. custom icon relative to plugins folder
        window.iconbitmap(sys.executable)
        if not frozen:
            try:
                photo = ImageTk.PhotoImage(file = fixPath2("icon.ico"))
                window.iconphoto(False, photo)
            except:
                pass
        if t.icon:
            try:
                photo = ImageTk.PhotoImage(file = fixPath2(t.icon))
                window.iconphoto(False, photo)
            except:
                try:
                    photo = ImageTk.PhotoImage(file = fixPath2(config.pluginFolder+"/"+t.icon))
                    window.iconphoto(False, photo)
                except:
                    pass

        control = window
        t=lua.table(name=t.name,
                    control=control,
                    tabParent=tabParent,
                    tabs=tabs,
                    close=close,
                    front=front,
                    exists=exists,
                    )
        
        controls.update({t.name:t})
        windows.update({t.name:t})
        #windows.update({t.name:window})
        
        #control.bind( "<ButtonRelease-1>", makeCmdNew(t))
        return t
    def makeText(self, t, variables):
        x,y,w,h = variables
        
        control = tkDave.Text(self.getTab(self), borderwidth=0, relief="solid",height=t.lineHeight)
        control.config(fg=config.colors.fg, bg=config.colors.bk3)
        
        control.insert(tk.END, t.text)
        control.place(x=x, y=y)
        if not t.lineHeight:
            control.place(height=h)
        control.place(width=w)
        
        def setText(text):
            control.delete(1.0, tk.END)
            control.insert(tk.END, text)
        def addText(text):
            control.insert(tk.END, text)
        def print(text=''):
            text=str(text)
            control.insert(tk.END, text+"\n")
        def clear():
            control.delete(1.0, tk.END)
        t=lua.table(name=t.name,
                    control=control,
                    height=h,
                    width=w,
                    setText = setText,
                    addText = addText,
                    print = print,
                    clear = clear,
                    )

        controls.update({t.name:t})

        #control.bind( "<Button-1>", makeCmdNew(t))
        control.bind( "<ButtonRelease-1>", makeCmdNew(t))
        control.bind( "<Return>", makeCmdNew(t))
        
        return t
    def makeEntry(self, t, variables):
        x,y,w,h = variables
        control=None
        padX=5
        padY=1
        frame = tk.Frame(self.getTab(self), borderwidth=0, relief="solid")
        frame.config(bg=config.colors.bk3)
        frame.place(x=x,y=y, width=w, height=h)
        
        control = tkDave.Entry(self.getTab(self), borderwidth=0, relief="solid",height=t.lineHeight)
        control.config(fg=config.colors.fg, bg=config.colors.bk3, insertbackground = config.colors.fg)
        control.insert(tk.END, t.text)
        control.place(x=x+padX, y=y+padY)
        if not t.lineHeight:
            control.place(height=h-padY*2)
        control.place(width=w-padX*2)
        
        def setText(text=""):
            control.delete(0, tk.END)
            control.insert(tk.END, text)
        t=lua.table(name=t.name,
                    control=control,
                    height=h,
                    width=w,
                    clear = lambda:setText(),
                    setText = setText,
                    getText = control.get,
                    )
        
        controls.update({t.name:t})

        control.bind( "<ButtonRelease-1>", makeCmdNew(t))
        control.bind( "<Return>", makeCmdNew(t))
        
        return t
    def makeTree(self, t, variables):
        x,y,w,h = variables
        
        style.configure('new.Treeview', background=config.colors.bk, fg=config.colors.fg)
        
        control = ttk.Treeview(self.getTab(self), style = "new.Treeview")
        control.place(x=x, y=y)
        #control.place(x=x, y=y, height=h, width=w)
        
        tree = control
        tree["columns"]=("one","two","three")
        tree['show'] = 'headings'
        tree.column("#0", width=50, minwidth=50, stretch=tk.NO)
        tree.column("one", width=50, minwidth=50, stretch=tk.NO)
        tree.column("two", width=50, minwidth=50, stretch=tk.NO)
        tree.column("three", width=50, minwidth=50, stretch=tk.NO)
        
        tree.heading(0, text ="Foo") 
        tree.heading(1, text ="Bar") 
        tree.heading(2, text ="Baz")
        
        id = tree.insert("", 'end', "test", text ="test1",  values =("a", "b", "c")) 
        tree.insert("", '0', "test2", text ="test2",  values =("a", "b", "c")) 
        tree.insert("", 'end', "test3", text ="test3",  values =("a", "b", "c")) 
        tree.insert(id, 'end', "test4", text ="test4",  values =("a", "b", "c")) 
        
        t=lua.table(name=t.name,
                    control=control,
                    height=h,
                    width=w,
                    )
        controls.update({t.name:t})

        control.bind( "<Button-1>", makeCmdNew(t))
        return t
    def makeLabel(self, t, variables):
        x,y,w,h = variables
        
        control = tkDave.Label(self.getTab(self), text=t.text, borderwidth=0, background="white", relief="solid")
        control.config(fg=config.colors.fg, bg=config.colors.bk2)
        
        if t.clear:
            control.config(fg=config.colors.fg, bg=config.colors.bk, borderwidth=0)
        if t.clear:
            control.place(x=x, y=y)
        else:
            control.place(x=x, y=y, height=h, width=w)
        
        def setFont(fontName="Verdana", size=12):
            control.config(font=(fontName, size))
            t.update()
        def setText(text):
            control.config(text=text)
        def setJustify(j="left"):
            t = {
                "left":tk.LEFT,
                "right":tk.RIGHT
                }
            control.config(justify=t.get(j, tk.LEFT))
            control.place()
        
        #tkDave.make_draggable(control)
        
        t=lua.table(name=t.name,
                    control=control,
                    height=h,
                    width=w,
                    setText = setText,
                    setFont = setFont,
                    setJustify = setJustify,
                    )
        
        controls.update({t.name:t})

        if t.name: control.bind( "<Button-1>", makeCmdNew(t))
        return t
    @lupa.unpacks_lua_table
    def makePaletteControlQt(self, t):
        ctrl = QtDave.PaletteControl(self.tabQt)
        ctrl.init(t)
        #ctrl.mousePressEvent = makeCmdNew(t)
        
        for cell in ctrl.cells:
            t2 = lua.table(
                name = t.name,
                cellNum = cell.cellNum,
                cell = cell,
                control = ctrl,
                cells = ctrl.cells,
                set = ctrl.set,
                setAll = ctrl.setAll,
            )
            #cell.mousePressEvent = makeCmdNew(t2)
            #cell.onMouseMove = makeCmdNew(t2)
            cell.onMousePress = makeCmdNew(t2)
            #cell.onMouseRelease = makeCmdNew(t2)

        
        
        controlsNew.update({ctrl.name:ctrl})
        return ctrl
    def selectTab(self, tab):
        window = self.getWindow(self)
        window.tabParent.select(list(window.tabs).index(tab))
        print(list(window.tabParent.tabs))
    def forceClose(self):
        #atexit.unregister(exitCleanup)
        sys.exit()
    def restart(self):
        #app.quit()
        #main.destroy()
        #main.close()
        
        #if onExit(skipCallback=True):
        if onExit():
            print("\n"+"*"*20+" RESTART "+"*"*20+"\n")
            
            main.close()
            
            os.chdir(initialFolder)
            if frozen:
                subprocess.Popen(sys.argv)
            else:
                subprocess.Popen([sys.executable]+ sys.argv)
            os.system('cls')

    def setTitle(self, title=''):
        main.setWindowTitle(title)
    
# Return it from eval so we can execute it with a 
# Python object as argument.  It will then add "NESBuilder"
# to Lua
ForLua.decorate(ForLua)
lua_func = lua.eval('function(o) {0} = o return o end'.format('NESBuilder'))
lua_func(ForLua)

lua_func = lua.eval('function(o) {0} = o return o end'.format('nesPalette'))
lua_func(lua.table(nesPalette))

def coalesce(*arg): return next((a for a in arg if a is not None), None)

def makeCmdNew(*args, extra = False):
    if not args[0].name:
        # no name specified, dont create a function
        return
    if args[0].anonymous:
        print('anon')
    if not extra:
        extra = dict()
    extra.update(plugin = lua.eval("_getPlugin and _getPlugin() or false"))

    return lambda x:doCommandNew(args, ev = x, extra = extra)
def makeCmdNoEvent(*args, extra = False):
    if extra:
        return lambda :doCommandNew(args, ev = lua.table(extra=extra))
    return lambda :doCommandNew(args)


# a single lua table is passed
def doCommandNew(*args, ev=False, extra = False):
    args = args[0][0]
    try:
        for k,v in ev.extra.items():
            args[k]=v
        ev.extra = False
    except:
        pass
    
    # now try items from the "extra" argument
    try:
        for k,v in extra.items():
            args[k]=v
    except:
        pass
    
    if ev and (ev.__class__.__name__ == "QMouseEvent"):
        event = dict(
            event = ev,
            x = ev.x,
            y = ev.y,
            button = ev.button,
            type = ev.type,
        )
        if callable(ev.type):
            b = dict({
                2:'ButtonPress',
                3:'ButtonRelease',
                4:'ButtonDblClick',
                5:'Move',
                })
            event.update(type=b.get(ev.type()))
        
        args.event = event
    elif ev and (ev.__class__.__name__ == "QListWidgetItem"):
        # ev exists, but isn't an event
        args.selectedWidget = ev
    # doCommand is a command preprocessor thing.  If 
    # It returns true then it moves on to name_command
    # if it exists, or name_cmd otherwise.
    lua_func = lua.eval("""function(o)
        local status=true
        if doCommand then status = doCommand(o) end
        if status then
            if {0}_command then
                {0}_command(o)
            elseif {0}_cmd then
                {0}_cmd(o)
            end
        end
    end""".format(args.name))
    try:
        lua_func(args)
    except LuaError as err:
        handleLuaError(err)
    except Exception as err:
        handlePythonError(err)

def handlePythonError(err=None, exit=False):
    print("-"*79)
    e = traceback.format_exc().splitlines()
    e = "\n".join([x for x in e if "lupa\_lupa.pyx" not in x])
    print(e)
    print("-"*79)
    
    if exit or cfg.getValue("main","breakonpythonerrors"):
        sys.exit(1)

def onExit(skipCallback=False):
    print('onExit')
    exit = True
    if skipCallback:
        pass
    elif lua.eval('type(onExit)') == 'function':
        exit = not lua.eval('onExit()')
    if exit:
        exitCleanup()
        app.quit()
        return true

main.onClose = onExit

def exitCleanup():
    x = main.x()
    y = main.y()
    w = main.width
    h = main.height
    
    if w>=500 and h>=400 and x>0 and y>0:
        cfg.setValue('main','x', x)
        cfg.setValue('main','y', y)
        cfg.setValue('main','w', w)
        cfg.setValue('main','h', h)
    cfg.save()

# run function on exit
#atexit.register(exitCleanup)

ctrl = QtDave.TabWidget(main)
main.tabParent = ctrl
t = lua.table(name = main.name+"tabs", y=main.menuBar().height(), control=ctrl)
ctrl.init(t)
ctrl.mousePressEvent = makeCmdNew(t)

main.tabParent.currentChanged.connect(makeCmdNoEvent(t))


#root = tk.Tk()
#root = tkDave.Tk()

# hide the window until it's ready
#root.withdraw()
#root.protocol( "WM_DELETE_WINDOW", onExit )
#root.iconbitmap(sys.executable)

#if not frozen:
#    photo = ImageTk.PhotoImage(file = fixPath2("icon.ico"))
#    root.iconphoto(False, photo)

#tab_parent = ttk.Notebook(root)

windows={}

#tab_parent.pack(expand=1, fill='both')

#var = tk.IntVar()
#def on_click():
#    print(var.get())

#style = ttk.Style()
#style.configure('new.TFrame')


def handleLuaError(err):
    err = str(err).replace('error loading code: ','')
    err = err.replace('[string "<python>"]',"[main.lua]")
    err = err.replace('[C]',"[lua]")
    err = err.replace("stack traceback:","\nstack traceback:")
    #err = '\n'.join(textwrap.wrap(err, width=70))
    #err = textwrap.indent(err, " "*4)
    
    err = [line.strip() for line in err.splitlines()]
    if err[0].startswith("error loading module "):
        err.pop(0)
        line = err[0].split(":")
        line[0]=line[0].replace(".\\","").replace("\\","")
        line[0]="["+line[0]+"]"
        line = ":".join(line)
        err[0] = line
    
    indent = 0
    for i, line in enumerate(err):
        err[i]=" "*indent+line
        if line.startswith("stack traceback:"):
            indent = 4
    
    err = "\n".join(err)
    err = textwrap.indent(err, " "*4)
    
    print("-"*80)
    print("LuaError:\n")
    print(err)
    print()
    print("-"*80)

    if cfg.getValue("main","breakonluaerrors"):
        sys.exit(1)


lua.execute("True, False = true, false")
lua.execute("len = function(item) return NESBuilder:getLen(item) end")

gotError = False

try:
    if len(sys.argv)>1:
        # use file specified in argument
        f = open(sys.argv[1],"r")
        lua.execute(f.read())
        f.close()
    elif frozen:
        # use internal main.lua
        filedata = pkgutil.get_data('include', 'main.lua' )
        lua.execute(filedata)
    else:
        # use external main.lua
        f = open("main.lua","r")
        lua.execute(f.read())
        f.close()
    pass
except LuaError as err:
    handleLuaError(err)
    gotError = True
    
if gotError:
    sys.exit(1)
    
    
    
config  = lua.eval('config or {}')

config.title = config.title or "SpideyGUI"
main.setWindowTitle(config.title)

print("This console is for debugging purposes.\n")

try:
    lua.execute("if init then init() end")
except LuaError as err:
    print("*** init() Failed")
    handleLuaError(err)
except Exception as err:
    handlePythonError(err, exit=True)

lua.execute("plugins = {}")

# load lua plugins
if cfg.getValue("main","loadplugins"):
    folder = config.pluginFolder
    folder = fixPath(script_path + "/" + folder)
    if os.path.exists(folder):
        lua.execute("""
        local _plugin
        """)
        for file in os.listdir(folder):
            if file.endswith(".lua") and not file.startswith("_"):
                print("Loading plugin: "+file)
                code = """
                    NESBuilder:setWorkingFolder()
                    _plugin = require("{0}.{1}")
                    _plugin.dontPrintThis = true
                    if type(_plugin) =="table" then
                        plugins[_plugin.name or "{1}"]=_plugin
                        _plugin.file = "{2}"
                        _plugin.name = _plugin.name or "{1}"
                        _plugin.data = _plugin.data or {{}}
                    end
                """.format(config.pluginFolder,os.path.splitext(file)[0], file)
                #print(fancy(code))
                try:
                    lua.execute(code)
                except LuaError as err:
                    print("*** Failed to load plugin: "+file)
                    handleLuaError(err)
                
        try:
            lua.execute("if onPluginsLoaded then onPluginsLoaded() end")
        except LuaError as err:
            print("*** onPluginsLoaded() Failed")
            handleLuaError(err)
        except Exception as err:
            handlePythonError(err)
try:
    lua.execute("if onReady then onReady() end")
except LuaError as err:
    print("*** onReady() Failed")
    handleLuaError(err)

w = cfg.getValue('main', 'w', default=coalesce(config.width, 800))
h = cfg.getValue('main', 'h', default=coalesce(config.height, 800))

x,y = cfg.getValue('main', 'x'), cfg.getValue('main', 'y')

main.setGeometry(x,y,w,h)

s = pkgutil.get_data('include', 'style.qss').decode('utf8')
r = dict(
    bk=config.colors.bk,
    bk2=config.colors.bk2,
    bk3=config.colors.bk3,
    bk4=config.colors.bk4,
    bkMenuHighlight=config.colors.bk_menu_highlight,
    menuBk=config.colors.menuBk,
    fg=config.colors.fg,
    borderLight=config.colors.borderLight,
    borderDark=config.colors.borderDark,
    bkHover=config.colors.bk_hover,
    link=config.colors.link,
    linkHover=config.colors.linkHover,
    textInputBorder=config.colors.textInputBorder,
)
for (k,v) in r.items():
    s = s.replace("_"+k+"_", v)

app.setStyleSheet(s)

if not frozen:
    main.setIcon(fixPath2('icon.ico'))

#controlsNew.update({main.name:main})

def onResize(width,height,oldWidth,oldHeight):
    for tab in main.tabs.values():
        #print(tab.name,tab.width,tab.height)
        
#        if tab.width!=0 and tab.height!=0:
#            tab.resize(tab.width+(width-oldWidth),tab.height+(height-oldHeight))
        pass
    try:
        lua.execute("if onResize then onResize({},{},{},{}) end".format(width,height,oldWidth,oldHeight))
    except LuaError as err:
        print("*** onResize() Failed")
        handleLuaError(err)
    except Exception as err:
        handlePythonError(err)
main.onResize = onResize


def onHoverWidget(widget):
    try:
        lua_func = lua.eval('function(o) if onHover then onHover(o) end end')
        lua_func(widget)
    except LuaError as err:
        print("*** onHoverWidget() Failed")
        handleLuaError(err)
    except Exception as err:
        handlePythonError(err)
main.onHoverWidget = onHoverWidget


main.show()
try:
    lua.execute("if onShow then onShow() end")
except LuaError as err:
    print("*** onShow() Failed")
    handleLuaError(err)
except Exception as err:
    handlePythonError(err)


app.mainloop()


