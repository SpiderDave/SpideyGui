config = {
    width=800,
    height=600,
    upperHex=false,
    cellWidth=24,
    cellHeight=24,
}

__print = print
print = function(txt)
    __print("[Lua] "..(txt or ''))
end


makeHex = function(n)
    if config.upperHex then
        return string.format("%02X",n)
    else
        return string.format("%02x",n)
    end
end

data = {selectedColor = {}}
data.palettes = {}
data.projectID = "project1" -- this determines the folder that it will load the project data from
data.projectID = "skeleton2"
data.folders = {
    projects = "projects/",
}


data.project = {}

nespalette={[0]=
{0x74,0x74,0x74},{0x24,0x18,0x8c},{0x00,0x00,0xa8},{0x44,0x00,0x9c},
{0x8c,0x00,0x74},{0xa8,0x00,0x10},{0xa4,0x00,0x00},{0x7c,0x08,0x00},
{0x40,0x2c,0x00},{0x00,0x44,0x00},{0x00,0x50,0x00},{0x00,0x3c,0x14},
{0x18,0x3c,0x5c},{0x00,0x00,0x00},{0x00,0x00,0x00},{0x00,0x00,0x00},
{0xbc,0xbc,0xbc},{0x00,0x70,0xec},{0x20,0x38,0xec},{0x80,0x00,0xf0},
{0xbc,0x00,0xbc},{0xe4,0x00,0x58},{0xd8,0x28,0x00},{0xc8,0x4c,0x0c},
{0x88,0x70,0x00},{0x00,0x94,0x00},{0x00,0xa8,0x00},{0x00,0x90,0x38},
{0x00,0x80,0x88},{0x00,0x00,0x00},{0x00,0x00,0x00},{0x00,0x00,0x00},
{0xfc,0xfc,0xfc},{0x3c,0xbc,0xfc},{0x5c,0x94,0xfc},{0xcc,0x88,0xfc},
{0xf4,0x78,0xfc},{0xfc,0x74,0xb4},{0xfc,0x74,0x60},{0xfc,0x98,0x38},
{0xf0,0xbc,0x3c},{0x80,0xd0,0x10},{0x4c,0xdc,0x48},{0x58,0xf8,0x98},
{0x00,0xe8,0xd8},{0x78,0x78,0x78},{0x00,0x00,0x00},{0x00,0x00,0x00},
{0xfc,0xfc,0xfc},{0xa8,0xe4,0xfc},{0xc4,0xd4,0xfc},{0xd4,0xc8,0xfc},
{0xfc,0xc4,0xfc},{0xfc,0xc4,0xd8},{0xfc,0xbc,0xb0},{0xfc,0xd8,0xa8},
{0xfc,0xe4,0xa0},{0xe0,0xfc,0xa0},{0xa8,0xf0,0xbc},{0xb0,0xfc,0xcc},
{0x9c,0xfc,0xf0},{0xc4,0xc4,0xc4},{0x00,0x00,0x00},{0x00,0x00,0x00},
}

for i=0,#nespalette do
    nespalette[i].index = i
end

