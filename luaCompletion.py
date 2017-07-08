import sublime
import sublime_plugin
import re
import time

try:
    import buildDefinition
    import utils
except ImportError:
    from . import buildDefinition
    from . import utils

global cache
global builder


def init():
    global cache, builder
    builder = buildDefinition.BuildDefinition()
    builder.loadCache()

    cache = {}
    for key, val in builder.defi.items():
        cache[key] = val

def getAutoBuildPath():
    settings = utils.loadSettings("LuaCWC")
    auto_build_path = settings.get("auto_build_path", "")
    return auto_build_path

class LuaBuildDefinitionCommand(sublime_plugin.TextCommand):

    def run(self, edit, dirs):
        global builder
        builder.build(dirs[0])
        builder.save()

        global cache
        cache = {}
        for key, val in builder.defi.items():
            cache[key] = val

    def is_enabled(self, dirs):
        return len(dirs) == 1

    def is_visible(self, dirs):
        return self.is_enabled(dirs)


class LuaAutoCompleteCommand(sublime_plugin.TextCommand):

    def run(self, edit, characters):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), characters)

        self.view.run_command("hide_auto_complete")
        sublime.set_timeout(self.delayed_complete, 1)

    def delayed_complete(self):
        self.view.run_command("auto_complete")


class LuaAutoComplete(sublime_plugin.EventListener):

    def __init__(self):
        self.lastTime=0

    def appendMember(self, clsName, havenew, point, lst):
        global cache

        if clsName != None and clsName in cache:
            obj = cache[clsName]
            sup = None
            for key, val in obj.items():
                if "::" in key:
                    if key == "::super":
                        sup = val
                    continue
                ma = re.match("^Ctor(\(.*\))", key)
                if ma != None:
                    if havenew:
                        newFunc = "New" + ma.group(1)
                        lst.append((newFunc + "\t" + clsName + "-" + "func", newFunc))
                    continue

                _type = val.split(":")[0]
                if _type == "func" and point == ".":
                    continue
                if _type == "val" and point == ":":
                    continue

                lst.append((key + "\t" + clsName +
                            "-" + _type, key))

            if sup != None:
                self.appendMember(sup, havenew, point, lst)

    def iterMemberClass(self, valArr, firstCls):
        global cache

        cls = None
        if firstCls in cache:
            cls = firstCls
            clsDic = None
            for x in range(1, len(valArr)):
                item = valArr[x]
                clsDic = cache[cls]
                if not clsDic:
                    break

                if item in clsDic:
                    cls = clsDic[item].split(":")[1]
                    if cls != "nil":
                        clsDic = cache[cls]
                    else:
                        break
                else:
                    func = self.getFunc(clsDic, item)
                    if func != None:
                        cls = func.split(":")[1]
                    else:
                        cls = None
                        break

        return cls

    def getFunc(self, dic, funcName):
        for key, val in dic.items():
            # print funcName, key
            if re.search(funcName + "\(.*\)", key) != None:
                return val

        return None

    def on_post_save(self, view):
        curTime = time.time()
        if curTime - self.lastTime<2:
            return

        auto_build_path = getAutoBuildPath()

        if len(auto_build_path) <= 0:
            return

        if not utils.isLuaFile(view.file_name()):
            return

        view.run_command("lua_build_definition", {"dirs":[auto_build_path]})

    def on_query_completions(self, view, prefix, locations):
        global cache

        line = view.substr(sublime.Region(
            view.line(locations[0]).begin(), locations[0]))
        match = re.search("([\w\d\.]+)([\.\:])$", line)
        
        if match != None:
            memList = []
            val = match.group(1)
            point = match.group(2)
            valArr = val.split(".")
            if valArr[0] in cache:
                cls = self.iterMemberClass(valArr, valArr[0])
                self.appendMember(cls, True, point, memList)
            elif valArr[0] == "self":
                content = view.substr(sublime.Region(0, view.size()))
                # function block
                mat = re.finditer(
                        "^function\s+([\w\d]+)[\:\.]([\w\d]+\s*\(.*\))(.*)$(?:\n+.+){1,}?\nend", content, re.MULTILINE)
                for item in mat:
                    pos = locations[0]
                    if pos >= item.start() and pos <= item.end():
                        cls = self.iterMemberClass(valArr, item.group(1))
                        self.appendMember(cls, False, point, memList)
                        break
            else:
                content = view.substr(sublime.Region(0, view.size()))
                match = re.search(
                    "^\s*(?:local){0,}\s*" + valArr[0] + "\s*=\s*(.+)", content, re.MULTILINE)

                if match != None:
                    matCls = re.search("([\w\d]+)\.New\(.+", match.group(1))

                    # mark Cls.New()
                    if matCls != None:
                        cls = self.iterMemberClass(valArr, matCls.group(1))
                        self.appendMember(cls, True, point, memList)

                    # mark val--[type:ClsName]
                    else:
                        matCls = re.search(".+\[type:([\w\d].+)\]", match.group(1))
                        if matCls != None:
                            cls = self.iterMemberClass(valArr, matCls.group(1))
                            self.appendMember(cls, True, point, memList)
                        # mark Func()--[crt:ClsName]
                        else:
                            matFunc = re.search(
                                "[\w\d]+([\.\:][\w\d]+\(.*\)){1,}", match.group(1))
                            if matFunc != None:
                                funcName = match.group(1)
                                firstIndex = funcName.find("(")
                                funcArr = []
                                startIndex = 0
                                # mark bracket
                                while firstIndex > 0:
                                    funcSub = funcName[firstIndex:]
                                    braCount = 1
                                    curIndex = firstIndex
                                    for i in range(1, len(funcSub)):
                                        ch = funcSub[i]
                                        if ch == ")":
                                            braCount -= 1
                                        elif ch == "(":
                                            braCount += 1
                                        curIndex = firstIndex + i
                                        if braCount <= 0:
                                            break

                                    curIndex += 1
                                    nextStr = funcName[curIndex:]
                                    funcArr.append(funcName[startIndex:firstIndex])
                                    startIndex = curIndex
                                    firstIndex = nextStr.find("(")
                                    if firstIndex > 0:
                                        firstIndex += curIndex

                                resolve = ""
                                for item in funcArr:
                                    resolve += item

                                valArr = re.split("[\.\:]", resolve)
                                # like ConfigManager.avatar, ConfigManager is class
                                if valArr[0] in cache:
                                    cls = self.iterMemberClass(valArr, valArr[0])
                                    self.appendMember(cls, True, point, memList)
                                else:  # TODO : support var by recur
                                    pass

            return (memList, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

        return []


# st3
def plugin_loaded():
    sublime.set_timeout(init, 200)

# st2
if not utils.isST3():
    init()
