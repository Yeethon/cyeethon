'Wrapper functions for Tcl/Tk.\n\nTkinter provides classes which allow the display, positioning and\ncontrol of widgets. Toplevel widgets are Tk and Toplevel. Other\nwidgets are Frame, Label, Entry, Text, Canvas, Button, Radiobutton,\nCheckbutton, Scale, Listbox, Scrollbar, OptionMenu, Spinbox\nLabelFrame and PanedWindow.\n\nProperties of the widgets are specified with keyword arguments.\nKeyword arguments have the same name as the corresponding resource\nunder Tk.\n\nWidgets are positioned with one of the geometry managers Place, Pack\nor Grid. These managers can be called with methods place, pack, grid\navailable in every Widget.\n\nActions are bound to events by resources (e.g. keyword argument\ncommand) or with the method bind.\n\nExample (Hello, World):\nimport tkinter\nfrom tkinter.constants import *\ntk = tkinter.Tk()\nframe = tkinter.Frame(tk, relief=RIDGE, borderwidth=2)\nframe.pack(fill=BOTH,expand=1)\nlabel = tkinter.Label(frame, text="Hello, World")\nlabel.pack(fill=X, expand=1)\nbutton = tkinter.Button(frame,text="Exit",command=tk.destroy)\nbutton.pack(side=BOTTOM)\ntk.mainloop()\n'
import enum
import sys
import types
import _tkinter

TclError = _tkinter.TclError
from tkinter.constants import *
import re

wantobjects = 1
TkVersion = float(_tkinter.TK_VERSION)
TclVersion = float(_tkinter.TCL_VERSION)
READABLE = _tkinter.READABLE
WRITABLE = _tkinter.WRITABLE
EXCEPTION = _tkinter.EXCEPTION
_magic_re = re.compile("([\\\\{}])")
_space_re = re.compile("([\\s])", re.ASCII)


def _join(value):
    "Internal function."
    return " ".join(map(_stringify, value))


def _stringify(value):
    "Internal function."
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = _stringify(value[0])
            if _magic_re.search(value):
                value = "{%s}" % value
        else:
            value = "{%s}" % _join(value)
    else:
        value = str(value)
        if not value:
            value = "{}"
        elif _magic_re.search(value):
            value = _magic_re.sub("\\\\\\1", value)
            value = value.replace("\n", "\\n")
            value = _space_re.sub("\\\\\\1", value)
            if value[0] == '"':
                value = "\\" + value
        elif (value[0] == '"') or _space_re.search(value):
            value = "{%s}" % value
    return value


def _flatten(seq):
    "Internal function."
    res = ()
    for item in seq:
        if isinstance(item, (tuple, list)):
            res = res + _flatten(item)
        elif item is not None:
            res = res + (item,)
    return res


try:
    _flatten = _tkinter._flatten
except AttributeError:
    pass


def _cnfmerge(cnfs):
    "Internal function."
    if isinstance(cnfs, dict):
        return cnfs
    elif isinstance(cnfs, (type(None), str)):
        return cnfs
    else:
        cnf = {}
        for c in _flatten(cnfs):
            try:
                cnf.update(c)
            except (AttributeError, TypeError) as msg:
                print("_cnfmerge: fallback due to:", msg)
                for (k, v) in c.items():
                    cnf[k] = v
        return cnf


try:
    _cnfmerge = _tkinter._cnfmerge
except AttributeError:
    pass


def _splitdict(tk, v, cut_minus=True, conv=None):
    "Return a properly formatted dict built from Tcl list pairs.\n\n    If cut_minus is True, the supposed '-' prefix will be removed from\n    keys. If conv is specified, it is used to convert values.\n\n    Tcl list is expected to contain an even number of elements.\n    "
    t = tk.splitlist(v)
    if len(t) % 2:
        raise RuntimeError(
            "Tcl list representing a dict is expected to contain an even number of elements"
        )
    it = iter(t)
    dict = {}
    for (key, value) in zip(it, it):
        key = str(key)
        if cut_minus and (key[0] == "-"):
            key = key[1:]
        if conv:
            value = conv(value)
        dict[key] = value
    return dict


@enum._simple_enum(enum.StrEnum)
class EventType:
    KeyPress = "2"
    Key = KeyPress
    KeyRelease = "3"
    ButtonPress = "4"
    Button = ButtonPress
    ButtonRelease = "5"
    Motion = "6"
    Enter = "7"
    Leave = "8"
    FocusIn = "9"
    FocusOut = "10"
    Keymap = "11"
    Expose = "12"
    GraphicsExpose = "13"
    NoExpose = "14"
    Visibility = "15"
    Create = "16"
    Destroy = "17"
    Unmap = "18"
    Map = "19"
    MapRequest = "20"
    Reparent = "21"
    Configure = "22"
    ConfigureRequest = "23"
    Gravity = "24"
    ResizeRequest = "25"
    Circulate = "26"
    CirculateRequest = "27"
    Property = "28"
    SelectionClear = "29"
    SelectionRequest = "30"
    Selection = "31"
    Colormap = "32"
    ClientMessage = "33"
    Mapping = "34"
    VirtualEvent = "35"
    Activate = "36"
    Deactivate = "37"
    MouseWheel = "38"


class Event:
    "Container for the properties of an event.\n\n    Instances of this type are generated if one of the following events occurs:\n\n    KeyPress, KeyRelease - for keyboard events\n    ButtonPress, ButtonRelease, Motion, Enter, Leave, MouseWheel - for mouse events\n    Visibility, Unmap, Map, Expose, FocusIn, FocusOut, Circulate,\n    Colormap, Gravity, Reparent, Property, Destroy, Activate,\n    Deactivate - for window events.\n\n    If a callback function for one of these events is registered\n    using bind, bind_all, bind_class, or tag_bind, the callback is\n    called with an Event as first argument. It will have the\n    following attributes (in braces are the event types for which\n    the attribute is valid):\n\n        serial - serial number of event\n    num - mouse button pressed (ButtonPress, ButtonRelease)\n    focus - whether the window has the focus (Enter, Leave)\n    height - height of the exposed window (Configure, Expose)\n    width - width of the exposed window (Configure, Expose)\n    keycode - keycode of the pressed key (KeyPress, KeyRelease)\n    state - state of the event as a number (ButtonPress, ButtonRelease,\n                            Enter, KeyPress, KeyRelease,\n                            Leave, Motion)\n    state - state as a string (Visibility)\n    time - when the event occurred\n    x - x-position of the mouse\n    y - y-position of the mouse\n    x_root - x-position of the mouse on the screen\n             (ButtonPress, ButtonRelease, KeyPress, KeyRelease, Motion)\n    y_root - y-position of the mouse on the screen\n             (ButtonPress, ButtonRelease, KeyPress, KeyRelease, Motion)\n    char - pressed character (KeyPress, KeyRelease)\n    send_event - see X/Windows documentation\n    keysym - keysym of the event as a string (KeyPress, KeyRelease)\n    keysym_num - keysym of the event as a number (KeyPress, KeyRelease)\n    type - type of the event as a number\n    widget - widget in which the event occurred\n    delta - delta of wheel movement (MouseWheel)\n    "

    def __repr__(self):
        attrs = {k: v for (k, v) in self.__dict__.items() if (v != "??")}
        if not self.char:
            del attrs["char"]
        elif self.char != "??":
            attrs["char"] = repr(self.char)
        if not getattr(self, "send_event", True):
            del attrs["send_event"]
        if self.state == 0:
            del attrs["state"]
        elif isinstance(self.state, int):
            state = self.state
            mods = (
                "Shift",
                "Lock",
                "Control",
                "Mod1",
                "Mod2",
                "Mod3",
                "Mod4",
                "Mod5",
                "Button1",
                "Button2",
                "Button3",
                "Button4",
                "Button5",
            )
            s = []
            for (i, n) in enumerate(mods):
                if state & (1 << i):
                    s.append(n)
            state = state & (~((1 << len(mods)) - 1))
            if state or (not s):
                s.append(hex(state))
            attrs["state"] = "|".join(s)
        if self.delta == 0:
            del attrs["delta"]
        keys = (
            "send_event",
            "state",
            "keysym",
            "keycode",
            "char",
            "num",
            "delta",
            "focus",
            "x",
            "y",
            "width",
            "height",
        )
        return "<%s event%s>" % (
            getattr(self.type, "name", self.type),
            "".join(((" %s=%s" % (k, attrs[k])) for k in keys if (k in attrs))),
        )


_support_default_root = True
_default_root = None


def NoDefaultRoot():
    "Inhibit setting of default root window.\n\n    Call this function to inhibit that the first instance of\n    Tk is used for windows without an explicit parent window.\n    "
    global _support_default_root, _default_root
    _support_default_root = False
    _default_root = None
    del _default_root


def _get_default_root(what=None):
    if not _support_default_root:
        raise RuntimeError(
            "No master specified and tkinter is configured to not support default root"
        )
    if _default_root is None:
        if what:
            raise RuntimeError(f"Too early to {what}: no default root window")
        root = Tk()
        assert _default_root is root
    return _default_root


def _get_temp_root():
    global _support_default_root
    if not _support_default_root:
        raise RuntimeError(
            "No master specified and tkinter is configured to not support default root"
        )
    root = _default_root
    if root is None:
        assert _support_default_root
        _support_default_root = False
        root = Tk()
        _support_default_root = True
        assert _default_root is None
        root.withdraw()
        root._temporary = True
    return root


def _destroy_temp_root(master):
    if getattr(master, "_temporary", False):
        try:
            master.destroy()
        except TclError:
            pass


def _tkerror(err):
    "Internal function."
    pass


def _exit(code=0):
    "Internal function. Calling it will raise the exception SystemExit."
    try:
        code = int(code)
    except ValueError:
        pass
    raise SystemExit(code)


_varnum = 0


class Variable:
    "Class to define value holders for e.g. buttons.\n\n    Subclasses StringVar, IntVar, DoubleVar, BooleanVar are specializations\n    that constrain the type of the value returned from get()."
    _default = ""
    _tk = None
    _tclCommands = None

    def __init__(self, master=None, value=None, name=None):
        'Construct a variable\n\n        MASTER can be given as master widget.\n        VALUE is an optional value (defaults to "")\n        NAME is an optional Tcl name (defaults to PY_VARnum).\n\n        If NAME matches an existing variable and VALUE is omitted\n        then the existing value is retained.\n        '
        if (name is not None) and (not isinstance(name, str)):
            raise TypeError("name must be a string")
        global _varnum
        if master is None:
            master = _get_default_root("create variable")
        self._root = master._root()
        self._tk = master.tk
        if name:
            self._name = name
        else:
            self._name = "PY_VAR" + repr(_varnum)
            _varnum += 1
        if value is not None:
            self.initialize(value)
        elif not self._tk.getboolean(self._tk.call("info", "exists", self._name)):
            self.initialize(self._default)

    def __del__(self):
        "Unset the variable in Tcl."
        if self._tk is None:
            return
        if self._tk.getboolean(self._tk.call("info", "exists", self._name)):
            self._tk.globalunsetvar(self._name)
        if self._tclCommands is not None:
            for name in self._tclCommands:
                self._tk.deletecommand(name)
            self._tclCommands = None

    def __str__(self):
        "Return the name of the variable in Tcl."
        return self._name

    def set(self, value):
        "Set the variable to VALUE."
        return self._tk.globalsetvar(self._name, value)

    initialize = set

    def get(self):
        "Return value of variable."
        return self._tk.globalgetvar(self._name)

    def _register(self, callback):
        f = CallWrapper(callback, None, self._root).__call__
        cbname = repr(id(f))
        try:
            callback = callback.__func__
        except AttributeError:
            pass
        try:
            cbname = cbname + callback.__name__
        except AttributeError:
            pass
        self._tk.createcommand(cbname, f)
        if self._tclCommands is None:
            self._tclCommands = []
        self._tclCommands.append(cbname)
        return cbname

    def trace_add(self, mode, callback):
        'Define a trace callback for the variable.\n\n        Mode is one of "read", "write", "unset", or a list or tuple of\n        such strings.\n        Callback must be a function which is called when the variable is\n        read, written or unset.\n\n        Return the name of the callback.\n        '
        cbname = self._register(callback)
        self._tk.call("trace", "add", "variable", self._name, mode, (cbname,))
        return cbname

    def trace_remove(self, mode, cbname):
        'Delete the trace callback for a variable.\n\n        Mode is one of "read", "write", "unset" or a list or tuple of\n        such strings.  Must be same as were specified in trace_add().\n        cbname is the name of the callback returned from trace_add().\n        '
        self._tk.call("trace", "remove", "variable", self._name, mode, cbname)
        for (m, ca) in self.trace_info():
            if self._tk.splitlist(ca)[0] == cbname:
                break
        else:
            self._tk.deletecommand(cbname)
            try:
                self._tclCommands.remove(cbname)
            except ValueError:
                pass

    def trace_info(self):
        "Return all trace callback information."
        splitlist = self._tk.splitlist
        return [
            (splitlist(k), v)
            for (k, v) in map(
                splitlist,
                splitlist(self._tk.call("trace", "info", "variable", self._name)),
            )
        ]

    def trace_variable(self, mode, callback):
        'Define a trace callback for the variable.\n\n        MODE is one of "r", "w", "u" for read, write, undefine.\n        CALLBACK must be a function which is called when\n        the variable is read, written or undefined.\n\n        Return the name of the callback.\n\n        This deprecated method wraps a deprecated Tcl method that will\n        likely be removed in the future.  Use trace_add() instead.\n        '
        cbname = self._register(callback)
        self._tk.call("trace", "variable", self._name, mode, cbname)
        return cbname

    trace = trace_variable

    def trace_vdelete(self, mode, cbname):
        'Delete the trace callback for a variable.\n\n        MODE is one of "r", "w", "u" for read, write, undefine.\n        CBNAME is the name of the callback returned from trace_variable or trace.\n\n        This deprecated method wraps a deprecated Tcl method that will\n        likely be removed in the future.  Use trace_remove() instead.\n        '
        self._tk.call("trace", "vdelete", self._name, mode, cbname)
        cbname = self._tk.splitlist(cbname)[0]
        for (m, ca) in self.trace_info():
            if self._tk.splitlist(ca)[0] == cbname:
                break
        else:
            self._tk.deletecommand(cbname)
            try:
                self._tclCommands.remove(cbname)
            except ValueError:
                pass

    def trace_vinfo(self):
        "Return all trace callback information.\n\n        This deprecated method wraps a deprecated Tcl method that will\n        likely be removed in the future.  Use trace_info() instead.\n        "
        return [
            self._tk.splitlist(x)
            for x in self._tk.splitlist(self._tk.call("trace", "vinfo", self._name))
        ]

    def __eq__(self, other):
        if not isinstance(other, Variable):
            return NotImplemented
        return (
            (self._name == other._name)
            and (self.__class__.__name__ == other.__class__.__name__)
            and (self._tk == other._tk)
        )


class StringVar(Variable):
    "Value holder for strings variables."
    _default = ""

    def __init__(self, master=None, value=None, name=None):
        'Construct a string variable.\n\n        MASTER can be given as master widget.\n        VALUE is an optional value (defaults to "")\n        NAME is an optional Tcl name (defaults to PY_VARnum).\n\n        If NAME matches an existing variable and VALUE is omitted\n        then the existing value is retained.\n        '
        Variable.__init__(self, master, value, name)

    def get(self):
        "Return value of variable as string."
        value = self._tk.globalgetvar(self._name)
        if isinstance(value, str):
            return value
        return str(value)


class IntVar(Variable):
    "Value holder for integer variables."
    _default = 0

    def __init__(self, master=None, value=None, name=None):
        "Construct an integer variable.\n\n        MASTER can be given as master widget.\n        VALUE is an optional value (defaults to 0)\n        NAME is an optional Tcl name (defaults to PY_VARnum).\n\n        If NAME matches an existing variable and VALUE is omitted\n        then the existing value is retained.\n        "
        Variable.__init__(self, master, value, name)

    def get(self):
        "Return the value of the variable as an integer."
        value = self._tk.globalgetvar(self._name)
        try:
            return self._tk.getint(value)
        except (TypeError, TclError):
            return int(self._tk.getdouble(value))


class DoubleVar(Variable):
    "Value holder for float variables."
    _default = 0.0

    def __init__(self, master=None, value=None, name=None):
        "Construct a float variable.\n\n        MASTER can be given as master widget.\n        VALUE is an optional value (defaults to 0.0)\n        NAME is an optional Tcl name (defaults to PY_VARnum).\n\n        If NAME matches an existing variable and VALUE is omitted\n        then the existing value is retained.\n        "
        Variable.__init__(self, master, value, name)

    def get(self):
        "Return the value of the variable as a float."
        return self._tk.getdouble(self._tk.globalgetvar(self._name))


class BooleanVar(Variable):
    "Value holder for boolean variables."
    _default = False

    def __init__(self, master=None, value=None, name=None):
        "Construct a boolean variable.\n\n        MASTER can be given as master widget.\n        VALUE is an optional value (defaults to False)\n        NAME is an optional Tcl name (defaults to PY_VARnum).\n\n        If NAME matches an existing variable and VALUE is omitted\n        then the existing value is retained.\n        "
        Variable.__init__(self, master, value, name)

    def set(self, value):
        "Set the variable to VALUE."
        return self._tk.globalsetvar(self._name, self._tk.getboolean(value))

    initialize = set

    def get(self):
        "Return the value of the variable as a bool."
        try:
            return self._tk.getboolean(self._tk.globalgetvar(self._name))
        except TclError:
            raise ValueError("invalid literal for getboolean()")


def mainloop(n=0):
    "Run the main loop of Tcl."
    _get_default_root("run the main loop").tk.mainloop(n)


getint = int
getdouble = float


def getboolean(s):
    "Convert Tcl object to True or False."
    try:
        return _get_default_root("use getboolean()").tk.getboolean(s)
    except TclError:
        raise ValueError("invalid literal for getboolean()")