function init()
    local x,y
    local x2,y2
    
    print("init")
    
    Python.incLua("Tserial")
    util = Python.incLua("util")
    
    -- make sure projects folder exists
    Python:makeDir(data.folders.projects)
    
    Python.setTab("Main")
    
    pad=6
    x=pad*1.5
    y=pad*1.5

    b=Python.makeButton{x=x,y=y,name="LoadProject",text="Load Project"}
    y = y + b.height + pad
    
    b=Python.makeButton{x=x,y=y,name="SaveProject",text="Save Project"}
    y = y + b.height + pad
    
    b=Python.makeButton{x=x,y=y,name="BuildProject",text="Build Project"}
    y = y + b.height + pad
    
    b=Python.makeButton{x=x,y=y,name="ButtonLevelExtract",text="Extract Level"}
    y = y + b.height + pad
    
    b=Python.makeButton{x=x,y=y,name="ButtonMakeCHR",text="Make CHR"}
    y = y + b.height + pad


    for i=0,4 do
        b=Python.makeButton{x=x,y=y,name="Button"..i,text="Button"..i}
        y = y + b.height + pad
    end
    
    
    --b=Python.makeText{x=x,y=y, lineHeight=20,lineWidth=80, name="Text1",text="Text1"}
    
    
    Python.setTab("Palette")
    Python.setDirection("h")
    
    p = {[0]=0x0f,0x21,0x11,0x01}
    c=Python.makePaletteControl{x=pad*1.5,y=pad*1.5,cellWidth=config.cellWidth,cellHeight=config.cellHeight, name="Palette", palette=nespalette}
    
    palette = {}
    for i=0,#p do
        palette[i] = nespalette[p[i]]
    end
    
    x2=Python.x+pad + 100
    y2=pad*1.5

    
    top = Python.y + pad*1.5
    left = pad*1.5
    
    placeX = left
    placeY = top
    
    for y = 0,1 do
        for x = 0,3 do
            Python.makePaletteControl{x=placeX,y=placeY,cellWidth=config.cellWidth,cellHeight=config.cellHeight, name=string.format("Pal%x",y*4+x), palette=palette}
            placeX = Python.x+pad*1.5
        end
        placeX = left
        placeY = Python.y+pad
    end
    
    x=placeX
    y=placeY
    b=Python.makeButton{x=x,y=y,name="ButtonLoadPalette",text="Load Palette"}
    
    y = y + b.height + pad
    b=Python.makeButton{x=x,y=y,name="ButtonSavePalette",text="Save Palette"}
    y = y + b.height + pad
    b=Python.makeText{x=x,y=y, lineHeight=16,lineWidth=80, name="Text1",text="Text1"}
    y = y + b.height + pad
    
    x=x2
    y=y2
    b=Python.makeList{x=x,y=y, name="PaletteList"}
--    b.insert(1,"test")
--    b.insert(1,"test2")
    b.append("palette00")
    b.append("palette01")
    b.append("palette02")
    b.append("palette03")
    
    --listbox.insert(END, text)
    
    Python.setTab("Image")
    p = {[0]=0x0f,0x21,0x11,0x01}
    palette = {}
    for i=0,#p do
        palette[i] = nespalette[p[i]]
    end

    x=pad
    y=pad+128*3+pad*1.5
    c=Python.makePaletteControl{x=x,y=y,cellWidth=config.cellWidth,cellHeight=config.cellHeight, name="CHRPalette", palette=palette}
    
    y = y + 32 + pad
    b=Python.makeButton{x=x,y=y,name="OpenCHR",text="Load CHR"}
    y = y + b.height + pad
    
    
    
--    f="chr.png"
--    Python:loadImageToCanvas(f)
    
    -- Import the "LevelExtract" method from "SMBLevelExtract.py" and 
    -- add it to the "Python" table.
    --LevelExtract = Python:importFunction('include.SMBLevelExtract','LevelExtract')
    
    LoadProject_cmd()
end

function doCommand(ctrl)
    if type(ctrl) == 'string' then
        print("doCommand "..ctrl)
    else
        print("doCommand "..ctrl.name)
    end
end

function Palette_cmd(name, dummy,t)
    t.cell = Python.getControl(t.cellName)
    if t.num ==1 then
        data.selectedColor.bg = t.cell.bg
        data.selectedColor.fg = t.cell.fg
        data.selectedColor.text = t.cell.text
        print(string.format("Selected palette %02x",t.cellNum))
        --print(string.format("Selected color %s",data.selectedColor.text))
    end
end


f = function(name, dummy, t)
    t.cell = Python.getControl(t.cellName)
    t.palNum = tonumber(string.sub(name, -1))
    Pal_cmd(name,dummy,t)
end

Pal0_cmd = f
Pal1_cmd = f
Pal2_cmd = f
Pal3_cmd = f
Pal4_cmd = f
Pal5_cmd = f
Pal6_cmd = f
Pal7_cmd = f

