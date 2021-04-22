"\nA number of functions that enhance IDLE on macOS.\n"
from os.path import expanduser
import plistlib
from sys import platform
import tkinter

_tk_type = None


def _init_tk_type():
    "\n    Initializes OS X Tk variant values for\n    isAquaTk(), isCarbonTk(), isCocoaTk(), and isXQuartz().\n    "
    global _tk_type
    if platform == "darwin":
        root = tkinter.Tk()
        ws = root.tk.call("tk", "windowingsystem")
        if "x11" in ws:
            _tk_type = "xquartz"
        elif "aqua" not in ws:
            _tk_type = "other"
        elif "AppKit" in root.tk.call("winfo", "server", "."):
            _tk_type = "cocoa"
        else:
            _tk_type = "carbon"
        root.destroy()
    else:
        _tk_type = "other"


def isAquaTk():
    "\n    Returns True if IDLE is using a native OS X Tk (Cocoa or Carbon).\n    "
    if not _tk_type:
        _init_tk_type()
    return (_tk_type == "cocoa") or (_tk_type == "carbon")


def isCarbonTk():
    "\n    Returns True if IDLE is using a Carbon Aqua Tk (instead of the\n    newer Cocoa Aqua Tk).\n    "
    if not _tk_type:
        _init_tk_type()
    return _tk_type == "carbon"


def isCocoaTk():
    "\n    Returns True if IDLE is using a Cocoa Aqua Tk.\n    "
    if not _tk_type:
        _init_tk_type()
    return _tk_type == "cocoa"


def isXQuartz():
    "\n    Returns True if IDLE is using an OS X X11 Tk.\n    "
    if not _tk_type:
        _init_tk_type()
    return _tk_type == "xquartz"


def tkVersionWarning(root):
    "\n    Returns a string warning message if the Tk version in use appears to\n    be one known to cause problems with IDLE.\n    1. Apple Cocoa-based Tk 8.5.7 shipped with Mac OS X 10.6 is unusable.\n    2. Apple Cocoa-based Tk 8.5.9 in OS X 10.7 and 10.8 is better but\n        can still crash unexpectedly.\n    "
    if isCocoaTk():
        patchlevel = root.tk.call("info", "patchlevel")
        if patchlevel not in ("8.5.7", "8.5.9"):
            return False
        return "WARNING: The version of Tcl/Tk ({0}) in use may be unstable.\nVisit http://www.python.org/download/mac/tcltk/ for current information.".format(
            patchlevel
        )
    else:
        return False


def readSystemPreferences():
    "\n    Fetch the macOS system preferences.\n    "
    if platform != "darwin":
        return None
    plist_path = expanduser("~/Library/Preferences/.GlobalPreferences.plist")
    try:
        with open(plist_path, "rb") as plist_file:
            return plistlib.load(plist_file)
    except OSError:
        return None


def preferTabsPreferenceWarning():
    '\n    Warn if "Prefer tabs when opening documents" is set to "Always".\n    '
    if platform != "darwin":
        return None
    prefs = readSystemPreferences()
    if prefs and (prefs.get("AppleWindowTabbingMode") == "always"):
        return 'WARNING: The system preference "Prefer tabs when opening documents" is set to "Always". This will cause various problems with IDLE. For the best experience, change this setting when running IDLE (via System Preferences -> Dock).'
    return None


def addOpenEventSupport(root, flist):
    "\n    This ensures that the application will respond to open AppleEvents, which\n    makes is feasible to use IDLE as the default application for python files.\n    "

    def doOpenFile(*args):
        for fn in args:
            flist.open(fn)

    root.createcommand("::tk::mac::OpenDocument", doOpenFile)


def hideTkConsole(root):
    try:
        root.tk.call("console", "hide")
    except tkinter.TclError:
        pass


def overrideRootMenu(root, flist):
    "\n    Replace the Tk root menu by something that is more appropriate for\n    IDLE with an Aqua Tk.\n    "
    from tkinter import Menu
    from idlelib import mainmenu
    from idlelib import window

    closeItem = mainmenu.menudefs[0][1][(-2)]
    del mainmenu.menudefs[0][1][(-3):]
    mainmenu.menudefs[0][1].insert(6, closeItem)
    del mainmenu.menudefs[(-1)][1][0:2]
    del mainmenu.menudefs[(-3)][1][0:2]
    menubar = Menu(root)
    root.configure(menu=menubar)
    menudict = {}
    menudict["window"] = menu = Menu(menubar, name="window", tearoff=0)
    menubar.add_cascade(label="Window", menu=menu, underline=0)

    def postwindowsmenu(menu=menu):
        end = menu.index("end")
        if end is None:
            end = -1
        if end > 0:
            menu.delete(0, end)
        window.add_windows_to_menu(menu)

    window.register_callback(postwindowsmenu)

    def about_dialog(event=None):
        "Handle Help 'About IDLE' event."
        from idlelib import help_about

        help_about.AboutDialog(root)

    def config_dialog(event=None):
        "Handle Options 'Configure IDLE' event."
        from idlelib import configdialog

        root.instance_dict = flist.inversedict
        configdialog.ConfigDialog(root, "Settings")

    def help_dialog(event=None):
        "Handle Help 'IDLE Help' event."
        from idlelib import help

        help.show_idlehelp(root)

    root.bind("<<about-idle>>", about_dialog)
    root.bind("<<open-config-dialog>>", config_dialog)
    root.createcommand("::tk::mac::ShowPreferences", config_dialog)
    if flist:
        root.bind("<<close-all-windows>>", flist.close_all_callback)
        root.createcommand("exit", flist.close_all_callback)
    if isCarbonTk():
        menudict["application"] = menu = Menu(menubar, name="apple", tearoff=0)
        menubar.add_cascade(label="IDLE", menu=menu)
        mainmenu.menudefs.insert(
            0, ("application", [("About IDLE", "<<about-idle>>"), None])
        )
    if isCocoaTk():
        root.createcommand("tkAboutDialog", about_dialog)
        root.createcommand("::tk::mac::ShowHelp", help_dialog)
        del mainmenu.menudefs[(-1)][1][0]


def fixb2context(root):
    "Removed bad AquaTk Button-2 (right) and Paste bindings.\n\n    They prevent context menu access and seem to be gone in AquaTk8.6.\n    See issue #24801.\n    "
    root.unbind_class("Text", "<B2>")
    root.unbind_class("Text", "<B2-Motion>")
    root.unbind_class("Text", "<<PasteSelection>>")


def setupApp(root, flist):
    "\n    Perform initial OS X customizations if needed.\n    Called from pyshell.main() after initial calls to Tk()\n\n    There are currently three major versions of Tk in use on OS X:\n        1. Aqua Cocoa Tk (native default since OS X 10.6)\n        2. Aqua Carbon Tk (original native, 32-bit only, deprecated)\n        3. X11 (supported by some third-party distributors, deprecated)\n    There are various differences among the three that affect IDLE\n    behavior, primarily with menus, mouse key events, and accelerators.\n    Some one-time customizations are performed here.\n    Others are dynamically tested throughout idlelib by calls to the\n    isAquaTk(), isCarbonTk(), isCocoaTk(), isXQuartz() functions which\n    are initialized here as well.\n    "
    if isAquaTk():
        hideTkConsole(root)
        overrideRootMenu(root, flist)
        addOpenEventSupport(root, flist)
        fixb2context(root)


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_macosx", verbosity=2)