class Misc:
    "Internal class.\n\n    Base class which defines methods common for interior widgets."
    _last_child_ids = None
    _tclCommands = None

    def destroy(self):
        "Internal function.\n\n        Delete all Tcl commands created for\n        this widget in the Tcl interpreter."
        if self._tclCommands is not None:
            for name in self._tclCommands:
                self.tk.deletecommand(name)
            self._tclCommands = None

    def deletecommand(self, name):
        "Internal function.\n\n        Delete the Tcl command provided in NAME."
        self.tk.deletecommand(name)
        try:
            self._tclCommands.remove(name)
        except ValueError:
            pass

    def tk_strictMotif(self, boolean=None):
        "Set Tcl internal variable, whether the look and feel\n        should adhere to Motif.\n\n        A parameter of 1 means adhere to Motif (e.g. no color\n        change if mouse passes over slider).\n        Returns the set value."
        return self.tk.getboolean(self.tk.call("set", "tk_strictMotif", boolean))

    def tk_bisque(self):
        "Change the color scheme to light brown as used in Tk 3.6 and before."
        self.tk.call("tk_bisque")

    def tk_setPalette(self, *args, **kw):
        "Set a new color scheme for all widget elements.\n\n        A single color as argument will cause that all colors of Tk\n        widget elements are derived from this.\n        Alternatively several keyword parameters and its associated\n        colors can be given. The following keywords are valid:\n        activeBackground, foreground, selectColor,\n        activeForeground, highlightBackground, selectBackground,\n        background, highlightColor, selectForeground,\n        disabledForeground, insertBackground, troughColor."
        self.tk.call(
            ((("tk_setPalette",) + _flatten(args)) + _flatten(list(kw.items())))
        )

    def wait_variable(self, name="PY_VAR"):
        "Wait until the variable is modified.\n\n        A parameter of type IntVar, StringVar, DoubleVar or\n        BooleanVar must be given."
        self.tk.call("tkwait", "variable", name)

    waitvar = wait_variable

    def wait_window(self, window=None):
        "Wait until a WIDGET is destroyed.\n\n        If no parameter is given self is used."
        if window is None:
            window = self
        self.tk.call("tkwait", "window", window._w)

    def wait_visibility(self, window=None):
        "Wait until the visibility of a WIDGET changes\n        (e.g. it appears).\n\n        If no parameter is given self is used."
        if window is None:
            window = self
        self.tk.call("tkwait", "visibility", window._w)

    def setvar(self, name="PY_VAR", value="1"):
        "Set Tcl variable NAME to VALUE."
        self.tk.setvar(name, value)

    def getvar(self, name="PY_VAR"):
        "Return value of Tcl variable NAME."
        return self.tk.getvar(name)

    def getint(self, s):
        try:
            return self.tk.getint(s)
        except TclError as exc:
            raise ValueError(str(exc))

    def getdouble(self, s):
        try:
            return self.tk.getdouble(s)
        except TclError as exc:
            raise ValueError(str(exc))

    def getboolean(self, s):
        "Return a boolean value for Tcl boolean values true and false given as parameter."
        try:
            return self.tk.getboolean(s)
        except TclError:
            raise ValueError("invalid literal for getboolean()")

    def focus_set(self):
        "Direct input focus to this widget.\n\n        If the application currently does not have the focus\n        this widget will get the focus if the application gets\n        the focus through the window manager."
        self.tk.call("focus", self._w)

    focus = focus_set

    def focus_force(self):
        "Direct input focus to this widget even if the\n        application does not have the focus. Use with\n        caution!"
        self.tk.call("focus", "-force", self._w)

    def focus_get(self):
        "Return the widget which has currently the focus in the\n        application.\n\n        Use focus_displayof to allow working with several\n        displays. Return None if application does not have\n        the focus."
        name = self.tk.call("focus")
        if (name == "none") or (not name):
            return None
        return self._nametowidget(name)

    def focus_displayof(self):
        "Return the widget which has currently the focus on the\n        display where this widget is located.\n\n        Return None if the application does not have the focus."
        name = self.tk.call("focus", "-displayof", self._w)
        if (name == "none") or (not name):
            return None
        return self._nametowidget(name)

    def focus_lastfor(self):
        "Return the widget which would have the focus if top level\n        for this widget gets the focus from the window manager."
        name = self.tk.call("focus", "-lastfor", self._w)
        if (name == "none") or (not name):
            return None
        return self._nametowidget(name)

    def tk_focusFollowsMouse(self):
        "The widget under mouse will get automatically focus. Can not\n        be disabled easily."
        self.tk.call("tk_focusFollowsMouse")

    def tk_focusNext(self):
        "Return the next widget in the focus order which follows\n        widget which has currently the focus.\n\n        The focus order first goes to the next child, then to\n        the children of the child recursively and then to the\n        next sibling which is higher in the stacking order.  A\n        widget is omitted if it has the takefocus resource set\n        to 0."
        name = self.tk.call("tk_focusNext", self._w)
        if not name:
            return None
        return self._nametowidget(name)

    def tk_focusPrev(self):
        "Return previous widget in the focus order. See tk_focusNext for details."
        name = self.tk.call("tk_focusPrev", self._w)
        if not name:
            return None
        return self._nametowidget(name)

    def after(self, ms, func=None, *args):
        "Call function once after given time.\n\n        MS specifies the time in milliseconds. FUNC gives the\n        function which shall be called. Additional parameters\n        are given as parameters to the function call.  Return\n        identifier to cancel scheduling with after_cancel."
        if func is None:
            self.tk.call("after", ms)
            return None
        else:

            def callit():
                try:
                    func(*args)
                finally:
                    try:
                        self.deletecommand(name)
                    except TclError:
                        pass

            callit.__name__ = func.__name__
            name = self._register(callit)
            return self.tk.call("after", ms, name)

    def after_idle(self, func, *args):
        "Call FUNC once if the Tcl main loop has no event to\n        process.\n\n        Return an identifier to cancel the scheduling with\n        after_cancel."
        return self.after("idle", func, *args)

    def after_cancel(self, id):
        "Cancel scheduling of function identified with ID.\n\n        Identifier returned by after or after_idle must be\n        given as first parameter.\n        "
        if not id:
            raise ValueError(
                "id must be a valid identifier returned from after or after_idle"
            )
        try:
            data = self.tk.call("after", "info", id)
            script = self.tk.splitlist(data)[0]
            self.deletecommand(script)
        except TclError:
            pass
        self.tk.call("after", "cancel", id)

    def bell(self, displayof=0):
        "Ring a display's bell."
        self.tk.call((("bell",) + self._displayof(displayof)))

    def clipboard_get(self, **kw):
        "Retrieve data from the clipboard on window's display.\n\n        The window keyword defaults to the root window of the Tkinter\n        application.\n\n        The type keyword specifies the form in which the data is\n        to be returned and should be an atom name such as STRING\n        or FILE_NAME.  Type defaults to STRING, except on X11, where the default\n        is to try UTF8_STRING and fall back to STRING.\n\n        This command is equivalent to:\n\n        selection_get(CLIPBOARD)\n        "
        if ("type" not in kw) and (self._windowingsystem == "x11"):
            try:
                kw["type"] = "UTF8_STRING"
                return self.tk.call((("clipboard", "get") + self._options(kw)))
            except TclError:
                del kw["type"]
        return self.tk.call((("clipboard", "get") + self._options(kw)))

    def clipboard_clear(self, **kw):
        "Clear the data in the Tk clipboard.\n\n        A widget specified for the optional displayof keyword\n        argument specifies the target display."
        if "displayof" not in kw:
            kw["displayof"] = self._w
        self.tk.call((("clipboard", "clear") + self._options(kw)))

    def clipboard_append(self, string, **kw):
        "Append STRING to the Tk clipboard.\n\n        A widget specified at the optional displayof keyword\n        argument specifies the target display. The clipboard\n        can be retrieved with selection_get."
        if "displayof" not in kw:
            kw["displayof"] = self._w
        self.tk.call(((("clipboard", "append") + self._options(kw)) + ("--", string)))

    def grab_current(self):
        "Return widget which has currently the grab in this application\n        or None."
        name = self.tk.call("grab", "current", self._w)
        if not name:
            return None
        return self._nametowidget(name)

    def grab_release(self):
        "Release grab for this widget if currently set."
        self.tk.call("grab", "release", self._w)

    def grab_set(self):
        "Set grab for this widget.\n\n        A grab directs all events to this and descendant\n        widgets in the application."
        self.tk.call("grab", "set", self._w)

    def grab_set_global(self):
        "Set global grab for this widget.\n\n        A global grab directs all events to this and\n        descendant widgets on the display. Use with caution -\n        other applications do not get events anymore."
        self.tk.call("grab", "set", "-global", self._w)

    def grab_status(self):
        'Return None, "local" or "global" if this widget has\n        no, a local or a global grab.'
        status = self.tk.call("grab", "status", self._w)
        if status == "none":
            status = None
        return status

    def option_add(self, pattern, value, priority=None):
        "Set a VALUE (second parameter) for an option\n        PATTERN (first parameter).\n\n        An optional third parameter gives the numeric priority\n        (defaults to 80)."
        self.tk.call("option", "add", pattern, value, priority)

    def option_clear(self):
        "Clear the option database.\n\n        It will be reloaded if option_add is called."
        self.tk.call("option", "clear")

    def option_get(self, name, className):
        "Return the value for an option NAME for this widget\n        with CLASSNAME.\n\n        Values with higher priority override lower values."
        return self.tk.call("option", "get", self._w, name, className)

    def option_readfile(self, fileName, priority=None):
        "Read file FILENAME into the option database.\n\n        An optional second parameter gives the numeric\n        priority."
        self.tk.call("option", "readfile", fileName, priority)

    def selection_clear(self, **kw):
        "Clear the current X selection."
        if "displayof" not in kw:
            kw["displayof"] = self._w
        self.tk.call((("selection", "clear") + self._options(kw)))

    def selection_get(self, **kw):
        "Return the contents of the current X selection.\n\n        A keyword parameter selection specifies the name of\n        the selection and defaults to PRIMARY.  A keyword\n        parameter displayof specifies a widget on the display\n        to use. A keyword parameter type specifies the form of data to be\n        fetched, defaulting to STRING except on X11, where UTF8_STRING is tried\n        before STRING."
        if "displayof" not in kw:
            kw["displayof"] = self._w
        if ("type" not in kw) and (self._windowingsystem == "x11"):
            try:
                kw["type"] = "UTF8_STRING"
                return self.tk.call((("selection", "get") + self._options(kw)))
            except TclError:
                del kw["type"]
        return self.tk.call((("selection", "get") + self._options(kw)))

    def selection_handle(self, command, **kw):
        "Specify a function COMMAND to call if the X\n        selection owned by this widget is queried by another\n        application.\n\n        This function must return the contents of the\n        selection. The function will be called with the\n        arguments OFFSET and LENGTH which allows the chunking\n        of very long selections. The following keyword\n        parameters can be provided:\n        selection - name of the selection (default PRIMARY),\n        type - type of the selection (e.g. STRING, FILE_NAME)."
        name = self._register(command)
        self.tk.call(((("selection", "handle") + self._options(kw)) + (self._w, name)))

    def selection_own(self, **kw):
        "Become owner of X selection.\n\n        A keyword parameter selection specifies the name of\n        the selection (default PRIMARY)."
        self.tk.call(((("selection", "own") + self._options(kw)) + (self._w,)))

    def selection_own_get(self, **kw):
        "Return owner of X selection.\n\n        The following keyword parameter can\n        be provided:\n        selection - name of the selection (default PRIMARY),\n        type - type of the selection (e.g. STRING, FILE_NAME)."
        if "displayof" not in kw:
            kw["displayof"] = self._w
        name = self.tk.call((("selection", "own") + self._options(kw)))
        if not name:
            return None
        return self._nametowidget(name)

    def send(self, interp, cmd, *args):
        "Send Tcl command CMD to different interpreter INTERP to be executed."
        return self.tk.call((("send", interp, cmd) + args))

    def lower(self, belowThis=None):
        "Lower this widget in the stacking order."
        self.tk.call("lower", self._w, belowThis)

    def tkraise(self, aboveThis=None):
        "Raise this widget in the stacking order."
        self.tk.call("raise", self._w, aboveThis)

    lift = tkraise

    def winfo_atom(self, name, displayof=0):
        "Return integer which represents atom NAME."
        args = (("winfo", "atom") + self._displayof(displayof)) + (name,)
        return self.tk.getint(self.tk.call(args))

    def winfo_atomname(self, id, displayof=0):
        "Return name of atom with identifier ID."
        args = (("winfo", "atomname") + self._displayof(displayof)) + (id,)
        return self.tk.call(args)

    def winfo_cells(self):
        "Return number of cells in the colormap for this widget."
        return self.tk.getint(self.tk.call("winfo", "cells", self._w))

    def winfo_children(self):
        "Return a list of all widgets which are children of this widget."
        result = []
        for child in self.tk.splitlist(self.tk.call("winfo", "children", self._w)):
            try:
                result.append(self._nametowidget(child))
            except KeyError:
                pass
        return result

    def winfo_class(self):
        "Return window class name of this widget."
        return self.tk.call("winfo", "class", self._w)

    def winfo_colormapfull(self):
        "Return True if at the last color request the colormap was full."
        return self.tk.getboolean(self.tk.call("winfo", "colormapfull", self._w))

    def winfo_containing(self, rootX, rootY, displayof=0):
        "Return the widget which is at the root coordinates ROOTX, ROOTY."
        args = (("winfo", "containing") + self._displayof(displayof)) + (rootX, rootY)
        name = self.tk.call(args)
        if not name:
            return None
        return self._nametowidget(name)

    def winfo_depth(self):
        "Return the number of bits per pixel."
        return self.tk.getint(self.tk.call("winfo", "depth", self._w))

    def winfo_exists(self):
        "Return true if this widget exists."
        return self.tk.getint(self.tk.call("winfo", "exists", self._w))

    def winfo_fpixels(self, number):
        'Return the number of pixels for the given distance NUMBER\n        (e.g. "3c") as float.'
        return self.tk.getdouble(self.tk.call("winfo", "fpixels", self._w, number))

    def winfo_geometry(self):
        'Return geometry string for this widget in the form "widthxheight+X+Y".'
        return self.tk.call("winfo", "geometry", self._w)

    def winfo_height(self):
        "Return height of this widget."
        return self.tk.getint(self.tk.call("winfo", "height", self._w))

    def winfo_id(self):
        "Return identifier ID for this widget."
        return int(self.tk.call("winfo", "id", self._w), 0)

    def winfo_interps(self, displayof=0):
        "Return the name of all Tcl interpreters for this display."
        args = ("winfo", "interps") + self._displayof(displayof)
        return self.tk.splitlist(self.tk.call(args))

    def winfo_ismapped(self):
        "Return true if this widget is mapped."
        return self.tk.getint(self.tk.call("winfo", "ismapped", self._w))

    def winfo_manager(self):
        "Return the window manager name for this widget."
        return self.tk.call("winfo", "manager", self._w)

    def winfo_name(self):
        "Return the name of this widget."
        return self.tk.call("winfo", "name", self._w)

    def winfo_parent(self):
        "Return the name of the parent of this widget."
        return self.tk.call("winfo", "parent", self._w)

    def winfo_pathname(self, id, displayof=0):
        "Return the pathname of the widget given by ID."
        args = (("winfo", "pathname") + self._displayof(displayof)) + (id,)
        return self.tk.call(args)

    def winfo_pixels(self, number):
        "Rounded integer value of winfo_fpixels."
        return self.tk.getint(self.tk.call("winfo", "pixels", self._w, number))

    def winfo_pointerx(self):
        "Return the x coordinate of the pointer on the root window."
        return self.tk.getint(self.tk.call("winfo", "pointerx", self._w))

    def winfo_pointerxy(self):
        "Return a tuple of x and y coordinates of the pointer on the root window."
        return self._getints(self.tk.call("winfo", "pointerxy", self._w))

    def winfo_pointery(self):
        "Return the y coordinate of the pointer on the root window."
        return self.tk.getint(self.tk.call("winfo", "pointery", self._w))

    def winfo_reqheight(self):
        "Return requested height of this widget."
        return self.tk.getint(self.tk.call("winfo", "reqheight", self._w))

    def winfo_reqwidth(self):
        "Return requested width of this widget."
        return self.tk.getint(self.tk.call("winfo", "reqwidth", self._w))

    def winfo_rgb(self, color):
        "Return a tuple of integer RGB values in range(65536) for color in this widget."
        return self._getints(self.tk.call("winfo", "rgb", self._w, color))

    def winfo_rootx(self):
        "Return x coordinate of upper left corner of this widget on the\n        root window."
        return self.tk.getint(self.tk.call("winfo", "rootx", self._w))

    def winfo_rooty(self):
        "Return y coordinate of upper left corner of this widget on the\n        root window."
        return self.tk.getint(self.tk.call("winfo", "rooty", self._w))

    def winfo_screen(self):
        "Return the screen name of this widget."
        return self.tk.call("winfo", "screen", self._w)

    def winfo_screencells(self):
        "Return the number of the cells in the colormap of the screen\n        of this widget."
        return self.tk.getint(self.tk.call("winfo", "screencells", self._w))

    def winfo_screendepth(self):
        "Return the number of bits per pixel of the root window of the\n        screen of this widget."
        return self.tk.getint(self.tk.call("winfo", "screendepth", self._w))

    def winfo_screenheight(self):
        "Return the number of pixels of the height of the screen of this widget\n        in pixel."
        return self.tk.getint(self.tk.call("winfo", "screenheight", self._w))

    def winfo_screenmmheight(self):
        "Return the number of pixels of the height of the screen of\n        this widget in mm."
        return self.tk.getint(self.tk.call("winfo", "screenmmheight", self._w))

    def winfo_screenmmwidth(self):
        "Return the number of pixels of the width of the screen of\n        this widget in mm."
        return self.tk.getint(self.tk.call("winfo", "screenmmwidth", self._w))

    def winfo_screenvisual(self):
        "Return one of the strings directcolor, grayscale, pseudocolor,\n        staticcolor, staticgray, or truecolor for the default\n        colormodel of this screen."
        return self.tk.call("winfo", "screenvisual", self._w)

    def winfo_screenwidth(self):
        "Return the number of pixels of the width of the screen of\n        this widget in pixel."
        return self.tk.getint(self.tk.call("winfo", "screenwidth", self._w))

    def winfo_server(self):
        'Return information of the X-Server of the screen of this widget in\n        the form "XmajorRminor vendor vendorVersion".'
        return self.tk.call("winfo", "server", self._w)

    def winfo_toplevel(self):
        "Return the toplevel widget of this widget."
        return self._nametowidget(self.tk.call("winfo", "toplevel", self._w))

    def winfo_viewable(self):
        "Return true if the widget and all its higher ancestors are mapped."
        return self.tk.getint(self.tk.call("winfo", "viewable", self._w))

    def winfo_visual(self):
        "Return one of the strings directcolor, grayscale, pseudocolor,\n        staticcolor, staticgray, or truecolor for the\n        colormodel of this widget."
        return self.tk.call("winfo", "visual", self._w)

    def winfo_visualid(self):
        "Return the X identifier for the visual for this widget."
        return self.tk.call("winfo", "visualid", self._w)

    def winfo_visualsavailable(self, includeids=False):
        "Return a list of all visuals available for the screen\n        of this widget.\n\n        Each item in the list consists of a visual name (see winfo_visual), a\n        depth and if includeids is true is given also the X identifier."
        data = self.tk.call(
            "winfo", "visualsavailable", self._w, ("includeids" if includeids else None)
        )
        data = [self.tk.splitlist(x) for x in self.tk.splitlist(data)]
        return [self.__winfo_parseitem(x) for x in data]

    def __winfo_parseitem(self, t):
        "Internal function."
        return t[:1] + tuple(map(self.__winfo_getint, t[1:]))

    def __winfo_getint(self, x):
        "Internal function."
        return int(x, 0)

    def winfo_vrootheight(self):
        "Return the height of the virtual root window associated with this\n        widget in pixels. If there is no virtual root window return the\n        height of the screen."
        return self.tk.getint(self.tk.call("winfo", "vrootheight", self._w))

    def winfo_vrootwidth(self):
        "Return the width of the virtual root window associated with this\n        widget in pixel. If there is no virtual root window return the\n        width of the screen."
        return self.tk.getint(self.tk.call("winfo", "vrootwidth", self._w))

    def winfo_vrootx(self):
        "Return the x offset of the virtual root relative to the root\n        window of the screen of this widget."
        return self.tk.getint(self.tk.call("winfo", "vrootx", self._w))

    def winfo_vrooty(self):
        "Return the y offset of the virtual root relative to the root\n        window of the screen of this widget."
        return self.tk.getint(self.tk.call("winfo", "vrooty", self._w))

    def winfo_width(self):
        "Return the width of this widget."
        return self.tk.getint(self.tk.call("winfo", "width", self._w))

    def winfo_x(self):
        "Return the x coordinate of the upper left corner of this widget\n        in the parent."
        return self.tk.getint(self.tk.call("winfo", "x", self._w))

    def winfo_y(self):
        "Return the y coordinate of the upper left corner of this widget\n        in the parent."
        return self.tk.getint(self.tk.call("winfo", "y", self._w))

    def update(self):
        "Enter event loop until all pending events have been processed by Tcl."
        self.tk.call("update")

    def update_idletasks(self):
        "Enter event loop until all idle callbacks have been called. This\n        will update the display of windows but not process events caused by\n        the user."
        self.tk.call("update", "idletasks")

    def bindtags(self, tagList=None):
        "Set or get the list of bindtags for this widget.\n\n        With no argument return the list of all bindtags associated with\n        this widget. With a list of strings as argument the bindtags are\n        set to this list. The bindtags determine in which order events are\n        processed (see bind)."
        if tagList is None:
            return self.tk.splitlist(self.tk.call("bindtags", self._w))
        else:
            self.tk.call("bindtags", self._w, tagList)

    def _bind(self, what, sequence, func, add, needcleanup=1):
        "Internal function."
        if isinstance(func, str):
            self.tk.call((what + (sequence, func)))
        elif func:
            funcid = self._register(func, self._substitute, needcleanup)
            cmd = '%sif {"[%s %s]" == "break"} break\n' % (
                ((add and "+") or ""),
                funcid,
                self._subst_format_str,
            )
            self.tk.call((what + (sequence, cmd)))
            return funcid
        elif sequence:
            return self.tk.call((what + (sequence,)))
        else:
            return self.tk.splitlist(self.tk.call(what))

    def bind(self, sequence=None, func=None, add=None):
        'Bind to this widget at event SEQUENCE a call to function FUNC.\n\n        SEQUENCE is a string of concatenated event\n        patterns. An event pattern is of the form\n        <MODIFIER-MODIFIER-TYPE-DETAIL> where MODIFIER is one\n        of Control, Mod2, M2, Shift, Mod3, M3, Lock, Mod4, M4,\n        Button1, B1, Mod5, M5 Button2, B2, Meta, M, Button3,\n        B3, Alt, Button4, B4, Double, Button5, B5 Triple,\n        Mod1, M1. TYPE is one of Activate, Enter, Map,\n        ButtonPress, Button, Expose, Motion, ButtonRelease\n        FocusIn, MouseWheel, Circulate, FocusOut, Property,\n        Colormap, Gravity Reparent, Configure, KeyPress, Key,\n        Unmap, Deactivate, KeyRelease Visibility, Destroy,\n        Leave and DETAIL is the button number for ButtonPress,\n        ButtonRelease and DETAIL is the Keysym for KeyPress and\n        KeyRelease. Examples are\n        <Control-Button-1> for pressing Control and mouse button 1 or\n        <Alt-A> for pressing A and the Alt key (KeyPress can be omitted).\n        An event pattern can also be a virtual event of the form\n        <<AString>> where AString can be arbitrary. This\n        event can be generated by event_generate.\n        If events are concatenated they must appear shortly\n        after each other.\n\n        FUNC will be called if the event sequence occurs with an\n        instance of Event as argument. If the return value of FUNC is\n        "break" no further bound function is invoked.\n\n        An additional boolean parameter ADD specifies whether FUNC will\n        be called additionally to the other bound function or whether\n        it will replace the previous function.\n\n        Bind will return an identifier to allow deletion of the bound function with\n        unbind without memory leak.\n\n        If FUNC or SEQUENCE is omitted the bound function or list\n        of bound events are returned.'
        return self._bind(("bind", self._w), sequence, func, add)

    def unbind(self, sequence, funcid=None):
        "Unbind for this widget for event SEQUENCE  the\n        function identified with FUNCID."
        self.tk.call("bind", self._w, sequence, "")
        if funcid:
            self.deletecommand(funcid)

    def bind_all(self, sequence=None, func=None, add=None):
        "Bind to all widgets at an event SEQUENCE a call to function FUNC.\n        An additional boolean parameter ADD specifies whether FUNC will\n        be called additionally to the other bound function or whether\n        it will replace the previous function. See bind for the return value."
        return self._bind(("bind", "all"), sequence, func, add, 0)

    def unbind_all(self, sequence):
        "Unbind for all widgets for event SEQUENCE all functions."
        self.tk.call("bind", "all", sequence, "")

    def bind_class(self, className, sequence=None, func=None, add=None):
        "Bind to widgets with bindtag CLASSNAME at event\n        SEQUENCE a call of function FUNC. An additional\n        boolean parameter ADD specifies whether FUNC will be\n        called additionally to the other bound function or\n        whether it will replace the previous function. See bind for\n        the return value."
        return self._bind(("bind", className), sequence, func, add, 0)

    def unbind_class(self, className, sequence):
        "Unbind for all widgets with bindtag CLASSNAME for event SEQUENCE\n        all functions."
        self.tk.call("bind", className, sequence, "")

    def mainloop(self, n=0):
        "Call the mainloop of Tk."
        self.tk.mainloop(n)

    def quit(self):
        "Quit the Tcl interpreter. All widgets will be destroyed."
        self.tk.quit()

    def _getints(self, string):
        "Internal function."
        if string:
            return tuple(map(self.tk.getint, self.tk.splitlist(string)))

    def _getdoubles(self, string):
        "Internal function."
        if string:
            return tuple(map(self.tk.getdouble, self.tk.splitlist(string)))

    def _getboolean(self, string):
        "Internal function."
        if string:
            return self.tk.getboolean(string)

    def _displayof(self, displayof):
        "Internal function."
        if displayof:
            return ("-displayof", displayof)
        if displayof is None:
            return ("-displayof", self._w)
        return ()

    @property
    def _windowingsystem(self):
        "Internal function."
        try:
            return self._root()._windowingsystem_cached
        except AttributeError:
            ws = self._root()._windowingsystem_cached = self.tk.call(
                "tk", "windowingsystem"
            )
            return ws

    def _options(self, cnf, kw=None):
        "Internal function."
        if kw:
            cnf = _cnfmerge((cnf, kw))
        else:
            cnf = _cnfmerge(cnf)
        res = ()
        for (k, v) in cnf.items():
            if v is not None:
                if k[(-1)] == "_":
                    k = k[:(-1)]
                if callable(v):
                    v = self._register(v)
                elif isinstance(v, (tuple, list)):
                    nv = []
                    for item in v:
                        if isinstance(item, int):
                            nv.append(str(item))
                        elif isinstance(item, str):
                            nv.append(_stringify(item))
                        else:
                            break
                    else:
                        v = " ".join(nv)
                res = res + (("-" + k), v)
        return res

    def nametowidget(self, name):
        "Return the Tkinter instance of a widget identified by\n        its Tcl name NAME."
        name = str(name).split(".")
        w = self
        if not name[0]:
            w = w._root()
            name = name[1:]
        for n in name:
            if not n:
                break
            w = w.children[n]
        return w

    _nametowidget = nametowidget

    def _register(self, func, subst=None, needcleanup=1):
        "Return a newly created Tcl function. If this\n        function is called, the Python function FUNC will\n        be executed. An optional function SUBST can\n        be given which will be executed before FUNC."
        f = CallWrapper(func, subst, self).__call__
        name = repr(id(f))
        try:
            func = func.__func__
        except AttributeError:
            pass
        try:
            name = name + func.__name__
        except AttributeError:
            pass
        self.tk.createcommand(name, f)
        if needcleanup:
            if self._tclCommands is None:
                self._tclCommands = []
            self._tclCommands.append(name)
        return name

    register = _register

    def _root(self):
        "Internal function."
        w = self
        while w.master is not None:
            w = w.master
        return w

    _subst_format = (
        "%#",
        "%b",
        "%f",
        "%h",
        "%k",
        "%s",
        "%t",
        "%w",
        "%x",
        "%y",
        "%A",
        "%E",
        "%K",
        "%N",
        "%W",
        "%T",
        "%X",
        "%Y",
        "%D",
    )
    _subst_format_str = " ".join(_subst_format)

    def _substitute(self, *args):
        "Internal function."
        if len(args) != len(self._subst_format):
            return args
        getboolean = self.tk.getboolean
        getint = self.tk.getint

        def getint_event(s):
            'Tk changed behavior in 8.4.2, returning "??" rather more often.'
            try:
                return getint(s)
            except (ValueError, TclError):
                return s

        (nsign, b, f, h, k, s, t, w, x, y, A, E, K, N, W, T, X, Y, D) = args
        e = Event()
        e.serial = getint(nsign)
        e.num = getint_event(b)
        try:
            e.focus = getboolean(f)
        except TclError:
            pass
        e.height = getint_event(h)
        e.keycode = getint_event(k)
        e.state = getint_event(s)
        e.time = getint_event(t)
        e.width = getint_event(w)
        e.x = getint_event(x)
        e.y = getint_event(y)
        e.char = A
        try:
            e.send_event = getboolean(E)
        except TclError:
            pass
        e.keysym = K
        e.keysym_num = getint_event(N)
        try:
            e.type = EventType(T)
        except ValueError:
            e.type = T
        try:
            e.widget = self._nametowidget(W)
        except KeyError:
            e.widget = W
        e.x_root = getint_event(X)
        e.y_root = getint_event(Y)
        try:
            e.delta = getint(D)
        except (ValueError, TclError):
            e.delta = 0
        return (e,)

    def _report_exception(self):
        "Internal function."
        (exc, val, tb) = sys.exc_info()
        root = self._root()
        root.report_callback_exception(exc, val, tb)

    def _getconfigure(self, *args):
        "Call Tcl configure command and return the result as a dict."
        cnf = {}
        for x in self.tk.splitlist(self.tk.call(*args)):
            x = self.tk.splitlist(x)
            cnf[x[0][1:]] = (x[0][1:],) + x[1:]
        return cnf

    def _getconfigure1(self, *args):
        x = self.tk.splitlist(self.tk.call(*args))
        return (x[0][1:],) + x[1:]

    def _configure(self, cmd, cnf, kw):
        "Internal function."
        if kw:
            cnf = _cnfmerge((cnf, kw))
        elif cnf:
            cnf = _cnfmerge(cnf)
        if cnf is None:
            return self._getconfigure(_flatten((self._w, cmd)))
        if isinstance(cnf, str):
            return self._getconfigure1(_flatten((self._w, cmd, ("-" + cnf))))
        self.tk.call((_flatten((self._w, cmd)) + self._options(cnf)))

    def configure(self, cnf=None, **kw):
        "Configure resources of a widget.\n\n        The values for resources are specified as keyword\n        arguments. To get an overview about\n        the allowed keyword arguments call the method keys.\n        "
        return self._configure("configure", cnf, kw)

    config = configure

    def cget(self, key):
        "Return the resource value for a KEY given as string."
        return self.tk.call(self._w, "cget", ("-" + key))

    __getitem__ = cget

    def __setitem__(self, key, value):
        self.configure({key: value})

    def keys(self):
        "Return a list of all resource names of this widget."
        splitlist = self.tk.splitlist
        return [
            splitlist(x)[0][1:] for x in splitlist(self.tk.call(self._w, "configure"))
        ]

    def __str__(self):
        "Return the window path name of this widget."
        return self._w

    def __repr__(self):
        return "<%s.%s object %s>" % (
            self.__class__.__module__,
            self.__class__.__qualname__,
            self._w,
        )

    _noarg_ = ["_noarg_"]

    def pack_propagate(self, flag=_noarg_):
        "Set or get the status for propagation of geometry information.\n\n        A boolean argument specifies whether the geometry information\n        of the slaves will determine the size of this widget. If no argument\n        is given the current setting will be returned.\n        "
        if flag is Misc._noarg_:
            return self._getboolean(self.tk.call("pack", "propagate", self._w))
        else:
            self.tk.call("pack", "propagate", self._w, flag)

    propagate = pack_propagate

    def pack_slaves(self):
        "Return a list of all slaves of this widget\n        in its packing order."
        return [
            self._nametowidget(x)
            for x in self.tk.splitlist(self.tk.call("pack", "slaves", self._w))
        ]

    slaves = pack_slaves

    def place_slaves(self):
        "Return a list of all slaves of this widget\n        in its packing order."
        return [
            self._nametowidget(x)
            for x in self.tk.splitlist(self.tk.call("place", "slaves", self._w))
        ]

    def grid_anchor(self, anchor=None):
        "The anchor value controls how to place the grid within the\n        master when no row/column has any weight.\n\n        The default anchor is nw."
        self.tk.call("grid", "anchor", self._w, anchor)

    anchor = grid_anchor

    def grid_bbox(self, column=None, row=None, col2=None, row2=None):
        "Return a tuple of integer coordinates for the bounding\n        box of this widget controlled by the geometry manager grid.\n\n        If COLUMN, ROW is given the bounding box applies from\n        the cell with row and column 0 to the specified\n        cell. If COL2 and ROW2 are given the bounding box\n        starts at that cell.\n\n        The returned integers specify the offset of the upper left\n        corner in the master widget and the width and height.\n        "
        args = ("grid", "bbox", self._w)
        if (column is not None) and (row is not None):
            args = args + (column, row)
        if (col2 is not None) and (row2 is not None):
            args = args + (col2, row2)
        return self._getints(self.tk.call(*args)) or None

    bbox = grid_bbox

    def _gridconvvalue(self, value):
        if isinstance(value, (str, _tkinter.Tcl_Obj)):
            try:
                svalue = str(value)
                if not svalue:
                    return None
                elif "." in svalue:
                    return self.tk.getdouble(svalue)
                else:
                    return self.tk.getint(svalue)
            except (ValueError, TclError):
                pass
        return value

    def _grid_configure(self, command, index, cnf, kw):
        "Internal function."
        if isinstance(cnf, str) and (not kw):
            if cnf[(-1):] == "_":
                cnf = cnf[:(-1)]
            if cnf[:1] != "-":
                cnf = "-" + cnf
            options = (cnf,)
        else:
            options = self._options(cnf, kw)
        if not options:
            return _splitdict(
                self.tk,
                self.tk.call("grid", command, self._w, index),
                conv=self._gridconvvalue,
            )
        res = self.tk.call((("grid", command, self._w, index) + options))
        if len(options) == 1:
            return self._gridconvvalue(res)

    def grid_columnconfigure(self, index, cnf={}, **kw):
        "Configure column INDEX of a grid.\n\n        Valid resources are minsize (minimum size of the column),\n        weight (how much does additional space propagate to this column)\n        and pad (how much space to let additionally)."
        return self._grid_configure("columnconfigure", index, cnf, kw)

    columnconfigure = grid_columnconfigure

    def grid_location(self, x, y):
        "Return a tuple of column and row which identify the cell\n        at which the pixel at position X and Y inside the master\n        widget is located."
        return self._getints(self.tk.call("grid", "location", self._w, x, y)) or None

    def grid_propagate(self, flag=_noarg_):
        "Set or get the status for propagation of geometry information.\n\n        A boolean argument specifies whether the geometry information\n        of the slaves will determine the size of this widget. If no argument\n        is given, the current setting will be returned.\n        "
        if flag is Misc._noarg_:
            return self._getboolean(self.tk.call("grid", "propagate", self._w))
        else:
            self.tk.call("grid", "propagate", self._w, flag)

    def grid_rowconfigure(self, index, cnf={}, **kw):
        "Configure row INDEX of a grid.\n\n        Valid resources are minsize (minimum size of the row),\n        weight (how much does additional space propagate to this row)\n        and pad (how much space to let additionally)."
        return self._grid_configure("rowconfigure", index, cnf, kw)

    rowconfigure = grid_rowconfigure

    def grid_size(self):
        "Return a tuple of the number of column and rows in the grid."
        return self._getints(self.tk.call("grid", "size", self._w)) or None

    size = grid_size

    def grid_slaves(self, row=None, column=None):
        "Return a list of all slaves of this widget\n        in its packing order."
        args = ()
        if row is not None:
            args = args + ("-row", row)
        if column is not None:
            args = args + ("-column", column)
        return [
            self._nametowidget(x)
            for x in self.tk.splitlist(
                self.tk.call((("grid", "slaves", self._w) + args))
            )
        ]

    def event_add(self, virtual, *sequences):
        "Bind a virtual event VIRTUAL (of the form <<Name>>)\n        to an event SEQUENCE such that the virtual event is triggered\n        whenever SEQUENCE occurs."
        args = ("event", "add", virtual) + sequences
        self.tk.call(args)

    def event_delete(self, virtual, *sequences):
        "Unbind a virtual event VIRTUAL from SEQUENCE."
        args = ("event", "delete", virtual) + sequences
        self.tk.call(args)

    def event_generate(self, sequence, **kw):
        "Generate an event SEQUENCE. Additional\n        keyword arguments specify parameter of the event\n        (e.g. x, y, rootx, rooty)."
        args = ("event", "generate", self._w, sequence)
        for (k, v) in kw.items():
            args = args + (("-%s" % k), str(v))
        self.tk.call(args)

    def event_info(self, virtual=None):
        "Return a list of all virtual events or the information\n        about the SEQUENCE bound to the virtual event VIRTUAL."
        return self.tk.splitlist(self.tk.call("event", "info", virtual))

    def image_names(self):
        "Return a list of all existing image names."
        return self.tk.splitlist(self.tk.call("image", "names"))

    def image_types(self):
        "Return a list of all available image types (e.g. photo bitmap)."
        return self.tk.splitlist(self.tk.call("image", "types"))


