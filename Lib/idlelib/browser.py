"Module browser.\n\nXXX TO DO:\n\n- reparse when source changed (maybe just a button would be OK?)\n    (or recheck on window popup)\n- add popup menu with more options (e.g. doc strings, base classes, imports)\n- add base classes to class browser tree\n- finish removing limitation to x.py files (ModuleBrowserTreeItem)\n"
import os
import pyclbr
import sys
from idlelib.config import idleConf
from idlelib import pyshell
from idlelib.tree import TreeNode, TreeItem, ScrolledCanvas
from idlelib.window import ListedToplevel

file_open = None


def transform_children(child_dict, modname=None):
    "Transform a child dictionary to an ordered sequence of objects.\n\n    The dictionary maps names to pyclbr information objects.\n    Filter out imported objects.\n    Augment class names with bases.\n    The insertion order of the dictionary is assumed to have been in line\n    number order, so sorting is not necessary.\n\n    The current tree only calls this once per child_dict as it saves\n    TreeItems once created.  A future tree and tests might violate this,\n    so a check prevents multiple in-place augmentations.\n    "
    obs = []
    for (key, obj) in child_dict.items():
        if (modname is None) or (obj.module == modname):
            if hasattr(obj, "super") and obj.super and (obj.name == key):
                supers = []
                for sup in obj.super:
                    if type(sup) is type(""):
                        sname = sup
                    else:
                        sname = sup.name
                        if sup.module != obj.module:
                            sname = f"{sup.module}.{sname}"
                    supers.append(sname)
                obj.name += "({})".format(", ".join(supers))
            obs.append(obj)
    return obs


class ModuleBrowser:
    "Browse module classes and functions in IDLE.\n    "

    def __init__(self, master, path, *, _htest=False, _utest=False):
        "Create a window for browsing a module's structure.\n\n        Args:\n            master: parent for widgets.\n            path: full path of file to browse.\n            _htest - bool; change box location when running htest.\n            -utest - bool; suppress contents when running unittest.\n\n        Global variables:\n            file_open: Function used for opening a file.\n\n        Instance variables:\n            name: Module name.\n            file: Full path and module with .py extension.  Used in\n                creating ModuleBrowserTreeItem as the rootnode for\n                the tree and subsequently in the children.\n        "
        self.master = master
        self.path = path
        self._htest = _htest
        self._utest = _utest
        self.init()

    def close(self, event=None):
        "Dismiss the window and the tree nodes."
        self.top.destroy()
        self.node.destroy()

    def init(self):
        "Create browser tkinter widgets, including the tree."
        global file_open
        root = self.master
        flist = (
            pyshell.flist
            if (not (self._htest or self._utest))
            else pyshell.PyShellFileList(root)
        )
        file_open = flist.open
        pyclbr._modules.clear()
        self.top = top = ListedToplevel(root)
        top.protocol("WM_DELETE_WINDOW", self.close)
        top.bind("<Escape>", self.close)
        if self._htest:
            top.geometry(("+%d+%d" % (root.winfo_rootx(), (root.winfo_rooty() + 200))))
        self.settitle()
        top.focus_set()
        theme = idleConf.CurrentTheme()
        background = idleConf.GetHighlight(theme, "normal")["background"]
        sc = ScrolledCanvas(top, bg=background, highlightthickness=0, takefocus=1)
        sc.frame.pack(expand=1, fill="both")
        item = self.rootnode()
        self.node = node = TreeNode(sc.canvas, None, item)
        if not self._utest:
            node.update()
            node.expand()

    def settitle(self):
        "Set the window title."
        self.top.wm_title(("Module Browser - " + os.path.basename(self.path)))
        self.top.wm_iconname("Module Browser")

    def rootnode(self):
        "Return a ModuleBrowserTreeItem as the root of the tree."
        return ModuleBrowserTreeItem(self.path)


class ModuleBrowserTreeItem(TreeItem):
    "Browser tree for Python module.\n\n    Uses TreeItem as the basis for the structure of the tree.\n    Used by both browsers.\n    "

    def __init__(self, file):
        "Create a TreeItem for the file.\n\n        Args:\n            file: Full path and module name.\n        "
        self.file = file

    def GetText(self):
        "Return the module name as the text string to display."
        return os.path.basename(self.file)

    def GetIconName(self):
        "Return the name of the icon to display."
        return "python"

    def GetSubList(self):
        "Return ChildBrowserTreeItems for children."
        return [ChildBrowserTreeItem(obj) for obj in self.listchildren()]

    def OnDoubleClick(self):
        "Open a module in an editor window when double clicked."
        if os.path.normcase(self.file[(-3):]) != ".py":
            return
        if not os.path.exists(self.file):
            return
        file_open(self.file)

    def IsExpandable(self):
        "Return True if Python (.py) file."
        return os.path.normcase(self.file[(-3):]) == ".py"

    def listchildren(self):
        "Return sequenced classes and functions in the module."
        (dir, base) = os.path.split(self.file)
        (name, ext) = os.path.splitext(base)
        if os.path.normcase(ext) != ".py":
            return []
        try:
            tree = pyclbr.readmodule_ex(name, ([dir] + sys.path))
        except ImportError:
            return []
        return transform_children(tree, name)


class ChildBrowserTreeItem(TreeItem):
    "Browser tree for child nodes within the module.\n\n    Uses TreeItem as the basis for the structure of the tree.\n    "

    def __init__(self, obj):
        "Create a TreeItem for a pyclbr class/function object."
        self.obj = obj
        self.name = obj.name
        self.isfunction = isinstance(obj, pyclbr.Function)

    def GetText(self):
        "Return the name of the function/class to display."
        name = self.name
        if self.isfunction:
            return ("def " + name) + "(...)"
        else:
            return "class " + name

    def GetIconName(self):
        "Return the name of the icon to display."
        if self.isfunction:
            return "python"
        else:
            return "folder"

    def IsExpandable(self):
        "Return True if self.obj has nested objects."
        return self.obj.children != {}

    def GetSubList(self):
        "Return ChildBrowserTreeItems for children."
        return [
            ChildBrowserTreeItem(obj) for obj in transform_children(self.obj.children)
        ]

    def OnDoubleClick(self):
        "Open module with file_open and position to lineno."
        try:
            edit = file_open(self.obj.file)
            edit.gotoline(self.obj.lineno)
        except (OSError, AttributeError):
            pass


def _module_browser(parent):
    if len(sys.argv) > 1:
        file = sys.argv[1]
    else:
        file = __file__

        class Nested_in_func(TreeNode):
            def nested_in_class():
                pass

        def closure():
            class Nested_in_closure:
                pass

    ModuleBrowser(parent, file, _htest=True)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        from unittest import main

        main("idlelib.idle_test.test_browser", verbosity=2, exit=False)
    from idlelib.idle_test.htest import run

    run(_module_browser)
