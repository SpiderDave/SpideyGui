"""
Bugs/Issues:
    * symbol recursion issue:
        symbol = symbol + 1     ; does not work
        symbol = {symbol} +1    ; works
    * rept recursion
ToDo:
    * create large test .asm
    * text mapping
        - named textmaps, alternate formats
    * option to automatically localize labels in macros
    * rept ... endr
    * get standalone command line switches working
    * namespaces
        - namespace directive
        - use namespaces when defining/specifying labels or symbols
    * segment and related directives
"""


import math, os, sys
try:
    from . import include
except:
    import include
Cfg = include.Cfg
import time
from datetime import date

import re

import pathlib
import operator

import random

from textwrap import dedent


try:
    from PIL import ImageTk, Image, ImageDraw, ImageOps, ImageGrab
    PIL = True
except:
    PIL = False


#try: import numpy as np
#except: np = False

# need better code for slicing with numpy.
# just disable for now.
np = False

version = dict(
    stage = 'alpha',
    buildDate =  date.today().strftime('%Y.%m.%d'),
    author = 'SpiderDave',
    url = 'https://github.com/SpiderDave/SpiderDaveAsm',
)
version.update(version = 'v{} {}'.format(version.get('buildDate'), version.get('stage')))

defaultPalette=[
    [116, 116, 116], [36, 24, 140], [0, 0, 168], [68, 0, 156],[140, 0, 116],
    [168, 0, 16],[164, 0, 0],[124, 8, 0],[64, 44, 0],[0, 68, 0],[0, 80, 0],
    [0, 60, 20],[24, 60, 92],[0, 0, 0],[0, 0, 0],[0, 0, 0],[188, 188, 188],
    [0, 112, 236],[32, 56, 236],[128, 0, 240],[188, 0, 188],[228, 0, 88],
    [216, 40, 0],[200, 76, 12],[136, 112, 0],[0, 148, 0],[0, 168, 0],
    [0, 144, 56],[0, 128, 136],[0, 0, 0],[0, 0, 0],[0, 0, 0],[252, 252, 252],
    [60, 188, 252],[92, 148, 252],[204, 136, 252],[244, 120, 252],
    [252, 116, 180],[252, 116, 96],[252, 152, 56],[240, 188, 60],
    [128, 208, 16],[76, 220, 72],[88, 248, 152],[0, 232, 216],[120, 120, 120],
    [0, 0, 0],[0, 0, 0],[252, 252, 252],[168, 228, 252],[196, 212, 252],
    [212, 200, 252],[252, 196, 252],[252, 196, 216],[252, 188, 176],
    [252, 216, 168],[252, 228, 160],[224, 252, 160],[168, 240, 188],
    [176, 252, 204],[156, 252, 240],[196, 196, 196],[0, 0, 0],[0, 0, 0],
]

def imageToCHRData(f, colors=False, x=0,y=0, rows=False, cols=False):
    try:
        with Image.open(f) as im:
            px = im.load()
    except:
        print("error loading image")
        return
    
    width, height = im.size
    if rows:
        height = rows*8
    if cols:
        width = cols*8
    
    (left, upper, right, lower) = (x, y, width, height)
    im = im.crop((left, upper, right, lower))
    
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
    
    ret = out
    
    return ret

def flattenList(k):
    result = list()
    for i in k:
        if isinstance(i,list):
            #The isinstance() function checks if the object (first argument) is an 
            #instance or subclass of classinfo class (second argument)
            result.extend(flattenList(i)) #Recursive call
        else:
            result.append(i)
    return result

def inScriptFolder(f):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),f)

class Map(dict):
    """
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]

class Assembler():
    cfg = False
    currentFolder = None
    initialFolder = None
    hideOutputLine = False
    currentTextMap = 'default'
    textMap = {}
    errorLinePos = False
    palette = defaultPalette[:]
    currentPalette = [0x0f,0x01,0x11,0x30]
    stripHeader = False
    namespace = ''
    quotes = ('"""','"',"'")
    hidePrefix = '__hide__'
    
    nesRegisters = Map(
        PPUCTRL = 0x2000, PPUMASK = 0x2001, PPUSTATUS = 0x2002,
        OAMADDR = 0x2003, OAMDATA = 0x2004, PPUSCROLL = 0x2005,
        PPUADDR = 0x2006, PPUDATA = 0x2007, OAMDMA = 0x4014,
        SQ1VOL = 0x4000, SQ1SWEEP = 0x4001, SQ1LO = 0x4002,
        SQ1HI = 0x4003, 
        SQ2VOL = 0x4004, SQ2SWEEP = 0x4005, SQ2LO = 0x4006,
        SQ2HI = 0x4007,
        TRILINEAR = 0x4008, TRILO = 0x400A, TRIHI = 0x400B,
        NOISEVOL = 0x400C, NOISELO = 0x400E, NOISEHI = 0x400F,
        DMCFREQ = 0x4010, DMCRAW = 0x4011, DMCSTART = 0x4012,
        DMCLEN = 0x4013,
        APUSTATUS = 0x4015, APUFRAME = 0x4017,
        JOY = 0x4016, JOY1 = 0x4016, JOY2 = 0x4017,
    )
    nesRegisters = Map({x.lower():y for x,y in nesRegisters.items()})

    def __init__(self):
        pass
    def dummy(self):
        pass
    def lower(self, txt, caseSensitive=False):
        if caseSensitive:
            return txt
        return txt.lower()
    def stripQuotes(self, text):
        for q in self.quotes:
            if text.startswith(q) and text.endswith(q):
                return text[len(q):-len(q)]
        return text
    def tokenize(self, text='', tokens=[], splitter=','):
        tokens = tokens or [text]
        txt = tokens[-1]
        q = False
        for quote in self.quotes:
            if txt.startswith(quote):
                q = quote
                break
        n1=0
        if q:
            n1 = txt.find(q,len(q))+len(q)
        n2 = txt.find(splitter,n1)
        
        if n2==-1:
            return tokens
        
        left = txt[:n2].strip()
        right = txt[n2+1:].strip()
        
        tokens = tokens[:-1] + [left, right]
        return self.tokenize(text, tokens)
    def mapText(self, text):
        #print("Mapping text:", text)
        textMap = self.textMap.get(self.currentTextMap, {})
        
        return [textMap.get(x, ord(x)) for x in text]
    def setTextMap(self, name):
        self.currentTextMap = name
    def getTextMap(self):
        return self.currentTextMap
    def clearTextMap(self, name=False, all=False):
        if all:
            self.currentTextMap = 'default'
            self.textMap = {}
        if not name:
            name = self.currentTextMap
        if name in self.textMap:
            self.textMap.pop(name)
    def setTextMapData(self, chars, mapTo):
        textMap = self.textMap.get(self.currentTextMap, {})
        textMap.update(dict(zip(chars,bytearray.fromhex(mapTo))))
        
        self.textMap[self.currentTextMap] = textMap
    def loadTbl(self, filename=False):
        filename = self.findFile(filename)
        if filename:
            try:
                file = open(filename, "rb")
            except:
                self.errorHint = 'could not open file.'
                return False
            
            tbl=['','']
            for line in file.read().decode('utf-8-sig').splitlines():
                l = line.split('=')
                
                if len(l[0])==1 and len(l[1])==2:
                    l = list(reversed(l))
                if len(l[0])==2 and len(l[1])==1:
                    tbl[1]+=l[0]
                    tbl[0]+=l[1]
                elif line == '':
                    pass
                else:
                    self.errorHint = 'Invalid tbl entry'
                    return False
            self.setTextMapData(tbl[0],tbl[1])
            
            return True
        else:
            self.errorHint = 'file not found'
            return False
    def loadPalette(self, filename=False):
        if filename:
            filename = self.findFile(filename)
            if filename:
                try:
                    file = open(filename, "rb")
                except:
                    self.errorHint = 'could not open file.'
                    return False
                p = list(file.read())
                if len(p) != 192:
                    self.errorHint = 'palette file size must be 192 bytes'
                    return False
                p = [p[i:i + 3] for i in range(0, len(p), 3)]
                self.palette = p
            else:
                self.errorHint = 'file not found'
                return False
        else:
            self.palette = defaultPalette[:]
        
        return self.palette
    def findFile(self, filename):
        
        # Search for files in this order:
        #   Exact match
        #   Relative to current script folder
        #   Relative to initial script folder
        #   Relative to current working folder
        #   Relative to top level of initial script folder
        #   Relative to executable folder
        files = [
            filename,
            os.path.join(self.currentFolder,filename),
            os.path.join(self.initialFolder,filename),
            os.path.join(os.getcwd(),filename),
            os.path.join(str(pathlib.Path(*pathlib.Path(self.initialFolder).parts[:1])),filename),
            os.path.join(os.path.dirname(os.path.realpath(__file__)),filename),
        ]
        
        for f in files:
            if os.path.isfile(f): return f
        
        return False

assembler = Assembler()


operations = {
#    '-':operator.sub,
#    '+':operator.add,
    '/':operator.truediv,
    '&':operator.and_,
    '^':operator.xor,
    '~':operator.invert,
    '|':operator.or_,
    '**':operator.pow,
    '<<':operator.lshift,
    '>>':operator.rshift,
    '%':operator.mod,
    '*':operator.mul,
}