class CallWrapper:
    "Internal class. Stores function to call when some user\n    defined Tcl function is called e.g. after an event occurred."

    def __init__(self, func, subst, widget):
        "Store FUNC, SUBST and WIDGET as members."
        self.func = func
        self.subst = subst
        self.widget = widget

    def __call__(self, *args):
        "Apply first function SUBST to arguments, than FUNC."
        try:
            if self.subst:
                args = self.subst(*args)
            return self.func(*args)
        except SystemExit:
            raise
        except:
            self.widget._report_exception()


class XView:
    "Mix-in class for querying and changing the horizontal position\n    of a widget's window."

    def xview(self, *args):
        "Query and change the horizontal position of the view."
        res = self.tk.call(self._w, "xview", *args)
        if not args:
            return self._getdoubles(res)

    def xview_moveto(self, fraction):
        "Adjusts the view in the window so that FRACTION of the\n        total width of the canvas is off-screen to the left."
        self.tk.call(self._w, "xview", "moveto", fraction)

    def xview_scroll(self, number, what):
        'Shift the x-view according to NUMBER which is measured in "units"\n        or "pages" (WHAT).'
        self.tk.call(self._w, "xview", "scroll", number, what)


class YView:
    "Mix-in class for querying and changing the vertical position\n    of a widget's window."

    def yview(self, *args):
        "Query and change the vertical position of the view."
        res = self.tk.call(self._w, "yview", *args)
        if not args:
            return self._getdoubles(res)

    def yview_moveto(self, fraction):
        "Adjusts the view in the window so that FRACTION of the\n        total height of the canvas is off-screen to the top."
        self.tk.call(self._w, "yview", "moveto", fraction)

    def yview_scroll(self, number, what):
        'Shift the y-view according to NUMBER which is measured in\n        "units" or "pages" (WHAT).'
        self.tk.call(self._w, "yview", "scroll", number, what)


