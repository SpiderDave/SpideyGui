local util = {}

util.serialize = function(t)
    if not t then return end
    return Tserial.pack(t)
end
util.unserialize = function(s)
    if not s then return end
    return Tserial.unpack(s)
end

function util.writeToFile(file,address, data, wipe)
    if wipe==true or (not util.fileExists(file)) then
        local f=io.open(file,"w")
        f:close()
    end
    if not data then return nil end
    local f = io.open(file,"r+b")
    if not f then return nil end
    f:seek("set",address)
    f:write(data)
    f:close()
    return true
end

function util.getFileContents(path)
    local file = io.open(path,"rb")
    if file==nil then return nil end
    io.input(file)
    local ret=io.read("*a")
    io.close(file)
    return ret
end

function util.fileExists(name)
   local f=io.open(name,"r")
   if f~=nil then io.close(f) return true else return false end
end

return util