directives = [
    'org','base','pad','fillto','align','fill', 'fillvalue',
    'include','incsrc','includeall','incbin','bin',
    'db','dw','byte','byt','word','hex','dc.b','dc.w',
    'dsb','dsw','ds.b','ds.w','dl','dh',
    'enum','ende','endenum',
    'print','warning','error',
    'setincludefolder',
    'macro','endm','endmacro',
    'if','ifdef','ifndef','else','elseif','endif','iffileexist','iffile',
    'arch','table','loadtable','cleartable','mapdb','clampdb',
    'index','mem','bank','banksize','chrsize','header','noheader','stripheader',
    'define', '_find',
    'seed','outputfile','listfile','textmap','text','insert',
    'inesprg','ineschr','inesmir','inesmap','inesbattery','inesfourscreen',
    'inesworkram','inessaveram','ines2',
    'orgpad','quit','incchr','chr','setpalette','loadpalette',
    'rept','endr','endrept','nextrept',
]

filters = [
    'shuffle','getbyte','getword','choose',
    'format','random','range','textmap',
    'evalvar',
]

asm=[
Map(opcode = 'adc', mode = 'Immediate', byte = 105, length = 2),
Map(opcode = 'adc', mode = 'Zero Page', byte = 101, length = 2),
Map(opcode = 'adc', mode = 'Zero Page, X', byte = 117, length = 2),
Map(opcode = 'adc', mode = 'Absolute', byte = 109, length = 3),
Map(opcode = 'adc', mode = 'Absolute, X', byte = 125, length = 3),
Map(opcode = 'adc', mode = 'Absolute, Y', byte = 121, length = 3),
Map(opcode = 'adc', mode = '(Indirect, X)', byte = 97, length = 2),
Map(opcode = 'adc', mode = '(Indirect), Y', byte = 113, length = 2),
Map(opcode = 'and', mode = 'Immediate', byte = 41, length = 2),
Map(opcode = 'and', mode = 'Zero Page', byte = 37, length = 2),
Map(opcode = 'and', mode = 'Zero Page, X', byte = 53, length = 2),
Map(opcode = 'and', mode = 'Absolute', byte = 45, length = 3),
Map(opcode = 'and', mode = 'Absolute, X', byte = 61, length = 3),
Map(opcode = 'and', mode = 'Absolute, Y', byte = 57, length = 3),
Map(opcode = 'and', mode = '(Indirect, X)', byte = 33, length = 2),
Map(opcode = 'and', mode = '(Indirect), Y', byte = 49, length = 2),
Map(opcode = 'asl', mode = 'Accumulator', byte = 10, length = 1),
Map(opcode = 'asl', mode = 'Zero Page', byte = 6, length = 2),
Map(opcode = 'asl', mode = 'Zero Page, X', byte = 22, length = 2),
Map(opcode = 'asl', mode = 'Absolute', byte = 14, length = 3),
Map(opcode = 'asl', mode = 'Absolute, X', byte = 30, length = 3),
Map(opcode = 'bcc', mode = 'Relative', byte = 144, length = 2),
Map(opcode = 'bcs', mode = 'Relative', byte = 176, length = 2),
Map(opcode = 'beq', mode = 'Relative', byte = 240, length = 2),
Map(opcode = 'bit', mode = 'Zero Page', byte = 36, length = 2),
Map(opcode = 'bit', mode = 'Absolute', byte = 44, length = 3),
Map(opcode = 'bmi', mode = 'Relative', byte = 48, length = 2),
Map(opcode = 'bne', mode = 'Relative', byte = 208, length = 2),
Map(opcode = 'bpl', mode = 'Relative', byte = 16, length = 2),
Map(opcode = 'brk', mode = 'Implied', byte = 0, length = 1),
Map(opcode = 'bvc', mode = 'Relative', byte = 80, length = 2),
Map(opcode = 'bvs', mode = 'Relative', byte = 112, length = 2),
Map(opcode = 'clc', mode = 'Implied', byte = 24, length = 1),
Map(opcode = 'cld', mode = 'Implied', byte = 216, length = 1),
Map(opcode = 'cli', mode = 'Implied', byte = 88, length = 1),
Map(opcode = 'clv', mode = 'Implied', byte = 184, length = 1),
Map(opcode = 'cmp', mode = 'Immediate', byte = 201, length = 2),
Map(opcode = 'cmp', mode = 'Zero Page', byte = 197, length = 2),
Map(opcode = 'cmp', mode = 'Zero Page, X', byte = 213, length = 2),
Map(opcode = 'cmp', mode = 'Absolute', byte = 205, length = 3),
Map(opcode = 'cmp', mode = 'Absolute, X', byte = 221, length = 3),
Map(opcode = 'cmp', mode = 'Absolute, Y', byte = 217, length = 3),
Map(opcode = 'cmp', mode = '(Indirect, X)', byte = 193, length = 2),
Map(opcode = 'cmp', mode = '(Indirect), Y', byte = 209, length = 2),
Map(opcode = 'cpx', mode = 'Immediate', byte = 224, length = 2),
Map(opcode = 'cpx', mode = 'Zero Page', byte = 228, length = 2),
Map(opcode = 'cpx', mode = 'Absolute', byte = 236, length = 3),
Map(opcode = 'cpy', mode = 'Immediate', byte = 192, length = 2),
Map(opcode = 'cpy', mode = 'Zero Page', byte = 196, length = 2),
Map(opcode = 'cpy', mode = 'Absolute', byte = 204, length = 3),
Map(opcode = 'dec', mode = 'Zero Page', byte = 198, length = 2),
Map(opcode = 'dec', mode = 'Zero Page, X', byte = 214, length = 2),
Map(opcode = 'dec', mode = 'Absolute', byte = 206, length = 3),
Map(opcode = 'dec', mode = 'Absolute, X', byte = 222, length = 3),
Map(opcode = 'dex', mode = 'Implied', byte = 202, length = 1),
Map(opcode = 'dey', mode = 'Implied', byte = 136, length = 1),
Map(opcode = 'eor', mode = 'Immediate', byte = 73, length = 2),
Map(opcode = 'eor', mode = 'Zero Page', byte = 69, length = 2),
Map(opcode = 'eor', mode = 'Zero Page, X', byte = 85, length = 2),
Map(opcode = 'eor', mode = 'Absolute', byte = 77, length = 3),
Map(opcode = 'eor', mode = 'Absolute, X', byte = 93, length = 3),
Map(opcode = 'eor', mode = 'Absolute, Y', byte = 89, length = 3),
Map(opcode = 'eor', mode = '(Indirect, X)', byte = 65, length = 2),
Map(opcode = 'eor', mode = '(Indirect), Y', byte = 81, length = 2),
Map(opcode = 'inc', mode = 'Zero Page', byte = 230, length = 2),
Map(opcode = 'inc', mode = 'Zero Page, X', byte = 246, length = 2),
Map(opcode = 'inc', mode = 'Absolute', byte = 238, length = 3),
Map(opcode = 'inc', mode = 'Absolute, X', byte = 254, length = 3),
Map(opcode = 'inx', mode = 'Implied', byte = 232, length = 1),
Map(opcode = 'iny', mode = 'Implied', byte = 200, length = 1),
Map(opcode = 'jmp', mode = 'Indirect', byte = 108, length = 3),
Map(opcode = 'jmp', mode = 'Absolute', byte = 76, length = 3),
Map(opcode = 'jsr', mode = 'Absolute', byte = 32, length = 3),
Map(opcode = 'lda', mode = 'Immediate', byte = 169, length = 2),
Map(opcode = 'lda', mode = 'Zero Page', byte = 165, length = 2),
Map(opcode = 'lda', mode = 'Zero Page, X', byte = 181, length = 2),
Map(opcode = 'lda', mode = 'Absolute', byte = 173, length = 3),
Map(opcode = 'lda', mode = 'Absolute, X', byte = 189, length = 3),
Map(opcode = 'lda', mode = 'Absolute, Y', byte = 185, length = 3),
Map(opcode = 'lda', mode = '(Indirect, X)', byte = 161, length = 2),
Map(opcode = 'lda', mode = '(Indirect), Y', byte = 177, length = 2),
Map(opcode = 'ldx', mode = 'Zero Page', byte = 166, length = 2),
Map(opcode = 'ldx', mode = 'Zero Page, Y', byte = 182, length = 2),
Map(opcode = 'ldx', mode = 'Absolute', byte = 174, length = 3),
Map(opcode = 'ldx', mode = 'Absolute, Y', byte = 190, length = 3),
Map(opcode = 'ldx', mode = 'Immediate', byte = 162, length = 2),
Map(opcode = 'ldy', mode = 'Immediate', byte = 160, length = 2),
Map(opcode = 'ldy', mode = 'Zero Page', byte = 164, length = 2),
Map(opcode = 'ldy', mode = 'Zero Page, X', byte = 180, length = 2),
Map(opcode = 'ldy', mode = 'Absolute', byte = 172, length = 3),
Map(opcode = 'ldy', mode = 'Absolute, X', byte = 188, length = 3),
Map(opcode = 'lsr', mode = 'Accumulator', byte = 74, length = 1),
Map(opcode = 'lsr', mode = 'Zero Page', byte = 70, length = 2),
Map(opcode = 'lsr', mode = 'Zero Page, X', byte = 86, length = 2),
Map(opcode = 'lsr', mode = 'Absolute', byte = 78, length = 3),
Map(opcode = 'lsr', mode = 'Absolute, X', byte = 94, length = 3),
Map(opcode = 'nop', mode = 'Implied', byte = 234, length = 1),
Map(opcode = 'ora', mode = 'Immediate', byte = 9, length = 2),
Map(opcode = 'ora', mode = 'Zero Page', byte = 5, length = 2),
Map(opcode = 'ora', mode = 'Zero Page, X', byte = 21, length = 2),
Map(opcode = 'ora', mode = 'Absolute', byte = 13, length = 3),
Map(opcode = 'ora', mode = 'Absolute, X', byte = 29, length = 3),
Map(opcode = 'ora', mode = 'Absolute, Y', byte = 25, length = 3),
Map(opcode = 'ora', mode = '(Indirect, X)', byte = 1, length = 2),
Map(opcode = 'ora', mode = '(Indirect), Y', byte = 17, length = 2),
Map(opcode = 'pha', mode = 'Implied', byte = 72, length = 1),
Map(opcode = 'php', mode = 'Implied', byte = 8, length = 1),
Map(opcode = 'pla', mode = 'Implied', byte = 104, length = 1),
Map(opcode = 'plp', mode = 'Implied', byte = 40, length = 1),
Map(opcode = 'rol', mode = 'Accumulator', byte = 42, length = 1),
Map(opcode = 'rol', mode = 'Zero Page', byte = 38, length = 2),
Map(opcode = 'rol', mode = 'Zero Page, X', byte = 54, length = 2),
Map(opcode = 'rol', mode = 'Absolute', byte = 46, length = 3),
Map(opcode = 'rol', mode = 'Absolute, X', byte = 62, length = 3),
Map(opcode = 'ror', mode = 'Accumulator', byte = 106, length = 1),
Map(opcode = 'ror', mode = 'Zero Page', byte = 102, length = 2),
Map(opcode = 'ror', mode = 'Zero Page, X', byte = 118, length = 2),
Map(opcode = 'ror', mode = 'Absolute', byte = 110, length = 3),
Map(opcode = 'ror', mode = 'Absolute, X', byte = 126, length = 3),
Map(opcode = 'rti', mode = 'Implied', byte = 64, length = 1),
Map(opcode = 'rts', mode = 'Implied', byte = 96, length = 1),
Map(opcode = 'sbc', mode = 'Immediate', byte = 233, length = 2),
Map(opcode = 'sbc', mode = 'Zero Page', byte = 229, length = 2),
Map(opcode = 'sbc', mode = 'Zero Page, X', byte = 245, length = 2),
Map(opcode = 'sbc', mode = 'Absolute', byte = 237, length = 3),
Map(opcode = 'sbc', mode = 'Absolute, X', byte = 253, length = 3),
Map(opcode = 'sbc', mode = 'Absolute, Y', byte = 249, length = 3),
Map(opcode = 'sbc', mode = '(Indirect, X)', byte = 225, length = 2),
Map(opcode = 'sbc', mode = '(Indirect), Y', byte = 241, length = 2),
Map(opcode = 'sec', mode = 'Implied', byte = 56, length = 1),
Map(opcode = 'sed', mode = 'Implied', byte = 248, length = 1),
Map(opcode = 'sei', mode = 'Implied', byte = 120, length = 1),
Map(opcode = 'sta', mode = 'Zero Page', byte = 133, length = 2),
Map(opcode = 'sta', mode = 'Zero Page, X', byte = 149, length = 2),
Map(opcode = 'sta', mode = 'Absolute', byte = 141, length = 3),
Map(opcode = 'sta', mode = 'Absolute, X', byte = 157, length = 3),
Map(opcode = 'sta', mode = 'Absolute, Y', byte = 153, length = 3),
Map(opcode = 'sta', mode = '(Indirect, X)', byte = 129, length = 2),
Map(opcode = 'sta', mode = '(Indirect), Y', byte = 145, length = 2),
Map(opcode = 'stx', mode = 'Zero Page', byte = 134, length = 2),
Map(opcode = 'stx', mode = 'Zero Page, Y', byte = 150, length = 2),
Map(opcode = 'stx', mode = 'Absolute', byte = 142, length = 3),
Map(opcode = 'sty', mode = 'Zero Page', byte = 132, length = 2),
Map(opcode = 'sty', mode = 'Zero Page, X', byte = 148, length = 2),
Map(opcode = 'sty', mode = 'Absolute', byte = 140, length = 3),
Map(opcode = 'tax', mode = 'Implied', byte = 170, length = 1),
Map(opcode = 'tay', mode = 'Implied', byte = 168, length = 1),
Map(opcode = 'tsx', mode = 'Implied', byte = 186, length = 1),
Map(opcode = 'txa', mode = 'Implied', byte = 138, length = 1),
Map(opcode = 'txs', mode = 'Implied', byte = 154, length = 1),
Map(opcode = 'tya', mode = 'Implied', byte = 152, length = 1),
]