class Wm:
    "Provides functions for the communication with the window manager."

    def wm_aspect(self, minNumer=None, minDenom=None, maxNumer=None, maxDenom=None):
        "Instruct the window manager to set the aspect ratio (width/height)\n        of this widget to be between MINNUMER/MINDENOM and MAXNUMER/MAXDENOM. Return a tuple\n        of the actual values if no argument is given."
        return self._getints(
            self.tk.call(
                "wm", "aspect", self._w, minNumer, minDenom, maxNumer, maxDenom
            )
        )

    aspect = wm_aspect

    def wm_attributes(self, *args):
        "This subcommand returns or sets platform specific attributes\n\n        The first form returns a list of the platform specific flags and\n        their values. The second form returns the value for the specific\n        option. The third form sets one or more of the values. The values\n        are as follows:\n\n        On Windows, -disabled gets or sets whether the window is in a\n        disabled state. -toolwindow gets or sets the style of the window\n        to toolwindow (as defined in the MSDN). -topmost gets or sets\n        whether this is a topmost window (displays above all other\n        windows).\n\n        On Macintosh, XXXXX\n\n        On Unix, there are currently no special attribute values.\n        "
        args = ("wm", "attributes", self._w) + args
        return self.tk.call(args)

    attributes = wm_attributes

    def wm_client(self, name=None):
        "Store NAME in WM_CLIENT_MACHINE property of this widget. Return\n        current value."
        return self.tk.call("wm", "client", self._w, name)

    client = wm_client

    def wm_colormapwindows(self, *wlist):
        "Store list of window names (WLIST) into WM_COLORMAPWINDOWS property\n        of this widget. This list contains windows whose colormaps differ from their\n        parents. Return current list of widgets if WLIST is empty."
        if len(wlist) > 1:
            wlist = (wlist,)
        args = ("wm", "colormapwindows", self._w) + wlist
        if wlist:
            self.tk.call(args)
        else:
            return [
                self._nametowidget(x) for x in self.tk.splitlist(self.tk.call(args))
            ]

    colormapwindows = wm_colormapwindows

    def wm_command(self, value=None):
        "Store VALUE in WM_COMMAND property. It is the command\n        which shall be used to invoke the application. Return current\n        command if VALUE is None."
        return self.tk.call("wm", "command", self._w, value)

    command = wm_command

    def wm_deiconify(self):
        "Deiconify this widget. If it was never mapped it will not be mapped.\n        On Windows it will raise this widget and give it the focus."
        return self.tk.call("wm", "deiconify", self._w)

    deiconify = wm_deiconify

    def wm_focusmodel(self, model=None):
        'Set focus model to MODEL. "active" means that this widget will claim\n        the focus itself, "passive" means that the window manager shall give\n        the focus. Return current focus model if MODEL is None.'
        return self.tk.call("wm", "focusmodel", self._w, model)

    focusmodel = wm_focusmodel

    def wm_forget(self, window):
        "The window will be unmapped from the screen and will no longer\n        be managed by wm. toplevel windows will be treated like frame\n        windows once they are no longer managed by wm, however, the menu\n        option configuration will be remembered and the menus will return\n        once the widget is managed again."
        self.tk.call("wm", "forget", window)

    forget = wm_forget

    def wm_frame(self):
        "Return identifier for decorative frame of this widget if present."
        return self.tk.call("wm", "frame", self._w)

    frame = wm_frame

    def wm_geometry(self, newGeometry=None):
        "Set geometry to NEWGEOMETRY of the form =widthxheight+x+y. Return\n        current value if None is given."
        return self.tk.call("wm", "geometry", self._w, newGeometry)

    geometry = wm_geometry

    def wm_grid(self, baseWidth=None, baseHeight=None, widthInc=None, heightInc=None):
        "Instruct the window manager that this widget shall only be\n        resized on grid boundaries. WIDTHINC and HEIGHTINC are the width and\n        height of a grid unit in pixels. BASEWIDTH and BASEHEIGHT are the\n        number of grid units requested in Tk_GeometryRequest."
        return self._getints(
            self.tk.call(
                "wm", "grid", self._w, baseWidth, baseHeight, widthInc, heightInc
            )
        )

    grid = wm_grid

    def wm_group(self, pathName=None):
        "Set the group leader widgets for related widgets to PATHNAME. Return\n        the group leader of this widget if None is given."
        return self.tk.call("wm", "group", self._w, pathName)

    group = wm_group

    def wm_iconbitmap(self, bitmap=None, default=None):
        "Set bitmap for the iconified widget to BITMAP. Return\n        the bitmap if None is given.\n\n        Under Windows, the DEFAULT parameter can be used to set the icon\n        for the widget and any descendents that don't have an icon set\n        explicitly.  DEFAULT can be the relative path to a .ico file\n        (example: root.iconbitmap(default='myicon.ico') ).  See Tk\n        documentation for more information."
        if default:
            return self.tk.call("wm", "iconbitmap", self._w, "-default", default)
        else:
            return self.tk.call("wm", "iconbitmap", self._w, bitmap)

    iconbitmap = wm_iconbitmap

    def wm_iconify(self):
        "Display widget as icon."
        return self.tk.call("wm", "iconify", self._w)

    iconify = wm_iconify

    def wm_iconmask(self, bitmap=None):
        "Set mask for the icon bitmap of this widget. Return the\n        mask if None is given."
        return self.tk.call("wm", "iconmask", self._w, bitmap)

    iconmask = wm_iconmask

    def wm_iconname(self, newName=None):
        "Set the name of the icon for this widget. Return the name if\n        None is given."
        return self.tk.call("wm", "iconname", self._w, newName)

    iconname = wm_iconname

    def wm_iconphoto(self, default=False, *args):
        "Sets the titlebar icon for this window based on the named photo\n        images passed through args. If default is True, this is applied to\n        all future created toplevels as well.\n\n        The data in the images is taken as a snapshot at the time of\n        invocation. If the images are later changed, this is not reflected\n        to the titlebar icons. Multiple images are accepted to allow\n        different images sizes to be provided. The window manager may scale\n        provided icons to an appropriate size.\n\n        On Windows, the images are packed into a Windows icon structure.\n        This will override an icon specified to wm_iconbitmap, and vice\n        versa.\n\n        On X, the images are arranged into the _NET_WM_ICON X property,\n        which most modern window managers support. An icon specified by\n        wm_iconbitmap may exist simultaneously.\n\n        On Macintosh, this currently does nothing."
        if default:
            self.tk.call("wm", "iconphoto", self._w, "-default", *args)
        else:
            self.tk.call("wm", "iconphoto", self._w, *args)

    iconphoto = wm_iconphoto

    def wm_iconposition(self, x=None, y=None):
        "Set the position of the icon of this widget to X and Y. Return\n        a tuple of the current values of X and X if None is given."
        return self._getints(self.tk.call("wm", "iconposition", self._w, x, y))

    iconposition = wm_iconposition

    def wm_iconwindow(self, pathName=None):
        "Set widget PATHNAME to be displayed instead of icon. Return the current\n        value if None is given."
        return self.tk.call("wm", "iconwindow", self._w, pathName)

    iconwindow = wm_iconwindow

    def wm_manage(self, widget):
        "The widget specified will become a stand alone top-level window.\n        The window will be decorated with the window managers title bar,\n        etc."
        self.tk.call("wm", "manage", widget)

    manage = wm_manage

    def wm_maxsize(self, width=None, height=None):
        "Set max WIDTH and HEIGHT for this widget. If the window is gridded\n        the values are given in grid units. Return the current values if None\n        is given."
        return self._getints(self.tk.call("wm", "maxsize", self._w, width, height))

    maxsize = wm_maxsize

    def wm_minsize(self, width=None, height=None):
        "Set min WIDTH and HEIGHT for this widget. If the window is gridded\n        the values are given in grid units. Return the current values if None\n        is given."
        return self._getints(self.tk.call("wm", "minsize", self._w, width, height))

    minsize = wm_minsize

    def wm_overrideredirect(self, boolean=None):
        "Instruct the window manager to ignore this widget\n        if BOOLEAN is given with 1. Return the current value if None\n        is given."
        return self._getboolean(
            self.tk.call("wm", "overrideredirect", self._w, boolean)
        )

    overrideredirect = wm_overrideredirect

    def wm_positionfrom(self, who=None):
        'Instruct the window manager that the position of this widget shall\n        be defined by the user if WHO is "user", and by its own policy if WHO is\n        "program".'
        return self.tk.call("wm", "positionfrom", self._w, who)

    positionfrom = wm_positionfrom

    def wm_protocol(self, name=None, func=None):
        'Bind function FUNC to command NAME for this widget.\n        Return the function bound to NAME if None is given. NAME could be\n        e.g. "WM_SAVE_YOURSELF" or "WM_DELETE_WINDOW".'
        if callable(func):
            command = self._register(func)
        else:
            command = func
        return self.tk.call("wm", "protocol", self._w, name, command)

    protocol = wm_protocol

    def wm_resizable(self, width=None, height=None):
        "Instruct the window manager whether this width can be resized\n        in WIDTH or HEIGHT. Both values are boolean values."
        return self.tk.call("wm", "resizable", self._w, width, height)

    resizable = wm_resizable

    def wm_sizefrom(self, who=None):
        'Instruct the window manager that the size of this widget shall\n        be defined by the user if WHO is "user", and by its own policy if WHO is\n        "program".'
        return self.tk.call("wm", "sizefrom", self._w, who)

    sizefrom = wm_sizefrom

    def wm_state(self, newstate=None):
        "Query or set the state of this widget as one of normal, icon,\n        iconic (see wm_iconwindow), withdrawn, or zoomed (Windows only)."
        return self.tk.call("wm", "state", self._w, newstate)

    state = wm_state

    def wm_title(self, string=None):
        "Set the title of this widget."
        return self.tk.call("wm", "title", self._w, string)

    title = wm_title

    def wm_transient(self, master=None):
        "Instruct the window manager that this widget is transient\n        with regard to widget MASTER."
        return self.tk.call("wm", "transient", self._w, master)

    transient = wm_transient

    def wm_withdraw(self):
        "Withdraw this widget from the screen such that it is unmapped\n        and forgotten by the window manager. Re-draw it with wm_deiconify."
        return self.tk.call("wm", "withdraw", self._w)

    withdraw = wm_withdraw


class Tk(Misc, Wm):
    "Toplevel widget of Tk which represents mostly the main window\n    of an application. It has an associated Tcl interpreter."
    _w = "."

    def __init__(
        self,
        screenName=None,
        baseName=None,
        className="Tk",
        useTk=True,
        sync=False,
        use=None,
    ):
        "Return a new Toplevel widget on screen SCREENNAME. A new Tcl interpreter will\n        be created. BASENAME will be used for the identification of the profile file (see\n        readprofile).\n        It is constructed from sys.argv[0] without extensions if None is given. CLASSNAME\n        is the name of the widget class."
        self.master = None
        self.children = {}
        self._tkloaded = False
        self.tk = None
        if baseName is None:
            import os

            baseName = os.path.basename(sys.argv[0])
            (baseName, ext) = os.path.splitext(baseName)
            if ext not in (".py", ".pyc"):
                baseName = baseName + ext
        interactive = False
        self.tk = _tkinter.create(
            screenName, baseName, className, interactive, wantobjects, useTk, sync, use
        )
        if useTk:
            self._loadtk()
        if not sys.flags.ignore_environment:
            self.readprofile(baseName, className)

    def loadtk(self):
        if not self._tkloaded:
            self.tk.loadtk()
            self._loadtk()

    def _loadtk(self):
        self._tkloaded = True
        global _default_root
        tk_version = self.tk.getvar("tk_version")
        if tk_version != _tkinter.TK_VERSION:
            raise RuntimeError(
                (
                    "tk.h version (%s) doesn't match libtk.a version (%s)"
                    % (_tkinter.TK_VERSION, tk_version)
                )
            )
        tcl_version = str(self.tk.getvar("tcl_version"))
        if tcl_version != _tkinter.TCL_VERSION:
            raise RuntimeError(
                (
                    "tcl.h version (%s) doesn't match libtcl.a version (%s)"
                    % (_tkinter.TCL_VERSION, tcl_version)
                )
            )
        if self._tclCommands is None:
            self._tclCommands = []
        self.tk.createcommand("tkerror", _tkerror)
        self.tk.createcommand("exit", _exit)
        self._tclCommands.append("tkerror")
        self._tclCommands.append("exit")
        if _support_default_root and (_default_root is None):
            _default_root = self
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def destroy(self):
        "Destroy this and all descendants widgets. This will\n        end the application of this Tcl interpreter."
        for c in list(self.children.values()):
            c.destroy()
        self.tk.call("destroy", self._w)
        Misc.destroy(self)
        global _default_root
        if _support_default_root and (_default_root is self):
            _default_root = None

    def readprofile(self, baseName, className):
        "Internal function. It reads BASENAME.tcl and CLASSNAME.tcl into\n        the Tcl Interpreter and calls exec on the contents of BASENAME.py and\n        CLASSNAME.py if such a file exists in the home directory."
        import os

        if "HOME" in os.environ:
            home = os.environ["HOME"]
        else:
            home = os.curdir
        class_tcl = os.path.join(home, (".%s.tcl" % className))
        class_py = os.path.join(home, (".%s.py" % className))
        base_tcl = os.path.join(home, (".%s.tcl" % baseName))
        base_py = os.path.join(home, (".%s.py" % baseName))
        dir = {"self": self}
        exec("from tkinter import *", dir)
        if os.path.isfile(class_tcl):
            self.tk.call("source", class_tcl)
        if os.path.isfile(class_py):
            exec(open(class_py).read(), dir)
        if os.path.isfile(base_tcl):
            self.tk.call("source", base_tcl)
        if os.path.isfile(base_py):
            exec(open(base_py).read(), dir)

    def report_callback_exception(self, exc, val, tb):
        "Report callback exception on sys.stderr.\n\n        Applications may want to override this internal function, and\n        should when sys.stderr is None."
        import traceback

        print("Exception in Tkinter callback", file=sys.stderr)
        sys.last_type = exc
        sys.last_value = val
        sys.last_traceback = tb
        traceback.print_exception(exc, val, tb)

    def __getattr__(self, attr):
        "Delegate attribute access to the interpreter object"
        return getattr(self.tk, attr)