function Pal_cmd(name, dummy,t)
    if t.num==3 then
        t.cell.bg = data.selectedColor.bg
        t.cell.fg = data.selectedColor.fg
        t.cell.text = data.selectedColor.text
    elseif t.num==1 then
        data.selectedColor.bg = t.cell.bg
        data.selectedColor.fg = t.cell.fg
        data.selectedColor.text = t.cell.text
        print(string.format("Selected palette %02x",t.cellNum))
    end
end

function CHRPalette_cmd(name, dummy,t)
    print(string.format("Selected palette %02x",t.cellNum))
    data.drawColorIndex = t.cellNum
end

function ButtonMakeCHR_cmd()
    f = Python:openFile({{"Images", ".png"}})
    if f == "" then
        print("Open cancelled.")
    else
        print("file: "..f)
        
        f2 = Python:saveFileAs({{"CHR", ".chr"}},'output.chr')
        if f2 == "" then
            print("Save cancelled.")
        else
            print("file: "..f2)
            Python:imageToCHR(f,f2,Python:getNESColors('0f211101'))
        end
    end
end

function Button0_cmd()
    --print(nesPalette[1][1])
    --print(#nesPalette)
    --print(Python.eval('nesPalette')[0][0])
    
    --dict([(x,y) for x,y in enumerate(p)])
    --t = Python.eval('lua.table_from(nesPalette)')
    --t = Python.eval('lua.table_from(dict([(x,y) for x,y in enumerate(nesPalette)]))')
    --t = Python.eval('lua.table_from(dict([(x,y) for x,y in enumerate(nesPalette)]))')
    --print(type(t[0]))
    
    --t = Python.eval('lua.table({{0:42},1,2,3})')
    t=Python.eval('nesPalette')
    
    for k,v in python.enumerate(t) do
        print(math.floor(v[0]))
    end
    
--    for k,v in pairs(t) do
--        print(string.format("%s, %s %s",k,v, type(v)))
--    end
    
    
end

function Button2_cmd()
    --Python.exec("print('hello world!')")
    --Python.exec("root.geometry('400x400')")
    --Python.exec("controls['Button0'].place(x=0,y=0)")
    --Python.exec("controls['Button0']['text'] = 'foo'")
    --controls = Python.exec("ForLua.execRet = lambda: controls")
    --controls = Python.eval("controls['Button0']['text']")
    --print(controls)
    
    Python.hideControl('Button1')
    --Python.removeControl('Button4')

    
    -- Import the "LevelExtract" method from "SMBLevelExtract.py" and 
    -- add it to the "Python" table.
    --Python:importFunction('SMBLevelExtract','LevelExtract')
    --Python.LevelExtract('smbGreatEd.nes','outputtest.asm')
end

function Button1_cmd()
    --Python.exec("controls['Text1'].setText('blahhhh')")
    c = Python.getControl('PaletteList')
    print(type(c))
    for k,v in pairs(c) do
        print(k)
    end
    c.set(1)
    print(c.get() or 'none')
end

function ButtonLevelExtract_cmd()
    f = Python:openFile({{"NES rom", ".nes"}})
    if f == "" then
        print("Open cancelled.")
    else
        print("file: "..f)
        
        f2 = Python:saveFileAs({{"ASM", ".asm"}},'output.asm')
        if f2 == "" then
            print("Save cancelled.")
        else
            print("file: "..f2)
            SMBLevelExtract(f,f2)
        end
    end
end

function LoadProject_cmd()
    projectFolder = data.projectID.."/"
    
    filename = data.folders.projects..projectFolder.."project.dat"
    data.project = util.unserialize(util.getFileContents(filename))
    
    if not data.project then
        data.project = {}
    end
    
    
    data.project.folder = projectFolder
    
    c = Python.getControl('PaletteList')
    c.set(data.project.paletteIndex or 0)
    ButtonLoadPalette_cmd()

    f=data.folders.projects..projectFolder.."chr.png"
    Python:loadImageToCanvas(f)

end

function BuildProject_cmd()
    -- save CHR image to .chr
    -- for now it just loads the chr.png
    f = data.folders.projects..data.project.folder.."chr.png"
    f2 = data.folders.projects..data.project.folder.."chr.chr"
    Python:imageToCHR(f,f2,Python:getNESColors('0f211101'))
end

function SaveProject_cmd()
    c = Python.getControl('PaletteList')
    data.project.paletteIndex = c.getIndex()

    Python:makeDir(data.folders.projects..data.project.folder)

    filename = data.folders.projects..data.project.folder.."project.dat"
    util.writeToFile(filename,0, util.serialize(data.project), true)
end

function ButtonSavePalette_cmd()
    c = Python.getControl('PaletteList')
    filename = data.folders.projects..projectFolder..string.format("%s.dat",c.get())

    local p = {}
    local i=0
    local out="PaletteData:\n"
    for pNum = 0,7 do
        out=out.."  .db "
        for cellNum = 0,3 do
            local c = Python.getControl(string.format("Pal%x_%02x",pNum,cellNum))
            p[i]=tonumber(c.text,16)
            i=i+1
            out=out..string.format("$%s",c.text)
            if cellNum==3 then
                out=out.."\n"
            else
                out=out..", "
            end
        end
    end
    out=out.."\n"
    
    
    --Python.exec("controls['Text1'].setText('"..out.."')")
    --local c = Python.getControl("Text1")
    Python.setText(Python.getControl("Text1"),out)
    
    local data = util.serialize(p)
    --local data = out
    util.writeToFile(filename,0, data, true)
    
end

function ButtonLoadPalette_cmd()
    c = Python.getControl('PaletteList')
    filename = data.folders.projects..projectFolder..string.format("%s.dat",c.get())
    local p = util.unserialize(util.getFileContents(filename))
    
    if p then
    
        local firstWhite = {[0]=0x00,0x01,0x0d,0x0e}
        local i = 0
        local out="PaletteData:\n"
        for pNum = 0,7 do
            out=out.."  .db "
            for cellNum = 0,3 do
                local c = Python.getControl(string.format("Pal%x_%02x",pNum,cellNum))
                local x = p[i] % 16
                local y = math.floor(p[i]/16)
                
                if x>=firstWhite[y] then
                    c.fg="white"
                else
                    c.fg="black"
                end
                c.bg = string.format("#%02x%02x%02x", nespalette[p[i]][1], nespalette[p[i]][2], nespalette[p[i]][3])
                c.text = string.format("%02x",p[i])
                i=i+1
                out=out..string.format("$%s",c.text)
                if cellNum==3 then
                    out=out.."\n"
                else
                    out=out..", "
                end
            end
        end
        out=out.."\n"
        
        --Python.exec("controls['Text1'].setText('"..out.."')")
        --local c = Python.getControl("Text1")
        Python.setText(Python.getControl("Text1"),out)
    end
end


function Label1_cmd(name, label)
    print(name)
end


function PaletteList_cmd(t)
--    print(t.getSelection())
--    print(type(t.getSelection()))
--    n = t.getSelection()
--    print(tonumber(string.format("%d",n)))
--    print(t.test)
    
    -- display the palette list item
    print(t.get())
    
    -- load the current palette
    ButtonLoadPalette_cmd()
    
--    print(type(t))
--    for k,v in pairs(t) do
--        print(k)
--    end
--    print(t.control.fg)
--    print('************')
    --print(t.control)
--    t.append('test')
end

function About_cmd()
    Python.exec("webbrowser.get('windows-default').open('https://github.com/SpiderDave/SpideyGui')")
end

function Quit_cmd()
    Python.Quit()
end

function OpenCHR_cmd()
    f = Python:openFile(nil)
    if f == "" then
        print("Open cancelled.")
    else
        print("file: "..f)
        Python:loadImageToCanvas(f)
    end
end

function Open_cmd()
    --f = Python:openFile(nil)
    f, projectID = Python:openFolder("projects")
    if f == "" then
        print("Open cancelled.")
    else
        print("file: "..f)
        --Python:loadImageToCanvas(f)
        data.projectID = projectID
        LoadProject_cmd()
    end
end

function Save_cmd()
    f = Python:saveFileAs()
    if f == "" then
        print("Save cancelled.")
    else
        print("file: "..f)
    end
end


function onExit(cancel)
    print("onExit")
end