architectures = ['nes.cpu','6502']

# Converting to dictionary removes duplicates
opcodes = list(dict.fromkeys([x.opcode for x in asm]))

opcodes2 = [
    'lda','ldx','ldy',
    'sta','stx','sty',
    'and','asl','bit','eor','lsr','ora','rol','ror',
    'adc','dec','dex','dey','inc','inx','iny','sbc',
    'cmp','cpx','cpy',
    'jmp',
]
opcodes2 = [x+'.b' for x in opcodes2]+[x+'.w' for x in opcodes2]


implied = [x.opcode for x in asm if x.mode=='Implied']
accumulator = [x.opcode for x in asm if x.mode=="Accumulator"]
ifDirectives = ['if','endif','else','elseif','ifdef','ifndef','iffileexist','iffile']

mergeList = lambda a,b: [(a[i], b[i]) for i in range(min(len(a),len(b)))]
makeHex = lambda x: '$'+x.to_bytes(((x.bit_length()|1  + 7) // 8),"big").hex()

specialSymbols = [
    'sdasm','bank','banksize','chrsize','randbyte','randword','fileoffset',
    'prgbanks','chrbanks','lastbank','lastchr','reptindex',
]

timeSymbols = ['year','month','day','hour','minute','second']

specialSymbols+= timeSymbols
specialSymbols+= [x.lower() for x in assembler.nesRegisters.keys()]

def assemble(filename, outputFilename = 'output.bin', listFilename = False, configFile=False, fileData=False, binFile=False):
    if not configFile:
        configFile = inScriptFolder('config.ini')
    
    cfg = False
    # create our config parser
    cfg = Cfg(configFile)

    # read config file if it exists
    cfg.load()
    
    # number of bytes to show when generating list
    cfg.setDefault('main', 'list_nBytes', 8)
    cfg.setDefault('main', 'comment', ';,//')
    cfg.setDefault('main', 'commentBlockOpen', '/*')
    cfg.setDefault('main', 'commentBlockClose', '*/')
    cfg.setDefault('main', 'nestedComments', True)
    cfg.setDefault('main', 'fillValue', '$00')
    cfg.setDefault('main', 'localPrefix', '@')
    cfg.setDefault('main', 'debug', False)
    cfg.setDefault('main', 'varOpen', '{')
    cfg.setDefault('main', 'varClose', '}')
    cfg.setDefault('main', 'labelSuffix', ':')
    cfg.setDefault('main', 'orgPad', 0)
    cfg.setDefault('main', 'mapdb', False)
    cfg.setDefault('main', 'lineSep', '')
    cfg.setDefault('main', 'clampdb', False)
    cfg.setDefault('main', 'caseSensitive', False)

    # save configuration so our defaults can be changed
    cfg.save()
    
    assembler.cfg = cfg

    _assemble(filename, outputFilename, listFilename, cfg=cfg, fileData=fileData, binFile=binFile)

def _assemble(filename, outputFilename, listFilename, cfg, fileData, binFile):
    
    def bytesForNumber(n):
        if type(n) is int:
            l = len(hex(n))-1 >>1
        elif type(n) is str:
            l = len(n)
        elif type(n) is list:
            l = len(n)
        
        return l
    def getValueAsString(s):
        try:
            return getString(getValue(s))
        except:
            return False
    
    def getString(s, strip=True):
        if type(s) is int:
            return False
        
        if type(s) is list:
            s = bytes(s).decode()
        
        if strip:
            s=s.strip()
        
        for q in assembler.quotes:
            #if s.startswith(q) and s.endswith(q):
            if s.strip().startswith(q) and s.strip().endswith(q):
                s=s.strip()
                s=s[len(q):-len(q)]
                return s
        return s
    
    def getSpecial(s):
        if s == 'sdasm':
            v = 1
        elif s == 'bank':
            if bank == None:
                return ''
            else:
                return makeHex(bank)
        elif s == 'banksize':
            if bank == None:
                return ''
            else:
                return str(bankSize)
        elif s == 'chrsize':
            return str(chrSize)
        elif s == 'prgbanks':
            return str(out[4])
        elif s == 'lastbank':
            return str(out[4]-1)
        elif s == 'chrbanks' or s == 'lastchr':
            return str(out[5])
        elif s == 'fileoffset':
            if bank != None:
                return str(addr + bank * bankSize + headerSize)
            else:
                #return str(addr + headerSize)
                return str(addr)
        elif s == 'randbyte':
            return makeHex(random.randrange(0x100))
        elif s == 'randword':
            #return makeHex(random.randrange(0x10000))
            return '${:04x}'.format(random.randrange(0x10000))
        elif s == 'reptindex':
            return str(rept.index)
        elif s in timeSymbols:
            v = list(datetime.now().timetuple())[timeSymbols.index(s)]
        elif s in assembler.nesRegisters:
            v = assembler.nesRegisters[s]
            return '${:04x}'.format(v)
        else:
            v = 0
            l = 1
        if type(v) in (int,float):
            return makeHex(v)
        else:
            return v
    def findFile(filename):
        return assembler.findFile(filename)
    
    def makeList(item):
        if type(item)!=list:
            return flattenList([item])
        else:
            return flattenList(item)
    
    def isImmediate(v):
        if v.startswith("#"):
            return True
        else:
            return False

    def isNumber(v):
        return all([x in "0123456789" for x in str(v)])
    
    def splitNumber(v):
        i = ([x in '0123456789' for x in v]+[False]).index(False)
        if i == len(v):
            return [v]
        else:
            return [v[:i], v[i:]]

    def getValueAndLength(v, mode=False, param=False, hint=False):
        assembler.errorHint = False
        if type(v) is int:
            l = 1 if v <=256 else 2
            return v,l
        
        if mode == 'choose':
            v = v.split(',')
            random.shuffle(v)
            v=v[0]
            l=1
            return v,l
        
        if mode == 'range':
            v=v.split(',')
            v = [getValue(x) for x in v]
            if len(v) == 1:
                v[0]+=1
            elif len(v) == 2:
                v[1]+=1
            elif len(v) == 3:
                v[1]+=v[2]
            
            v = list(range(*v))
            l = len(v)
            return v,l
        if mode == 'evalvar':
            print(v)
            v,l = getValueAndLength(v)
            return v,l
        if mode == 'random':
            v=v.split(',',1)
            r1 = getValue(v[0])
            if len(v) == 2:
                r2 = getValue(v[1])
            else:
                r2 = None
            v = random.randrange(r1,r2)
            l = 1
            return v,l
        
        if v.startswith("[") and v.endswith("]"):
            v = v[1:-1]
        
        v = v.strip()
        l = False
        
        vToken = assembler.tokenize(v)
        
        #v = v.replace(", ",",").replace(" ,",",")
        if v.startswith("(") and v.endswith(")"):
            v = v[1:-1]
        
        if vToken[-1] in ('x','y','X','Y'):
            vToken = vToken[:-1]
            v = ', '.join(vToken)
        
#        if v.endswith(",x"):
#            v = v.split(",x")[0]
#        if v.endswith(",y"):
#            v = v.split(",y")[0]
        if v.startswith("(") and v.endswith(")"):
            v = v[1:-1]
        if '(' in v and ')' in v:
            result = re.findall('\(([^\(].*?)\)', v)
            if result:
                for item in result:
                    item = '('+item+')'
                    v = v.replace(item, str(getValue(item)))
        if v=='':
            return 0,0
        
        # this will handle comma separated lists
        vToken = assembler.tokenize(v)
        #if len(assembler.tokenize(v)) > 1:
        if len(vToken) > 1:
            v = [getValue(x) for x in vToken]
            l = len(v)
            if mode == 'shuffle':
                random.shuffle(v)
            elif mode == 'choose':
                random.shuffle(v)
                v=v[0]
                l=1
            return v,l
        
        if v.startswith(assembler.quotes) and v.endswith(assembler.quotes):
            if mode == 'textmap':
                v = assembler.mapText(assembler.stripQuotes(v))
            else:
                v = list(bytes(assembler.stripQuotes(v), 'utf-8'))
            l=len(v)
            return v, l
        
#        if ',' in v:
#            v = [getValue(x) for x in v.split(',')]
#            l = len(v)
#            if mode == 'shuffle':
#                random.shuffle(v)
#            elif mode == 'choose':
#                random.shuffle(v)
#                v=v[0]
#                l=1
                
#            return v,l
        if v.startswith('-'):
            label = v.split(' ',1)[0]
            if len(aLabels) > 0:
                foundAddresses = [x[1] for x in aLabels if x[0]==label and x[1]<currentAddress]
                if len(foundAddresses) !=0:
                    return foundAddresses[-1], 2
            # negative number?
            return int(v), 0
        if v.startswith('+'):
            label = v.split(' ',1)[0]
            try:
                return [x[1] for x in aLabels if x[0]==label and x[1]>=currentAddress][0], 2
            except:
                return 0,0
        
#        if v.startswith('"') and '"' in v[1:]:
            # Check for a comma after closing quotes
#            quotePos = v.find('"', 1)
#            if quotePos!=-1 and quotePos==len(v)-1:
#                print(v)
#                print('*'*20)
                # string starts and ends with quotes
#                v = list(bytes(v[1:-1], 'utf-8'))
#                l=len(v)
#                return v, l
            
#            commaPos = v.find(',',quotePos)
            
#            l,r = False, False
#            if commaPos == -1:
                # No comma found
#                l = v[1:quotePos]
#                r = v[quotePos+1:]

#                v = list(bytes(l, 'utf-8'))
#                r = getValue(r)
                
#                print('l=',l,'r=',r)

#            else:
                # comma found
#                l = v[1:commaPos]
#                r = v[commaPos+1:]
                

#        if v.startswith('"') and v.endswith('"'):
#            if mode == 'textmap':
#                v = assembler.mapText(v[1:-1])
#            else:
#                v = list(bytes(v[1:-1], 'utf-8'))
#            l=len(v)
#            return v, l
        # ToDo: tokenize, allow (), implement proper order of operations.
        if '+' in v:
            v = v.split('+')
            left, right = getValue(v[0]), getValue(v[1])
            if type(left)==type(right):
                v = left + right
            elif type(left)==list:
                v = [x+right for x in left]
                return v,len(v)
            else:
                return 0, 1
            l = 1 if v <=256 else 2
            return v,l
        if '-' in v:
            v = v.split('-')
            left, right = getValue(v[0]), getValue(v[1])
            if type(left)==type(right):
                v = left - right
            elif type(left)==list:
                v = [x-right for x in left]
                return v,len(v)
            else:
                return 0, 1
            l = 1 if v <=256 else 2
            return v,l
        
        if v.startswith("<"):
            v = getValue(v[1:]) % 0x100
            l = 1
            return v,l
        if v.startswith(">"):
            v = getValue(v[1:]) >> 8
            l = 1
            return v,l
        
        if v == '$' or v.lower() == 'pc':
            v = currentAddress
            l=2
        elif v.lower() == 'randbyte':
            v = random.randrange(0,256)
            l=1
#        elif v.startswith('$'):
#            v = int(v[1:],16)
#            l = bytesForNumber(v)
#        elif v.startswith('%'):
#            l = 1
#            v = int(v[1:],2)
        elif v.startswith('%'):
            # do this to avoid clogging things up with operations below
            v = '_0b_'+v[1:]
            v = getValue(v)
            l = 1
            return v,l
        elif any(x in v for x in operations):
            for op in operations:
                if op in v:
                    v = v.split(op)
                    
                    v0 = getValue(v[0], mode)
                    v1 = getValue(v[1])
                    
                    if type(v0) is list:
                        v = [operations[op](x, v1) for x in v0]
                        l = len(v)
                    else:
                        v = operations[op](v0, v1)
                        l = 1 if v <=256 else 2
                    #v = operations[op](getValue(v[0]), getValue(v[1]))
                    #l = 1 if v <=256 else 2
                    return v,l
        elif v.startswith('$'):
            v = int(v[1:],16)
            l = bytesForNumber(v)
        elif v.startswith('_0b_'):
            l = 1
            v = int(v[4:],2)
        elif v.startswith('%'):
            l = 1
            v = int(v[1:],2)
        elif isNumber(v):
            l = 1 if int(v,10) <=256 else 2
            v = int(v,10)
        elif assembler.lower(v) in symbols:
            v, l = getValueAndLength(symbols[assembler.lower(v)])
        elif v.lower() in specialSymbols:
            v, l = getValueAndLength(getSpecial(v.lower()))
        else:
            if passNum==2:
                #errorText= 'invalid value: {}'.format(v)
                #print('*** '+errorText)
                pass
            assembler.errorHint = "invalid value"
            v = 0
            l = -1
        
        if mode == 'textmap':
            v = assembler.mapText(bytearray(makeList(v)).decode('utf8'))
            l = len(v)
        
        if mode == 'getbyte':
            # this looks like the right result but i don't know why
            # i have to subtract the 0x4000
            if bank != None:
                fileOffset = v - 0x8000 + (bank * bankSize) + headerSize - 0x4000
            else:
                fileOffset = v - 0x8000 + headerSize - 0x4000
            v = int(out[fileOffset])
            l = 1
        if mode == 'getword':
            if bank != None:
                fileOffset = v - 0x8000 + (bank * bankSize) + headerSize - 0x4000
            else:
                fileOffset = v - 0x8000 + headerSize - 0x4000
            v = int(out[fileOffset]) + int(out[fileOffset+1]) * 0x100
            l = 2
        
        return v, l

    def getValue(v, mode=False, param=False, hint=False):
        return getValueAndLength(v, mode=mode, param=param, hint=hint)[0]
    def getLength(v, mode=False, param=False, hint=False):
        return getValueAndLength(v, mode=mode, param=param, hint=hint)[1]

    def getOpWithMode(opcode,mode):
        ops = [x for x in asm if x.opcode==opcode]
        if mode in [x.mode for x in ops]:
            return [x for x in ops if x.mode==mode][0]
        else:
            return False

    try:
        file = open(filename, "r")
    except:
        print("Error: could not open file.")
        exit()
    
    print('sdasm {} by {}\n{}'.format(version.get('version'), version.get('author'), version.get('url')))
    print(dedent("""
    ------------------------------------------------------------
    WARNING: This project is currently in {} stage.
    Some features may be incomplete, have bugs, or change.
    ------------------------------------------------------------
    """.format(version.get('stage'))))
    print('assembling {}'.format(filename))
    
    assembler.initialFolder = os.path.split(filename)[0]
    assembler.currentFolder = assembler.initialFolder

    # Doing it this way removes the line endings
    lines = file.read().splitlines()
    originalLines = lines

    symbols = Map()
    equ = Map()
    
    # Allow lda.b, lda.w, etc.
    # It wont set the byte size but this is better than nothing.
#    def alias(opcode):
#        equ[opcode+'.b']=opcode
#        equ[opcode+'.w']=opcode
    
#    for o in opcodes:
#        alias(o)
    
    aLabels = []
    lLabels = []
    macros = Map()
    blockComment = 0
    
    if binFile:
        filename = assembler.findFile(binFile)
        if filename:
            try:
                with open(filename,'rb') as file:
                    fileData = file.read()
            except:
                print("Could not load file: {}".format(filename))
                return
        else:
            print("Could not find file: {}".format(binFile))
            return
    for passNum in (1,2):
        commentSep = makeList(cfg.getValue('main', 'comment'))
        commentBlockOpen = makeList(cfg.getValue('main', 'commentBlockOpen'))
        commentBlockClose = makeList(cfg.getValue('main', 'commentBlockClose'))
        fillValue = getValue(cfg.getValue('main', 'fillValue'))
        localPrefix = makeList(cfg.getValue('main', 'localPrefix'))
        debug = cfg.isTrue(cfg.getValue('main', 'debug'))
        varOpen = makeList(cfg.getValue('main', 'varOpen'))
        varClose = makeList(cfg.getValue('main', 'varClose'))
        varOpenClose = mergeList(varOpen,varClose)
        labelSuffix = makeList(cfg.getValue('main', 'labelSuffix'))
        orgPad = int(cfg.getValue('main', 'orgPad'))
        mapdb = cfg.isTrue(cfg.getValue('main', 'mapdb'))
        clampdb = cfg.isTrue(cfg.getValue('main', 'clampdb'))
        lineSep = makeList(cfg.getValue('main', 'linesep'))
        caseSensitive = cfg.isTrue(cfg.getValue('main', 'caseSensitive'))
        lineSep = [x for x in lineSep if x != '']
        
        lines = originalLines
        
#        if lineSep:
#            for s in lineSep:
#                lines = [l.split(s) for l in lines]
#            lines = flattenList(lines)
        
        addr = 0
        oldAddr = 0
        
        noOutput = False
        
        macro = False
        currentAddress = 0
        mode = ""
        showAddress = False
        out = []
        
        if type(fileData) != bool:
            out = list(fileData)
        
        if np:
            out = np.array([],dtype="B")
        
        outputText = ''

        outputText+= 'Assembled with sdasm\n'
        outputText+= '{1}{0}{1}{0}{2}{0}{3}\n'.format(' ', '_'*5, '_'*25, '_'*40)
        outputText+= '{1:5}{0}{2:5}{0}{3:25}{0}{4}\n'.format('|','file','prg',' bytes',' asm code')
        outputText+= '{1:5}{0}{2:5}{0}{3:25}{0}{4}\n'.format('|','offst','addr','','')
        outputText+= '{1}{0}{1}{0}{2}{0}{3}\n'.format('|', '-'*5, '-'*25, '-'*40)

        startAddress = False
#        assembler.currentFolder = ''
#        assembler.currentFolder = os.path.split(filename)[0]
        assembler.currentFolder = assembler.initialFolder
        ifLevel = 0
        ifData = Map()
        arch = 'nes.cpu'
        headerSize = 0
        bankSize = 0x10000
        chrSize = 0x2000
        bank = None
        rept = Map()
        rept.status = False
        rept.block = []
        rept.count = 0
        rept.index = 0
        rept.depth = 0
        
        assembler.clearTextMap(all=True)
        
        fileList = []
        print('pass {}...'.format(passNum))
        
        for i in range(10000000):
            if i>len(lines)-1:
                break
            line = lines[i]
            
            hide = False
            
            #currentAddress = addr
            originalLine = line
            errorText = False
            assembler.errorLinePos = False
            
            
            lineTime = time.time()
            
            #print(originalLine)
            
            # change tabs to spaces
            line = line.replace("\t"," ")
            
            # remove single line comments
            for sep in commentSep:
                line = line.strip().split(sep,1)[0].strip()
            
            # remove comment blocks
            for sep in commentBlockOpen:
                if sep in line:
                    line = line.strip().split(sep,1)[0].strip()
                    blockComment+=1
            for sep in commentBlockClose:
                if sep in line:
                    line = line.strip().split(sep,1)[1].strip()
                    blockComment-=1
                    if cfg.isFalse(cfg.getValue('main', 'nestedComments')):
                        blockComment = 0
            if blockComment>0:
                line = ''
            
            # used to help hide internal directive lines
            if line.startswith(assembler.hidePrefix):
                line = line.split(assembler.hidePrefix,1)[1]
                assembler.hideOutputLine = True
            
            if rept.status == 'gather':
                k = line.split(" ",1)[0].strip()
                if k in ('endr','endrept'):
                    pass
                else:
                    rept.block.append(line)
                    line = ''
                
            if lineSep:
                line = [line]
                for s in lineSep:
                    line = flattenList([l.split(s) for l in line])
            
                if len(line) > 1:
                    #print(line)
                    lines = lines[:i]+['']+line[1:]+lines[i+1:]
                line = line[0]
            
            # "EQU" replacement
            for item in equ:
                line = line.replace(item, equ[item])
            
            # {var} replacement
            for o,c in varOpenClose:
                if o in line and c in line:
                    while o+":" in line:
                        start = line.find('{:')
                        end = line.find('}', start)
                        
                        line = line.replace(line[start:end+1], str(getValue(line[start+2:end])))
                    
                    for item in specialSymbols:
                        if o+item+c in line:
                            s = getSpecial(item)
                            line = line.replace(o+item+c, s)
                    
                    for item in filters:
                        while o+item+":" in line:
                            start = line.find('{'+item+':')
                            end = line.find('}', start)
                            
                            if item == 'format':
                                fmtStart = line.find(':',start)+1
                                fmtEnd = line.find(':',fmtStart)
                                fmtString = '{:' + line[fmtStart:fmtEnd] + '}'
                                l = getValue(line[fmtEnd+1:end])
                                l = fmtString.format(l)
                            else:
                                l = getValue(line[start+2+len(item):end], mode=item)
                            
                            if type(l) is int:
                                l = str(l)
                            elif type(l) is list:
                                l = ','.join([str(x) for x in l])
                            line = line.replace(line[start:end+1], l)
                    
                    while o in line:
                        start = line.find(o)
                        end = line.find(c, start)
                        
                        line = line.replace(line[start:end+1], str(getValue(line[start+1:end])))
            
            if ifLevel:
                if ifLevel>1 and ifData[ifLevel-1].bool == False:
                    ifData[ifLevel].bool = False
                    ifData[ifLevel].done = True

                if ifData[ifLevel].bool == False:
                    
                    key = line.split(" ",1)[0].strip().lower()
                    if key.startswith('.'):
                        key = key[1:]
                    
                    if key not in ifDirectives:
                        ifData.line = line
                        line = ''
            
            if macro:
                if line.split(" ",1)[0].strip().lower() not in ['endm','endmacro','.endm','.endmacro']:
                    macros[macro].lines.append(originalLine)
                    line = ''
            
            b=[]
            k0 = line.split(" ",1)[0].strip()
            k = k0.lower()
            
            if k!='' and (k=="-"*len(k) or k=="+"*len(k)):
                if not [k,currentAddress] in aLabels:
                    aLabels.append([k, currentAddress])
                    
                    # update so rest of line can be processed
                    line = (line.split(" ",1)+[''])[1].strip()
                    k0 = line.split(" ",1)[0].strip()
                    k = k0.lower()
            
            # This is really complicated but we have to check to see
            # if this is a label without a suffix somehow.
            if k!='' and not (k.startswith('.') and k[1:] in directives) and not k.endswith(tuple(labelSuffix)) and ' equ ' not in line.lower() and '=' not in line and k not in list(directives)+list(macros)+list(opcodes)+opcodes2:
                if k.startswith('-') or k.startswith('+'):
                    aLabels.append([assembler.lower(k0), currentAddress])
                else:
                    if debug: print('label without suffix: {}'.format(k))
                    k += labelSuffix[0]
                    k0 += labelSuffix[0]
            if k.endswith(tuple(labelSuffix)):
                if k.startswith('-') or k.startswith('+'):
                    aLabels.append([k0[:-1], currentAddress])
                else:
                    symbols[assembler.namespace + assembler.lower(k0[:-1])] = str(currentAddress)
                    
                    # remove all local labels
                    if not k.startswith(tuple(localPrefix)):
                        symbols = {k:v for (k,v) in symbols.items() if not k.startswith(tuple(localPrefix))}
                    
                    # update so rest of line can be processed
                    line = (line.split(" ",1)+[''])[1].strip()
                    k = line.split(" ",1)[0].strip().lower()
            
            # prefix is optional for valid directives
            if k.startswith(".") and k[1:] in directives:
                k=k[1:]
            
            if k == 'ifdef':
                ifLevel+=1
                ifData[ifLevel] = Map()
                
                data = line.split(" ",1)[1].strip().replace('==','=')
                if assembler.lower(data) in symbols:
                    ifData[ifLevel].bool = True
                    ifData[ifLevel].done = True
                else:
                    ifData[ifLevel].bool = False
            elif k == 'ifndef':
                ifLevel+=1
                ifData[ifLevel] = Map()
                
                data = line.split(" ",1)[1].strip().replace('==','=')
                
                if assembler.lower(data) in symbols:
                    ifData[ifLevel].bool = False
                else:
                    ifData[ifLevel].bool = True
                    ifData[ifLevel].done = True
            elif k == 'elseif':
                if ifData[ifLevel].done:
                    ifData[ifLevel].bool=False
                else:
                    k = 'if'
            elif k == 'iffileexist' or k == 'iffile':
                ifLevel+=1
                ifData[ifLevel] = Map()
                
                data = line.split(" ",1)[1].strip()
                data = getString(data)
                if assembler.findFile(data):
                    ifData[ifLevel].bool = True
                    ifData[ifLevel].done = True
                else:
                    ifData[ifLevel].bool = False
            if k == 'if':
                ifLevel+=1
                ifData[ifLevel] = Map()
                
                inv = False
                data = line.split(" ",1)[1].strip().replace('==','=')
                if data.split(" ")[0].strip().lower() == 'not':
                    data = data.split(' ',1)[1]
                    inv = True
                
                if '=' in data:
                    l,r = data.split('=')
                    if ((getValue(l) == getValue(r)) and inv == False) or ((getValue(l) != getValue(r)) and inv == True):
                        ifData[ifLevel].bool = True
                        ifData[ifLevel].done = True
                    else:
                        ifData[ifLevel].bool = False
                else:
                    if (getValue(data) and inv==False) or (not getValue(data) and inv==True):
                        ifData[ifLevel].bool = True
                        ifData[ifLevel].done = True
                    else:
                        ifData[ifLevel].bool = False
#                if inv:
#                    ifData[ifLevel].bool = not ifData[ifLevel].done
            if k == 'else':
                ifData[ifLevel].bool = not ifData[ifLevel].done
            elif k == 'endif':
                ifLevel-=1
            elif k == 'arch':
                arch = line.split(" ")[1].strip()
                if arch.lower() not in architectures:
                    errorText = 'invalid architecture'
                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
#                if debug:
#                    print('  Architecture: {}'.format(arch))
            elif k == 'noheader':
                headerSize = 0
                assembler.stripHeader = False
            elif k == 'header':
                headerSize = 16
                assembler.stripHeader = False
            elif k == 'stripheader':
                headerSize = 16
                assembler.stripHeader = True
            elif k == 'banksize':
                bankSize = getValue(line.split(" ")[1].strip())
            elif k == 'chrsize':
                chrSize = getValue(line.split(" ")[1].strip())
            elif k == 'bank':
                v = line.split(" ")[1].strip()
                bank = getValue(v)

                # bank resets
                currentAddress = 0x8000
                addr = bank * bankSize
            elif k == 'chr':
                v = getValue(line.split(" ")[1].strip())
                
                bank = int((getValue('prgbanks') * 0x4000) / bankSize)
                
                # bank resets
                currentAddress = chrSize*v
                addr = chrSize*v
            elif k == 'setpalette':
                v = getValue(line.split(" ",1)[1].strip())
                assembler.currentPalette = v
            elif k == 'quit':
                v = (line.split(" ",1)[1:]+[''])[0]
                print('*** quit ***\n{}\n'.format(v))
                return
            elif k == 'inesprg':
                out[4] = getValue(line.split(" ")[1].strip())
                print('setting prg to ',out[4])
            elif k == 'ineschr':
                out[5] = getValue(line.split(" ")[1].strip())
            elif k == 'inesmir':
                v = getValue(line.split(" ")[1].strip())
                out[6] = (out[6] & 0xfe) | v
            elif k == 'inesbattery':
                v = getValue(line.split(" ")[1].strip())
                out[6] = (out[6] & 0xfd) | v<<1
            elif k == 'ines2':
                v = getValue(line.split(" ")[1].strip())
                out[7] = (out[7] & 0xf3) | v<<3
            elif k == 'inesworkram':
                v = getValue(line.split(" ")[1].strip())
                out[10] = (out[10] & 0xf0) | v
            elif k == 'inessaveram':
                v = getValue(line.split(" ")[1].strip())
                out[10] = (out[10] & 0x0f) | v<<4
            elif k == 'inesfourscreen':
                v = getValue(line.split(" ")[1].strip())
                out[6] = (out[6] & 0xf7) | v<<3
            elif k == 'inesmap':
                v = getValue(line.split(" ")[1].strip())
                out[6] = (out[6] & 0x0f) | (v & 0x0f)<<4
                out[7] = (out[7] & 0x0f) | (v & 0xf0)
            elif k == 'orgpad':
                orgPad = getValue(line.split(" ")[1].strip())
            elif k == 'insert':
                v = getValue(line.split(" ", 1)[1].strip())
                fileOffset = addr + bank * bankSize + headerSize
                
                fv = fillValue
                
                out = out[:fileOffset]+([fv] * v)+out[fileOffset:]
                
                print('insert', v, 'bytes.')
            elif k == 'seed':
                v = getValue(line.split(" ")[1].strip())
                random.seed(v)
            elif k == 'cleartable':
                assembler.clearTextMap()
            elif k == 'textmap':
                data = line.split(' ',1)[1]
                
                if data.lower() == 'clear':
                    assembler.clearTextMap()
                else:
                    data = data.split()
                    if data[0].lower() == 'space':
                        data[0] = ' '
                    elif '...' in data[0]:
                        c1,c2 = data[0].split('...')
                        data[0] = ''.join([chr(c) for c in range(ord(c1), ord(c2)+1)])
                        
                        n1 = int(data[1],16)
                        data[1] = ''.join(['{:02x}'.format(x) for x in range(n1,n1+len(data[0]))])
                    
                    if data[0].lower() == 'set':
                        assembler.setTextMap(data[1])
                    else:
                        assembler.setTextMapData(data[0], data[1])
            elif k == 'outputfile':
                outputFilename = getValueAsString(line.split(" ",1)[1].strip())
            elif k == 'listfile':
                listFilename = getValueAsString(line.split(" ",1)[1].strip())
                
                if listFilename.lower() in ('false','0','none', ''):
                    listFilename = False
            
            # hidden internally used directive used with include paths
            if k == "setincludefolder":
                assembler.currentFolder = (line.split(" ",1)+[''])[1].strip()
                hide = True
            
            elif k=='loadtable' or k == 'table':
                l = line.split(" ",1)[1].strip()
                l = l.split(',',1)
                if len(l)==2:
                    pass
                filename = getValueAsString(l[0]) or getString(l[0])
                if not assembler.loadTbl(filename):
                    errorText = assembler.errorHint or 'file not found'
                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
            elif k == 'loadpalette':
                if len(line.split(" ",1))==1:
                    # load default palette
                    assembler.loadPalette()
                else:
                    filename = line.split(" ",1)[1].strip()
                    filename = getValueAsString(filename) or getString(filename)
                    filename = assembler.findFile(filename)
                    if filename:
                        if not assembler.loadPalette(filename):
                            errorText = assembler.errorHint or 'file not found'
                            assembler.errorLinePos = len(line.split(' ',1)[0])+1
                    else:
                        errorText = 'file not found'
                        assembler.errorLinePos = len(line.split(' ',1)[0])+1
            elif k == 'incchr':
                if PIL:
                    x, y, rows, cols = False, False, False, False
                    filename = line.split(" ",1)[1].strip()
                    if ',' in filename:
                        arg = filename.split(',')[1:]
                        arg = [getValue(x) for x in arg]
                        if len(arg) == 4:
                            x,y,cols,rows = arg
                        if len(arg)==2:
                            cols,rows = arg
                        filename = filename.split(',')[0]
                        
                    filename = getString(filename)
                    filename = assembler.findFile(filename)
                    if filename:
                        colors = [assembler.palette[x] for x in assembler.currentPalette]
                        
                        chrData = imageToCHRData(filename, colors=colors, x=x,y=y,rows=rows, cols=cols)
                        b = b + chrData
                    else:
                        assembler.errorLinePos = len(line.split(' ',1)[0])+1
                        errorText = 'file not found'
                else:
                    errorText = 'PIL not available.'
            elif k == "incbin" or k == "bin":
                l = line.split(" ",1)[1].strip()
                
                offset = 0
                nBytes = -1
                if ',' in l:
                    l = l.split(',')
                    filename = l[0].strip()
                    offset = getValue(l[1])
                    if len(l)>2:
                        nBytes = getValue(l[2])
                    print("offset: ", offset)
                else:
                    filename = l
                
                filename = getString(filename)
                filename = assembler.findFile(filename)
                
                if filename:
                    b=False
                    try:
                        with open(filename, 'rb') as file:
                            file.seek(offset)
                            b = list(file.read(nBytes))
                    except:
                        print("Could not open file.")
                    if b:
                        fileList.append(filename)
                        lines = lines[:i]+['']+['setincludefolder '+assembler.currentFolder]+lines[i+1:]
                else:
                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
                    errorText = 'file not found'
            elif k == 'rept':
                rept.count = getValue(line.split(" ",1)[1].strip())
                rept.index = 0
                rept.block = []
                rept.status = 'gather'
                print('rept depth',rept.depth)
            elif k == 'nextrept':
                rept.index += 1
            elif k == 'endr':
                rept.block.append(assembler.hidePrefix + 'nextrept')
                
                lines = lines[:i]+['']+ rept.block * rept.count + lines[i+1:]
                
                rept.block = []
                rept.status = False
            elif k == 'include' or k=='incsrc':
                filename = line.split(" ",1)[1].strip()
                filename = getString(filename)
                filename = assembler.findFile(filename)
                if filename:
                    #print(filename)
                    newLines = False
                    try:
                        with open(filename, 'r') as file:
                            newLines = file.read().splitlines()
                    except:
                        print("Could not open file.")
                    
                    if newLines:
                        fileList.append(filename)
                        folder = os.path.split(filename)[0]
                        
#                        if lineSep:
#                            for s in lineSep:
#                                newLines = [l.split(s) for l in newLines]
#                            newLines = flattenList(newLines)
                        
                        newLines = ['setincludefolder '+folder]+newLines+['setincludefolder '+assembler.currentFolder]
                        assembler.currentFolder = folder
                        
                        lines = lines[:i]+['']+newLines+lines[i+1:]
                else:
                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
                    errorText = 'file not found'
            elif k == 'includeall':
                folder = line.split(" ",1)[1].strip()
                files = [x for x in os.listdir(folder) if os.path.splitext(x.lower())[1] in ['.asm']]
                files = [x for x in files if not x.startswith('_')]
                lines = lines[:i]+['']+['include {}/{}'.format(folder, x) for x in files]+lines[i+1:]
            
            elif k == 'print' and passNum==2:
                v = line.split(" ",1)[1].strip()
                print(getString(v))
            elif k == 'warning' and passNum==2:
                v = line.split(" ",1)[1].strip()
                print('warning: ' + v)
            elif k == 'error' and passNum==2:
                v = line.split(" ",1)[1].strip()
                print('Error: ' + v)
                exit()
            
            elif k == '_find':
                data = line.split(' ',1)[1]
                findData = list(bytes.fromhex(''.join(['0'*(len(x)%2) + x for x in data.split()])))
                #b = b + list(bytes.fromhex(''.join(['0'*(len(x)%2) + x for x in data.split()])))
                result = [i for i in range(len(out)-len(findData)+1) if out[i:i+len(findData)]==findData]
                a = result[0]
                print([hex(x-headerSize) for x in result])
                
                a = (a-headerSize)
                resultBank = math.floor(a/bankSize)
                a=a-resultBank*bankSize+0x8000
                print('{:02x}:{:04x}'.format(resultBank,a))
                
            elif k == 'macro':
                v = line.split(" ")[1].strip()
                macro = v.lower()
                macros[macro]=Map()
                data = line.split(" ", 2)
                macros[macro].params = (data+[''])[2].replace(',',' ').split()
                macros[macro].lines = []
                noOutput = True
            elif k == 'endm' or k == 'endmacro':
                macro = False
                noOutput = False
            
            if k in macros:
                params = (line.split(" ",1)+[''])[1].replace(',',' ').split()
                
                for item in macros[k].params:
                    if assembler.lower(item) in symbols:
                        symbols.pop(assembler.lower(item))
                
                for item in mergeList(macros[k].params, params):
                    symbols[assembler.lower(item[0])] = item[1]
                
                lines = lines[:i]+['']+macros[k].lines+lines[i+1:]
                
            if k == 'enum':
                oldAddr = addr
                addr = getValue(v)
                currentAddress = addr
                noOutput = True
            elif k == 'ende' or k == 'endenum':
                addr = oldAddr
                currentAddress = addr
                noOutput = False
            
#            elif k == '_base':
#                addr = getValue(line.split(' ',1)[1])
#                if startAddress == False:
#                    startAddress = addr
#                currentAddress = addr
            elif k == 'base' or (k == 'org' and startAddress==False):
                v = getValue(line.split(' ',1)[1])
                if startAddress == False:
                    startAddress = v
                currentAddress = v
                
            elif k == 'org':
                v = getValue(line.split(' ',1)[1])

                if (orgPad == 1) and (startAddress!=False):
                    k = 'pad'
                else:
                    addr = addr + (v-currentAddress)
                    currentAddress += (v-currentAddress)
                    
#                    print('addr=',hex(addr))
#                    print('currentAddress=',hex(currentAddress))
                    
                    if bank != None:
                        addr = addr % bankSize
                    
                    if startAddress==False:
                        startAddress = addr
                        k = 'pad'
                        line = 'pad ${:04x}'.format(addr)

            if k == 'pad' or k == 'fillto':
                data = line.split(' ',1)[1]
                
                fv = fillValue
                if ',' in data:
                    fv = getValue(data.split(',')[1])
                a = getValue(data.split(',')[0])
                #print('fillto {:05x} {:05x} {:05x} {}'.format(a, currentAddress, addr, bank))
                if currentAddress <= a:
                    b = b + ([fv] * (a-currentAddress))
                else:
                    b = b + ([fv] * (a-(addr+bank*bankSize)))
            elif k == 'fill':
                data = line.split(' ',1)[1]
                
                fv = fillValue
                if ',' in data:
                    fv = getValue(data.split(',')[1])
                n = getValue(data.split(',')[0])
                
                b = b + ([fv] * n)
            elif k == 'align':
                data = line.split(' ',1)[1]
                
                fv = fillValue
                if ',' in data:
                    fv = getValue(data.split(',')[1])
                a = getValue(data.split(',')[0])
                
                b = b + ([fv] * ((a-currentAddress%a)%a))
                
            elif k == 'hex':
                data = line.split(' ',1)[1]
                b = b + list(bytes.fromhex(''.join(['0'*(len(x)%2) + x for x in data.split()])))
            
            elif k == 'dsb' or k == 'ds.b':
                data = line.split(' ',1)[1]
                n = getValue(data.split(",")[0])
                v = getValue((data.split(",")+['0'])[1])
                b = b + [v] * n
                
            elif k == 'dsw' or k == 'ds.w':
                data = line.split(' ',1)[1]
                n = getValue(data.split(",")[0])
                v = getValue((data.split(",")+['0'])[1])
                b = b + [v % 0x100, v>>8] * n
                
            elif k == "dl":
                values = line.split(' ',1)[1].split(",")
                values = [x.strip() for x in values]
                
                for v in [getValue(x) % 0x100 for x in values]:
                    b = b + makeList(v)
            
            elif k == "dh":
                values = line.split(' ',1)[1].split(",")
                values = [x.strip() for x in values]
                
                for v in [getValue(x) >>8 for x in values]:
                    b = b + makeList(v)
            elif k == 'mapdb':
                v = line.split(' ',1)
                if len(v) == 1:
                    mapdb = True
                else:
                    v = v[1].strip()
                    if (v.lower() in ['on','true']) or (getValue(v) == 1):
                        mapdb = True
                    else:
                        mapdb = False
            elif k == 'clampdb':
                v = line.split(' ',1)
                if len(v) == 1:
                    clampdb = True
                else:
                    v = v[1].strip()
                    if (v.lower() in ['on','true']) or (getValue(v) == 1):
                        clampdb = True
                    else:
                        clampdb = False
            elif k == 'text' or (k in ('db','dl') and mapdb == True):
                values = line.split(' ',1)[1].strip()
                
                values = assembler.tokenize(values)
                
                for i, v in enumerate(values):
                    if v.startswith(assembler.quotes):
                        values[i] = getValue(v, mode='textmap')
                    else:
                        values[i] = getValue(v)
                
                values = flattenList(values)
                
                if any(x not in range(256) for x in values):
                    if k != 'dl' and clampdb == False:
                        assembler.errorLinePos = len(line.split(' ',1)[0])+1
                        errorText = "invalid value"
                    values = [max(0, x) % 256 for x in values]
#                if 'YOU SHALL' in line:
#                    print(line)
#                    print(values)
#                    print(len(values))
                
                #values = getValue(values)
                #values = getString(values, strip=False)
                
#                if values == False:
#                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
#                    errorText = "invalid value"
#                else:
#                    values = assembler.mapText(values)
#                    b = b + makeList(values)
                b = b + makeList(values)
            elif k == 'db' or k=='byte' or k == 'byt' or k == 'dc.b' or k == 'dl':
                values = line.split(' ',1)[1]
                
                values = assembler.tokenize(values)
                values = [getValue(x) for x in values]
                values = flattenList(values)
                
                if any(x not in range(256) for x in values):
                    if k != 'dl' and clampdb == False:
                        assembler.errorLinePos = len(line.split(' ',1)[0])+1
                        errorText = "invalid value"
                    values = [max(0, x) % 256 for x in values]
                
                l = len(values)
                
                assembler.errorLinePos = len(line.split(' ',1)[0])+1
                if l==-1:
                    errorText = assembler.errorHint or 'value out of range'
                else:
                    values = makeList(values)
                    
                    for value in values:
                        if value>255:
                            errorText = "value out of range"
                            break
                        if value < 0:
                            value += 0x100
                        b = b + [value]
                
            elif k == "dw" or k=="word" or k=='dbyt' or k == 'dc.w':
                values = line.split(' ',1)[1]
                values, l = getValueAndLength(values)
                if l==-1:
                    errorText = assembler.errorHint or 'value out of range'
                    assembler.errorLinePos = len(line.split(' ',1)[0])+1
                else:
                    values = makeList(values)
                    
                    for value in values:
                        if value>65535:
                            errorText = "value out of range"
                            break
                        if value < 0:
                            value += 0x10000
                        b = b + [value % 0x100, value>>8]
            
            elif (k in opcodes) or (k in opcodes2):
                setLength = False
                if k.endswith('.b'):
                    setLength = 1
                    k = k.rsplit('.b',1)[0]
                elif k.endswith('.w'):
                    setLength = 2
                    k = k.rsplit('.w',1)[0]
                
                # Special handling for pseudo opcode
                # Example:
                # nop 6 ; 6 nop instructions
                if k == 'nop':
                    v = (line.split(" ",1)+[''])[1].strip()
                    if v:
                        op = getOpWithMode(k, "Implied") # op will be set to False below
                        b=b+([op.byte] * getValue(v))
                    
                v = "0"
                oldv = v
                
                if k in implied and k.strip() == line.strip().lower():
                    op = getOpWithMode(k, "Implied")
                elif k in accumulator and k.strip() == line.strip().lower():
                    op = getOpWithMode(k, "Accumulator")
                elif line.strip().lower() in [x+' a' for x in accumulator]:
                    op = getOpWithMode(k, "Accumulator")
                else:
                    op = False
                    ops = [x for x in asm if x.opcode==k]
                    
                    v = (line.split(" ",1)+[''])[1].strip()
                    oldv = v
                    v=v.replace(', ',',').replace(' ,',',')
                    
                    if k == "jmp" and v.startswith("("):
                        op = getOpWithMode(k, 'Indirect')
                    elif v.endswith('),y'):
                        op = getOpWithMode(k, '(Indirect), Y')
                    elif v.endswith(',x)'):
                        op = getOpWithMode(k, '(Indirect, X)')
                    elif v.endswith(',x'):
                        v = v.split(',x',1)[0]
                        
                        length = setLength or getLength(v)
                        #if getLength(v)==1 and getOpWithMode(k, 'Zero Page, X'):
                        if length == 1 and getOpWithMode(k, 'Zero Page, X'):
                            op = getOpWithMode(k, 'Zero Page, X')
                        elif getOpWithMode(k, 'Absolute, X'):
                            op = getOpWithMode(k, 'Absolute, X')
                    elif v.endswith(',y'):
                        v = v.split(',y',1)[0]
                        length = setLength or getLength(v)
                        #if getLength(v)==1 and getOpWithMode(k, 'Zero Page, Y'):
                        if length == 1 and getOpWithMode(k, 'Zero Page, Y'):
                            op = getOpWithMode(k, 'Zero Page, Y')
                        elif getOpWithMode(k, 'Absolute, Y'):
                            op = getOpWithMode(k, 'Absolute, Y')
                    elif v.startswith("#"):
                        v = v[1:]
                        op = getOpWithMode(k, 'Immediate')
                    else:
                        length = setLength or getLength(v)
                        #if getLength(v)==1 and getOpWithMode(k, 'Zero Page'):
                        if length == 1 and getOpWithMode(k, 'Zero Page'):
                            op = getOpWithMode(k, "Zero Page")
                        elif getOpWithMode(k, "Absolute"):
                            op = getOpWithMode(k, "Absolute")
                        elif getOpWithMode(k, "Relative"):
                            op = getOpWithMode(k, "Relative")
                if op:
                    if op.mode == 'Relative' and passNum==2:
                        if getValue(v) == currentAddress+op.length:
                            v = 0
                        elif getValue(v) > currentAddress+op.length:
                            v = getValue(v) - (currentAddress+op.length)
                            v='${:02x}'.format(v)
                        else:
                            v = (currentAddress+op.length) - getValue(v)
                            v='${:02x}'.format(0x100 - v)
                    v,l = getValueAndLength(v)
                    l = bytesForNumber(v)
                    
                    if type(v) is str:
                        v = int.from_bytes(v.encode('utf8'),'little')
                    elif type(v) is list:
                        v = int.from_bytes(v,'little')
                    
                    # if lda.b is used with a larger number, 
                    # silently clamp to a byte.
                    if setLength == 1 and l>1:
                        v = v % 0x100
                        l = 1
                    
                    if oldv == '#' or ((op.length>1) and l==0):
                        b = [op.byte] + [0] * (op.length-1)
                        assembler.errorLinePos = len(line)
                        errorText= 'missing value'
                    elif (op.length>1) and l>op.length-1:
                        b = [op.byte] + [0] * (op.length-1)
                        assembler.errorLinePos = line.find(oldv)
                        if oldv.startswith('#'):
                            assembler.errorLinePos += 1
                        errorText= 'value out of range: {}'.format(hex(v))
                    else:
                        b = [op.byte]
                        if op.length == 2:
                            b.append(v % 0x100)
                        elif op.length == 3:
                            b.append(v % 0x100)
                            b.append(math.floor(v/0x100))
            
            if k == 'define':
                k = line.split(" ")[1].strip()
                v = line.split(" ",2)[-1].strip()
                if k.startswith(assembler.quotes) and k.endswith(assembler.quotes):
                    k = assembler.stripQuotes(k)
                    assembler.setTextMapData(k, '{:02x}'.format(getValue(v)))
                else:
                    if k == '$':
                        addr = getValue(v)
                        if startAddress == False:
                            startAddress = addr
                        currentAddress = addr
                    else:
                        symbols[assembler.lower(k)] = v
                k=''
            if ' equ ' in line.lower():
                k = line[:line.lower().find(' equ ')]
                v = line[line.lower().find(' equ ')+len(' equ '):]
                equ[k] = v
            elif (line.split('=')+[''])[1]:
                k = line.split("=",1)[0].strip()
                v = line.split("=",1)[1].strip()
                if k == '$':
                    addr = getValue(v)
                    if startAddress == False:
                        startAddress = addr
                    currentAddress = addr
                else:
                    symbols[assembler.lower(k)] = v
                k=''
            
            if len(b)>0:
                invalidBytes = [(i,x) for (i,x) in enumerate(b) if x not in range(256)]
                if len(invalidBytes)!=0:
                    # If we're here it means error handling didn't catch it.
                    errorText= 'invalid bytes: '+str(b)
            
                showAddress = True
                if noOutput==False and passNum == 2:
                    
                    if bank == None:
                        fileOffset = addr
                        if fileOffset == len(out):
                            # We're in the right spot, just append
                            if np:
                                out = np.append(out, np.array(b, dtype='B'))
                            else:
                                out = out + b
                        elif fileOffset>len(out):
                            fv = fillValue
                            if np:
                                out = np.append(out, np.array(([fv] * (fileOffset-len(out))), dtype='B'))
                                out = np.append(out, np.array(b, dtype='B'))
                            else:
                                out = out + ([fv] * (fileOffset-len(out))) + b
                        elif fileOffset<len(out):
                            out = out[:fileOffset]+b+out[fileOffset+len(b):]
                    else:
                        #fileOffset = addr % bankSize + bank*bankSize+headerSize
                        fileOffset = addr + bank * bankSize + headerSize
                        
                        if fileOffset == len(out):
                            # We're in the right spot, just append

                            if np:
                                out = np.append(out, np.array(b, dtype='B'))
                            else:
                                out = out + b
                        elif fileOffset>len(out):
                            fv = fillValue
                            if np:
                                out = np.append(out, np.array(([fv] * (fileOffset-len(out))), dtype='B'))
                                out = np.append(out, np.array(b, dtype='B'))
                            else:
                                out = out + ([fv] * (fileOffset-len(out))) + b
                        elif fileOffset<len(out):
                            out = out[:fileOffset]+b+out[fileOffset+len(b):]
                addr = addr + len(b)
                currentAddress = currentAddress + len(b)
            
            if assembler.hideOutputLine:
                assembler.hideOutputLine = False
            elif passNum == 2 and not hide:
                nBytes = cfg.getValue('main', 'list_nBytes')
                
                fileOffset = getValue('fileoffset')-len(b)
                outputText+="{:05X} ".format(fileOffset)

                if startAddress:
                    
                    outputText+="{:05X} ".format(currentAddress-len(b))
                else:
                    outputText+=' '*6
                
                if nBytes == 0:
                    outputText+="{}\n".format(originalLine)
                else:
                    listBytes = False
                    if noOutput:
                        listBytes = ' '*(3*nBytes+1)
                    else:
                        listBytes = ' '.join(['{:02X}'.format(x) for x in b[:nBytes]]).ljust(3*nBytes-1) + ('..' if len(b)>nBytes else '  ')
                    outputText+="{} {}\n".format(listBytes, originalLine)
                if errorText:
                    if assembler.errorLinePos:
                        outputText +=' '*38 + ' '*assembler.errorLinePos+'^\n'
                    outputText+='*** {}\n'.format(errorText)
                    
                    print(line)
                    if assembler.errorLinePos:
                        print(' '*assembler.errorLinePos+'^')
                    print('*** {}\n'.format(errorText))
                    errorText = False
                    assembler.errorLinePos = False
            if k==".org": showAddress = True
    
    if passNum == 2:
        with open(outputFilename, "wb") as file:
            invalidBytes = [(i,x) for (i,x) in enumerate(out) if x not in range(256)]
            if len(invalidBytes)!=0:
                outputText+='*** Invalid bytes:'
                print('Invalid bytes:')
                for a,b in invalidBytes:
                    outputText += '{:05x}: {:02x}'.format(a,b)
                    print('{:05x}: {:02x}'.format(a,b))
                    out[a] = 0
            
            if assembler.stripHeader:
                out = out[16:]
            
            file.write(bytes(out))
            print('{} written.'.format(outputFilename))
        
        if listFilename:
            with open(listFilename, 'w') as file:
                print(outputText, file=file)
                print('{} written.'.format(listFilename))

        if debug:
            f = 'debug_symbols.txt'
            with open(f, "w") as file:
                for k,v in symbols.items():
                    print('{} = {}'.format(k,v), file=file)
            print('{} written.'.format(f))
        if debug:
            f = 'debug_files.txt'
            with open(f, "w") as file:
                file.writelines(fileList)
            print('{} written.'.format(f))
        print()
if __name__ == '__main__':
    # This stuff doesn't work because I need to get the relative
    # imports more organized.
    
    import argparse

    parser = argparse.ArgumentParser(description='ASM 6502 Assembler made in Python')
    
    parser.add_argument('-l', type=str, metavar="<file>",
                        help='Create a list file')
    parser.add_argument('-bin', type=str, metavar="<file>",
                        help='Include binary file')
    parser.add_argument('-cfg', type=str, metavar="<file>",
                        help='Specify config file')
#    parser.add_argument('-q', action='store_true',
#                        help='Quiet mode')

    parser.add_argument('sourcefile', type=str,
                        help='The file to assemble')
    parser.add_argument('outputfile', type=str, nargs='?',
                        help='The output file')

    args = parser.parse_args()

    filename = args.sourcefile
    outputFilename = args.outputfile
    listFilename = args.l
    configFile = args.cfg
    binFile = args.bin # not implemented
    
    start = time.time()
    
    print(args)
    
    
    #exit()
    assemble(filename, outputFilename = outputFilename, listFilename = listFilename, configFile = configFile, binFile = binFile)

    end = time.time()-start
    if end>=3:
        print(time.strftime('Finished in %Hh %Mm %Ss.',time.gmtime(end)))