def Tcl(screenName=None, baseName=None, className="Tk", useTk=False):
    return Tk(screenName, baseName, className, useTk)


class Pack:
    "Geometry manager Pack.\n\n    Base class to use the methods pack_* in every widget."

    def pack_configure(self, cnf={}, **kw):
        "Pack a widget in the parent widget. Use as options:\n        after=widget - pack it after you have packed widget\n        anchor=NSEW (or subset) - position widget according to\n                                  given direction\n        before=widget - pack it before you will pack widget\n        expand=bool - expand widget if parent size grows\n        fill=NONE or X or Y or BOTH - fill widget if widget grows\n        in=master - use master to contain this widget\n        in_=master - see 'in' option description\n        ipadx=amount - add internal padding in x direction\n        ipady=amount - add internal padding in y direction\n        padx=amount - add padding in x direction\n        pady=amount - add padding in y direction\n        side=TOP or BOTTOM or LEFT or RIGHT -  where to add this widget.\n        "
        self.tk.call((("pack", "configure", self._w) + self._options(cnf, kw)))

    pack = configure = config = pack_configure

    def pack_forget(self):
        "Unmap this widget and do not use it for the packing order."
        self.tk.call("pack", "forget", self._w)

    forget = pack_forget

    def pack_info(self):
        "Return information about the packing options\n        for this widget."
        d = _splitdict(self.tk, self.tk.call("pack", "info", self._w))
        if "in" in d:
            d["in"] = self.nametowidget(d["in"])
        return d

    info = pack_info
    propagate = pack_propagate = Misc.pack_propagate
    slaves = pack_slaves = Misc.pack_slaves


class Place:
    "Geometry manager Place.\n\n    Base class to use the methods place_* in every widget."

    def place_configure(self, cnf={}, **kw):
        'Place a widget in the parent widget. Use as options:\n        in=master - master relative to which the widget is placed\n        in_=master - see \'in\' option description\n        x=amount - locate anchor of this widget at position x of master\n        y=amount - locate anchor of this widget at position y of master\n        relx=amount - locate anchor of this widget between 0.0 and 1.0\n                      relative to width of master (1.0 is right edge)\n        rely=amount - locate anchor of this widget between 0.0 and 1.0\n                      relative to height of master (1.0 is bottom edge)\n        anchor=NSEW (or subset) - position anchor according to given direction\n        width=amount - width of this widget in pixel\n        height=amount - height of this widget in pixel\n        relwidth=amount - width of this widget between 0.0 and 1.0\n                          relative to width of master (1.0 is the same width\n                          as the master)\n        relheight=amount - height of this widget between 0.0 and 1.0\n                           relative to height of master (1.0 is the same\n                           height as the master)\n        bordermode="inside" or "outside" - whether to take border width of\n                                           master widget into account\n        '
        self.tk.call((("place", "configure", self._w) + self._options(cnf, kw)))

    place = configure = config = place_configure

    def place_forget(self):
        "Unmap this widget."
        self.tk.call("place", "forget", self._w)

    forget = place_forget

    def place_info(self):
        "Return information about the placing options\n        for this widget."
        d = _splitdict(self.tk, self.tk.call("place", "info", self._w))
        if "in" in d:
            d["in"] = self.nametowidget(d["in"])
        return d

    info = place_info
    slaves = place_slaves = Misc.place_slaves


class Grid:
    "Geometry manager Grid.\n\n    Base class to use the methods grid_* in every widget."

    def grid_configure(self, cnf={}, **kw):
        "Position a widget in the parent widget in a grid. Use as options:\n        column=number - use cell identified with given column (starting with 0)\n        columnspan=number - this widget will span several columns\n        in=master - use master to contain this widget\n        in_=master - see 'in' option description\n        ipadx=amount - add internal padding in x direction\n        ipady=amount - add internal padding in y direction\n        padx=amount - add padding in x direction\n        pady=amount - add padding in y direction\n        row=number - use cell identified with given row (starting with 0)\n        rowspan=number - this widget will span several rows\n        sticky=NSEW - if cell is larger on which sides will this\n                      widget stick to the cell boundary\n        "
        self.tk.call((("grid", "configure", self._w) + self._options(cnf, kw)))

    grid = configure = config = grid_configure
    bbox = grid_bbox = Misc.grid_bbox
    columnconfigure = grid_columnconfigure = Misc.grid_columnconfigure

    def grid_forget(self):
        "Unmap this widget."
        self.tk.call("grid", "forget", self._w)

    forget = grid_forget

    def grid_remove(self):
        "Unmap this widget but remember the grid options."
        self.tk.call("grid", "remove", self._w)

    def grid_info(self):
        "Return information about the options\n        for positioning this widget in a grid."
        d = _splitdict(self.tk, self.tk.call("grid", "info", self._w))
        if "in" in d:
            d["in"] = self.nametowidget(d["in"])
        return d

    info = grid_info
    location = grid_location = Misc.grid_location
    propagate = grid_propagate = Misc.grid_propagate
    rowconfigure = grid_rowconfigure = Misc.grid_rowconfigure
    size = grid_size = Misc.grid_size
    slaves = grid_slaves = Misc.grid_slaves


class BaseWidget(Misc):
    "Internal class."

    def _setup(self, master, cnf):
        "Internal function. Sets up information about children."
        if master is None:
            master = _get_default_root()
        self.master = master
        self.tk = master.tk
        name = None
        if "name" in cnf:
            name = cnf["name"]
            del cnf["name"]
        if not name:
            name = self.__class__.__name__.lower()
            if master._last_child_ids is None:
                master._last_child_ids = {}
            count = master._last_child_ids.get(name, 0) + 1
            master._last_child_ids[name] = count
            if count == 1:
                name = "!%s" % (name,)
            else:
                name = "!%s%d" % (name, count)
        self._name = name
        if master._w == ".":
            self._w = "." + name
        else:
            self._w = (master._w + ".") + name
        self.children = {}
        if self._name in self.master.children:
            self.master.children[self._name].destroy()
        self.master.children[self._name] = self

    def __init__(self, master, widgetName, cnf={}, kw={}, extra=()):
        "Construct a widget with the parent widget MASTER, a name WIDGETNAME\n        and appropriate options."
        if kw:
            cnf = _cnfmerge((cnf, kw))
        self.widgetName = widgetName
        BaseWidget._setup(self, master, cnf)
        if self._tclCommands is None:
            self._tclCommands = []
        classes = [(k, v) for (k, v) in cnf.items() if isinstance(k, type)]
        for (k, v) in classes:
            del cnf[k]
        self.tk.call((((widgetName, self._w) + extra) + self._options(cnf)))
        for (k, v) in classes:
            k.configure(self, v)

    def destroy(self):
        "Destroy this and all descendants widgets."
        for c in list(self.children.values()):
            c.destroy()
        self.tk.call("destroy", self._w)
        if self._name in self.master.children:
            del self.master.children[self._name]
        Misc.destroy(self)

    def _do(self, name, args=()):
        return self.tk.call(((self._w, name) + args))


class Widget(BaseWidget, Pack, Place, Grid):
    "Internal class.\n\n    Base class for a widget which can be positioned with the geometry managers\n    Pack, Place or Grid."
    pass


class Toplevel(BaseWidget, Wm):
    "Toplevel widget, e.g. for dialogs."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a toplevel widget with the parent MASTER.\n\n        Valid resource names: background, bd, bg, borderwidth, class,\n        colormap, container, cursor, height, highlightbackground,\n        highlightcolor, highlightthickness, menu, relief, screen, takefocus,\n        use, visual, width."
        if kw:
            cnf = _cnfmerge((cnf, kw))
        extra = ()
        for wmkey in ["screen", "class_", "class", "visual", "colormap"]:
            if wmkey in cnf:
                val = cnf[wmkey]
                if wmkey[(-1)] == "_":
                    opt = "-" + wmkey[:(-1)]
                else:
                    opt = "-" + wmkey
                extra = extra + (opt, val)
                del cnf[wmkey]
        BaseWidget.__init__(self, master, "toplevel", cnf, {}, extra)
        root = self._root()
        self.iconname(root.iconname())
        self.title(root.title())
        self.protocol("WM_DELETE_WINDOW", self.destroy)


class Button(Widget):
    "Button widget."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a button widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            activebackground, activeforeground, anchor,\n            background, bitmap, borderwidth, cursor,\n            disabledforeground, font, foreground\n            highlightbackground, highlightcolor,\n            highlightthickness, image, justify,\n            padx, pady, relief, repeatdelay,\n            repeatinterval, takefocus, text,\n            textvariable, underline, wraplength\n\n        WIDGET-SPECIFIC OPTIONS\n\n            command, compound, default, height,\n            overrelief, state, width\n        "
        Widget.__init__(self, master, "button", cnf, kw)

    def flash(self):
        "Flash the button.\n\n        This is accomplished by redisplaying\n        the button several times, alternating between active and\n        normal colors. At the end of the flash the button is left\n        in the same normal/active state as when the command was\n        invoked. This command is ignored if the button's state is\n        disabled.\n        "
        self.tk.call(self._w, "flash")

    def invoke(self):
        "Invoke the command associated with the button.\n\n        The return value is the return value from the command,\n        or an empty string if there is no command associated with\n        the button. This command is ignored if the button's state\n        is disabled.\n        "
        return self.tk.call(self._w, "invoke")


class Canvas(Widget, XView, YView):
    "Canvas widget to display graphical elements like lines or text."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a canvas widget with the parent MASTER.\n\n        Valid resource names: background, bd, bg, borderwidth, closeenough,\n        confine, cursor, height, highlightbackground, highlightcolor,\n        highlightthickness, insertbackground, insertborderwidth,\n        insertofftime, insertontime, insertwidth, offset, relief,\n        scrollregion, selectbackground, selectborderwidth, selectforeground,\n        state, takefocus, width, xscrollcommand, xscrollincrement,\n        yscrollcommand, yscrollincrement."
        Widget.__init__(self, master, "canvas", cnf, kw)

    def addtag(self, *args):
        "Internal function."
        self.tk.call(((self._w, "addtag") + args))

    def addtag_above(self, newtag, tagOrId):
        "Add tag NEWTAG to all items above TAGORID."
        self.addtag(newtag, "above", tagOrId)

    def addtag_all(self, newtag):
        "Add tag NEWTAG to all items."
        self.addtag(newtag, "all")

    def addtag_below(self, newtag, tagOrId):
        "Add tag NEWTAG to all items below TAGORID."
        self.addtag(newtag, "below", tagOrId)

    def addtag_closest(self, newtag, x, y, halo=None, start=None):
        "Add tag NEWTAG to item which is closest to pixel at X, Y.\n        If several match take the top-most.\n        All items closer than HALO are considered overlapping (all are\n        closests). If START is specified the next below this tag is taken."
        self.addtag(newtag, "closest", x, y, halo, start)

    def addtag_enclosed(self, newtag, x1, y1, x2, y2):
        "Add tag NEWTAG to all items in the rectangle defined\n        by X1,Y1,X2,Y2."
        self.addtag(newtag, "enclosed", x1, y1, x2, y2)

    def addtag_overlapping(self, newtag, x1, y1, x2, y2):
        "Add tag NEWTAG to all items which overlap the rectangle\n        defined by X1,Y1,X2,Y2."
        self.addtag(newtag, "overlapping", x1, y1, x2, y2)

    def addtag_withtag(self, newtag, tagOrId):
        "Add tag NEWTAG to all items with TAGORID."
        self.addtag(newtag, "withtag", tagOrId)

    def bbox(self, *args):
        "Return a tuple of X1,Y1,X2,Y2 coordinates for a rectangle\n        which encloses all items with tags specified as arguments."
        return self._getints(self.tk.call(((self._w, "bbox") + args))) or None

    def tag_unbind(self, tagOrId, sequence, funcid=None):
        "Unbind for all items with TAGORID for event SEQUENCE  the\n        function identified with FUNCID."
        self.tk.call(self._w, "bind", tagOrId, sequence, "")
        if funcid:
            self.deletecommand(funcid)

    def tag_bind(self, tagOrId, sequence=None, func=None, add=None):
        "Bind to all items with TAGORID at event SEQUENCE a call to function FUNC.\n\n        An additional boolean parameter ADD specifies whether FUNC will be\n        called additionally to the other bound function or whether it will\n        replace the previous function. See bind for the return value."
        return self._bind((self._w, "bind", tagOrId), sequence, func, add)

    def canvasx(self, screenx, gridspacing=None):
        "Return the canvas x coordinate of pixel position SCREENX rounded\n        to nearest multiple of GRIDSPACING units."
        return self.tk.getdouble(self.tk.call(self._w, "canvasx", screenx, gridspacing))

    def canvasy(self, screeny, gridspacing=None):
        "Return the canvas y coordinate of pixel position SCREENY rounded\n        to nearest multiple of GRIDSPACING units."
        return self.tk.getdouble(self.tk.call(self._w, "canvasy", screeny, gridspacing))

    def coords(self, *args):
        "Return a list of coordinates for the item given in ARGS."
        return [
            self.tk.getdouble(x)
            for x in self.tk.splitlist(self.tk.call(((self._w, "coords") + args)))
        ]

    def _create(self, itemType, args, kw):
        "Internal function."
        args = _flatten(args)
        cnf = args[(-1)]
        if isinstance(cnf, (dict, tuple)):
            args = args[:(-1)]
        else:
            cnf = {}
        return self.tk.getint(
            self.tk.call(self._w, "create", itemType, *(args + self._options(cnf, kw)))
        )

    def create_arc(self, *args, **kw):
        "Create arc shaped region with coordinates x1,y1,x2,y2."
        return self._create("arc", args, kw)

    def create_bitmap(self, *args, **kw):
        "Create bitmap with coordinates x1,y1."
        return self._create("bitmap", args, kw)

    def create_image(self, *args, **kw):
        "Create image item with coordinates x1,y1."
        return self._create("image", args, kw)

    def create_line(self, *args, **kw):
        "Create line with coordinates x1,y1,...,xn,yn."
        return self._create("line", args, kw)

    def create_oval(self, *args, **kw):
        "Create oval with coordinates x1,y1,x2,y2."
        return self._create("oval", args, kw)

    def create_polygon(self, *args, **kw):
        "Create polygon with coordinates x1,y1,...,xn,yn."
        return self._create("polygon", args, kw)

    def create_rectangle(self, *args, **kw):
        "Create rectangle with coordinates x1,y1,x2,y2."
        return self._create("rectangle", args, kw)

    def create_text(self, *args, **kw):
        "Create text with coordinates x1,y1."
        return self._create("text", args, kw)

    def create_window(self, *args, **kw):
        "Create window with coordinates x1,y1,x2,y2."
        return self._create("window", args, kw)

    def dchars(self, *args):
        "Delete characters of text items identified by tag or id in ARGS (possibly\n        several times) from FIRST to LAST character (including)."
        self.tk.call(((self._w, "dchars") + args))

    def delete(self, *args):
        "Delete items identified by all tag or ids contained in ARGS."
        self.tk.call(((self._w, "delete") + args))

    def dtag(self, *args):
        "Delete tag or id given as last arguments in ARGS from items\n        identified by first argument in ARGS."
        self.tk.call(((self._w, "dtag") + args))

    def find(self, *args):
        "Internal function."
        return self._getints(self.tk.call(((self._w, "find") + args))) or ()

    def find_above(self, tagOrId):
        "Return items above TAGORID."
        return self.find("above", tagOrId)

    def find_all(self):
        "Return all items."
        return self.find("all")

    def find_below(self, tagOrId):
        "Return all items below TAGORID."
        return self.find("below", tagOrId)

    def find_closest(self, x, y, halo=None, start=None):
        "Return item which is closest to pixel at X, Y.\n        If several match take the top-most.\n        All items closer than HALO are considered overlapping (all are\n        closest). If START is specified the next below this tag is taken."
        return self.find("closest", x, y, halo, start)

    def find_enclosed(self, x1, y1, x2, y2):
        "Return all items in rectangle defined\n        by X1,Y1,X2,Y2."
        return self.find("enclosed", x1, y1, x2, y2)

    def find_overlapping(self, x1, y1, x2, y2):
        "Return all items which overlap the rectangle\n        defined by X1,Y1,X2,Y2."
        return self.find("overlapping", x1, y1, x2, y2)

    def find_withtag(self, tagOrId):
        "Return all items with TAGORID."
        return self.find("withtag", tagOrId)

    def focus(self, *args):
        "Set focus to the first item specified in ARGS."
        return self.tk.call(((self._w, "focus") + args))

    def gettags(self, *args):
        "Return tags associated with the first item specified in ARGS."
        return self.tk.splitlist(self.tk.call(((self._w, "gettags") + args)))

    def icursor(self, *args):
        "Set cursor at position POS in the item identified by TAGORID.\n        In ARGS TAGORID must be first."
        self.tk.call(((self._w, "icursor") + args))

    def index(self, *args):
        "Return position of cursor as integer in item specified in ARGS."
        return self.tk.getint(self.tk.call(((self._w, "index") + args)))

    def insert(self, *args):
        "Insert TEXT in item TAGORID at position POS. ARGS must\n        be TAGORID POS TEXT."
        self.tk.call(((self._w, "insert") + args))

    def itemcget(self, tagOrId, option):
        "Return the resource value for an OPTION for item TAGORID."
        return self.tk.call(((self._w, "itemcget") + (tagOrId, ("-" + option))))

    def itemconfigure(self, tagOrId, cnf=None, **kw):
        "Configure resources of an item TAGORID.\n\n        The values for resources are specified as keyword\n        arguments. To get an overview about\n        the allowed keyword arguments call the method without arguments.\n        "
        return self._configure(("itemconfigure", tagOrId), cnf, kw)

    itemconfig = itemconfigure

    def tag_lower(self, *args):
        "Lower an item TAGORID given in ARGS\n        (optional below another item)."
        self.tk.call(((self._w, "lower") + args))

    lower = tag_lower

    def move(self, *args):
        "Move an item TAGORID given in ARGS."
        self.tk.call(((self._w, "move") + args))

    def moveto(self, tagOrId, x="", y=""):
        "Move the items given by TAGORID in the canvas coordinate\n        space so that the first coordinate pair of the bottommost\n        item with tag TAGORID is located at position (X,Y).\n        X and Y may be the empty string, in which case the\n        corresponding coordinate will be unchanged. All items matching\n        TAGORID remain in the same positions relative to each other."
        self.tk.call(self._w, "moveto", tagOrId, x, y)

    def postscript(self, cnf={}, **kw):
        "Print the contents of the canvas to a postscript\n        file. Valid options: colormap, colormode, file, fontmap,\n        height, pageanchor, pageheight, pagewidth, pagex, pagey,\n        rotate, width, x, y."
        return self.tk.call(((self._w, "postscript") + self._options(cnf, kw)))

    def tag_raise(self, *args):
        "Raise an item TAGORID given in ARGS\n        (optional above another item)."
        self.tk.call(((self._w, "raise") + args))

    lift = tkraise = tag_raise

    def scale(self, *args):
        "Scale item TAGORID with XORIGIN, YORIGIN, XSCALE, YSCALE."
        self.tk.call(((self._w, "scale") + args))

    def scan_mark(self, x, y):
        "Remember the current X, Y coordinates."
        self.tk.call(self._w, "scan", "mark", x, y)

    def scan_dragto(self, x, y, gain=10):
        "Adjust the view of the canvas to GAIN times the\n        difference between X and Y and the coordinates given in\n        scan_mark."
        self.tk.call(self._w, "scan", "dragto", x, y, gain)

    def select_adjust(self, tagOrId, index):
        "Adjust the end of the selection near the cursor of an item TAGORID to index."
        self.tk.call(self._w, "select", "adjust", tagOrId, index)

    def select_clear(self):
        "Clear the selection if it is in this widget."
        self.tk.call(self._w, "select", "clear")

    def select_from(self, tagOrId, index):
        "Set the fixed end of a selection in item TAGORID to INDEX."
        self.tk.call(self._w, "select", "from", tagOrId, index)

    def select_item(self):
        "Return the item which has the selection."
        return self.tk.call(self._w, "select", "item") or None

    def select_to(self, tagOrId, index):
        "Set the variable end of a selection in item TAGORID to INDEX."
        self.tk.call(self._w, "select", "to", tagOrId, index)

    def type(self, tagOrId):
        "Return the type of the item TAGORID."
        return self.tk.call(self._w, "type", tagOrId) or None


class Checkbutton(Widget):
    "Checkbutton widget which is either in on- or off-state."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a checkbutton widget with the parent MASTER.\n\n        Valid resource names: activebackground, activeforeground, anchor,\n        background, bd, bg, bitmap, borderwidth, command, cursor,\n        disabledforeground, fg, font, foreground, height,\n        highlightbackground, highlightcolor, highlightthickness, image,\n        indicatoron, justify, offvalue, onvalue, padx, pady, relief,\n        selectcolor, selectimage, state, takefocus, text, textvariable,\n        underline, variable, width, wraplength."
        Widget.__init__(self, master, "checkbutton", cnf, kw)

    def deselect(self):
        "Put the button in off-state."
        self.tk.call(self._w, "deselect")

    def flash(self):
        "Flash the button."
        self.tk.call(self._w, "flash")

    def invoke(self):
        "Toggle the button and invoke a command if given as resource."
        return self.tk.call(self._w, "invoke")

    def select(self):
        "Put the button in on-state."
        self.tk.call(self._w, "select")

    def toggle(self):
        "Toggle the button."
        self.tk.call(self._w, "toggle")


class Entry(Widget, XView):
    "Entry widget which allows displaying simple text."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct an entry widget with the parent MASTER.\n\n        Valid resource names: background, bd, bg, borderwidth, cursor,\n        exportselection, fg, font, foreground, highlightbackground,\n        highlightcolor, highlightthickness, insertbackground,\n        insertborderwidth, insertofftime, insertontime, insertwidth,\n        invalidcommand, invcmd, justify, relief, selectbackground,\n        selectborderwidth, selectforeground, show, state, takefocus,\n        textvariable, validate, validatecommand, vcmd, width,\n        xscrollcommand."
        Widget.__init__(self, master, "entry", cnf, kw)

    def delete(self, first, last=None):
        "Delete text from FIRST to LAST (not included)."
        self.tk.call(self._w, "delete", first, last)

    def get(self):
        "Return the text."
        return self.tk.call(self._w, "get")

    def icursor(self, index):
        "Insert cursor at INDEX."
        self.tk.call(self._w, "icursor", index)

    def index(self, index):
        "Return position of cursor."
        return self.tk.getint(self.tk.call(self._w, "index", index))

    def insert(self, index, string):
        "Insert STRING at INDEX."
        self.tk.call(self._w, "insert", index, string)

    def scan_mark(self, x):
        "Remember the current X, Y coordinates."
        self.tk.call(self._w, "scan", "mark", x)

    def scan_dragto(self, x):
        "Adjust the view of the canvas to 10 times the\n        difference between X and Y and the coordinates given in\n        scan_mark."
        self.tk.call(self._w, "scan", "dragto", x)

    def selection_adjust(self, index):
        "Adjust the end of the selection near the cursor to INDEX."
        self.tk.call(self._w, "selection", "adjust", index)

    select_adjust = selection_adjust

    def selection_clear(self):
        "Clear the selection if it is in this widget."
        self.tk.call(self._w, "selection", "clear")

    select_clear = selection_clear

    def selection_from(self, index):
        "Set the fixed end of a selection to INDEX."
        self.tk.call(self._w, "selection", "from", index)

    select_from = selection_from

    def selection_present(self):
        "Return True if there are characters selected in the entry, False\n        otherwise."
        return self.tk.getboolean(self.tk.call(self._w, "selection", "present"))

    select_present = selection_present

    def selection_range(self, start, end):
        "Set the selection from START to END (not included)."
        self.tk.call(self._w, "selection", "range", start, end)

    select_range = selection_range

    def selection_to(self, index):
        "Set the variable end of a selection to INDEX."
        self.tk.call(self._w, "selection", "to", index)

    select_to = selection_to


class Frame(Widget):
    "Frame widget which may contain other widgets and can have a 3D border."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a frame widget with the parent MASTER.\n\n        Valid resource names: background, bd, bg, borderwidth, class,\n        colormap, container, cursor, height, highlightbackground,\n        highlightcolor, highlightthickness, relief, takefocus, visual, width."
        cnf = _cnfmerge((cnf, kw))
        extra = ()
        if "class_" in cnf:
            extra = ("-class", cnf["class_"])
            del cnf["class_"]
        elif "class" in cnf:
            extra = ("-class", cnf["class"])
            del cnf["class"]
        Widget.__init__(self, master, "frame", cnf, {}, extra)


class Label(Widget):
    "Label widget which can display text and bitmaps."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a label widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            activebackground, activeforeground, anchor,\n            background, bitmap, borderwidth, cursor,\n            disabledforeground, font, foreground,\n            highlightbackground, highlightcolor,\n            highlightthickness, image, justify,\n            padx, pady, relief, takefocus, text,\n            textvariable, underline, wraplength\n\n        WIDGET-SPECIFIC OPTIONS\n\n            height, state, width\n\n        "
        Widget.__init__(self, master, "label", cnf, kw)


class Listbox(Widget, XView, YView):
    "Listbox widget which can display a list of strings."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a listbox widget with the parent MASTER.\n\n        Valid resource names: background, bd, bg, borderwidth, cursor,\n        exportselection, fg, font, foreground, height, highlightbackground,\n        highlightcolor, highlightthickness, relief, selectbackground,\n        selectborderwidth, selectforeground, selectmode, setgrid, takefocus,\n        width, xscrollcommand, yscrollcommand, listvariable."
        Widget.__init__(self, master, "listbox", cnf, kw)

    def activate(self, index):
        "Activate item identified by INDEX."
        self.tk.call(self._w, "activate", index)

    def bbox(self, index):
        "Return a tuple of X1,Y1,X2,Y2 coordinates for a rectangle\n        which encloses the item identified by the given index."
        return self._getints(self.tk.call(self._w, "bbox", index)) or None

    def curselection(self):
        "Return the indices of currently selected item."
        return self._getints(self.tk.call(self._w, "curselection")) or ()

    def delete(self, first, last=None):
        "Delete items from FIRST to LAST (included)."
        self.tk.call(self._w, "delete", first, last)

    def get(self, first, last=None):
        "Get list of items from FIRST to LAST (included)."
        if last is not None:
            return self.tk.splitlist(self.tk.call(self._w, "get", first, last))
        else:
            return self.tk.call(self._w, "get", first)

    def index(self, index):
        "Return index of item identified with INDEX."
        i = self.tk.call(self._w, "index", index)
        if i == "none":
            return None
        return self.tk.getint(i)

    def insert(self, index, *elements):
        "Insert ELEMENTS at INDEX."
        self.tk.call(((self._w, "insert", index) + elements))

    def nearest(self, y):
        "Get index of item which is nearest to y coordinate Y."
        return self.tk.getint(self.tk.call(self._w, "nearest", y))

    def scan_mark(self, x, y):
        "Remember the current X, Y coordinates."
        self.tk.call(self._w, "scan", "mark", x, y)

    def scan_dragto(self, x, y):
        "Adjust the view of the listbox to 10 times the\n        difference between X and Y and the coordinates given in\n        scan_mark."
        self.tk.call(self._w, "scan", "dragto", x, y)

    def see(self, index):
        "Scroll such that INDEX is visible."
        self.tk.call(self._w, "see", index)

    def selection_anchor(self, index):
        "Set the fixed end oft the selection to INDEX."
        self.tk.call(self._w, "selection", "anchor", index)

    select_anchor = selection_anchor

    def selection_clear(self, first, last=None):
        "Clear the selection from FIRST to LAST (included)."
        self.tk.call(self._w, "selection", "clear", first, last)

    select_clear = selection_clear

    def selection_includes(self, index):
        "Return True if INDEX is part of the selection."
        return self.tk.getboolean(self.tk.call(self._w, "selection", "includes", index))

    select_includes = selection_includes

    def selection_set(self, first, last=None):
        "Set the selection from FIRST to LAST (included) without\n        changing the currently selected elements."
        self.tk.call(self._w, "selection", "set", first, last)

    select_set = selection_set

    def size(self):
        "Return the number of elements in the listbox."
        return self.tk.getint(self.tk.call(self._w, "size"))

    def itemcget(self, index, option):
        "Return the resource value for an ITEM and an OPTION."
        return self.tk.call(((self._w, "itemcget") + (index, ("-" + option))))

    def itemconfigure(self, index, cnf=None, **kw):
        "Configure resources of an ITEM.\n\n        The values for resources are specified as keyword arguments.\n        To get an overview about the allowed keyword arguments\n        call the method without arguments.\n        Valid resource names: background, bg, foreground, fg,\n        selectbackground, selectforeground."
        return self._configure(("itemconfigure", index), cnf, kw)

    itemconfig = itemconfigure


class Menu(Widget):
    "Menu widget which allows displaying menu bars, pull-down menus and pop-up menus."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct menu widget with the parent MASTER.\n\n        Valid resource names: activebackground, activeborderwidth,\n        activeforeground, background, bd, bg, borderwidth, cursor,\n        disabledforeground, fg, font, foreground, postcommand, relief,\n        selectcolor, takefocus, tearoff, tearoffcommand, title, type."
        Widget.__init__(self, master, "menu", cnf, kw)

    def tk_popup(self, x, y, entry=""):
        "Post the menu at position X,Y with entry ENTRY."
        self.tk.call("tk_popup", self._w, x, y, entry)

    def activate(self, index):
        "Activate entry at INDEX."
        self.tk.call(self._w, "activate", index)

    def add(self, itemType, cnf={}, **kw):
        "Internal function."
        self.tk.call(((self._w, "add", itemType) + self._options(cnf, kw)))

    def add_cascade(self, cnf={}, **kw):
        "Add hierarchical menu item."
        self.add("cascade", (cnf or kw))

    def add_checkbutton(self, cnf={}, **kw):
        "Add checkbutton menu item."
        self.add("checkbutton", (cnf or kw))

    def add_command(self, cnf={}, **kw):
        "Add command menu item."
        self.add("command", (cnf or kw))

    def add_radiobutton(self, cnf={}, **kw):
        "Addd radio menu item."
        self.add("radiobutton", (cnf or kw))

    def add_separator(self, cnf={}, **kw):
        "Add separator."
        self.add("separator", (cnf or kw))

    def insert(self, index, itemType, cnf={}, **kw):
        "Internal function."
        self.tk.call(((self._w, "insert", index, itemType) + self._options(cnf, kw)))

    def insert_cascade(self, index, cnf={}, **kw):
        "Add hierarchical menu item at INDEX."
        self.insert(index, "cascade", (cnf or kw))

    def insert_checkbutton(self, index, cnf={}, **kw):
        "Add checkbutton menu item at INDEX."
        self.insert(index, "checkbutton", (cnf or kw))

    def insert_command(self, index, cnf={}, **kw):
        "Add command menu item at INDEX."
        self.insert(index, "command", (cnf or kw))

    def insert_radiobutton(self, index, cnf={}, **kw):
        "Addd radio menu item at INDEX."
        self.insert(index, "radiobutton", (cnf or kw))

    def insert_separator(self, index, cnf={}, **kw):
        "Add separator at INDEX."
        self.insert(index, "separator", (cnf or kw))

    def delete(self, index1, index2=None):
        "Delete menu items between INDEX1 and INDEX2 (included)."
        if index2 is None:
            index2 = index1
        (num_index1, num_index2) = (self.index(index1), self.index(index2))
        if (num_index1 is None) or (num_index2 is None):
            (num_index1, num_index2) = (0, (-1))
        for i in range(num_index1, (num_index2 + 1)):
            if "command" in self.entryconfig(i):
                c = str(self.entrycget(i, "command"))
                if c:
                    self.deletecommand(c)
        self.tk.call(self._w, "delete", index1, index2)

    def entrycget(self, index, option):
        "Return the resource value of a menu item for OPTION at INDEX."
        return self.tk.call(self._w, "entrycget", index, ("-" + option))

    def entryconfigure(self, index, cnf=None, **kw):
        "Configure a menu item at INDEX."
        return self._configure(("entryconfigure", index), cnf, kw)

    entryconfig = entryconfigure

    def index(self, index):
        "Return the index of a menu item identified by INDEX."
        i = self.tk.call(self._w, "index", index)
        if i == "none":
            return None
        return self.tk.getint(i)

    def invoke(self, index):
        "Invoke a menu item identified by INDEX and execute\n        the associated command."
        return self.tk.call(self._w, "invoke", index)

    def post(self, x, y):
        "Display a menu at position X,Y."
        self.tk.call(self._w, "post", x, y)

    def type(self, index):
        "Return the type of the menu item at INDEX."
        return self.tk.call(self._w, "type", index)

    def unpost(self):
        "Unmap a menu."
        self.tk.call(self._w, "unpost")

    def xposition(self, index):
        "Return the x-position of the leftmost pixel of the menu item\n        at INDEX."
        return self.tk.getint(self.tk.call(self._w, "xposition", index))

    def yposition(self, index):
        "Return the y-position of the topmost pixel of the menu item at INDEX."
        return self.tk.getint(self.tk.call(self._w, "yposition", index))


class Menubutton(Widget):
    "Menubutton widget, obsolete since Tk8.0."

    def __init__(self, master=None, cnf={}, **kw):
        Widget.__init__(self, master, "menubutton", cnf, kw)


class Message(Widget):
    "Message widget to display multiline text. Obsolete since Label does it too."

    def __init__(self, master=None, cnf={}, **kw):
        Widget.__init__(self, master, "message", cnf, kw)


class Radiobutton(Widget):
    "Radiobutton widget which shows only one of several buttons in on-state."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a radiobutton widget with the parent MASTER.\n\n        Valid resource names: activebackground, activeforeground, anchor,\n        background, bd, bg, bitmap, borderwidth, command, cursor,\n        disabledforeground, fg, font, foreground, height,\n        highlightbackground, highlightcolor, highlightthickness, image,\n        indicatoron, justify, padx, pady, relief, selectcolor, selectimage,\n        state, takefocus, text, textvariable, underline, value, variable,\n        width, wraplength."
        Widget.__init__(self, master, "radiobutton", cnf, kw)

    def deselect(self):
        "Put the button in off-state."
        self.tk.call(self._w, "deselect")

    def flash(self):
        "Flash the button."
        self.tk.call(self._w, "flash")

    def invoke(self):
        "Toggle the button and invoke a command if given as resource."
        return self.tk.call(self._w, "invoke")

    def select(self):
        "Put the button in on-state."
        self.tk.call(self._w, "select")


class Scale(Widget):
    "Scale widget which can display a numerical scale."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a scale widget with the parent MASTER.\n\n        Valid resource names: activebackground, background, bigincrement, bd,\n        bg, borderwidth, command, cursor, digits, fg, font, foreground, from,\n        highlightbackground, highlightcolor, highlightthickness, label,\n        length, orient, relief, repeatdelay, repeatinterval, resolution,\n        showvalue, sliderlength, sliderrelief, state, takefocus,\n        tickinterval, to, troughcolor, variable, width."
        Widget.__init__(self, master, "scale", cnf, kw)

    def get(self):
        "Get the current value as integer or float."
        value = self.tk.call(self._w, "get")
        try:
            return self.tk.getint(value)
        except (ValueError, TypeError, TclError):
            return self.tk.getdouble(value)

    def set(self, value):
        "Set the value to VALUE."
        self.tk.call(self._w, "set", value)

    def coords(self, value=None):
        "Return a tuple (X,Y) of the point along the centerline of the\n        trough that corresponds to VALUE or the current value if None is\n        given."
        return self._getints(self.tk.call(self._w, "coords", value))

    def identify(self, x, y):
        'Return where the point X,Y lies. Valid return values are "slider",\n        "though1" and "though2".'
        return self.tk.call(self._w, "identify", x, y)


class Scrollbar(Widget):
    "Scrollbar widget which displays a slider at a certain position."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a scrollbar widget with the parent MASTER.\n\n        Valid resource names: activebackground, activerelief,\n        background, bd, bg, borderwidth, command, cursor,\n        elementborderwidth, highlightbackground,\n        highlightcolor, highlightthickness, jump, orient,\n        relief, repeatdelay, repeatinterval, takefocus,\n        troughcolor, width."
        Widget.__init__(self, master, "scrollbar", cnf, kw)

    def activate(self, index=None):
        'Marks the element indicated by index as active.\n        The only index values understood by this method are "arrow1",\n        "slider", or "arrow2".  If any other value is specified then no\n        element of the scrollbar will be active.  If index is not specified,\n        the method returns the name of the element that is currently active,\n        or None if no element is active.'
        return self.tk.call(self._w, "activate", index) or None

    def delta(self, deltax, deltay):
        "Return the fractional change of the scrollbar setting if it\n        would be moved by DELTAX or DELTAY pixels."
        return self.tk.getdouble(self.tk.call(self._w, "delta", deltax, deltay))

    def fraction(self, x, y):
        "Return the fractional value which corresponds to a slider\n        position of X,Y."
        return self.tk.getdouble(self.tk.call(self._w, "fraction", x, y))

    def identify(self, x, y):
        'Return the element under position X,Y as one of\n        "arrow1","slider","arrow2" or "".'
        return self.tk.call(self._w, "identify", x, y)

    def get(self):
        "Return the current fractional values (upper and lower end)\n        of the slider position."
        return self._getdoubles(self.tk.call(self._w, "get"))

    def set(self, first, last):
        "Set the fractional values of the slider position (upper and\n        lower ends as value between 0 and 1)."
        self.tk.call(self._w, "set", first, last)


class Text(Widget, XView, YView):
    "Text widget which can display text in various forms."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a text widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            background, borderwidth, cursor,\n            exportselection, font, foreground,\n            highlightbackground, highlightcolor,\n            highlightthickness, insertbackground,\n            insertborderwidth, insertofftime,\n            insertontime, insertwidth, padx, pady,\n            relief, selectbackground,\n            selectborderwidth, selectforeground,\n            setgrid, takefocus,\n            xscrollcommand, yscrollcommand,\n\n        WIDGET-SPECIFIC OPTIONS\n\n            autoseparators, height, maxundo,\n            spacing1, spacing2, spacing3,\n            state, tabs, undo, width, wrap,\n\n        "
        Widget.__init__(self, master, "text", cnf, kw)

    def bbox(self, index):
        "Return a tuple of (x,y,width,height) which gives the bounding\n        box of the visible part of the character at the given index."
        return self._getints(self.tk.call(self._w, "bbox", index)) or None

    def compare(self, index1, op, index2):
        "Return whether between index INDEX1 and index INDEX2 the\n        relation OP is satisfied. OP is one of <, <=, ==, >=, >, or !=."
        return self.tk.getboolean(self.tk.call(self._w, "compare", index1, op, index2))

    def count(self, index1, index2, *args):
        'Counts the number of relevant things between the two indices.\n        If index1 is after index2, the result will be a negative number\n        (and this holds for each of the possible options).\n\n        The actual items which are counted depends on the options given by\n        args. The result is a list of integers, one for the result of each\n        counting option given. Valid counting options are "chars",\n        "displaychars", "displayindices", "displaylines", "indices",\n        "lines", "xpixels" and "ypixels". There is an additional possible\n        option "update", which if given then all subsequent options ensure\n        that any possible out of date information is recalculated.'
        args = [("-%s" % arg) for arg in args if (not arg.startswith("-"))]
        args += [index1, index2]
        res = self.tk.call(self._w, "count", *args) or None
        if (res is not None) and (len(args) <= 3):
            return (res,)
        else:
            return res

    def debug(self, boolean=None):
        "Turn on the internal consistency checks of the B-Tree inside the text\n        widget according to BOOLEAN."
        if boolean is None:
            return self.tk.getboolean(self.tk.call(self._w, "debug"))
        self.tk.call(self._w, "debug", boolean)

    def delete(self, index1, index2=None):
        "Delete the characters between INDEX1 and INDEX2 (not included)."
        self.tk.call(self._w, "delete", index1, index2)

    def dlineinfo(self, index):
        "Return tuple (x,y,width,height,baseline) giving the bounding box\n        and baseline position of the visible part of the line containing\n        the character at INDEX."
        return self._getints(self.tk.call(self._w, "dlineinfo", index))

    def dump(self, index1, index2=None, command=None, **kw):
        "Return the contents of the widget between index1 and index2.\n\n        The type of contents returned in filtered based on the keyword\n        parameters; if 'all', 'image', 'mark', 'tag', 'text', or 'window' are\n        given and true, then the corresponding items are returned. The result\n        is a list of triples of the form (key, value, index). If none of the\n        keywords are true then 'all' is used by default.\n\n        If the 'command' argument is given, it is called once for each element\n        of the list of triples, with the values of each triple serving as the\n        arguments to the function. In this case the list is not returned."
        args = []
        func_name = None
        result = None
        if not command:
            result = []

            def append_triple(key, value, index, result=result):
                result.append((key, value, index))

            command = append_triple
        try:
            if not isinstance(command, str):
                func_name = command = self._register(command)
            args += ["-command", command]
            for key in kw:
                if kw[key]:
                    args.append(("-" + key))
            args.append(index1)
            if index2:
                args.append(index2)
            self.tk.call(self._w, "dump", *args)
            return result
        finally:
            if func_name:
                self.deletecommand(func_name)

    def edit(self, *args):
        "Internal method\n\n        This method controls the undo mechanism and\n        the modified flag. The exact behavior of the\n        command depends on the option argument that\n        follows the edit argument. The following forms\n        of the command are currently supported:\n\n        edit_modified, edit_redo, edit_reset, edit_separator\n        and edit_undo\n\n        "
        return self.tk.call(self._w, "edit", *args)

    def edit_modified(self, arg=None):
        "Get or Set the modified flag\n\n        If arg is not specified, returns the modified\n        flag of the widget. The insert, delete, edit undo and\n        edit redo commands or the user can set or clear the\n        modified flag. If boolean is specified, sets the\n        modified flag of the widget to arg.\n        "
        return self.edit("modified", arg)

    def edit_redo(self):
        "Redo the last undone edit\n\n        When the undo option is true, reapplies the last\n        undone edits provided no other edits were done since\n        then. Generates an error when the redo stack is empty.\n        Does nothing when the undo option is false.\n        "
        return self.edit("redo")

    def edit_reset(self):
        "Clears the undo and redo stacks\n        "
        return self.edit("reset")

    def edit_separator(self):
        "Inserts a separator (boundary) on the undo stack.\n\n        Does nothing when the undo option is false\n        "
        return self.edit("separator")

    def edit_undo(self):
        "Undoes the last edit action\n\n        If the undo option is true. An edit action is defined\n        as all the insert and delete commands that are recorded\n        on the undo stack in between two separators. Generates\n        an error when the undo stack is empty. Does nothing\n        when the undo option is false\n        "
        return self.edit("undo")

    def get(self, index1, index2=None):
        "Return the text from INDEX1 to INDEX2 (not included)."
        return self.tk.call(self._w, "get", index1, index2)

    def image_cget(self, index, option):
        "Return the value of OPTION of an embedded image at INDEX."
        if option[:1] != "-":
            option = "-" + option
        if option[(-1):] == "_":
            option = option[:(-1)]
        return self.tk.call(self._w, "image", "cget", index, option)

    def image_configure(self, index, cnf=None, **kw):
        "Configure an embedded image at INDEX."
        return self._configure(("image", "configure", index), cnf, kw)

    def image_create(self, index, cnf={}, **kw):
        "Create an embedded image at INDEX."
        return self.tk.call(self._w, "image", "create", index, *self._options(cnf, kw))

    def image_names(self):
        "Return all names of embedded images in this widget."
        return self.tk.call(self._w, "image", "names")

    def index(self, index):
        "Return the index in the form line.char for INDEX."
        return str(self.tk.call(self._w, "index", index))

    def insert(self, index, chars, *args):
        "Insert CHARS before the characters at INDEX. An additional\n        tag can be given in ARGS. Additional CHARS and tags can follow in ARGS."
        self.tk.call(((self._w, "insert", index, chars) + args))

    def mark_gravity(self, markName, direction=None):
        "Change the gravity of a mark MARKNAME to DIRECTION (LEFT or RIGHT).\n        Return the current value if None is given for DIRECTION."
        return self.tk.call((self._w, "mark", "gravity", markName, direction))

    def mark_names(self):
        "Return all mark names."
        return self.tk.splitlist(self.tk.call(self._w, "mark", "names"))

    def mark_set(self, markName, index):
        "Set mark MARKNAME before the character at INDEX."
        self.tk.call(self._w, "mark", "set", markName, index)

    def mark_unset(self, *markNames):
        "Delete all marks in MARKNAMES."
        self.tk.call(((self._w, "mark", "unset") + markNames))

    def mark_next(self, index):
        "Return the name of the next mark after INDEX."
        return self.tk.call(self._w, "mark", "next", index) or None

    def mark_previous(self, index):
        "Return the name of the previous mark before INDEX."
        return self.tk.call(self._w, "mark", "previous", index) or None

    def peer_create(self, newPathName, cnf={}, **kw):
        "Creates a peer text widget with the given newPathName, and any\n        optional standard configuration options. By default the peer will\n        have the same start and end line as the parent widget, but\n        these can be overridden with the standard configuration options."
        self.tk.call(self._w, "peer", "create", newPathName, *self._options(cnf, kw))

    def peer_names(self):
        "Returns a list of peers of this widget (this does not include\n        the widget itself)."
        return self.tk.splitlist(self.tk.call(self._w, "peer", "names"))

    def replace(self, index1, index2, chars, *args):
        "Replaces the range of characters between index1 and index2 with\n        the given characters and tags specified by args.\n\n        See the method insert for some more information about args, and the\n        method delete for information about the indices."
        self.tk.call(self._w, "replace", index1, index2, chars, *args)

    def scan_mark(self, x, y):
        "Remember the current X, Y coordinates."
        self.tk.call(self._w, "scan", "mark", x, y)

    def scan_dragto(self, x, y):
        "Adjust the view of the text to 10 times the\n        difference between X and Y and the coordinates given in\n        scan_mark."
        self.tk.call(self._w, "scan", "dragto", x, y)

    def search(
        self,
        pattern,
        index,
        stopindex=None,
        forwards=None,
        backwards=None,
        exact=None,
        regexp=None,
        nocase=None,
        count=None,
        elide=None,
    ):
        "Search PATTERN beginning from INDEX until STOPINDEX.\n        Return the index of the first character of a match or an\n        empty string."
        args = [self._w, "search"]
        if forwards:
            args.append("-forwards")
        if backwards:
            args.append("-backwards")
        if exact:
            args.append("-exact")
        if regexp:
            args.append("-regexp")
        if nocase:
            args.append("-nocase")
        if elide:
            args.append("-elide")
        if count:
            args.append("-count")
            args.append(count)
        if pattern and (pattern[0] == "-"):
            args.append("--")
        args.append(pattern)
        args.append(index)
        if stopindex:
            args.append(stopindex)
        return str(self.tk.call(tuple(args)))

    def see(self, index):
        "Scroll such that the character at INDEX is visible."
        self.tk.call(self._w, "see", index)

    def tag_add(self, tagName, index1, *args):
        "Add tag TAGNAME to all characters between INDEX1 and index2 in ARGS.\n        Additional pairs of indices may follow in ARGS."
        self.tk.call(((self._w, "tag", "add", tagName, index1) + args))

    def tag_unbind(self, tagName, sequence, funcid=None):
        "Unbind for all characters with TAGNAME for event SEQUENCE  the\n        function identified with FUNCID."
        self.tk.call(self._w, "tag", "bind", tagName, sequence, "")
        if funcid:
            self.deletecommand(funcid)

    def tag_bind(self, tagName, sequence, func, add=None):
        "Bind to all characters with TAGNAME at event SEQUENCE a call to function FUNC.\n\n        An additional boolean parameter ADD specifies whether FUNC will be\n        called additionally to the other bound function or whether it will\n        replace the previous function. See bind for the return value."
        return self._bind((self._w, "tag", "bind", tagName), sequence, func, add)

    def tag_cget(self, tagName, option):
        "Return the value of OPTION for tag TAGNAME."
        if option[:1] != "-":
            option = "-" + option
        if option[(-1):] == "_":
            option = option[:(-1)]
        return self.tk.call(self._w, "tag", "cget", tagName, option)

    def tag_configure(self, tagName, cnf=None, **kw):
        "Configure a tag TAGNAME."
        return self._configure(("tag", "configure", tagName), cnf, kw)

    tag_config = tag_configure

    def tag_delete(self, *tagNames):
        "Delete all tags in TAGNAMES."
        self.tk.call(((self._w, "tag", "delete") + tagNames))

    def tag_lower(self, tagName, belowThis=None):
        "Change the priority of tag TAGNAME such that it is lower\n        than the priority of BELOWTHIS."
        self.tk.call(self._w, "tag", "lower", tagName, belowThis)

    def tag_names(self, index=None):
        "Return a list of all tag names."
        return self.tk.splitlist(self.tk.call(self._w, "tag", "names", index))

    def tag_nextrange(self, tagName, index1, index2=None):
        "Return a list of start and end index for the first sequence of\n        characters between INDEX1 and INDEX2 which all have tag TAGNAME.\n        The text is searched forward from INDEX1."
        return self.tk.splitlist(
            self.tk.call(self._w, "tag", "nextrange", tagName, index1, index2)
        )

    def tag_prevrange(self, tagName, index1, index2=None):
        "Return a list of start and end index for the first sequence of\n        characters between INDEX1 and INDEX2 which all have tag TAGNAME.\n        The text is searched backwards from INDEX1."
        return self.tk.splitlist(
            self.tk.call(self._w, "tag", "prevrange", tagName, index1, index2)
        )

    def tag_raise(self, tagName, aboveThis=None):
        "Change the priority of tag TAGNAME such that it is higher\n        than the priority of ABOVETHIS."
        self.tk.call(self._w, "tag", "raise", tagName, aboveThis)

    def tag_ranges(self, tagName):
        "Return a list of ranges of text which have tag TAGNAME."
        return self.tk.splitlist(self.tk.call(self._w, "tag", "ranges", tagName))

    def tag_remove(self, tagName, index1, index2=None):
        "Remove tag TAGNAME from all characters between INDEX1 and INDEX2."
        self.tk.call(self._w, "tag", "remove", tagName, index1, index2)

    def window_cget(self, index, option):
        "Return the value of OPTION of an embedded window at INDEX."
        if option[:1] != "-":
            option = "-" + option
        if option[(-1):] == "_":
            option = option[:(-1)]
        return self.tk.call(self._w, "window", "cget", index, option)

    def window_configure(self, index, cnf=None, **kw):
        "Configure an embedded window at INDEX."
        return self._configure(("window", "configure", index), cnf, kw)

    window_config = window_configure

    def window_create(self, index, cnf={}, **kw):
        "Create a window at INDEX."
        self.tk.call(((self._w, "window", "create", index) + self._options(cnf, kw)))

    def window_names(self):
        "Return all names of embedded windows in this widget."
        return self.tk.splitlist(self.tk.call(self._w, "window", "names"))

    def yview_pickplace(self, *what):
        "Obsolete function, use see."
        self.tk.call(((self._w, "yview", "-pickplace") + what))


class _setit:
    "Internal class. It wraps the command in the widget OptionMenu."

    def __init__(self, var, value, callback=None):
        self.__value = value
        self.__var = var
        self.__callback = callback

    def __call__(self, *args):
        self.__var.set(self.__value)
        if self.__callback is not None:
            self.__callback(self.__value, *args)


class OptionMenu(Menubutton):
    "OptionMenu which allows the user to select a value from a menu."

    def __init__(self, master, variable, value, *values, **kwargs):
        "Construct an optionmenu widget with the parent MASTER, with\n        the resource textvariable set to VARIABLE, the initially selected\n        value VALUE, the other menu values VALUES and an additional\n        keyword argument command."
        kw = {
            "borderwidth": 2,
            "textvariable": variable,
            "indicatoron": 1,
            "relief": RAISED,
            "anchor": "c",
            "highlightthickness": 2,
        }
        Widget.__init__(self, master, "menubutton", kw)
        self.widgetName = "tk_optionMenu"
        menu = self.__menu = Menu(self, name="menu", tearoff=0)
        self.menuname = menu._w
        callback = kwargs.get("command")
        if "command" in kwargs:
            del kwargs["command"]
        if kwargs:
            raise TclError(("unknown option -" + next(iter(kwargs))))
        menu.add_command(label=value, command=_setit(variable, value, callback))
        for v in values:
            menu.add_command(label=v, command=_setit(variable, v, callback))
        self["menu"] = menu

    def __getitem__(self, name):
        if name == "menu":
            return self.__menu
        return Widget.__getitem__(self, name)

    def destroy(self):
        "Destroy this widget and the associated menu."
        Menubutton.destroy(self)
        self.__menu = None


class Image:
    "Base class for images."
    _last_id = 0

    def __init__(self, imgtype, name=None, cnf={}, master=None, **kw):
        self.name = None
        if master is None:
            master = _get_default_root("create image")
        self.tk = getattr(master, "tk", master)
        if not name:
            Image._last_id += 1
            name = "pyimage%r" % (Image._last_id,)
        if kw and cnf:
            cnf = _cnfmerge((cnf, kw))
        elif kw:
            cnf = kw
        options = ()
        for (k, v) in cnf.items():
            if callable(v):
                v = self._register(v)
            options = options + (("-" + k), v)
        self.tk.call((("image", "create", imgtype, name) + options))
        self.name = name

    def __str__(self):
        return self.name

    def __del__(self):
        if self.name:
            try:
                self.tk.call("image", "delete", self.name)
            except TclError:
                pass

    def __setitem__(self, key, value):
        self.tk.call(self.name, "configure", ("-" + key), value)

    def __getitem__(self, key):
        return self.tk.call(self.name, "configure", ("-" + key))

    def configure(self, **kw):
        "Configure the image."
        res = ()
        for (k, v) in _cnfmerge(kw).items():
            if v is not None:
                if k[(-1)] == "_":
                    k = k[:(-1)]
                if callable(v):
                    v = self._register(v)
                res = res + (("-" + k), v)
        self.tk.call(((self.name, "config") + res))

    config = configure

    def height(self):
        "Return the height of the image."
        return self.tk.getint(self.tk.call("image", "height", self.name))

    def type(self):
        'Return the type of the image, e.g. "photo" or "bitmap".'
        return self.tk.call("image", "type", self.name)

    def width(self):
        "Return the width of the image."
        return self.tk.getint(self.tk.call("image", "width", self.name))


class PhotoImage(Image):
    "Widget which can display images in PGM, PPM, GIF, PNG format."

    def __init__(self, name=None, cnf={}, master=None, **kw):
        "Create an image with NAME.\n\n        Valid resource names: data, format, file, gamma, height, palette,\n        width."
        Image.__init__(self, "photo", name, cnf, master, **kw)

    def blank(self):
        "Display a transparent image."
        self.tk.call(self.name, "blank")

    def cget(self, option):
        "Return the value of OPTION."
        return self.tk.call(self.name, "cget", ("-" + option))

    def __getitem__(self, key):
        return self.tk.call(self.name, "cget", ("-" + key))

    def copy(self):
        "Return a new PhotoImage with the same image as this widget."
        destImage = PhotoImage(master=self.tk)
        self.tk.call(destImage, "copy", self.name)
        return destImage

    def zoom(self, x, y=""):
        "Return a new PhotoImage with the same image as this widget\n        but zoom it with a factor of x in the X direction and y in the Y\n        direction.  If y is not given, the default value is the same as x.\n        "
        destImage = PhotoImage(master=self.tk)
        if y == "":
            y = x
        self.tk.call(destImage, "copy", self.name, "-zoom", x, y)
        return destImage

    def subsample(self, x, y=""):
        "Return a new PhotoImage based on the same image as this widget\n        but use only every Xth or Yth pixel.  If y is not given, the\n        default value is the same as x.\n        "
        destImage = PhotoImage(master=self.tk)
        if y == "":
            y = x
        self.tk.call(destImage, "copy", self.name, "-subsample", x, y)
        return destImage

    def get(self, x, y):
        "Return the color (red, green, blue) of the pixel at X,Y."
        return self.tk.call(self.name, "get", x, y)

    def put(self, data, to=None):
        'Put row formatted colors to image starting from\n        position TO, e.g. image.put("{red green} {blue yellow}", to=(4,6))'
        args = (self.name, "put", data)
        if to:
            if to[0] == "-to":
                to = to[1:]
            args = (args + ("-to",)) + tuple(to)
        self.tk.call(args)

    def write(self, filename, format=None, from_coords=None):
        "Write image to file FILENAME in FORMAT starting from\n        position FROM_COORDS."
        args = (self.name, "write", filename)
        if format:
            args = args + ("-format", format)
        if from_coords:
            args = (args + ("-from",)) + tuple(from_coords)
        self.tk.call(args)

    def transparency_get(self, x, y):
        "Return True if the pixel at x,y is transparent."
        return self.tk.getboolean(self.tk.call(self.name, "transparency", "get", x, y))

    def transparency_set(self, x, y, boolean):
        "Set the transparency of the pixel at x,y."
        self.tk.call(self.name, "transparency", "set", x, y, boolean)


class BitmapImage(Image):
    "Widget which can display images in XBM format."

    def __init__(self, name=None, cnf={}, master=None, **kw):
        "Create a bitmap with NAME.\n\n        Valid resource names: background, data, file, foreground, maskdata, maskfile."
        Image.__init__(self, "bitmap", name, cnf, master, **kw)


def image_names():
    tk = _get_default_root("use image_names()").tk
    return tk.splitlist(tk.call("image", "names"))


def image_types():
    tk = _get_default_root("use image_types()").tk
    return tk.splitlist(tk.call("image", "types"))


class Spinbox(Widget, XView):
    "spinbox widget."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a spinbox widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            activebackground, background, borderwidth,\n            cursor, exportselection, font, foreground,\n            highlightbackground, highlightcolor,\n            highlightthickness, insertbackground,\n            insertborderwidth, insertofftime,\n            insertontime, insertwidth, justify, relief,\n            repeatdelay, repeatinterval,\n            selectbackground, selectborderwidth\n            selectforeground, takefocus, textvariable\n            xscrollcommand.\n\n        WIDGET-SPECIFIC OPTIONS\n\n            buttonbackground, buttoncursor,\n            buttondownrelief, buttonuprelief,\n            command, disabledbackground,\n            disabledforeground, format, from,\n            invalidcommand, increment,\n            readonlybackground, state, to,\n            validate, validatecommand values,\n            width, wrap,\n        "
        Widget.__init__(self, master, "spinbox", cnf, kw)

    def bbox(self, index):
        "Return a tuple of X1,Y1,X2,Y2 coordinates for a\n        rectangle which encloses the character given by index.\n\n        The first two elements of the list give the x and y\n        coordinates of the upper-left corner of the screen\n        area covered by the character (in pixels relative\n        to the widget) and the last two elements give the\n        width and height of the character, in pixels. The\n        bounding box may refer to a region outside the\n        visible area of the window.\n        "
        return self._getints(self.tk.call(self._w, "bbox", index)) or None

    def delete(self, first, last=None):
        "Delete one or more elements of the spinbox.\n\n        First is the index of the first character to delete,\n        and last is the index of the character just after\n        the last one to delete. If last isn't specified it\n        defaults to first+1, i.e. a single character is\n        deleted.  This command returns an empty string.\n        "
        return self.tk.call(self._w, "delete", first, last)

    def get(self):
        "Returns the spinbox's string"
        return self.tk.call(self._w, "get")

    def icursor(self, index):
        "Alter the position of the insertion cursor.\n\n        The insertion cursor will be displayed just before\n        the character given by index. Returns an empty string\n        "
        return self.tk.call(self._w, "icursor", index)

    def identify(self, x, y):
        "Returns the name of the widget at position x, y\n\n        Return value is one of: none, buttondown, buttonup, entry\n        "
        return self.tk.call(self._w, "identify", x, y)

    def index(self, index):
        "Returns the numerical index corresponding to index\n        "
        return self.tk.call(self._w, "index", index)

    def insert(self, index, s):
        "Insert string s at index\n\n         Returns an empty string.\n        "
        return self.tk.call(self._w, "insert", index, s)

    def invoke(self, element):
        "Causes the specified element to be invoked\n\n        The element could be buttondown or buttonup\n        triggering the action associated with it.\n        "
        return self.tk.call(self._w, "invoke", element)

    def scan(self, *args):
        "Internal function."
        return self._getints(self.tk.call(((self._w, "scan") + args))) or ()

    def scan_mark(self, x):
        "Records x and the current view in the spinbox window;\n\n        used in conjunction with later scan dragto commands.\n        Typically this command is associated with a mouse button\n        press in the widget. It returns an empty string.\n        "
        return self.scan("mark", x)

    def scan_dragto(self, x):
        "Compute the difference between the given x argument\n        and the x argument to the last scan mark command\n\n        It then adjusts the view left or right by 10 times the\n        difference in x-coordinates. This command is typically\n        associated with mouse motion events in the widget, to\n        produce the effect of dragging the spinbox at high speed\n        through the window. The return value is an empty string.\n        "
        return self.scan("dragto", x)

    def selection(self, *args):
        "Internal function."
        return self._getints(self.tk.call(((self._w, "selection") + args))) or ()

    def selection_adjust(self, index):
        "Locate the end of the selection nearest to the character\n        given by index,\n\n        Then adjust that end of the selection to be at index\n        (i.e including but not going beyond index). The other\n        end of the selection is made the anchor point for future\n        select to commands. If the selection isn't currently in\n        the spinbox, then a new selection is created to include\n        the characters between index and the most recent selection\n        anchor point, inclusive.\n        "
        return self.selection("adjust", index)

    def selection_clear(self):
        "Clear the selection\n\n        If the selection isn't in this widget then the\n        command has no effect.\n        "
        return self.selection("clear")

    def selection_element(self, element=None):
        "Sets or gets the currently selected element.\n\n        If a spinbutton element is specified, it will be\n        displayed depressed.\n        "
        return self.tk.call(self._w, "selection", "element", element)

    def selection_from(self, index):
        "Set the fixed end of a selection to INDEX."
        self.selection("from", index)

    def selection_present(self):
        "Return True if there are characters selected in the spinbox, False\n        otherwise."
        return self.tk.getboolean(self.tk.call(self._w, "selection", "present"))

    def selection_range(self, start, end):
        "Set the selection from START to END (not included)."
        self.selection("range", start, end)

    def selection_to(self, index):
        "Set the variable end of a selection to INDEX."
        self.selection("to", index)


class LabelFrame(Widget):
    "labelframe widget."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a labelframe widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            borderwidth, cursor, font, foreground,\n            highlightbackground, highlightcolor,\n            highlightthickness, padx, pady, relief,\n            takefocus, text\n\n        WIDGET-SPECIFIC OPTIONS\n\n            background, class, colormap, container,\n            height, labelanchor, labelwidget,\n            visual, width\n        "
        Widget.__init__(self, master, "labelframe", cnf, kw)


class PanedWindow(Widget):
    "panedwindow widget."

    def __init__(self, master=None, cnf={}, **kw):
        "Construct a panedwindow widget with the parent MASTER.\n\n        STANDARD OPTIONS\n\n            background, borderwidth, cursor, height,\n            orient, relief, width\n\n        WIDGET-SPECIFIC OPTIONS\n\n            handlepad, handlesize, opaqueresize,\n            sashcursor, sashpad, sashrelief,\n            sashwidth, showhandle,\n        "
        Widget.__init__(self, master, "panedwindow", cnf, kw)

    def add(self, child, **kw):
        "Add a child widget to the panedwindow in a new pane.\n\n        The child argument is the name of the child widget\n        followed by pairs of arguments that specify how to\n        manage the windows. The possible options and values\n        are the ones accepted by the paneconfigure method.\n        "
        self.tk.call(((self._w, "add", child) + self._options(kw)))

    def remove(self, child):
        "Remove the pane containing child from the panedwindow\n\n        All geometry management options for child will be forgotten.\n        "
        self.tk.call(self._w, "forget", child)

    forget = remove

    def identify(self, x, y):
        "Identify the panedwindow component at point x, y\n\n        If the point is over a sash or a sash handle, the result\n        is a two element list containing the index of the sash or\n        handle, and a word indicating whether it is over a sash\n        or a handle, such as {0 sash} or {2 handle}. If the point\n        is over any other part of the panedwindow, the result is\n        an empty list.\n        "
        return self.tk.call(self._w, "identify", x, y)

    def proxy(self, *args):
        "Internal function."
        return self._getints(self.tk.call(((self._w, "proxy") + args))) or ()

    def proxy_coord(self):
        "Return the x and y pair of the most recent proxy location\n        "
        return self.proxy("coord")

    def proxy_forget(self):
        "Remove the proxy from the display.\n        "
        return self.proxy("forget")

    def proxy_place(self, x, y):
        "Place the proxy at the given x and y coordinates.\n        "
        return self.proxy("place", x, y)

    def sash(self, *args):
        "Internal function."
        return self._getints(self.tk.call(((self._w, "sash") + args))) or ()

    def sash_coord(self, index):
        "Return the current x and y pair for the sash given by index.\n\n        Index must be an integer between 0 and 1 less than the\n        number of panes in the panedwindow. The coordinates given are\n        those of the top left corner of the region containing the sash.\n        pathName sash dragto index x y This command computes the\n        difference between the given coordinates and the coordinates\n        given to the last sash coord command for the given sash. It then\n        moves that sash the computed difference. The return value is the\n        empty string.\n        "
        return self.sash("coord", index)

    def sash_mark(self, index):
        "Records x and y for the sash given by index;\n\n        Used in conjunction with later dragto commands to move the sash.\n        "
        return self.sash("mark", index)

    def sash_place(self, index, x, y):
        "Place the sash given by index at the given coordinates\n        "
        return self.sash("place", index, x, y)

    def panecget(self, child, option):
        "Query a management option for window.\n\n        Option may be any value allowed by the paneconfigure subcommand\n        "
        return self.tk.call(((self._w, "panecget") + (child, ("-" + option))))

    def paneconfigure(self, tagOrId, cnf=None, **kw):
        'Query or modify the management options for window.\n\n        If no option is specified, returns a list describing all\n        of the available options for pathName.  If option is\n        specified with no value, then the command returns a list\n        describing the one named option (this list will be identical\n        to the corresponding sublist of the value returned if no\n        option is specified). If one or more option-value pairs are\n        specified, then the command modifies the given widget\n        option(s) to have the given value(s); in this case the\n        command returns an empty string. The following options\n        are supported:\n\n        after window\n            Insert the window after the window specified. window\n            should be the name of a window already managed by pathName.\n        before window\n            Insert the window before the window specified. window\n            should be the name of a window already managed by pathName.\n        height size\n            Specify a height for the window. The height will be the\n            outer dimension of the window including its border, if\n            any. If size is an empty string, or if -height is not\n            specified, then the height requested internally by the\n            window will be used initially; the height may later be\n            adjusted by the movement of sashes in the panedwindow.\n            Size may be any value accepted by Tk_GetPixels.\n        minsize n\n            Specifies that the size of the window cannot be made\n            less than n. This constraint only affects the size of\n            the widget in the paned dimension -- the x dimension\n            for horizontal panedwindows, the y dimension for\n            vertical panedwindows. May be any value accepted by\n            Tk_GetPixels.\n        padx n\n            Specifies a non-negative value indicating how much\n            extra space to leave on each side of the window in\n            the X-direction. The value may have any of the forms\n            accepted by Tk_GetPixels.\n        pady n\n            Specifies a non-negative value indicating how much\n            extra space to leave on each side of the window in\n            the Y-direction. The value may have any of the forms\n            accepted by Tk_GetPixels.\n        sticky style\n            If a window\'s pane is larger than the requested\n            dimensions of the window, this option may be used\n            to position (or stretch) the window within its pane.\n            Style is a string that contains zero or more of the\n            characters n, s, e or w. The string can optionally\n            contains spaces or commas, but they are ignored. Each\n            letter refers to a side (north, south, east, or west)\n            that the window will "stick" to. If both n and s\n            (or e and w) are specified, the window will be\n            stretched to fill the entire height (or width) of\n            its cavity.\n        width size\n            Specify a width for the window. The width will be\n            the outer dimension of the window including its\n            border, if any. If size is an empty string, or\n            if -width is not specified, then the width requested\n            internally by the window will be used initially; the\n            width may later be adjusted by the movement of sashes\n            in the panedwindow. Size may be any value accepted by\n            Tk_GetPixels.\n\n        '
        if (cnf is None) and (not kw):
            return self._getconfigure(self._w, "paneconfigure", tagOrId)
        if isinstance(cnf, str) and (not kw):
            return self._getconfigure1(self._w, "paneconfigure", tagOrId, ("-" + cnf))
        self.tk.call(((self._w, "paneconfigure", tagOrId) + self._options(cnf, kw)))

    paneconfig = paneconfigure

    def panes(self):
        "Returns an ordered list of the child panes."
        return self.tk.splitlist(self.tk.call(self._w, "panes"))


def _test():
    root = Tk()
    text = "This is Tcl/Tk version %s" % TclVersion
    text += "\nThis should be a cedilla: ç"
    label = Label(root, text=text)
    label.pack()
    test = Button(
        root,
        text="Click me!",
        command=(
            lambda root=root: root.test.configure(text=("[%s]" % root.test["text"]))
        ),
    )
    test.pack()
    root.test = test
    quit = Button(root, text="QUIT", command=root.destroy)
    quit.pack()
    root.iconify()
    root.update()
    root.deiconify()
    root.mainloop()


__all__ = [
    name
    for (name, obj) in globals().items()
    if (
        (not name.startswith("_"))
        and (not isinstance(obj, types.ModuleType))
        and (name not in {"wantobjects"})
    )
]
if __name__ == "__main__":
    _test()
