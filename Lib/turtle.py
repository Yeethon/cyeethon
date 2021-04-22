"\nTurtle graphics is a popular way for introducing programming to\nkids. It was part of the original Logo programming language developed\nby Wally Feurzig and Seymour Papert in 1966.\n\nImagine a robotic turtle starting at (0, 0) in the x-y plane. After an ``import turtle``, give it\nthe command turtle.forward(15), and it moves (on-screen!) 15 pixels in\nthe direction it is facing, drawing a line as it moves. Give it the\ncommand turtle.right(25), and it rotates in-place 25 degrees clockwise.\n\nBy combining together these and similar commands, intricate shapes and\npictures can easily be drawn.\n\n----- turtle.py\n\nThis module is an extended reimplementation of turtle.py from the\nPython standard distribution up to Python 2.5. (See: http://www.python.org)\n\nIt tries to keep the merits of turtle.py and to be (nearly) 100%\ncompatible with it. This means in the first place to enable the\nlearning programmer to use all the commands, classes and methods\ninteractively when using the module from within IDLE run with\nthe -n switch.\n\nRoughly it has the following features added:\n\n- Better animation of the turtle movements, especially of turning the\n  turtle. So the turtles can more easily be used as a visual feedback\n  instrument by the (beginning) programmer.\n\n- Different turtle shapes, gif-images as turtle shapes, user defined\n  and user controllable turtle shapes, among them compound\n  (multicolored) shapes. Turtle shapes can be stretched and tilted, which\n  makes turtles very versatile geometrical objects.\n\n- Fine control over turtle movement and screen updates via delay(),\n  and enhanced tracer() and speed() methods.\n\n- Aliases for the most commonly used commands, like fd for forward etc.,\n  following the early Logo traditions. This reduces the boring work of\n  typing long sequences of commands, which often occur in a natural way\n  when kids try to program fancy pictures on their first encounter with\n  turtle graphics.\n\n- Turtles now have an undo()-method with configurable undo-buffer.\n\n- Some simple commands/methods for creating event driven programs\n  (mouse-, key-, timer-events). Especially useful for programming games.\n\n- A scrollable Canvas class. The default scrollable Canvas can be\n  extended interactively as needed while playing around with the turtle(s).\n\n- A TurtleScreen class with methods controlling background color or\n  background image, window and canvas size and other properties of the\n  TurtleScreen.\n\n- There is a method, setworldcoordinates(), to install a user defined\n  coordinate-system for the TurtleScreen.\n\n- The implementation uses a 2-vector class named Vec2D, derived from tuple.\n  This class is public, so it can be imported by the application programmer,\n  which makes certain types of computations very natural and compact.\n\n- Appearance of the TurtleScreen and the Turtles at startup/import can be\n  configured by means of a turtle.cfg configuration file.\n  The default configuration mimics the appearance of the old turtle module.\n\n- If configured appropriately the module reads in docstrings from a docstring\n  dictionary in some different language, supplied separately  and replaces\n  the English ones by those read in. There is a utility function\n  write_docstringdict() to write a dictionary with the original (English)\n  docstrings to disc, so it can serve as a template for translations.\n\nBehind the scenes there are some features included with possible\nextensions in mind. These will be commented and documented elsewhere.\n\n"
_ver = "turtle 1.1b- - for Python 3.1   -  4. 5. 2009"
import tkinter as TK
import types
import math
import time
import inspect
import sys
from os.path import isfile, split, join
from copy import deepcopy
from tkinter import simpledialog

_tg_classes = [
    "ScrolledCanvas",
    "TurtleScreen",
    "Screen",
    "RawTurtle",
    "Turtle",
    "RawPen",
    "Pen",
    "Shape",
    "Vec2D",
]
_tg_screen_functions = [
    "addshape",
    "bgcolor",
    "bgpic",
    "bye",
    "clearscreen",
    "colormode",
    "delay",
    "exitonclick",
    "getcanvas",
    "getshapes",
    "listen",
    "mainloop",
    "mode",
    "numinput",
    "onkey",
    "onkeypress",
    "onkeyrelease",
    "onscreenclick",
    "ontimer",
    "register_shape",
    "resetscreen",
    "screensize",
    "setup",
    "setworldcoordinates",
    "textinput",
    "title",
    "tracer",
    "turtles",
    "update",
    "window_height",
    "window_width",
]
_tg_turtle_functions = [
    "back",
    "backward",
    "begin_fill",
    "begin_poly",
    "bk",
    "circle",
    "clear",
    "clearstamp",
    "clearstamps",
    "clone",
    "color",
    "degrees",
    "distance",
    "dot",
    "down",
    "end_fill",
    "end_poly",
    "fd",
    "fillcolor",
    "filling",
    "forward",
    "get_poly",
    "getpen",
    "getscreen",
    "get_shapepoly",
    "getturtle",
    "goto",
    "heading",
    "hideturtle",
    "home",
    "ht",
    "isdown",
    "isvisible",
    "left",
    "lt",
    "onclick",
    "ondrag",
    "onrelease",
    "pd",
    "pen",
    "pencolor",
    "pendown",
    "pensize",
    "penup",
    "pos",
    "position",
    "pu",
    "radians",
    "right",
    "reset",
    "resizemode",
    "rt",
    "seth",
    "setheading",
    "setpos",
    "setposition",
    "settiltangle",
    "setundobuffer",
    "setx",
    "sety",
    "shape",
    "shapesize",
    "shapetransform",
    "shearfactor",
    "showturtle",
    "speed",
    "st",
    "stamp",
    "tilt",
    "tiltangle",
    "towards",
    "turtlesize",
    "undo",
    "undobufferentries",
    "up",
    "width",
    "write",
    "xcor",
    "ycor",
]
_tg_utilities = ["write_docstringdict", "done"]
__all__ = (
    ((_tg_classes + _tg_screen_functions) + _tg_turtle_functions) + _tg_utilities
) + ["Terminator"]
_alias_list = [
    "addshape",
    "backward",
    "bk",
    "fd",
    "ht",
    "lt",
    "pd",
    "pos",
    "pu",
    "rt",
    "seth",
    "setpos",
    "setposition",
    "st",
    "turtlesize",
    "up",
    "width",
]
_CFG = {
    "width": 0.5,
    "height": 0.75,
    "canvwidth": 400,
    "canvheight": 300,
    "leftright": None,
    "topbottom": None,
    "mode": "standard",
    "colormode": 1.0,
    "delay": 10,
    "undobuffersize": 1000,
    "shape": "classic",
    "pencolor": "black",
    "fillcolor": "black",
    "resizemode": "noresize",
    "visible": True,
    "language": "english",
    "exampleturtle": "turtle",
    "examplescreen": "screen",
    "title": "Python Turtle Graphics",
    "using_IDLE": False,
}


def config_dict(filename):
    "Convert content of config-file into dictionary."
    with open(filename, "r") as f:
        cfglines = f.readlines()
    cfgdict = {}
    for line in cfglines:
        line = line.strip()
        if (not line) or line.startswith("#"):
            continue
        try:
            (key, value) = line.split("=")
        except ValueError:
            print(("Bad line in config-file %s:\n%s" % (filename, line)))
            continue
        key = key.strip()
        value = value.strip()
        if value in ["True", "False", "None", "''", '""']:
            value = eval(value)
        else:
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass
        cfgdict[key] = value
    return cfgdict


def readconfig(cfgdict):
    "Read config-files, change configuration-dict accordingly.\n\n    If there is a turtle.cfg file in the current working directory,\n    read it from there. If this contains an importconfig-value,\n    say 'myway', construct filename turtle_mayway.cfg else use\n    turtle.cfg and read it from the import-directory, where\n    turtle.py is located.\n    Update configuration dictionary first according to config-file,\n    in the import directory, then according to config-file in the\n    current working directory.\n    If no config-file is found, the default configuration is used.\n    "
    default_cfg = "turtle.cfg"
    cfgdict1 = {}
    cfgdict2 = {}
    if isfile(default_cfg):
        cfgdict1 = config_dict(default_cfg)
    if "importconfig" in cfgdict1:
        default_cfg = "turtle_%s.cfg" % cfgdict1["importconfig"]
    try:
        (head, tail) = split(__file__)
        cfg_file2 = join(head, default_cfg)
    except Exception:
        cfg_file2 = ""
    if isfile(cfg_file2):
        cfgdict2 = config_dict(cfg_file2)
    _CFG.update(cfgdict2)
    _CFG.update(cfgdict1)


try:
    readconfig(_CFG)
except Exception:
    print("No configfile read, reason unknown")


class Vec2D(tuple):
    "A 2 dimensional vector class, used as a helper class\n    for implementing turtle graphics.\n    May be useful for turtle graphics programs also.\n    Derived from tuple, so a vector is a tuple!\n\n    Provides (for a, b vectors, k number):\n       a+b vector addition\n       a-b vector subtraction\n       a*b inner product\n       k*a and a*k multiplication with scalar\n       |a| absolute value of a\n       a.rotate(angle) rotation\n    "

    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    def __add__(self, other):
        return Vec2D((self[0] + other[0]), (self[1] + other[1]))

    def __mul__(self, other):
        if isinstance(other, Vec2D):
            return (self[0] * other[0]) + (self[1] * other[1])
        return Vec2D((self[0] * other), (self[1] * other))

    def __rmul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return Vec2D((self[0] * other), (self[1] * other))
        return NotImplemented

    def __sub__(self, other):
        return Vec2D((self[0] - other[0]), (self[1] - other[1]))

    def __neg__(self):
        return Vec2D((-self[0]), (-self[1]))

    def __abs__(self):
        return math.hypot(*self)

    def rotate(self, angle):
        "rotate self counterclockwise by angle\n        "
        perp = Vec2D((-self[1]), self[0])
        angle = math.radians(angle)
        (c, s) = (math.cos(angle), math.sin(angle))
        return Vec2D(((self[0] * c) + (perp[0] * s)), ((self[1] * c) + (perp[1] * s)))

    def __getnewargs__(self):
        return (self[0], self[1])

    def __repr__(self):
        return "(%.2f,%.2f)" % self


def __methodDict(cls, _dict):
    "helper function for Scrolled Canvas"
    baseList = list(cls.__bases__)
    baseList.reverse()
    for _super in baseList:
        __methodDict(_super, _dict)
    for (key, value) in cls.__dict__.items():
        if type(value) == types.FunctionType:
            _dict[key] = value


def __methods(cls):
    "helper function for Scrolled Canvas"
    _dict = {}
    __methodDict(cls, _dict)
    return _dict.keys()


__stringBody = (
    "def %(method)s(self, *args, **kw): return "
    + "self.%(attribute)s.%(method)s(*args, **kw)"
)


def __forwardmethods(fromClass, toClass, toPart, exclude=()):
    _dict_1 = {}
    __methodDict(toClass, _dict_1)
    _dict = {}
    mfc = __methods(fromClass)
    for ex in _dict_1.keys():
        if (ex[:1] == "_") or (ex[(-1):] == "_") or (ex in exclude) or (ex in mfc):
            pass
        else:
            _dict[ex] = _dict_1[ex]
    for (method, func) in _dict.items():
        d = {"method": method, "func": func}
        if isinstance(toPart, str):
            execString = __stringBody % {"method": method, "attribute": toPart}
        exec(execString, d)
        setattr(fromClass, method, d[method])


class ScrolledCanvas(TK.Frame):
    "Modeled after the scrolled canvas class from Grayons's Tkinter book.\n\n    Used as the default canvas, which pops up automatically when\n    using turtle graphics functions or the Turtle class.\n    "

    def __init__(self, master, width=500, height=350, canvwidth=600, canvheight=500):
        TK.Frame.__init__(self, master, width=width, height=height)
        self._rootwindow = self.winfo_toplevel()
        (self.width, self.height) = (width, height)
        (self.canvwidth, self.canvheight) = (canvwidth, canvheight)
        self.bg = "white"
        self._canvas = TK.Canvas(
            master,
            width=width,
            height=height,
            bg=self.bg,
            relief=TK.SUNKEN,
            borderwidth=2,
        )
        self.hscroll = TK.Scrollbar(
            master, command=self._canvas.xview, orient=TK.HORIZONTAL
        )
        self.vscroll = TK.Scrollbar(master, command=self._canvas.yview)
        self._canvas.configure(
            xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set
        )
        self.rowconfigure(0, weight=1, minsize=0)
        self.columnconfigure(0, weight=1, minsize=0)
        self._canvas.grid(
            padx=1,
            in_=self,
            pady=1,
            row=0,
            column=0,
            rowspan=1,
            columnspan=1,
            sticky="news",
        )
        self.vscroll.grid(
            padx=1,
            in_=self,
            pady=1,
            row=0,
            column=1,
            rowspan=1,
            columnspan=1,
            sticky="news",
        )
        self.hscroll.grid(
            padx=1,
            in_=self,
            pady=1,
            row=1,
            column=0,
            rowspan=1,
            columnspan=1,
            sticky="news",
        )
        self.reset()
        self._rootwindow.bind("<Configure>", self.onResize)

    def reset(self, canvwidth=None, canvheight=None, bg=None):
        "Adjust canvas and scrollbars according to given canvas size."
        if canvwidth:
            self.canvwidth = canvwidth
        if canvheight:
            self.canvheight = canvheight
        if bg:
            self.bg = bg
        self._canvas.config(
            bg=bg,
            scrollregion=(
                ((-self.canvwidth) // 2),
                ((-self.canvheight) // 2),
                (self.canvwidth // 2),
                (self.canvheight // 2),
            ),
        )
        self._canvas.xview_moveto(
            ((0.5 * ((self.canvwidth - self.width) + 30)) / self.canvwidth)
        )
        self._canvas.yview_moveto(
            ((0.5 * ((self.canvheight - self.height) + 30)) / self.canvheight)
        )
        self.adjustScrolls()

    def adjustScrolls(self):
        " Adjust scrollbars according to window- and canvas-size.\n        "
        cwidth = self._canvas.winfo_width()
        cheight = self._canvas.winfo_height()
        self._canvas.xview_moveto(((0.5 * (self.canvwidth - cwidth)) / self.canvwidth))
        self._canvas.yview_moveto(
            ((0.5 * (self.canvheight - cheight)) / self.canvheight)
        )
        if (cwidth < self.canvwidth) or (cheight < self.canvheight):
            self.hscroll.grid(
                padx=1,
                in_=self,
                pady=1,
                row=1,
                column=0,
                rowspan=1,
                columnspan=1,
                sticky="news",
            )
            self.vscroll.grid(
                padx=1,
                in_=self,
                pady=1,
                row=0,
                column=1,
                rowspan=1,
                columnspan=1,
                sticky="news",
            )
        else:
            self.hscroll.grid_forget()
            self.vscroll.grid_forget()

    def onResize(self, event):
        "self-explanatory"
        self.adjustScrolls()

    def bbox(self, *args):
        " 'forward' method, which canvas itself has inherited...\n        "
        return self._canvas.bbox(*args)

    def cget(self, *args, **kwargs):
        " 'forward' method, which canvas itself has inherited...\n        "
        return self._canvas.cget(*args, **kwargs)

    def config(self, *args, **kwargs):
        " 'forward' method, which canvas itself has inherited...\n        "
        self._canvas.config(*args, **kwargs)

    def bind(self, *args, **kwargs):
        " 'forward' method, which canvas itself has inherited...\n        "
        self._canvas.bind(*args, **kwargs)

    def unbind(self, *args, **kwargs):
        " 'forward' method, which canvas itself has inherited...\n        "
        self._canvas.unbind(*args, **kwargs)

    def focus_force(self):
        " 'forward' method, which canvas itself has inherited...\n        "
        self._canvas.focus_force()


__forwardmethods(ScrolledCanvas, TK.Canvas, "_canvas")


class _Root(TK.Tk):
    "Root class for Screen based on Tkinter."

    def __init__(self):
        TK.Tk.__init__(self)

    def setupcanvas(self, width, height, cwidth, cheight):
        self._canvas = ScrolledCanvas(self, width, height, cwidth, cheight)
        self._canvas.pack(expand=1, fill="both")

    def _getcanvas(self):
        return self._canvas

    def set_geometry(self, width, height, startx, starty):
        self.geometry(("%dx%d%+d%+d" % (width, height, startx, starty)))

    def ondestroy(self, destroy):
        self.wm_protocol("WM_DELETE_WINDOW", destroy)

    def win_width(self):
        return self.winfo_screenwidth()

    def win_height(self):
        return self.winfo_screenheight()


Canvas = TK.Canvas


class TurtleScreenBase(object):
    "Provide the basic graphics functionality.\n       Interface between Tkinter and turtle.py.\n\n       To port turtle.py to some different graphics toolkit\n       a corresponding TurtleScreenBase class has to be implemented.\n    "

    @staticmethod
    def _blankimage():
        "return a blank image object\n        "
        img = TK.PhotoImage(width=1, height=1)
        img.blank()
        return img

    @staticmethod
    def _image(filename):
        "return an image object containing the\n        imagedata from a gif-file named filename.\n        "
        return TK.PhotoImage(file=filename)

    def __init__(self, cv):
        self.cv = cv
        if isinstance(cv, ScrolledCanvas):
            w = self.cv.canvwidth
            h = self.cv.canvheight
        else:
            w = int(self.cv.cget("width"))
            h = int(self.cv.cget("height"))
            self.cv.config(scrollregion=(((-w) // 2), ((-h) // 2), (w // 2), (h // 2)))
        self.canvwidth = w
        self.canvheight = h
        self.xscale = self.yscale = 1.0

    def _createpoly(self):
        "Create an invisible polygon item on canvas self.cv)\n        "
        return self.cv.create_polygon((0, 0, 0, 0, 0, 0), fill="", outline="")

    def _drawpoly(
        self, polyitem, coordlist, fill=None, outline=None, width=None, top=False
    ):
        "Configure polygonitem polyitem according to provided\n        arguments:\n        coordlist is sequence of coordinates\n        fill is filling color\n        outline is outline color\n        top is a boolean value, which specifies if polyitem\n        will be put on top of the canvas' displaylist so it\n        will not be covered by other items.\n        "
        cl = []
        for (x, y) in coordlist:
            cl.append((x * self.xscale))
            cl.append(((-y) * self.yscale))
        self.cv.coords(polyitem, *cl)
        if fill is not None:
            self.cv.itemconfigure(polyitem, fill=fill)
        if outline is not None:
            self.cv.itemconfigure(polyitem, outline=outline)
        if width is not None:
            self.cv.itemconfigure(polyitem, width=width)
        if top:
            self.cv.tag_raise(polyitem)

    def _createline(self):
        "Create an invisible line item on canvas self.cv)\n        "
        return self.cv.create_line(0, 0, 0, 0, fill="", width=2, capstyle=TK.ROUND)

    def _drawline(self, lineitem, coordlist=None, fill=None, width=None, top=False):
        "Configure lineitem according to provided arguments:\n        coordlist is sequence of coordinates\n        fill is drawing color\n        width is width of drawn line.\n        top is a boolean value, which specifies if polyitem\n        will be put on top of the canvas' displaylist so it\n        will not be covered by other items.\n        "
        if coordlist is not None:
            cl = []
            for (x, y) in coordlist:
                cl.append((x * self.xscale))
                cl.append(((-y) * self.yscale))
            self.cv.coords(lineitem, *cl)
        if fill is not None:
            self.cv.itemconfigure(lineitem, fill=fill)
        if width is not None:
            self.cv.itemconfigure(lineitem, width=width)
        if top:
            self.cv.tag_raise(lineitem)

    def _delete(self, item):
        'Delete graphics item from canvas.\n        If item is"all" delete all graphics items.\n        '
        self.cv.delete(item)

    def _update(self):
        "Redraw graphics items on canvas\n        "
        self.cv.update()

    def _delay(self, delay):
        "Delay subsequent canvas actions for delay ms."
        self.cv.after(delay)

    def _iscolorstring(self, color):
        "Check if the string color is a legal Tkinter color string.\n        "
        try:
            rgb = self.cv.winfo_rgb(color)
            ok = True
        except TK.TclError:
            ok = False
        return ok

    def _bgcolor(self, color=None):
        "Set canvas' backgroundcolor if color is not None,\n        else return backgroundcolor."
        if color is not None:
            self.cv.config(bg=color)
            self._update()
        else:
            return self.cv.cget("bg")

    def _write(self, pos, txt, align, font, pencolor):
        "Write txt at pos in canvas with specified font\n        and color.\n        Return text item and x-coord of right bottom corner\n        of text's bounding box."
        (x, y) = pos
        x = x * self.xscale
        y = y * self.yscale
        anchor = {"left": "sw", "center": "s", "right": "se"}
        item = self.cv.create_text(
            (x - 1), (-y), text=txt, anchor=anchor[align], fill=pencolor, font=font
        )
        (x0, y0, x1, y1) = self.cv.bbox(item)
        self.cv.update()
        return (item, (x1 - 1))

    def _onclick(self, item, fun, num=1, add=None):
        "Bind fun to mouse-click event on turtle.\n        fun must be a function with two arguments, the coordinates\n        of the clicked point on the canvas.\n        num, the number of the mouse-button defaults to 1\n        "
        if fun is None:
            self.cv.tag_unbind(item, ("<Button-%s>" % num))
        else:

            def eventfun(event):
                (x, y) = (
                    (self.cv.canvasx(event.x) / self.xscale),
                    ((-self.cv.canvasy(event.y)) / self.yscale),
                )
                fun(x, y)

            self.cv.tag_bind(item, ("<Button-%s>" % num), eventfun, add)

    def _onrelease(self, item, fun, num=1, add=None):
        "Bind fun to mouse-button-release event on turtle.\n        fun must be a function with two arguments, the coordinates\n        of the point on the canvas where mouse button is released.\n        num, the number of the mouse-button defaults to 1\n\n        If a turtle is clicked, first _onclick-event will be performed,\n        then _onscreensclick-event.\n        "
        if fun is None:
            self.cv.tag_unbind(item, ("<Button%s-ButtonRelease>" % num))
        else:

            def eventfun(event):
                (x, y) = (
                    (self.cv.canvasx(event.x) / self.xscale),
                    ((-self.cv.canvasy(event.y)) / self.yscale),
                )
                fun(x, y)

            self.cv.tag_bind(item, ("<Button%s-ButtonRelease>" % num), eventfun, add)

    def _ondrag(self, item, fun, num=1, add=None):
        "Bind fun to mouse-move-event (with pressed mouse button) on turtle.\n        fun must be a function with two arguments, the coordinates of the\n        actual mouse position on the canvas.\n        num, the number of the mouse-button defaults to 1\n\n        Every sequence of mouse-move-events on a turtle is preceded by a\n        mouse-click event on that turtle.\n        "
        if fun is None:
            self.cv.tag_unbind(item, ("<Button%s-Motion>" % num))
        else:

            def eventfun(event):
                try:
                    (x, y) = (
                        (self.cv.canvasx(event.x) / self.xscale),
                        ((-self.cv.canvasy(event.y)) / self.yscale),
                    )
                    fun(x, y)
                except Exception:
                    pass

            self.cv.tag_bind(item, ("<Button%s-Motion>" % num), eventfun, add)

    def _onscreenclick(self, fun, num=1, add=None):
        "Bind fun to mouse-click event on canvas.\n        fun must be a function with two arguments, the coordinates\n        of the clicked point on the canvas.\n        num, the number of the mouse-button defaults to 1\n\n        If a turtle is clicked, first _onclick-event will be performed,\n        then _onscreensclick-event.\n        "
        if fun is None:
            self.cv.unbind(("<Button-%s>" % num))
        else:

            def eventfun(event):
                (x, y) = (
                    (self.cv.canvasx(event.x) / self.xscale),
                    ((-self.cv.canvasy(event.y)) / self.yscale),
                )
                fun(x, y)

            self.cv.bind(("<Button-%s>" % num), eventfun, add)

    def _onkeyrelease(self, fun, key):
        "Bind fun to key-release event of key.\n        Canvas must have focus. See method listen\n        "
        if fun is None:
            self.cv.unbind(("<KeyRelease-%s>" % key), None)
        else:

            def eventfun(event):
                fun()

            self.cv.bind(("<KeyRelease-%s>" % key), eventfun)

    def _onkeypress(self, fun, key=None):
        "If key is given, bind fun to key-press event of key.\n        Otherwise bind fun to any key-press.\n        Canvas must have focus. See method listen.\n        "
        if fun is None:
            if key is None:
                self.cv.unbind("<KeyPress>", None)
            else:
                self.cv.unbind(("<KeyPress-%s>" % key), None)
        else:

            def eventfun(event):
                fun()

            if key is None:
                self.cv.bind("<KeyPress>", eventfun)
            else:
                self.cv.bind(("<KeyPress-%s>" % key), eventfun)

    def _listen(self):
        "Set focus on canvas (in order to collect key-events)\n        "
        self.cv.focus_force()

    def _ontimer(self, fun, t):
        "Install a timer, which calls fun after t milliseconds.\n        "
        if t == 0:
            self.cv.after_idle(fun)
        else:
            self.cv.after(t, fun)

    def _createimage(self, image):
        "Create and return image item on canvas.\n        "
        return self.cv.create_image(0, 0, image=image)

    def _drawimage(self, item, pos, image):
        "Configure image item as to draw image object\n        at position (x,y) on canvas)\n        "
        (x, y) = pos
        self.cv.coords(item, ((x * self.xscale), ((-y) * self.yscale)))
        self.cv.itemconfig(item, image=image)

    def _setbgpic(self, item, image):
        "Configure image item as to draw image object\n        at center of canvas. Set item to the first item\n        in the displaylist, so it will be drawn below\n        any other item ."
        self.cv.itemconfig(item, image=image)
        self.cv.tag_lower(item)

    def _type(self, item):
        "Return 'line' or 'polygon' or 'image' depending on\n        type of item.\n        "
        return self.cv.type(item)

    def _pointlist(self, item):
        "returns list of coordinate-pairs of points of item\n        Example (for insiders):\n        >>> from turtle import *\n        >>> getscreen()._pointlist(getturtle().turtle._item)\n        [(0.0, 9.9999999999999982), (0.0, -9.9999999999999982),\n        (9.9999999999999982, 0.0)]\n        >>> "
        cl = self.cv.coords(item)
        pl = [(cl[i], (-cl[(i + 1)])) for i in range(0, len(cl), 2)]
        return pl

    def _setscrollregion(self, srx1, sry1, srx2, sry2):
        self.cv.config(scrollregion=(srx1, sry1, srx2, sry2))

    def _rescale(self, xscalefactor, yscalefactor):
        items = self.cv.find_all()
        for item in items:
            coordinates = list(self.cv.coords(item))
            newcoordlist = []
            while coordinates:
                (x, y) = coordinates[:2]
                newcoordlist.append((x * xscalefactor))
                newcoordlist.append((y * yscalefactor))
                coordinates = coordinates[2:]
            self.cv.coords(item, *newcoordlist)

    def _resize(self, canvwidth=None, canvheight=None, bg=None):
        "Resize the canvas the turtles are drawing on. Does\n        not alter the drawing window.\n        "
        if not isinstance(self.cv, ScrolledCanvas):
            return (self.canvwidth, self.canvheight)
        if canvwidth is canvheight is bg is None:
            return (self.cv.canvwidth, self.cv.canvheight)
        if canvwidth is not None:
            self.canvwidth = canvwidth
        if canvheight is not None:
            self.canvheight = canvheight
        self.cv.reset(canvwidth, canvheight, bg)

    def _window_size(self):
        " Return the width and height of the turtle window.\n        "
        width = self.cv.winfo_width()
        if width <= 1:
            width = self.cv["width"]
        height = self.cv.winfo_height()
        if height <= 1:
            height = self.cv["height"]
        return (width, height)

    def mainloop(self):
        "Starts event loop - calling Tkinter's mainloop function.\n\n        No argument.\n\n        Must be last statement in a turtle graphics program.\n        Must NOT be used if a script is run from within IDLE in -n mode\n        (No subprocess) - for interactive use of turtle graphics.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.mainloop()\n\n        "
        TK.mainloop()

    def textinput(self, title, prompt):
        'Pop up a dialog window for input of a string.\n\n        Arguments: title is the title of the dialog window,\n        prompt is a text mostly describing what information to input.\n\n        Return the string input\n        If the dialog is canceled, return None.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.textinput("NIM", "Name of first player:")\n\n        '
        return simpledialog.askstring(title, prompt)

    def numinput(self, title, prompt, default=None, minval=None, maxval=None):
        'Pop up a dialog window for input of a number.\n\n        Arguments: title is the title of the dialog window,\n        prompt is a text mostly describing what numerical information to input.\n        default: default value\n        minval: minimum value for input\n        maxval: maximum value for input\n\n        The number input must be in the range minval .. maxval if these are\n        given. If not, a hint is issued and the dialog remains open for\n        correction. Return the number input.\n        If the dialog is canceled,  return None.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.numinput("Poker", "Your stakes:", 1000, minval=10, maxval=10000)\n\n        '
        return simpledialog.askfloat(
            title, prompt, initialvalue=default, minvalue=minval, maxvalue=maxval
        )


class Terminator(Exception):
    "Will be raised in TurtleScreen.update, if _RUNNING becomes False.\n\n    This stops execution of a turtle graphics script.\n    Main purpose: use in the Demo-Viewer turtle.Demo.py.\n    "
    pass


class TurtleGraphicsError(Exception):
    "Some TurtleGraphics Error\n    "


class Shape(object):
    'Data structure modeling shapes.\n\n    attribute _type is one of "polygon", "image", "compound"\n    attribute _data is - depending on _type a poygon-tuple,\n    an image or a list constructed using the addcomponent method.\n    '

    def __init__(self, type_, data=None):
        self._type = type_
        if type_ == "polygon":
            if isinstance(data, list):
                data = tuple(data)
        elif type_ == "image":
            if isinstance(data, str):
                if data.lower().endswith(".gif") and isfile(data):
                    data = TurtleScreen._image(data)
        elif type_ == "compound":
            data = []
        else:
            raise TurtleGraphicsError(("There is no shape type %s" % type_))
        self._data = data

    def addcomponent(self, poly, fill, outline=None):
        'Add component to a shape of type compound.\n\n        Arguments: poly is a polygon, i. e. a tuple of number pairs.\n        fill is the fillcolor of the component,\n        outline is the outline color of the component.\n\n        call (for a Shapeobject namend s):\n        --   s.addcomponent(((0,0), (10,10), (-10,10)), "red", "blue")\n\n        Example:\n        >>> poly = ((0,0),(10,-5),(0,10),(-10,-5))\n        >>> s = Shape("compound")\n        >>> s.addcomponent(poly, "red", "blue")\n        >>> # .. add more components and then use register_shape()\n        '
        if self._type != "compound":
            raise TurtleGraphicsError(("Cannot add component to %s Shape" % self._type))
        if outline is None:
            outline = fill
        self._data.append([poly, fill, outline])


class Tbuffer(object):
    "Ring buffer used as undobuffer for RawTurtle objects."

    def __init__(self, bufsize=10):
        self.bufsize = bufsize
        self.buffer = [[None]] * bufsize
        self.ptr = -1
        self.cumulate = False

    def reset(self, bufsize=None):
        if bufsize is None:
            for i in range(self.bufsize):
                self.buffer[i] = [None]
        else:
            self.bufsize = bufsize
            self.buffer = [[None]] * bufsize
        self.ptr = -1

    def push(self, item):
        if self.bufsize > 0:
            if not self.cumulate:
                self.ptr = (self.ptr + 1) % self.bufsize
                self.buffer[self.ptr] = item
            else:
                self.buffer[self.ptr].append(item)

    def pop(self):
        if self.bufsize > 0:
            item = self.buffer[self.ptr]
            if item is None:
                return None
            else:
                self.buffer[self.ptr] = [None]
                self.ptr = (self.ptr - 1) % self.bufsize
                return item

    def nr_of_items(self):
        return self.bufsize - self.buffer.count([None])

    def __repr__(self):
        return (str(self.buffer) + " ") + str(self.ptr)


class TurtleScreen(TurtleScreenBase):
    "Provides screen oriented methods like setbg etc.\n\n    Only relies upon the methods of TurtleScreenBase and NOT\n    upon components of the underlying graphics toolkit -\n    which is Tkinter in this case.\n    "
    _RUNNING = True

    def __init__(
        self, cv, mode=_CFG["mode"], colormode=_CFG["colormode"], delay=_CFG["delay"]
    ):
        self._shapes = {
            "arrow": Shape("polygon", (((-10), 0), (10, 0), (0, 10))),
            "turtle": Shape(
                "polygon",
                (
                    (0, 16),
                    ((-2), 14),
                    ((-1), 10),
                    ((-4), 7),
                    ((-7), 9),
                    ((-9), 8),
                    ((-6), 5),
                    ((-7), 1),
                    ((-5), (-3)),
                    ((-8), (-6)),
                    ((-6), (-8)),
                    ((-4), (-5)),
                    (0, (-7)),
                    (4, (-5)),
                    (6, (-8)),
                    (8, (-6)),
                    (5, (-3)),
                    (7, 1),
                    (6, 5),
                    (9, 8),
                    (7, 9),
                    (4, 7),
                    (1, 10),
                    (2, 14),
                ),
            ),
            "circle": Shape(
                "polygon",
                (
                    (10, 0),
                    (9.51, 3.09),
                    (8.09, 5.88),
                    (5.88, 8.09),
                    (3.09, 9.51),
                    (0, 10),
                    ((-3.09), 9.51),
                    ((-5.88), 8.09),
                    ((-8.09), 5.88),
                    ((-9.51), 3.09),
                    ((-10), 0),
                    ((-9.51), (-3.09)),
                    ((-8.09), (-5.88)),
                    ((-5.88), (-8.09)),
                    ((-3.09), (-9.51)),
                    ((-0.0), (-10.0)),
                    (3.09, (-9.51)),
                    (5.88, (-8.09)),
                    (8.09, (-5.88)),
                    (9.51, (-3.09)),
                ),
            ),
            "square": Shape(
                "polygon", ((10, (-10)), (10, 10), ((-10), 10), ((-10), (-10)))
            ),
            "triangle": Shape("polygon", ((10, (-5.77)), (0, 11.55), ((-10), (-5.77)))),
            "classic": Shape("polygon", ((0, 0), ((-5), (-9)), (0, (-7)), (5, (-9)))),
            "blank": Shape("image", self._blankimage()),
        }
        self._bgpics = {"nopic": ""}
        TurtleScreenBase.__init__(self, cv)
        self._mode = mode
        self._delayvalue = delay
        self._colormode = _CFG["colormode"]
        self._keys = []
        self.clear()
        if sys.platform == "darwin":
            rootwindow = cv.winfo_toplevel()
            rootwindow.call("wm", "attributes", ".", "-topmost", "1")
            rootwindow.call("wm", "attributes", ".", "-topmost", "0")

    def clear(self):
        "Delete all drawings and all turtles from the TurtleScreen.\n\n        No argument.\n\n        Reset empty TurtleScreen to its initial state: white background,\n        no backgroundimage, no eventbindings and tracing on.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.clear()\n\n        Note: this method is not available as function.\n        "
        self._delayvalue = _CFG["delay"]
        self._colormode = _CFG["colormode"]
        self._delete("all")
        self._bgpic = self._createimage("")
        self._bgpicname = "nopic"
        self._tracing = 1
        self._updatecounter = 0
        self._turtles = []
        self.bgcolor("white")
        for btn in (1, 2, 3):
            self.onclick(None, btn)
        self.onkeypress(None)
        for key in self._keys[:]:
            self.onkey(None, key)
            self.onkeypress(None, key)
        Turtle._pen = None

    def mode(self, mode=None):
        "Set turtle-mode ('standard', 'logo' or 'world') and perform reset.\n\n        Optional argument:\n        mode -- one of the strings 'standard', 'logo' or 'world'\n\n        Mode 'standard' is compatible with turtle.py.\n        Mode 'logo' is compatible with most Logo-Turtle-Graphics.\n        Mode 'world' uses userdefined 'worldcoordinates'. *Attention*: in\n        this mode angles appear distorted if x/y unit-ratio doesn't equal 1.\n        If mode is not given, return the current mode.\n\n             Mode      Initial turtle heading     positive angles\n         ------------|-------------------------|-------------------\n          'standard'    to the right (east)       counterclockwise\n            'logo'        upward    (north)         clockwise\n\n        Examples:\n        >>> mode('logo')   # resets turtle heading to north\n        >>> mode()\n        'logo'\n        "
        if mode is None:
            return self._mode
        mode = mode.lower()
        if mode not in ["standard", "logo", "world"]:
            raise TurtleGraphicsError(("No turtle-graphics-mode %s" % mode))
        self._mode = mode
        if mode in ["standard", "logo"]:
            self._setscrollregion(
                ((-self.canvwidth) // 2),
                ((-self.canvheight) // 2),
                (self.canvwidth // 2),
                (self.canvheight // 2),
            )
            self.xscale = self.yscale = 1.0
        self.reset()

    def setworldcoordinates(self, llx, lly, urx, ury):
        "Set up a user defined coordinate-system.\n\n        Arguments:\n        llx -- a number, x-coordinate of lower left corner of canvas\n        lly -- a number, y-coordinate of lower left corner of canvas\n        urx -- a number, x-coordinate of upper right corner of canvas\n        ury -- a number, y-coordinate of upper right corner of canvas\n\n        Set up user coodinat-system and switch to mode 'world' if necessary.\n        This performs a screen.reset. If mode 'world' is already active,\n        all drawings are redrawn according to the new coordinates.\n\n        But ATTENTION: in user-defined coordinatesystems angles may appear\n        distorted. (see Screen.mode())\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.setworldcoordinates(-10,-0.5,50,1.5)\n        >>> for _ in range(36):\n        ...     left(10)\n        ...     forward(0.5)\n        "
        if self.mode() != "world":
            self.mode("world")
        xspan = float((urx - llx))
        yspan = float((ury - lly))
        (wx, wy) = self._window_size()
        self.screensize((wx - 20), (wy - 20))
        (oldxscale, oldyscale) = (self.xscale, self.yscale)
        self.xscale = self.canvwidth / xspan
        self.yscale = self.canvheight / yspan
        srx1 = llx * self.xscale
        sry1 = (-ury) * self.yscale
        srx2 = self.canvwidth + srx1
        sry2 = self.canvheight + sry1
        self._setscrollregion(srx1, sry1, srx2, sry2)
        self._rescale((self.xscale / oldxscale), (self.yscale / oldyscale))
        self.update()

    def register_shape(self, name, shape=None):
        'Adds a turtle shape to TurtleScreen\'s shapelist.\n\n        Arguments:\n        (1) name is the name of a gif-file and shape is None.\n            Installs the corresponding image shape.\n            !! Image-shapes DO NOT rotate when turning the turtle,\n            !! so they do not display the heading of the turtle!\n        (2) name is an arbitrary string and shape is a tuple\n            of pairs of coordinates. Installs the corresponding\n            polygon shape\n        (3) name is an arbitrary string and shape is a\n            (compound) Shape object. Installs the corresponding\n            compound shape.\n        To use a shape, you have to issue the command shape(shapename).\n\n        call: register_shape("turtle.gif")\n        --or: register_shape("tri", ((0,0), (10,10), (-10,10)))\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.register_shape("triangle", ((5,-3),(0,5),(-5,-3)))\n\n        '
        if shape is None:
            if name.lower().endswith(".gif"):
                shape = Shape("image", self._image(name))
            else:
                raise TurtleGraphicsError(
                    (
                        "Bad arguments for register_shape.\n"
                        + "Use  help(register_shape)"
                    )
                )
        elif isinstance(shape, tuple):
            shape = Shape("polygon", shape)
        self._shapes[name] = shape

    def _colorstr(self, color):
        "Return color string corresponding to args.\n\n        Argument may be a string or a tuple of three\n        numbers corresponding to actual colormode,\n        i.e. in the range 0<=n<=colormode.\n\n        If the argument doesn't represent a color,\n        an error is raised.\n        "
        if len(color) == 1:
            color = color[0]
        if isinstance(color, str):
            if self._iscolorstring(color) or (color == ""):
                return color
            else:
                raise TurtleGraphicsError(("bad color string: %s" % str(color)))
        try:
            (r, g, b) = color
        except (TypeError, ValueError):
            raise TurtleGraphicsError(("bad color arguments: %s" % str(color)))
        if self._colormode == 1.0:
            (r, g, b) = [round((255.0 * x)) for x in (r, g, b)]
        if not ((0 <= r <= 255) and (0 <= g <= 255) and (0 <= b <= 255)):
            raise TurtleGraphicsError(("bad color sequence: %s" % str(color)))
        return "#%02x%02x%02x" % (r, g, b)

    def _color(self, cstr):
        if not cstr.startswith("#"):
            return cstr
        if len(cstr) == 7:
            cl = [int(cstr[i : (i + 2)], 16) for i in (1, 3, 5)]
        elif len(cstr) == 4:
            cl = [(16 * int(cstr[h], 16)) for h in cstr[1:]]
        else:
            raise TurtleGraphicsError(("bad colorstring: %s" % cstr))
        return tuple((((c * self._colormode) / 255) for c in cl))

    def colormode(self, cmode=None):
        "Return the colormode or set it to 1.0 or 255.\n\n        Optional argument:\n        cmode -- one of the values 1.0 or 255\n\n        r, g, b values of colortriples have to be in range 0..cmode.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.colormode()\n        1.0\n        >>> screen.colormode(255)\n        >>> pencolor(240,160,80)\n        "
        if cmode is None:
            return self._colormode
        if cmode == 1.0:
            self._colormode = float(cmode)
        elif cmode == 255:
            self._colormode = int(cmode)

    def reset(self):
        "Reset all Turtles on the Screen to their initial state.\n\n        No argument.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.reset()\n        "
        for turtle in self._turtles:
            turtle._setmode(self._mode)
            turtle.reset()

    def turtles(self):
        "Return the list of turtles on the screen.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.turtles()\n        [<turtle.Turtle object at 0x00E11FB0>]\n        "
        return self._turtles

    def bgcolor(self, *args):
        "Set or return backgroundcolor of the TurtleScreen.\n\n        Arguments (if given): a color string or three numbers\n        in the range 0..colormode or a 3-tuple of such numbers.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.bgcolor(\"orange\")\n        >>> screen.bgcolor()\n        'orange'\n        >>> screen.bgcolor(0.5,0,0.5)\n        >>> screen.bgcolor()\n        '#800080'\n        "
        if args:
            color = self._colorstr(args)
        else:
            color = None
        color = self._bgcolor(color)
        if color is not None:
            color = self._color(color)
        return color

    def tracer(self, n=None, delay=None):
        "Turns turtle animation on/off and set delay for update drawings.\n\n        Optional arguments:\n        n -- nonnegative  integer\n        delay -- nonnegative  integer\n\n        If n is given, only each n-th regular screen update is really performed.\n        (Can be used to accelerate the drawing of complex graphics.)\n        Second arguments sets delay value (see RawTurtle.delay())\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.tracer(8, 25)\n        >>> dist = 2\n        >>> for i in range(200):\n        ...     fd(dist)\n        ...     rt(90)\n        ...     dist += 2\n        "
        if n is None:
            return self._tracing
        self._tracing = int(n)
        self._updatecounter = 0
        if delay is not None:
            self._delayvalue = int(delay)
        if self._tracing:
            self.update()

    def delay(self, delay=None):
        " Return or set the drawing delay in milliseconds.\n\n        Optional argument:\n        delay -- positive integer\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.delay(15)\n        >>> screen.delay()\n        15\n        "
        if delay is None:
            return self._delayvalue
        self._delayvalue = int(delay)

    def _incrementudc(self):
        "Increment update counter."
        if not TurtleScreen._RUNNING:
            TurtleScreen._RUNNING = True
            raise Terminator
        if self._tracing > 0:
            self._updatecounter += 1
            self._updatecounter %= self._tracing

    def update(self):
        "Perform a TurtleScreen update.\n        "
        tracing = self._tracing
        self._tracing = True
        for t in self.turtles():
            t._update_data()
            t._drawturtle()
        self._tracing = tracing
        self._update()

    def window_width(self):
        " Return the width of the turtle window.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.window_width()\n        640\n        "
        return self._window_size()[0]

    def window_height(self):
        " Return the height of the turtle window.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.window_height()\n        480\n        "
        return self._window_size()[1]

    def getcanvas(self):
        "Return the Canvas of this TurtleScreen.\n\n        No argument.\n\n        Example (for a Screen instance named screen):\n        >>> cv = screen.getcanvas()\n        >>> cv\n        <turtle.ScrolledCanvas instance at 0x010742D8>\n        "
        return self.cv

    def getshapes(self):
        "Return a list of names of all currently available turtle shapes.\n\n        No argument.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.getshapes()\n        ['arrow', 'blank', 'circle', ... , 'turtle']\n        "
        return sorted(self._shapes.keys())

    def onclick(self, fun, btn=1, add=None):
        "Bind fun to mouse-click event on canvas.\n\n        Arguments:\n        fun -- a function with two arguments, the coordinates of the\n               clicked point on the canvas.\n        btn -- the number of the mouse-button, defaults to 1\n\n        Example (for a TurtleScreen instance named screen)\n\n        >>> screen.onclick(goto)\n        >>> # Subsequently clicking into the TurtleScreen will\n        >>> # make the turtle move to the clicked point.\n        >>> screen.onclick(None)\n        "
        self._onscreenclick(fun, btn, add)

    def onkey(self, fun, key):
        'Bind fun to key-release event of key.\n\n        Arguments:\n        fun -- a function with no arguments\n        key -- a string: key (e.g. "a") or key-symbol (e.g. "space")\n\n        In order to be able to register key-events, TurtleScreen\n        must have focus. (See method listen.)\n\n        Example (for a TurtleScreen instance named screen):\n\n        >>> def f():\n        ...     fd(50)\n        ...     lt(60)\n        ...\n        >>> screen.onkey(f, "Up")\n        >>> screen.listen()\n\n        Subsequently the turtle can be moved by repeatedly pressing\n        the up-arrow key, consequently drawing a hexagon\n\n        '
        if fun is None:
            if key in self._keys:
                self._keys.remove(key)
        elif key not in self._keys:
            self._keys.append(key)
        self._onkeyrelease(fun, key)

    def onkeypress(self, fun, key=None):
        'Bind fun to key-press event of key if key is given,\n        or to any key-press-event if no key is given.\n\n        Arguments:\n        fun -- a function with no arguments\n        key -- a string: key (e.g. "a") or key-symbol (e.g. "space")\n\n        In order to be able to register key-events, TurtleScreen\n        must have focus. (See method listen.)\n\n        Example (for a TurtleScreen instance named screen\n        and a Turtle instance named turtle):\n\n        >>> def f():\n        ...     fd(50)\n        ...     lt(60)\n        ...\n        >>> screen.onkeypress(f, "Up")\n        >>> screen.listen()\n\n        Subsequently the turtle can be moved by repeatedly pressing\n        the up-arrow key, or by keeping pressed the up-arrow key.\n        consequently drawing a hexagon.\n        '
        if fun is None:
            if key in self._keys:
                self._keys.remove(key)
        elif (key is not None) and (key not in self._keys):
            self._keys.append(key)
        self._onkeypress(fun, key)

    def listen(self, xdummy=None, ydummy=None):
        "Set focus on TurtleScreen (in order to collect key-events)\n\n        No arguments.\n        Dummy arguments are provided in order\n        to be able to pass listen to the onclick method.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.listen()\n        "
        self._listen()

    def ontimer(self, fun, t=0):
        "Install a timer, which calls fun after t milliseconds.\n\n        Arguments:\n        fun -- a function with no arguments.\n        t -- a number >= 0\n\n        Example (for a TurtleScreen instance named screen):\n\n        >>> running = True\n        >>> def f():\n        ...     if running:\n        ...             fd(50)\n        ...             lt(60)\n        ...             screen.ontimer(f, 250)\n        ...\n        >>> f()   # makes the turtle marching around\n        >>> running = False\n        "
        self._ontimer(fun, t)

    def bgpic(self, picname=None):
        'Set background image or return name of current backgroundimage.\n\n        Optional argument:\n        picname -- a string, name of a gif-file or "nopic".\n\n        If picname is a filename, set the corresponding image as background.\n        If picname is "nopic", delete backgroundimage, if present.\n        If picname is None, return the filename of the current backgroundimage.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.bgpic()\n        \'nopic\'\n        >>> screen.bgpic("landscape.gif")\n        >>> screen.bgpic()\n        \'landscape.gif\'\n        '
        if picname is None:
            return self._bgpicname
        if picname not in self._bgpics:
            self._bgpics[picname] = self._image(picname)
        self._setbgpic(self._bgpic, self._bgpics[picname])
        self._bgpicname = picname

    def screensize(self, canvwidth=None, canvheight=None, bg=None):
        "Resize the canvas the turtles are drawing on.\n\n        Optional arguments:\n        canvwidth -- positive integer, new width of canvas in pixels\n        canvheight --  positive integer, new height of canvas in pixels\n        bg -- colorstring or color-tuple, new backgroundcolor\n        If no arguments are given, return current (canvaswidth, canvasheight)\n\n        Do not alter the drawing window. To observe hidden parts of\n        the canvas use the scrollbars. (Can make visible those parts\n        of a drawing, which were outside the canvas before!)\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.screensize(2000,1500)\n        >>> # e.g. to search for an erroneously escaped turtle ;-)\n        "
        return self._resize(canvwidth, canvheight, bg)

    onscreenclick = onclick
    resetscreen = reset
    clearscreen = clear
    addshape = register_shape
    onkeyrelease = onkey


class TNavigator(object):
    "Navigation part of the RawTurtle.\n    Implements methods for turtle movement.\n    "
    START_ORIENTATION = {
        "standard": Vec2D(1.0, 0.0),
        "world": Vec2D(1.0, 0.0),
        "logo": Vec2D(0.0, 1.0),
    }
    DEFAULT_MODE = "standard"
    DEFAULT_ANGLEOFFSET = 0
    DEFAULT_ANGLEORIENT = 1

    def __init__(self, mode=DEFAULT_MODE):
        self._angleOffset = self.DEFAULT_ANGLEOFFSET
        self._angleOrient = self.DEFAULT_ANGLEORIENT
        self._mode = mode
        self.undobuffer = None
        self.degrees()
        self._mode = None
        self._setmode(mode)
        TNavigator.reset(self)

    def reset(self):
        "reset turtle to its initial values\n\n        Will be overwritten by parent class\n        "
        self._position = Vec2D(0.0, 0.0)
        self._orient = TNavigator.START_ORIENTATION[self._mode]

    def _setmode(self, mode=None):
        "Set turtle-mode to 'standard', 'world' or 'logo'.\n        "
        if mode is None:
            return self._mode
        if mode not in ["standard", "logo", "world"]:
            return
        self._mode = mode
        if mode in ["standard", "world"]:
            self._angleOffset = 0
            self._angleOrient = 1
        else:
            self._angleOffset = self._fullcircle / 4.0
            self._angleOrient = -1

    def _setDegreesPerAU(self, fullcircle):
        "Helper function for degrees() and radians()"
        self._fullcircle = fullcircle
        self._degreesPerAU = 360 / fullcircle
        if self._mode == "standard":
            self._angleOffset = 0
        else:
            self._angleOffset = fullcircle / 4.0

    def degrees(self, fullcircle=360.0):
        " Set angle measurement units to degrees.\n\n        Optional argument:\n        fullcircle -  a number\n\n        Set angle measurement units, i. e. set number\n        of 'degrees' for a full circle. Default value is\n        360 degrees.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.left(90)\n        >>> turtle.heading()\n        90\n\n        Change angle measurement unit to grad (also known as gon,\n        grade, or gradian and equals 1/100-th of the right angle.)\n        >>> turtle.degrees(400.0)\n        >>> turtle.heading()\n        100\n\n        "
        self._setDegreesPerAU(fullcircle)

    def radians(self):
        " Set the angle measurement units to radians.\n\n        No arguments.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.heading()\n        90\n        >>> turtle.radians()\n        >>> turtle.heading()\n        1.5707963267948966\n        "
        self._setDegreesPerAU(math.tau)

    def _go(self, distance):
        "move turtle forward by specified distance"
        ende = self._position + (self._orient * distance)
        self._goto(ende)

    def _rotate(self, angle):
        "Turn turtle counterclockwise by specified angle if angle > 0."
        angle *= self._degreesPerAU
        self._orient = self._orient.rotate(angle)

    def _goto(self, end):
        "move turtle to position end."
        self._position = end

    def forward(self, distance):
        "Move the turtle forward by the specified distance.\n\n        Aliases: forward | fd\n\n        Argument:\n        distance -- a number (integer or float)\n\n        Move the turtle forward by the specified distance, in the direction\n        the turtle is headed.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.position()\n        (0.00, 0.00)\n        >>> turtle.forward(25)\n        >>> turtle.position()\n        (25.00,0.00)\n        >>> turtle.forward(-75)\n        >>> turtle.position()\n        (-50.00,0.00)\n        "
        self._go(distance)

    def back(self, distance):
        "Move the turtle backward by distance.\n\n        Aliases: back | backward | bk\n\n        Argument:\n        distance -- a number\n\n        Move the turtle backward by distance ,opposite to the direction the\n        turtle is headed. Do not change the turtle's heading.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.position()\n        (0.00, 0.00)\n        >>> turtle.backward(30)\n        >>> turtle.position()\n        (-30.00, 0.00)\n        "
        self._go((-distance))

    def right(self, angle):
        "Turn turtle right by angle units.\n\n        Aliases: right | rt\n\n        Argument:\n        angle -- a number (integer or float)\n\n        Turn turtle right by angle units. (Units are by default degrees,\n        but can be set via the degrees() and radians() functions.)\n        Angle orientation depends on mode. (See this.)\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.heading()\n        22.0\n        >>> turtle.right(45)\n        >>> turtle.heading()\n        337.0\n        "
        self._rotate((-angle))

    def left(self, angle):
        "Turn turtle left by angle units.\n\n        Aliases: left | lt\n\n        Argument:\n        angle -- a number (integer or float)\n\n        Turn turtle left by angle units. (Units are by default degrees,\n        but can be set via the degrees() and radians() functions.)\n        Angle orientation depends on mode. (See this.)\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.heading()\n        22.0\n        >>> turtle.left(45)\n        >>> turtle.heading()\n        67.0\n        "
        self._rotate(angle)

    def pos(self):
        "Return the turtle's current location (x,y), as a Vec2D-vector.\n\n        Aliases: pos | position\n\n        No arguments.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pos()\n        (0.00, 240.00)\n        "
        return self._position

    def xcor(self):
        " Return the turtle's x coordinate.\n\n        No arguments.\n\n        Example (for a Turtle instance named turtle):\n        >>> reset()\n        >>> turtle.left(60)\n        >>> turtle.forward(100)\n        >>> print turtle.xcor()\n        50.0\n        "
        return self._position[0]

    def ycor(self):
        " Return the turtle's y coordinate\n        ---\n        No arguments.\n\n        Example (for a Turtle instance named turtle):\n        >>> reset()\n        >>> turtle.left(60)\n        >>> turtle.forward(100)\n        >>> print turtle.ycor()\n        86.6025403784\n        "
        return self._position[1]

    def goto(self, x, y=None):
        "Move turtle to an absolute position.\n\n        Aliases: setpos | setposition | goto:\n\n        Arguments:\n        x -- a number      or     a pair/vector of numbers\n        y -- a number             None\n\n        call: goto(x, y)         # two coordinates\n        --or: goto((x, y))       # a pair (tuple) of coordinates\n        --or: goto(vec)          # e.g. as returned by pos()\n\n        Move turtle to an absolute position. If the pen is down,\n        a line will be drawn. The turtle's orientation does not change.\n\n        Example (for a Turtle instance named turtle):\n        >>> tp = turtle.pos()\n        >>> tp\n        (0.00, 0.00)\n        >>> turtle.setpos(60,30)\n        >>> turtle.pos()\n        (60.00,30.00)\n        >>> turtle.setpos((20,80))\n        >>> turtle.pos()\n        (20.00,80.00)\n        >>> turtle.setpos(tp)\n        >>> turtle.pos()\n        (0.00,0.00)\n        "
        if y is None:
            self._goto(Vec2D(*x))
        else:
            self._goto(Vec2D(x, y))

    def home(self):
        "Move turtle to the origin - coordinates (0,0).\n\n        No arguments.\n\n        Move turtle to the origin - coordinates (0,0) and set its\n        heading to its start-orientation (which depends on mode).\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.home()\n        "
        self.goto(0, 0)
        self.setheading(0)

    def setx(self, x):
        "Set the turtle's first coordinate to x\n\n        Argument:\n        x -- a number (integer or float)\n\n        Set the turtle's first coordinate to x, leave second coordinate\n        unchanged.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.position()\n        (0.00, 240.00)\n        >>> turtle.setx(10)\n        >>> turtle.position()\n        (10.00, 240.00)\n        "
        self._goto(Vec2D(x, self._position[1]))

    def sety(self, y):
        "Set the turtle's second coordinate to y\n\n        Argument:\n        y -- a number (integer or float)\n\n        Set the turtle's first coordinate to x, second coordinate remains\n        unchanged.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.position()\n        (0.00, 40.00)\n        >>> turtle.sety(-10)\n        >>> turtle.position()\n        (0.00, -10.00)\n        "
        self._goto(Vec2D(self._position[0], y))

    def distance(self, x, y=None):
        "Return the distance from the turtle to (x,y) in turtle step units.\n\n        Arguments:\n        x -- a number   or  a pair/vector of numbers   or   a turtle instance\n        y -- a number       None                            None\n\n        call: distance(x, y)         # two coordinates\n        --or: distance((x, y))       # a pair (tuple) of coordinates\n        --or: distance(vec)          # e.g. as returned by pos()\n        --or: distance(mypen)        # where mypen is another turtle\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pos()\n        (0.00, 0.00)\n        >>> turtle.distance(30,40)\n        50.0\n        >>> pen = Turtle()\n        >>> pen.forward(77)\n        >>> turtle.distance(pen)\n        77.0\n        "
        if y is not None:
            pos = Vec2D(x, y)
        if isinstance(x, Vec2D):
            pos = x
        elif isinstance(x, tuple):
            pos = Vec2D(*x)
        elif isinstance(x, TNavigator):
            pos = x._position
        return abs((pos - self._position))

    def towards(self, x, y=None):
        'Return the angle of the line from the turtle\'s position to (x, y).\n\n        Arguments:\n        x -- a number   or  a pair/vector of numbers   or   a turtle instance\n        y -- a number       None                            None\n\n        call: distance(x, y)         # two coordinates\n        --or: distance((x, y))       # a pair (tuple) of coordinates\n        --or: distance(vec)          # e.g. as returned by pos()\n        --or: distance(mypen)        # where mypen is another turtle\n\n        Return the angle, between the line from turtle-position to position\n        specified by x, y and the turtle\'s start orientation. (Depends on\n        modes - "standard" or "logo")\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pos()\n        (10.00, 10.00)\n        >>> turtle.towards(0,0)\n        225.0\n        '
        if y is not None:
            pos = Vec2D(x, y)
        if isinstance(x, Vec2D):
            pos = x
        elif isinstance(x, tuple):
            pos = Vec2D(*x)
        elif isinstance(x, TNavigator):
            pos = x._position
        (x, y) = pos - self._position
        result = round(math.degrees(math.atan2(y, x)), 10) % 360.0
        result /= self._degreesPerAU
        return (self._angleOffset + (self._angleOrient * result)) % self._fullcircle

    def heading(self):
        " Return the turtle's current heading.\n\n        No arguments.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.left(67)\n        >>> turtle.heading()\n        67.0\n        "
        (x, y) = self._orient
        result = round(math.degrees(math.atan2(y, x)), 10) % 360.0
        result /= self._degreesPerAU
        return (self._angleOffset + (self._angleOrient * result)) % self._fullcircle

    def setheading(self, to_angle):
        "Set the orientation of the turtle to to_angle.\n\n        Aliases:  setheading | seth\n\n        Argument:\n        to_angle -- a number (integer or float)\n\n        Set the orientation of the turtle to to_angle.\n        Here are some common directions in degrees:\n\n         standard - mode:          logo-mode:\n        -------------------|--------------------\n           0 - east                0 - north\n          90 - north              90 - east\n         180 - west              180 - south\n         270 - south             270 - west\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.setheading(90)\n        >>> turtle.heading()\n        90\n        "
        angle = (to_angle - self.heading()) * self._angleOrient
        full = self._fullcircle
        angle = ((angle + (full / 2.0)) % full) - (full / 2.0)
        self._rotate(angle)

    def circle(self, radius, extent=None, steps=None):
        " Draw a circle with given radius.\n\n        Arguments:\n        radius -- a number\n        extent (optional) -- a number\n        steps (optional) -- an integer\n\n        Draw a circle with given radius. The center is radius units left\n        of the turtle; extent - an angle - determines which part of the\n        circle is drawn. If extent is not given, draw the entire circle.\n        If extent is not a full circle, one endpoint of the arc is the\n        current pen position. Draw the arc in counterclockwise direction\n        if radius is positive, otherwise in clockwise direction. Finally\n        the direction of the turtle is changed by the amount of extent.\n\n        As the circle is approximated by an inscribed regular polygon,\n        steps determines the number of steps to use. If not given,\n        it will be calculated automatically. Maybe used to draw regular\n        polygons.\n\n        call: circle(radius)                  # full circle\n        --or: circle(radius, extent)          # arc\n        --or: circle(radius, extent, steps)\n        --or: circle(radius, steps=6)         # 6-sided polygon\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.circle(50)\n        >>> turtle.circle(120, 180)  # semicircle\n        "
        if self.undobuffer:
            self.undobuffer.push(["seq"])
            self.undobuffer.cumulate = True
        speed = self.speed()
        if extent is None:
            extent = self._fullcircle
        if steps is None:
            frac = abs(extent) / self._fullcircle
            steps = 1 + int((min((11 + (abs(radius) / 6.0)), 59.0) * frac))
        w = (1.0 * extent) / steps
        w2 = 0.5 * w
        l = (2.0 * radius) * math.sin((math.radians(w2) * self._degreesPerAU))
        if radius < 0:
            (l, w, w2) = ((-l), (-w), (-w2))
        tr = self._tracer()
        dl = self._delay()
        if speed == 0:
            self._tracer(0, 0)
        else:
            self.speed(0)
        self._rotate(w2)
        for i in range(steps):
            self.speed(speed)
            self._go(l)
            self.speed(0)
            self._rotate(w)
        self._rotate((-w2))
        if speed == 0:
            self._tracer(tr, dl)
        self.speed(speed)
        if self.undobuffer:
            self.undobuffer.cumulate = False

    def speed(self, s=0):
        "dummy method - to be overwritten by child class"

    def _tracer(self, a=None, b=None):
        "dummy method - to be overwritten by child class"

    def _delay(self, n=None):
        "dummy method - to be overwritten by child class"

    fd = forward
    bk = back
    backward = back
    rt = right
    lt = left
    position = pos
    setpos = goto
    setposition = goto
    seth = setheading


class TPen(object):
    "Drawing part of the RawTurtle.\n    Implements drawing properties.\n    "

    def __init__(self, resizemode=_CFG["resizemode"]):
        self._resizemode = resizemode
        self.undobuffer = None
        TPen._reset(self)

    def _reset(self, pencolor=_CFG["pencolor"], fillcolor=_CFG["fillcolor"]):
        self._pensize = 1
        self._shown = True
        self._pencolor = pencolor
        self._fillcolor = fillcolor
        self._drawing = True
        self._speed = 3
        self._stretchfactor = (1.0, 1.0)
        self._shearfactor = 0.0
        self._tilt = 0.0
        self._shapetrafo = (1.0, 0.0, 0.0, 1.0)
        self._outlinewidth = 1

    def resizemode(self, rmode=None):
        'Set resizemode to one of the values: "auto", "user", "noresize".\n\n        (Optional) Argument:\n        rmode -- one of the strings "auto", "user", "noresize"\n\n        Different resizemodes have the following effects:\n          - "auto" adapts the appearance of the turtle\n                   corresponding to the value of pensize.\n          - "user" adapts the appearance of the turtle according to the\n                   values of stretchfactor and outlinewidth (outline),\n                   which are set by shapesize()\n          - "noresize" no adaption of the turtle\'s appearance takes place.\n        If no argument is given, return current resizemode.\n        resizemode("user") is called by a call of shapesize with arguments.\n\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.resizemode("noresize")\n        >>> turtle.resizemode()\n        \'noresize\'\n        '
        if rmode is None:
            return self._resizemode
        rmode = rmode.lower()
        if rmode in ["auto", "user", "noresize"]:
            self.pen(resizemode=rmode)

    def pensize(self, width=None):
        'Set or return the line thickness.\n\n        Aliases:  pensize | width\n\n        Argument:\n        width -- positive number\n\n        Set the line thickness to width or return it. If resizemode is set\n        to "auto" and turtleshape is a polygon, that polygon is drawn with\n        the same line thickness. If no argument is given, current pensize\n        is returned.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pensize()\n        1\n        >>> turtle.pensize(10)   # from here on lines of width 10 are drawn\n        '
        if width is None:
            return self._pensize
        self.pen(pensize=width)

    def penup(self):
        "Pull the pen up -- no drawing when moving.\n\n        Aliases: penup | pu | up\n\n        No argument\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.penup()\n        "
        if not self._drawing:
            return
        self.pen(pendown=False)

    def pendown(self):
        "Pull the pen down -- drawing when moving.\n\n        Aliases: pendown | pd | down\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pendown()\n        "
        if self._drawing:
            return
        self.pen(pendown=True)

    def isdown(self):
        "Return True if pen is down, False if it's up.\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.penup()\n        >>> turtle.isdown()\n        False\n        >>> turtle.pendown()\n        >>> turtle.isdown()\n        True\n        "
        return self._drawing

    def speed(self, speed=None):
        " Return or set the turtle's speed.\n\n        Optional argument:\n        speed -- an integer in the range 0..10 or a speedstring (see below)\n\n        Set the turtle's speed to an integer value in the range 0 .. 10.\n        If no argument is given: return current speed.\n\n        If input is a number greater than 10 or smaller than 0.5,\n        speed is set to 0.\n        Speedstrings  are mapped to speedvalues in the following way:\n            'fastest' :  0\n            'fast'    :  10\n            'normal'  :  6\n            'slow'    :  3\n            'slowest' :  1\n        speeds from 1 to 10 enforce increasingly faster animation of\n        line drawing and turtle turning.\n\n        Attention:\n        speed = 0 : *no* animation takes place. forward/back makes turtle jump\n        and likewise left/right make the turtle turn instantly.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.speed(3)\n        "
        speeds = {"fastest": 0, "fast": 10, "normal": 6, "slow": 3, "slowest": 1}
        if speed is None:
            return self._speed
        if speed in speeds:
            speed = speeds[speed]
        elif 0.5 < speed < 10.5:
            speed = int(round(speed))
        else:
            speed = 0
        self.pen(speed=speed)

    def color(self, *args):
        "Return or set the pencolor and fillcolor.\n\n        Arguments:\n        Several input formats are allowed.\n        They use 0, 1, 2, or 3 arguments as follows:\n\n        color()\n            Return the current pencolor and the current fillcolor\n            as a pair of color specification strings as are returned\n            by pencolor and fillcolor.\n        color(colorstring), color((r,g,b)), color(r,g,b)\n            inputs as in pencolor, set both, fillcolor and pencolor,\n            to the given value.\n        color(colorstring1, colorstring2),\n        color((r1,g1,b1), (r2,g2,b2))\n            equivalent to pencolor(colorstring1) and fillcolor(colorstring2)\n            and analogously, if the other input format is used.\n\n        If turtleshape is a polygon, outline and interior of that polygon\n        is drawn with the newly set colors.\n        For more info see: pencolor, fillcolor\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.color('red', 'green')\n        >>> turtle.color()\n        ('red', 'green')\n        >>> colormode(255)\n        >>> color((40, 80, 120), (160, 200, 240))\n        >>> color()\n        ('#285078', '#a0c8f0')\n        "
        if args:
            l = len(args)
            if l == 1:
                pcolor = fcolor = args[0]
            elif l == 2:
                (pcolor, fcolor) = args
            elif l == 3:
                pcolor = fcolor = args
            pcolor = self._colorstr(pcolor)
            fcolor = self._colorstr(fcolor)
            self.pen(pencolor=pcolor, fillcolor=fcolor)
        else:
            return (self._color(self._pencolor), self._color(self._fillcolor))

    def pencolor(self, *args):
        " Return or set the pencolor.\n\n        Arguments:\n        Four input formats are allowed:\n          - pencolor()\n            Return the current pencolor as color specification string,\n            possibly in hex-number format (see example).\n            May be used as input to another color/pencolor/fillcolor call.\n          - pencolor(colorstring)\n            s is a Tk color specification string, such as \"red\" or \"yellow\"\n          - pencolor((r, g, b))\n            *a tuple* of r, g, and b, which represent, an RGB color,\n            and each of r, g, and b are in the range 0..colormode,\n            where colormode is either 1.0 or 255\n          - pencolor(r, g, b)\n            r, g, and b represent an RGB color, and each of r, g, and b\n            are in the range 0..colormode\n\n        If turtleshape is a polygon, the outline of that polygon is drawn\n        with the newly set pencolor.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.pencolor('brown')\n        >>> tup = (0.2, 0.8, 0.55)\n        >>> turtle.pencolor(tup)\n        >>> turtle.pencolor()\n        '#33cc8c'\n        "
        if args:
            color = self._colorstr(args)
            if color == self._pencolor:
                return
            self.pen(pencolor=color)
        else:
            return self._color(self._pencolor)

    def fillcolor(self, *args):
        ' Return or set the fillcolor.\n\n        Arguments:\n        Four input formats are allowed:\n          - fillcolor()\n            Return the current fillcolor as color specification string,\n            possibly in hex-number format (see example).\n            May be used as input to another color/pencolor/fillcolor call.\n          - fillcolor(colorstring)\n            s is a Tk color specification string, such as "red" or "yellow"\n          - fillcolor((r, g, b))\n            *a tuple* of r, g, and b, which represent, an RGB color,\n            and each of r, g, and b are in the range 0..colormode,\n            where colormode is either 1.0 or 255\n          - fillcolor(r, g, b)\n            r, g, and b represent an RGB color, and each of r, g, and b\n            are in the range 0..colormode\n\n        If turtleshape is a polygon, the interior of that polygon is drawn\n        with the newly set fillcolor.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.fillcolor(\'violet\')\n        >>> col = turtle.pencolor()\n        >>> turtle.fillcolor(col)\n        >>> turtle.fillcolor(0, .5, 0)\n        '
        if args:
            color = self._colorstr(args)
            if color == self._fillcolor:
                return
            self.pen(fillcolor=color)
        else:
            return self._color(self._fillcolor)

    def showturtle(self):
        "Makes the turtle visible.\n\n        Aliases: showturtle | st\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.hideturtle()\n        >>> turtle.showturtle()\n        "
        self.pen(shown=True)

    def hideturtle(self):
        "Makes the turtle invisible.\n\n        Aliases: hideturtle | ht\n\n        No argument.\n\n        It's a good idea to do this while you're in the\n        middle of a complicated drawing, because hiding\n        the turtle speeds up the drawing observably.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.hideturtle()\n        "
        self.pen(shown=False)

    def isvisible(self):
        "Return True if the Turtle is shown, False if it's hidden.\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.hideturtle()\n        >>> print turtle.isvisible():\n        False\n        "
        return self._shown

    def pen(self, pen=None, **pendict):
        "Return or set the pen's attributes.\n\n        Arguments:\n            pen -- a dictionary with some or all of the below listed keys.\n            **pendict -- one or more keyword-arguments with the below\n                         listed keys as keywords.\n\n        Return or set the pen's attributes in a 'pen-dictionary'\n        with the following key/value pairs:\n           \"shown\"      :   True/False\n           \"pendown\"    :   True/False\n           \"pencolor\"   :   color-string or color-tuple\n           \"fillcolor\"  :   color-string or color-tuple\n           \"pensize\"    :   positive number\n           \"speed\"      :   number in range 0..10\n           \"resizemode\" :   \"auto\" or \"user\" or \"noresize\"\n           \"stretchfactor\": (positive number, positive number)\n           \"shearfactor\":   number\n           \"outline\"    :   positive number\n           \"tilt\"       :   number\n\n        This dictionary can be used as argument for a subsequent\n        pen()-call to restore the former pen-state. Moreover one\n        or more of these attributes can be provided as keyword-arguments.\n        This can be used to set several pen attributes in one statement.\n\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.pen(fillcolor=\"black\", pencolor=\"red\", pensize=10)\n        >>> turtle.pen()\n        {'pensize': 10, 'shown': True, 'resizemode': 'auto', 'outline': 1,\n        'pencolor': 'red', 'pendown': True, 'fillcolor': 'black',\n        'stretchfactor': (1,1), 'speed': 3, 'shearfactor': 0.0}\n        >>> penstate=turtle.pen()\n        >>> turtle.color(\"yellow\",\"\")\n        >>> turtle.penup()\n        >>> turtle.pen()\n        {'pensize': 10, 'shown': True, 'resizemode': 'auto', 'outline': 1,\n        'pencolor': 'yellow', 'pendown': False, 'fillcolor': '',\n        'stretchfactor': (1,1), 'speed': 3, 'shearfactor': 0.0}\n        >>> p.pen(penstate, fillcolor=\"green\")\n        >>> p.pen()\n        {'pensize': 10, 'shown': True, 'resizemode': 'auto', 'outline': 1,\n        'pencolor': 'red', 'pendown': True, 'fillcolor': 'green',\n        'stretchfactor': (1,1), 'speed': 3, 'shearfactor': 0.0}\n        "
        _pd = {
            "shown": self._shown,
            "pendown": self._drawing,
            "pencolor": self._pencolor,
            "fillcolor": self._fillcolor,
            "pensize": self._pensize,
            "speed": self._speed,
            "resizemode": self._resizemode,
            "stretchfactor": self._stretchfactor,
            "shearfactor": self._shearfactor,
            "outline": self._outlinewidth,
            "tilt": self._tilt,
        }
        if not (pen or pendict):
            return _pd
        if isinstance(pen, dict):
            p = pen
        else:
            p = {}
        p.update(pendict)
        _p_buf = {}
        for key in p:
            _p_buf[key] = _pd[key]
        if self.undobuffer:
            self.undobuffer.push(("pen", _p_buf))
        newLine = False
        if "pendown" in p:
            if self._drawing != p["pendown"]:
                newLine = True
        if "pencolor" in p:
            if isinstance(p["pencolor"], tuple):
                p["pencolor"] = self._colorstr((p["pencolor"],))
            if self._pencolor != p["pencolor"]:
                newLine = True
        if "pensize" in p:
            if self._pensize != p["pensize"]:
                newLine = True
        if newLine:
            self._newLine()
        if "pendown" in p:
            self._drawing = p["pendown"]
        if "pencolor" in p:
            self._pencolor = p["pencolor"]
        if "pensize" in p:
            self._pensize = p["pensize"]
        if "fillcolor" in p:
            if isinstance(p["fillcolor"], tuple):
                p["fillcolor"] = self._colorstr((p["fillcolor"],))
            self._fillcolor = p["fillcolor"]
        if "speed" in p:
            self._speed = p["speed"]
        if "resizemode" in p:
            self._resizemode = p["resizemode"]
        if "stretchfactor" in p:
            sf = p["stretchfactor"]
            if isinstance(sf, (int, float)):
                sf = (sf, sf)
            self._stretchfactor = sf
        if "shearfactor" in p:
            self._shearfactor = p["shearfactor"]
        if "outline" in p:
            self._outlinewidth = p["outline"]
        if "shown" in p:
            self._shown = p["shown"]
        if "tilt" in p:
            self._tilt = p["tilt"]
        if ("stretchfactor" in p) or ("tilt" in p) or ("shearfactor" in p):
            (scx, scy) = self._stretchfactor
            shf = self._shearfactor
            (sa, ca) = (math.sin(self._tilt), math.cos(self._tilt))
            self._shapetrafo = (
                (scx * ca),
                (scy * ((shf * ca) + sa)),
                ((-scx) * sa),
                (scy * (ca - (shf * sa))),
            )
        self._update()

    def _newLine(self, usePos=True):
        "dummy method - to be overwritten by child class"

    def _update(self, count=True, forced=False):
        "dummy method - to be overwritten by child class"

    def _color(self, args):
        "dummy method - to be overwritten by child class"

    def _colorstr(self, args):
        "dummy method - to be overwritten by child class"

    width = pensize
    up = penup
    pu = penup
    pd = pendown
    down = pendown
    st = showturtle
    ht = hideturtle


class _TurtleImage(object):
    "Helper class: Datatype to store Turtle attributes\n    "

    def __init__(self, screen, shapeIndex):
        self.screen = screen
        self._type = None
        self._setshape(shapeIndex)

    def _setshape(self, shapeIndex):
        screen = self.screen
        self.shapeIndex = shapeIndex
        if self._type == "polygon" == screen._shapes[shapeIndex]._type:
            return
        if self._type == "image" == screen._shapes[shapeIndex]._type:
            return
        if self._type in ["image", "polygon"]:
            screen._delete(self._item)
        elif self._type == "compound":
            for item in self._item:
                screen._delete(item)
        self._type = screen._shapes[shapeIndex]._type
        if self._type == "polygon":
            self._item = screen._createpoly()
        elif self._type == "image":
            self._item = screen._createimage(screen._shapes["blank"]._data)
        elif self._type == "compound":
            self._item = [
                screen._createpoly() for item in screen._shapes[shapeIndex]._data
            ]


class RawTurtle(TPen, TNavigator):
    "Animation part of the RawTurtle.\n    Puts RawTurtle upon a TurtleScreen and provides tools for\n    its animation.\n    "
    screens = []

    def __init__(
        self,
        canvas=None,
        shape=_CFG["shape"],
        undobuffersize=_CFG["undobuffersize"],
        visible=_CFG["visible"],
    ):
        if isinstance(canvas, _Screen):
            self.screen = canvas
        elif isinstance(canvas, TurtleScreen):
            if canvas not in RawTurtle.screens:
                RawTurtle.screens.append(canvas)
            self.screen = canvas
        elif isinstance(canvas, (ScrolledCanvas, Canvas)):
            for screen in RawTurtle.screens:
                if screen.cv == canvas:
                    self.screen = screen
                    break
            else:
                self.screen = TurtleScreen(canvas)
                RawTurtle.screens.append(self.screen)
        else:
            raise TurtleGraphicsError(("bad canvas argument %s" % canvas))
        screen = self.screen
        TNavigator.__init__(self, screen.mode())
        TPen.__init__(self)
        screen._turtles.append(self)
        self.drawingLineItem = screen._createline()
        self.turtle = _TurtleImage(screen, shape)
        self._poly = None
        self._creatingPoly = False
        self._fillitem = self._fillpath = None
        self._shown = visible
        self._hidden_from_screen = False
        self.currentLineItem = screen._createline()
        self.currentLine = [self._position]
        self.items = [self.currentLineItem]
        self.stampItems = []
        self._undobuffersize = undobuffersize
        self.undobuffer = Tbuffer(undobuffersize)
        self._update()

    def reset(self):
        "Delete the turtle's drawings and restore its default values.\n\n        No argument.\n\n        Delete the turtle's drawings from the screen, re-center the turtle\n        and set variables to the default values.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.position()\n        (0.00,-22.00)\n        >>> turtle.heading()\n        100.0\n        >>> turtle.reset()\n        >>> turtle.position()\n        (0.00,0.00)\n        >>> turtle.heading()\n        0.0\n        "
        TNavigator.reset(self)
        TPen._reset(self)
        self._clear()
        self._drawturtle()
        self._update()

    def setundobuffer(self, size):
        "Set or disable undobuffer.\n\n        Argument:\n        size -- an integer or None\n\n        If size is an integer an empty undobuffer of given size is installed.\n        Size gives the maximum number of turtle-actions that can be undone\n        by the undo() function.\n        If size is None, no undobuffer is present.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.setundobuffer(42)\n        "
        if (size is None) or (size <= 0):
            self.undobuffer = None
        else:
            self.undobuffer = Tbuffer(size)

    def undobufferentries(self):
        "Return count of entries in the undobuffer.\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> while undobufferentries():\n        ...     undo()\n        "
        if self.undobuffer is None:
            return 0
        return self.undobuffer.nr_of_items()

    def _clear(self):
        "Delete all of pen's drawings"
        self._fillitem = self._fillpath = None
        for item in self.items:
            self.screen._delete(item)
        self.currentLineItem = self.screen._createline()
        self.currentLine = []
        if self._drawing:
            self.currentLine.append(self._position)
        self.items = [self.currentLineItem]
        self.clearstamps()
        self.setundobuffer(self._undobuffersize)

    def clear(self):
        "Delete the turtle's drawings from the screen. Do not move turtle.\n\n        No arguments.\n\n        Delete the turtle's drawings from the screen. Do not move turtle.\n        State and position of the turtle as well as drawings of other\n        turtles are not affected.\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.clear()\n        "
        self._clear()
        self._update()

    def _update_data(self):
        self.screen._incrementudc()
        if self.screen._updatecounter != 0:
            return
        if len(self.currentLine) > 1:
            self.screen._drawline(
                self.currentLineItem, self.currentLine, self._pencolor, self._pensize
            )

    def _update(self):
        "Perform a Turtle-data update.\n        "
        screen = self.screen
        if screen._tracing == 0:
            return
        elif screen._tracing == 1:
            self._update_data()
            self._drawturtle()
            screen._update()
            screen._delay(screen._delayvalue)
        else:
            self._update_data()
            if screen._updatecounter == 0:
                for t in screen.turtles():
                    t._drawturtle()
                screen._update()

    def _tracer(self, flag=None, delay=None):
        "Turns turtle animation on/off and set delay for update drawings.\n\n        Optional arguments:\n        n -- nonnegative  integer\n        delay -- nonnegative  integer\n\n        If n is given, only each n-th regular screen update is really performed.\n        (Can be used to accelerate the drawing of complex graphics.)\n        Second arguments sets delay value (see RawTurtle.delay())\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.tracer(8, 25)\n        >>> dist = 2\n        >>> for i in range(200):\n        ...     turtle.fd(dist)\n        ...     turtle.rt(90)\n        ...     dist += 2\n        "
        return self.screen.tracer(flag, delay)

    def _color(self, args):
        return self.screen._color(args)

    def _colorstr(self, args):
        return self.screen._colorstr(args)

    def _cc(self, args):
        "Convert colortriples to hexstrings.\n        "
        if isinstance(args, str):
            return args
        try:
            (r, g, b) = args
        except (TypeError, ValueError):
            raise TurtleGraphicsError(("bad color arguments: %s" % str(args)))
        if self.screen._colormode == 1.0:
            (r, g, b) = [round((255.0 * x)) for x in (r, g, b)]
        if not ((0 <= r <= 255) and (0 <= g <= 255) and (0 <= b <= 255)):
            raise TurtleGraphicsError(("bad color sequence: %s" % str(args)))
        return "#%02x%02x%02x" % (r, g, b)

    def clone(self):
        "Create and return a clone of the turtle.\n\n        No argument.\n\n        Create and return a clone of the turtle with same position, heading\n        and turtle properties.\n\n        Example (for a Turtle instance named mick):\n        mick = Turtle()\n        joe = mick.clone()\n        "
        screen = self.screen
        self._newLine(self._drawing)
        turtle = self.turtle
        self.screen = None
        self.turtle = None
        q = deepcopy(self)
        self.screen = screen
        self.turtle = turtle
        q.screen = screen
        q.turtle = _TurtleImage(screen, self.turtle.shapeIndex)
        screen._turtles.append(q)
        ttype = screen._shapes[self.turtle.shapeIndex]._type
        if ttype == "polygon":
            q.turtle._item = screen._createpoly()
        elif ttype == "image":
            q.turtle._item = screen._createimage(screen._shapes["blank"]._data)
        elif ttype == "compound":
            q.turtle._item = [
                screen._createpoly()
                for item in screen._shapes[self.turtle.shapeIndex]._data
            ]
        q.currentLineItem = screen._createline()
        q._update()
        return q

    def shape(self, name=None):
        "Set turtle shape to shape with given name / return current shapename.\n\n        Optional argument:\n        name -- a string, which is a valid shapename\n\n        Set turtle shape to shape with given name or, if name is not given,\n        return name of current shape.\n        Shape with name must exist in the TurtleScreen's shape dictionary.\n        Initially there are the following polygon shapes:\n        'arrow', 'turtle', 'circle', 'square', 'triangle', 'classic'.\n        To learn about how to deal with shapes see Screen-method register_shape.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.shape()\n        'arrow'\n        >>> turtle.shape(\"turtle\")\n        >>> turtle.shape()\n        'turtle'\n        "
        if name is None:
            return self.turtle.shapeIndex
        if not (name in self.screen.getshapes()):
            raise TurtleGraphicsError(("There is no shape named %s" % name))
        self.turtle._setshape(name)
        self._update()

    def shapesize(self, stretch_wid=None, stretch_len=None, outline=None):
        'Set/return turtle\'s stretchfactors/outline. Set resizemode to "user".\n\n        Optional arguments:\n           stretch_wid : positive number\n           stretch_len : positive number\n           outline  : positive number\n\n        Return or set the pen\'s attributes x/y-stretchfactors and/or outline.\n        Set resizemode to "user".\n        If and only if resizemode is set to "user", the turtle will be displayed\n        stretched according to its stretchfactors:\n        stretch_wid is stretchfactor perpendicular to orientation\n        stretch_len is stretchfactor in direction of turtles orientation.\n        outline determines the width of the shapes\'s outline.\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.resizemode("user")\n        >>> turtle.shapesize(5, 5, 12)\n        >>> turtle.shapesize(outline=8)\n        '
        if stretch_wid is stretch_len is outline is None:
            (stretch_wid, stretch_len) = self._stretchfactor
            return (stretch_wid, stretch_len, self._outlinewidth)
        if (stretch_wid == 0) or (stretch_len == 0):
            raise TurtleGraphicsError("stretch_wid/stretch_len must not be zero")
        if stretch_wid is not None:
            if stretch_len is None:
                stretchfactor = (stretch_wid, stretch_wid)
            else:
                stretchfactor = (stretch_wid, stretch_len)
        elif stretch_len is not None:
            stretchfactor = (self._stretchfactor[0], stretch_len)
        else:
            stretchfactor = self._stretchfactor
        if outline is None:
            outline = self._outlinewidth
        self.pen(resizemode="user", stretchfactor=stretchfactor, outline=outline)

    def shearfactor(self, shear=None):
        'Set or return the current shearfactor.\n\n        Optional argument: shear -- number, tangent of the shear angle\n\n        Shear the turtleshape according to the given shearfactor shear,\n        which is the tangent of the shear angle. DO NOT change the\n        turtle\'s heading (direction of movement).\n        If shear is not given: return the current shearfactor, i. e. the\n        tangent of the shear angle, by which lines parallel to the\n        heading of the turtle are sheared.\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("circle")\n        >>> turtle.shapesize(5,2)\n        >>> turtle.shearfactor(0.5)\n        >>> turtle.shearfactor()\n        >>> 0.5\n        '
        if shear is None:
            return self._shearfactor
        self.pen(resizemode="user", shearfactor=shear)

    def settiltangle(self, angle):
        'Rotate the turtleshape to point in the specified direction\n\n        Argument: angle -- number\n\n        Rotate the turtleshape to point in the direction specified by angle,\n        regardless of its current tilt-angle. DO NOT change the turtle\'s\n        heading (direction of movement).\n\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("circle")\n        >>> turtle.shapesize(5,2)\n        >>> turtle.settiltangle(45)\n        >>> stamp()\n        >>> turtle.fd(50)\n        >>> turtle.settiltangle(-45)\n        >>> stamp()\n        >>> turtle.fd(50)\n        '
        tilt = ((-angle) * self._degreesPerAU) * self._angleOrient
        tilt = math.radians(tilt) % math.tau
        self.pen(resizemode="user", tilt=tilt)

    def tiltangle(self, angle=None):
        'Set or return the current tilt-angle.\n\n        Optional argument: angle -- number\n\n        Rotate the turtleshape to point in the direction specified by angle,\n        regardless of its current tilt-angle. DO NOT change the turtle\'s\n        heading (direction of movement).\n        If angle is not given: return the current tilt-angle, i. e. the angle\n        between the orientation of the turtleshape and the heading of the\n        turtle (its direction of movement).\n\n        Deprecated since Python 3.1\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("circle")\n        >>> turtle.shapesize(5,2)\n        >>> turtle.tilt(45)\n        >>> turtle.tiltangle()\n        '
        if angle is None:
            tilt = (-math.degrees(self._tilt)) * self._angleOrient
            return (tilt / self._degreesPerAU) % self._fullcircle
        else:
            self.settiltangle(angle)

    def tilt(self, angle):
        'Rotate the turtleshape by angle.\n\n        Argument:\n        angle - a number\n\n        Rotate the turtleshape by angle from its current tilt-angle,\n        but do NOT change the turtle\'s heading (direction of movement).\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("circle")\n        >>> turtle.shapesize(5,2)\n        >>> turtle.tilt(30)\n        >>> turtle.fd(50)\n        >>> turtle.tilt(30)\n        >>> turtle.fd(50)\n        '
        self.settiltangle((angle + self.tiltangle()))

    def shapetransform(self, t11=None, t12=None, t21=None, t22=None):
        'Set or return the current transformation matrix of the turtle shape.\n\n        Optional arguments: t11, t12, t21, t22 -- numbers.\n\n        If none of the matrix elements are given, return the transformation\n        matrix.\n        Otherwise set the given elements and transform the turtleshape\n        according to the matrix consisting of first row t11, t12 and\n        second row t21, 22.\n        Modify stretchfactor, shearfactor and tiltangle according to the\n        given matrix.\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("square")\n        >>> turtle.shapesize(4,2)\n        >>> turtle.shearfactor(-0.5)\n        >>> turtle.shapetransform()\n        (4.0, -1.0, -0.0, 2.0)\n        '
        if t11 is t12 is t21 is t22 is None:
            return self._shapetrafo
        (m11, m12, m21, m22) = self._shapetrafo
        if t11 is not None:
            m11 = t11
        if t12 is not None:
            m12 = t12
        if t21 is not None:
            m21 = t21
        if t22 is not None:
            m22 = t22
        if ((t11 * t22) - (t12 * t21)) == 0:
            raise TurtleGraphicsError(
                "Bad shape transform matrix: must not be singular"
            )
        self._shapetrafo = (m11, m12, m21, m22)
        alfa = math.atan2((-m21), m11) % math.tau
        (sa, ca) = (math.sin(alfa), math.cos(alfa))
        (a11, a12, a21, a22) = (
            ((ca * m11) - (sa * m21)),
            ((ca * m12) - (sa * m22)),
            ((sa * m11) + (ca * m21)),
            ((sa * m12) + (ca * m22)),
        )
        self._stretchfactor = (a11, a22)
        self._shearfactor = a12 / a22
        self._tilt = alfa
        self.pen(resizemode="user")

    def _polytrafo(self, poly):
        "Computes transformed polygon shapes from a shape\n        according to current position and heading.\n        "
        screen = self.screen
        (p0, p1) = self._position
        (e0, e1) = self._orient
        e = Vec2D(e0, ((e1 * screen.yscale) / screen.xscale))
        (e0, e1) = (1.0 / abs(e)) * e
        return [
            (
                (p0 + (((e1 * x) + (e0 * y)) / screen.xscale)),
                (p1 + ((((-e0) * x) + (e1 * y)) / screen.yscale)),
            )
            for (x, y) in poly
        ]

    def get_shapepoly(self):
        'Return the current shape polygon as tuple of coordinate pairs.\n\n        No argument.\n\n        Examples (for a Turtle instance named turtle):\n        >>> turtle.shape("square")\n        >>> turtle.shapetransform(4, -1, 0, 2)\n        >>> turtle.get_shapepoly()\n        ((50, -20), (30, 20), (-50, 20), (-30, -20))\n\n        '
        shape = self.screen._shapes[self.turtle.shapeIndex]
        if shape._type == "polygon":
            return self._getshapepoly(shape._data, (shape._type == "compound"))

    def _getshapepoly(self, polygon, compound=False):
        "Calculate transformed shape polygon according to resizemode\n        and shapetransform.\n        "
        if (self._resizemode == "user") or compound:
            (t11, t12, t21, t22) = self._shapetrafo
        elif self._resizemode == "auto":
            l = max(1, (self._pensize / 5.0))
            (t11, t12, t21, t22) = (l, 0, 0, l)
        elif self._resizemode == "noresize":
            return polygon
        return tuple(
            ((((t11 * x) + (t12 * y)), ((t21 * x) + (t22 * y))) for (x, y) in polygon)
        )

    def _drawturtle(self):
        "Manages the correct rendering of the turtle with respect to\n        its shape, resizemode, stretch and tilt etc."
        screen = self.screen
        shape = screen._shapes[self.turtle.shapeIndex]
        ttype = shape._type
        titem = self.turtle._item
        if self._shown and (screen._updatecounter == 0) and (screen._tracing > 0):
            self._hidden_from_screen = False
            tshape = shape._data
            if ttype == "polygon":
                if self._resizemode == "noresize":
                    w = 1
                elif self._resizemode == "auto":
                    w = self._pensize
                else:
                    w = self._outlinewidth
                shape = self._polytrafo(self._getshapepoly(tshape))
                (fc, oc) = (self._fillcolor, self._pencolor)
                screen._drawpoly(titem, shape, fill=fc, outline=oc, width=w, top=True)
            elif ttype == "image":
                screen._drawimage(titem, self._position, tshape)
            elif ttype == "compound":
                for (item, (poly, fc, oc)) in zip(titem, tshape):
                    poly = self._polytrafo(self._getshapepoly(poly, True))
                    screen._drawpoly(
                        item,
                        poly,
                        fill=self._cc(fc),
                        outline=self._cc(oc),
                        width=self._outlinewidth,
                        top=True,
                    )
        else:
            if self._hidden_from_screen:
                return
            if ttype == "polygon":
                screen._drawpoly(titem, ((0, 0), (0, 0), (0, 0)), "", "")
            elif ttype == "image":
                screen._drawimage(titem, self._position, screen._shapes["blank"]._data)
            elif ttype == "compound":
                for item in titem:
                    screen._drawpoly(item, ((0, 0), (0, 0), (0, 0)), "", "")
            self._hidden_from_screen = True

    def stamp(self):
        'Stamp a copy of the turtleshape onto the canvas and return its id.\n\n        No argument.\n\n        Stamp a copy of the turtle shape onto the canvas at the current\n        turtle position. Return a stamp_id for that stamp, which can be\n        used to delete it by calling clearstamp(stamp_id).\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.color("blue")\n        >>> turtle.stamp()\n        13\n        >>> turtle.fd(50)\n        '
        screen = self.screen
        shape = screen._shapes[self.turtle.shapeIndex]
        ttype = shape._type
        tshape = shape._data
        if ttype == "polygon":
            stitem = screen._createpoly()
            if self._resizemode == "noresize":
                w = 1
            elif self._resizemode == "auto":
                w = self._pensize
            else:
                w = self._outlinewidth
            shape = self._polytrafo(self._getshapepoly(tshape))
            (fc, oc) = (self._fillcolor, self._pencolor)
            screen._drawpoly(stitem, shape, fill=fc, outline=oc, width=w, top=True)
        elif ttype == "image":
            stitem = screen._createimage("")
            screen._drawimage(stitem, self._position, tshape)
        elif ttype == "compound":
            stitem = []
            for element in tshape:
                item = screen._createpoly()
                stitem.append(item)
            stitem = tuple(stitem)
            for (item, (poly, fc, oc)) in zip(stitem, tshape):
                poly = self._polytrafo(self._getshapepoly(poly, True))
                screen._drawpoly(
                    item,
                    poly,
                    fill=self._cc(fc),
                    outline=self._cc(oc),
                    width=self._outlinewidth,
                    top=True,
                )
        self.stampItems.append(stitem)
        self.undobuffer.push(("stamp", stitem))
        return stitem

    def _clearstamp(self, stampid):
        "does the work for clearstamp() and clearstamps()\n        "
        if stampid in self.stampItems:
            if isinstance(stampid, tuple):
                for subitem in stampid:
                    self.screen._delete(subitem)
            else:
                self.screen._delete(stampid)
            self.stampItems.remove(stampid)
        item = ("stamp", stampid)
        buf = self.undobuffer
        if item not in buf.buffer:
            return
        index = buf.buffer.index(item)
        buf.buffer.remove(item)
        if index <= buf.ptr:
            buf.ptr = (buf.ptr - 1) % buf.bufsize
        buf.buffer.insert(((buf.ptr + 1) % buf.bufsize), [None])

    def clearstamp(self, stampid):
        'Delete stamp with given stampid\n\n        Argument:\n        stampid - an integer, must be return value of previous stamp() call.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.color("blue")\n        >>> astamp = turtle.stamp()\n        >>> turtle.fd(50)\n        >>> turtle.clearstamp(astamp)\n        '
        self._clearstamp(stampid)
        self._update()

    def clearstamps(self, n=None):
        "Delete all or first/last n of turtle's stamps.\n\n        Optional argument:\n        n -- an integer\n\n        If n is None, delete all of pen's stamps,\n        else if n > 0 delete first n stamps\n        else if n < 0 delete last n stamps.\n\n        Example (for a Turtle instance named turtle):\n        >>> for i in range(8):\n        ...     turtle.stamp(); turtle.fd(30)\n        ...\n        >>> turtle.clearstamps(2)\n        >>> turtle.clearstamps(-2)\n        >>> turtle.clearstamps()\n        "
        if n is None:
            toDelete = self.stampItems[:]
        elif n >= 0:
            toDelete = self.stampItems[:n]
        else:
            toDelete = self.stampItems[n:]
        for item in toDelete:
            self._clearstamp(item)
        self._update()

    def _goto(self, end):
        "Move the pen to the point end, thereby drawing a line\n        if pen is down. All other methods for turtle movement depend\n        on this one.\n        "
        go_modes = (
            self._drawing,
            self._pencolor,
            self._pensize,
            isinstance(self._fillpath, list),
        )
        screen = self.screen
        undo_entry = (
            "go",
            self._position,
            end,
            go_modes,
            (
                self.currentLineItem,
                self.currentLine[:],
                screen._pointlist(self.currentLineItem),
                self.items[:],
            ),
        )
        if self.undobuffer:
            self.undobuffer.push(undo_entry)
        start = self._position
        if self._speed and (screen._tracing == 1):
            diff = end - start
            diffsq = ((diff[0] * screen.xscale) ** 2) + ((diff[1] * screen.yscale) ** 2)
            nhops = 1 + int(
                ((diffsq ** 0.5) / ((3 * (1.1 ** self._speed)) * self._speed))
            )
            delta = diff * (1.0 / nhops)
            for n in range(1, nhops):
                if n == 1:
                    top = True
                else:
                    top = False
                self._position = start + (delta * n)
                if self._drawing:
                    screen._drawline(
                        self.drawingLineItem,
                        (start, self._position),
                        self._pencolor,
                        self._pensize,
                        top,
                    )
                self._update()
            if self._drawing:
                screen._drawline(
                    self.drawingLineItem, ((0, 0), (0, 0)), fill="", width=self._pensize
                )
        if self._drawing:
            self.currentLine.append(end)
        if isinstance(self._fillpath, list):
            self._fillpath.append(end)
        self._position = end
        if self._creatingPoly:
            self._poly.append(end)
        if len(self.currentLine) > 42:
            self._newLine()
        self._update()

    def _undogoto(self, entry):
        "Reverse a _goto. Used for undo()\n        "
        (old, new, go_modes, coodata) = entry
        (drawing, pc, ps, filling) = go_modes
        (cLI, cL, pl, items) = coodata
        screen = self.screen
        if abs((self._position - new)) > 0.5:
            print("undogoto: HALLO-DA-STIMMT-WAS-NICHT!")
        self.currentLineItem = cLI
        self.currentLine = cL
        if pl == [(0, 0), (0, 0)]:
            usepc = ""
        else:
            usepc = pc
        screen._drawline(cLI, pl, fill=usepc, width=ps)
        todelete = [
            i for i in self.items if ((i not in items) and (screen._type(i) == "line"))
        ]
        for i in todelete:
            screen._delete(i)
            self.items.remove(i)
        start = old
        if self._speed and (screen._tracing == 1):
            diff = old - new
            diffsq = ((diff[0] * screen.xscale) ** 2) + ((diff[1] * screen.yscale) ** 2)
            nhops = 1 + int(
                ((diffsq ** 0.5) / ((3 * (1.1 ** self._speed)) * self._speed))
            )
            delta = diff * (1.0 / nhops)
            for n in range(1, nhops):
                if n == 1:
                    top = True
                else:
                    top = False
                self._position = new + (delta * n)
                if drawing:
                    screen._drawline(
                        self.drawingLineItem, (start, self._position), pc, ps, top
                    )
                self._update()
            if drawing:
                screen._drawline(
                    self.drawingLineItem, ((0, 0), (0, 0)), fill="", width=ps
                )
        self._position = old
        if self._creatingPoly:
            if len(self._poly) > 0:
                self._poly.pop()
            if self._poly == []:
                self._creatingPoly = False
                self._poly = None
        if filling:
            if self._fillpath == []:
                self._fillpath = None
                print("Unwahrscheinlich in _undogoto!")
            elif self._fillpath is not None:
                self._fillpath.pop()
        self._update()

    def _rotate(self, angle):
        "Turns pen clockwise by angle.\n        "
        if self.undobuffer:
            self.undobuffer.push(("rot", angle, self._degreesPerAU))
        angle *= self._degreesPerAU
        neworient = self._orient.rotate(angle)
        tracing = self.screen._tracing
        if (tracing == 1) and (self._speed > 0):
            anglevel = 3.0 * self._speed
            steps = 1 + int((abs(angle) / anglevel))
            delta = (1.0 * angle) / steps
            for _ in range(steps):
                self._orient = self._orient.rotate(delta)
                self._update()
        self._orient = neworient
        self._update()

    def _newLine(self, usePos=True):
        "Closes current line item and starts a new one.\n           Remark: if current line became too long, animation\n           performance (via _drawline) slowed down considerably.\n        "
        if len(self.currentLine) > 1:
            self.screen._drawline(
                self.currentLineItem, self.currentLine, self._pencolor, self._pensize
            )
            self.currentLineItem = self.screen._createline()
            self.items.append(self.currentLineItem)
        else:
            self.screen._drawline(self.currentLineItem, top=True)
        self.currentLine = []
        if usePos:
            self.currentLine = [self._position]

    def filling(self):
        "Return fillstate (True if filling, False else).\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.begin_fill()\n        >>> if turtle.filling():\n        ...     turtle.pensize(5)\n        ... else:\n        ...     turtle.pensize(3)\n        "
        return isinstance(self._fillpath, list)

    def begin_fill(self):
        'Called just before drawing a shape to be filled.\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.color("black", "red")\n        >>> turtle.begin_fill()\n        >>> turtle.circle(60)\n        >>> turtle.end_fill()\n        '
        if not self.filling():
            self._fillitem = self.screen._createpoly()
            self.items.append(self._fillitem)
        self._fillpath = [self._position]
        self._newLine()
        if self.undobuffer:
            self.undobuffer.push(("beginfill", self._fillitem))
        self._update()

    def end_fill(self):
        'Fill the shape drawn after the call begin_fill().\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.color("black", "red")\n        >>> turtle.begin_fill()\n        >>> turtle.circle(60)\n        >>> turtle.end_fill()\n        '
        if self.filling():
            if len(self._fillpath) > 2:
                self.screen._drawpoly(
                    self._fillitem, self._fillpath, fill=self._fillcolor
                )
                if self.undobuffer:
                    self.undobuffer.push(("dofill", self._fillitem))
            self._fillitem = self._fillpath = None
            self._update()

    def dot(self, size=None, *color):
        'Draw a dot with diameter size, using color.\n\n        Optional arguments:\n        size -- an integer >= 1 (if given)\n        color -- a colorstring or a numeric color tuple\n\n        Draw a circular dot with diameter size, using color.\n        If size is not given, the maximum of pensize+4 and 2*pensize is used.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.dot()\n        >>> turtle.fd(50); turtle.dot(20, "blue"); turtle.fd(50)\n        '
        if not color:
            if isinstance(size, (str, tuple)):
                color = self._colorstr(size)
                size = self._pensize + max(self._pensize, 4)
            else:
                color = self._pencolor
                if not size:
                    size = self._pensize + max(self._pensize, 4)
        else:
            if size is None:
                size = self._pensize + max(self._pensize, 4)
            color = self._colorstr(color)
        if hasattr(self.screen, "_dot"):
            item = self.screen._dot(self._position, size, color)
            self.items.append(item)
            if self.undobuffer:
                self.undobuffer.push(("dot", item))
        else:
            pen = self.pen()
            if self.undobuffer:
                self.undobuffer.push(["seq"])
                self.undobuffer.cumulate = True
            try:
                if self.resizemode() == "auto":
                    self.ht()
                self.pendown()
                self.pensize(size)
                self.pencolor(color)
                self.forward(0)
            finally:
                self.pen(pen)
            if self.undobuffer:
                self.undobuffer.cumulate = False

    def _write(self, txt, align, font):
        "Performs the writing for write()\n        "
        (item, end) = self.screen._write(
            self._position, txt, align, font, self._pencolor
        )
        self.items.append(item)
        if self.undobuffer:
            self.undobuffer.push(("wri", item))
        return end

    def write(self, arg, move=False, align="left", font=("Arial", 8, "normal")):
        'Write text at the current turtle position.\n\n        Arguments:\n        arg -- info, which is to be written to the TurtleScreen\n        move (optional) -- True/False\n        align (optional) -- one of the strings "left", "center" or right"\n        font (optional) -- a triple (fontname, fontsize, fonttype)\n\n        Write text - the string representation of arg - at the current\n        turtle position according to align ("left", "center" or right")\n        and with the given font.\n        If move is True, the pen is moved to the bottom-right corner\n        of the text. By default, move is False.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.write(\'Home = \', True, align="center")\n        >>> turtle.write((0,0), True)\n        '
        if self.undobuffer:
            self.undobuffer.push(["seq"])
            self.undobuffer.cumulate = True
        end = self._write(str(arg), align.lower(), font)
        if move:
            (x, y) = self.pos()
            self.setpos(end, y)
        if self.undobuffer:
            self.undobuffer.cumulate = False

    def begin_poly(self):
        "Start recording the vertices of a polygon.\n\n        No argument.\n\n        Start recording the vertices of a polygon. Current turtle position\n        is first point of polygon.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.begin_poly()\n        "
        self._poly = [self._position]
        self._creatingPoly = True

    def end_poly(self):
        "Stop recording the vertices of a polygon.\n\n        No argument.\n\n        Stop recording the vertices of a polygon. Current turtle position is\n        last point of polygon. This will be connected with the first point.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.end_poly()\n        "
        self._creatingPoly = False

    def get_poly(self):
        'Return the lastly recorded polygon.\n\n        No argument.\n\n        Example (for a Turtle instance named turtle):\n        >>> p = turtle.get_poly()\n        >>> turtle.register_shape("myFavouriteShape", p)\n        '
        if self._poly is not None:
            return tuple(self._poly)

    def getscreen(self):
        'Return the TurtleScreen object, the turtle is drawing  on.\n\n        No argument.\n\n        Return the TurtleScreen object, the turtle is drawing  on.\n        So TurtleScreen-methods can be called for that object.\n\n        Example (for a Turtle instance named turtle):\n        >>> ts = turtle.getscreen()\n        >>> ts\n        <turtle.TurtleScreen object at 0x0106B770>\n        >>> ts.bgcolor("pink")\n        '
        return self.screen

    def getturtle(self):
        "Return the Turtleobject itself.\n\n        No argument.\n\n        Only reasonable use: as a function to return the 'anonymous turtle':\n\n        Example:\n        >>> pet = getturtle()\n        >>> pet.fd(50)\n        >>> pet\n        <turtle.Turtle object at 0x0187D810>\n        >>> turtles()\n        [<turtle.Turtle object at 0x0187D810>]\n        "
        return self

    getpen = getturtle

    def _delay(self, delay=None):
        "Set delay value which determines speed of turtle animation.\n        "
        return self.screen.delay(delay)

    def onclick(self, fun, btn=1, add=None):
        "Bind fun to mouse-click event on this turtle on canvas.\n\n        Arguments:\n        fun --  a function with two arguments, to which will be assigned\n                the coordinates of the clicked point on the canvas.\n        btn --  number of the mouse-button defaults to 1 (left mouse button).\n        add --  True or False. If True, new binding will be added, otherwise\n                it will replace a former binding.\n\n        Example for the anonymous turtle, i. e. the procedural way:\n\n        >>> def turn(x, y):\n        ...     left(360)\n        ...\n        >>> onclick(turn)  # Now clicking into the turtle will turn it.\n        >>> onclick(None)  # event-binding will be removed\n        "
        self.screen._onclick(self.turtle._item, fun, btn, add)
        self._update()

    def onrelease(self, fun, btn=1, add=None):
        'Bind fun to mouse-button-release event on this turtle on canvas.\n\n        Arguments:\n        fun -- a function with two arguments, to which will be assigned\n                the coordinates of the clicked point on the canvas.\n        btn --  number of the mouse-button defaults to 1 (left mouse button).\n\n        Example (for a MyTurtle instance named joe):\n        >>> class MyTurtle(Turtle):\n        ...     def glow(self,x,y):\n        ...             self.fillcolor("red")\n        ...     def unglow(self,x,y):\n        ...             self.fillcolor("")\n        ...\n        >>> joe = MyTurtle()\n        >>> joe.onclick(joe.glow)\n        >>> joe.onrelease(joe.unglow)\n\n        Clicking on joe turns fillcolor red, unclicking turns it to\n        transparent.\n        '
        self.screen._onrelease(self.turtle._item, fun, btn, add)
        self._update()

    def ondrag(self, fun, btn=1, add=None):
        "Bind fun to mouse-move event on this turtle on canvas.\n\n        Arguments:\n        fun -- a function with two arguments, to which will be assigned\n               the coordinates of the clicked point on the canvas.\n        btn -- number of the mouse-button defaults to 1 (left mouse button).\n\n        Every sequence of mouse-move-events on a turtle is preceded by a\n        mouse-click event on that turtle.\n\n        Example (for a Turtle instance named turtle):\n        >>> turtle.ondrag(turtle.goto)\n\n        Subsequently clicking and dragging a Turtle will move it\n        across the screen thereby producing handdrawings (if pen is\n        down).\n        "
        self.screen._ondrag(self.turtle._item, fun, btn, add)

    def _undo(self, action, data):
        "Does the main part of the work for undo()\n        "
        if self.undobuffer is None:
            return
        if action == "rot":
            (angle, degPAU) = data
            self._rotate((((-angle) * degPAU) / self._degreesPerAU))
            dummy = self.undobuffer.pop()
        elif action == "stamp":
            stitem = data[0]
            self.clearstamp(stitem)
        elif action == "go":
            self._undogoto(data)
        elif action in ["wri", "dot"]:
            item = data[0]
            self.screen._delete(item)
            self.items.remove(item)
        elif action == "dofill":
            item = data[0]
            self.screen._drawpoly(item, ((0, 0), (0, 0), (0, 0)), fill="", outline="")
        elif action == "beginfill":
            item = data[0]
            self._fillitem = self._fillpath = None
            if item in self.items:
                self.screen._delete(item)
                self.items.remove(item)
        elif action == "pen":
            TPen.pen(self, data[0])
            self.undobuffer.pop()

    def undo(self):
        "undo (repeatedly) the last turtle action.\n\n        No argument.\n\n        undo (repeatedly) the last turtle action.\n        Number of available undo actions is determined by the size of\n        the undobuffer.\n\n        Example (for a Turtle instance named turtle):\n        >>> for i in range(4):\n        ...     turtle.fd(50); turtle.lt(80)\n        ...\n        >>> for i in range(8):\n        ...     turtle.undo()\n        ...\n        "
        if self.undobuffer is None:
            return
        item = self.undobuffer.pop()
        action = item[0]
        data = item[1:]
        if action == "seq":
            while data:
                item = data.pop()
                self._undo(item[0], item[1:])
        else:
            self._undo(action, data)

    turtlesize = shapesize


RawPen = RawTurtle


def Screen():
    "Return the singleton screen object.\n    If none exists at the moment, create a new one and return it,\n    else return the existing one."
    if Turtle._screen is None:
        Turtle._screen = _Screen()
    return Turtle._screen


class _Screen(TurtleScreen):
    _root = None
    _canvas = None
    _title = _CFG["title"]

    def __init__(self):
        if _Screen._root is None:
            _Screen._root = self._root = _Root()
            self._root.title(_Screen._title)
            self._root.ondestroy(self._destroy)
        if _Screen._canvas is None:
            width = _CFG["width"]
            height = _CFG["height"]
            canvwidth = _CFG["canvwidth"]
            canvheight = _CFG["canvheight"]
            leftright = _CFG["leftright"]
            topbottom = _CFG["topbottom"]
            self._root.setupcanvas(width, height, canvwidth, canvheight)
            _Screen._canvas = self._root._getcanvas()
            TurtleScreen.__init__(self, _Screen._canvas)
            self.setup(width, height, leftright, topbottom)

    def setup(
        self,
        width=_CFG["width"],
        height=_CFG["height"],
        startx=_CFG["leftright"],
        starty=_CFG["topbottom"],
    ):
        " Set the size and position of the main window.\n\n        Arguments:\n        width: as integer a size in pixels, as float a fraction of the screen.\n          Default is 50% of screen.\n        height: as integer the height in pixels, as float a fraction of the\n          screen. Default is 75% of screen.\n        startx: if positive, starting position in pixels from the left\n          edge of the screen, if negative from the right edge\n          Default, startx=None is to center window horizontally.\n        starty: if positive, starting position in pixels from the top\n          edge of the screen, if negative from the bottom edge\n          Default, starty=None is to center window vertically.\n\n        Examples (for a Screen instance named screen):\n        >>> screen.setup (width=200, height=200, startx=0, starty=0)\n\n        sets window to 200x200 pixels, in upper left of screen\n\n        >>> screen.setup(width=.75, height=0.5, startx=None, starty=None)\n\n        sets window to 75% of screen by 50% of screen and centers\n        "
        if not hasattr(self._root, "set_geometry"):
            return
        sw = self._root.win_width()
        sh = self._root.win_height()
        if isinstance(width, float) and (0 <= width <= 1):
            width = sw * width
        if startx is None:
            startx = (sw - width) / 2
        if isinstance(height, float) and (0 <= height <= 1):
            height = sh * height
        if starty is None:
            starty = (sh - height) / 2
        self._root.set_geometry(width, height, startx, starty)
        self.update()

    def title(self, titlestring):
        'Set title of turtle-window\n\n        Argument:\n        titlestring -- a string, to appear in the titlebar of the\n                       turtle graphics window.\n\n        This is a method of Screen-class. Not available for TurtleScreen-\n        objects.\n\n        Example (for a Screen instance named screen):\n        >>> screen.title("Welcome to the turtle-zoo!")\n        '
        if _Screen._root is not None:
            _Screen._root.title(titlestring)
        _Screen._title = titlestring

    def _destroy(self):
        root = self._root
        if root is _Screen._root:
            Turtle._pen = None
            Turtle._screen = None
            _Screen._root = None
            _Screen._canvas = None
        TurtleScreen._RUNNING = False
        root.destroy()

    def bye(self):
        "Shut the turtlegraphics window.\n\n        Example (for a TurtleScreen instance named screen):\n        >>> screen.bye()\n        "
        self._destroy()

    def exitonclick(self):
        'Go into mainloop until the mouse is clicked.\n\n        No arguments.\n\n        Bind bye() method to mouseclick on TurtleScreen.\n        If "using_IDLE" - value in configuration dictionary is False\n        (default value), enter mainloop.\n        If IDLE with -n switch (no subprocess) is used, this value should be\n        set to True in turtle.cfg. In this case IDLE\'s mainloop\n        is active also for the client script.\n\n        This is a method of the Screen-class and not available for\n        TurtleScreen instances.\n\n        Example (for a Screen instance named screen):\n        >>> screen.exitonclick()\n\n        '

        def exitGracefully(x, y):
            "Screen.bye() with two dummy-parameters"
            self.bye()

        self.onclick(exitGracefully)
        if _CFG["using_IDLE"]:
            return
        try:
            mainloop()
        except AttributeError:
            exit(0)


class Turtle(RawTurtle):
    "RawTurtle auto-creating (scrolled) canvas.\n\n    When a Turtle object is created or a function derived from some\n    Turtle method is called a TurtleScreen object is automatically created.\n    "
    _pen = None
    _screen = None

    def __init__(
        self,
        shape=_CFG["shape"],
        undobuffersize=_CFG["undobuffersize"],
        visible=_CFG["visible"],
    ):
        if Turtle._screen is None:
            Turtle._screen = Screen()
        RawTurtle.__init__(
            self,
            Turtle._screen,
            shape=shape,
            undobuffersize=undobuffersize,
            visible=visible,
        )


Pen = Turtle


def write_docstringdict(filename="turtle_docstringdict"):
    "Create and write docstring-dictionary to file.\n\n    Optional argument:\n    filename -- a string, used as filename\n                default value is turtle_docstringdict\n\n    Has to be called explicitly, (not used by the turtle-graphics classes)\n    The docstring dictionary will be written to the Python script <filname>.py\n    It is intended to serve as a template for translation of the docstrings\n    into different languages.\n    "
    docsdict = {}
    for methodname in _tg_screen_functions:
        key = "_Screen." + methodname
        docsdict[key] = eval(key).__doc__
    for methodname in _tg_turtle_functions:
        key = "Turtle." + methodname
        docsdict[key] = eval(key).__doc__
    with open(("%s.py" % filename), "w") as f:
        keys = sorted((x for x in docsdict if (x.split(".")[1] not in _alias_list)))
        f.write("docsdict = {\n\n")
        for key in keys[:(-1)]:
            f.write(("%s :\n" % repr(key)))
            f.write(('        """%s\n""",\n\n' % docsdict[key]))
        key = keys[(-1)]
        f.write(("%s :\n" % repr(key)))
        f.write(('        """%s\n"""\n\n' % docsdict[key]))
        f.write("}\n")
        f.close()


def read_docstrings(lang):
    "Read in docstrings from lang-specific docstring dictionary.\n\n    Transfer docstrings, translated to lang, from a dictionary-file\n    to the methods of classes Screen and Turtle and - in revised form -\n    to the corresponding functions.\n    "
    modname = "turtle_docstringdict_%(language)s" % {"language": lang.lower()}
    module = __import__(modname)
    docsdict = module.docsdict
    for key in docsdict:
        try:
            eval(key).__doc__ = docsdict[key]
        except Exception:
            print(("Bad docstring-entry: %s" % key))


_LANGUAGE = _CFG["language"]
try:
    if _LANGUAGE != "english":
        read_docstrings(_LANGUAGE)
except ImportError:
    print("Cannot find docsdict for", _LANGUAGE)
except Exception:
    print(("Unknown Error when trying to import %s-docstring-dictionary" % _LANGUAGE))


def getmethparlist(ob):
    'Get strings describing the arguments for the given object\n\n    Returns a pair of strings representing function parameter lists\n    including parenthesis.  The first string is suitable for use in\n    function definition and the second is suitable for use in function\n    call.  The "self" parameter is not included.\n    '
    defText = callText = ""
    (args, varargs, varkw) = inspect.getargs(ob.__code__)
    items2 = args[1:]
    realArgs = args[1:]
    defaults = ob.__defaults__ or []
    defaults = [("=%r" % (value,)) for value in defaults]
    defaults = ([""] * (len(realArgs) - len(defaults))) + defaults
    items1 = [(arg + dflt) for (arg, dflt) in zip(realArgs, defaults)]
    if varargs is not None:
        items1.append(("*" + varargs))
        items2.append(("*" + varargs))
    if varkw is not None:
        items1.append(("**" + varkw))
        items2.append(("**" + varkw))
    defText = ", ".join(items1)
    defText = "(%s)" % defText
    callText = ", ".join(items2)
    callText = "(%s)" % callText
    return (defText, callText)


def _turtle_docrevise(docstr):
    "To reduce docstrings from RawTurtle class for functions\n    "
    import re

    if docstr is None:
        return None
    turtlename = _CFG["exampleturtle"]
    newdocstr = docstr.replace(("%s." % turtlename), "")
    parexp = re.compile((" \\(.+ %s\\):" % turtlename))
    newdocstr = parexp.sub(":", newdocstr)
    return newdocstr


def _screen_docrevise(docstr):
    "To reduce docstrings from TurtleScreen class for functions\n    "
    import re

    if docstr is None:
        return None
    screenname = _CFG["examplescreen"]
    newdocstr = docstr.replace(("%s." % screenname), "")
    parexp = re.compile((" \\(.+ %s\\):" % screenname))
    newdocstr = parexp.sub(":", newdocstr)
    return newdocstr


__func_body = "def {name}{paramslist}:\n    if {obj} is None:\n        if not TurtleScreen._RUNNING:\n            TurtleScreen._RUNNING = True\n            raise Terminator\n        {obj} = {init}\n    try:\n        return {obj}.{name}{argslist}\n    except TK.TclError:\n        if not TurtleScreen._RUNNING:\n            TurtleScreen._RUNNING = True\n            raise Terminator\n        raise\n"


def _make_global_funcs(functions, cls, obj, init, docrevise):
    for methodname in functions:
        method = getattr(cls, methodname)
        (pl1, pl2) = getmethparlist(method)
        if pl1 == "":
            print(">>>>>>", pl1, pl2)
            continue
        defstr = __func_body.format(
            obj=obj, init=init, name=methodname, paramslist=pl1, argslist=pl2
        )
        exec(defstr, globals())
        globals()[methodname].__doc__ = docrevise(method.__doc__)


_make_global_funcs(
    _tg_screen_functions, _Screen, "Turtle._screen", "Screen()", _screen_docrevise
)
_make_global_funcs(
    _tg_turtle_functions, Turtle, "Turtle._pen", "Turtle()", _turtle_docrevise
)
done = mainloop
if __name__ == "__main__":

    def switchpen():
        if isdown():
            pu()
        else:
            pd()

    def demo1():
        "Demo of old turtle.py - module"
        reset()
        tracer(True)
        up()
        backward(100)
        down()
        width(3)
        for i in range(3):
            if i == 2:
                begin_fill()
            for _ in range(4):
                forward(20)
                left(90)
            if i == 2:
                color("maroon")
                end_fill()
            up()
            forward(30)
            down()
        width(1)
        color("black")
        tracer(False)
        up()
        right(90)
        forward(100)
        right(90)
        forward(100)
        right(180)
        down()
        write("startstart", 1)
        write("start", 1)
        color("red")
        for i in range(5):
            forward(20)
            left(90)
            forward(20)
            right(90)
        tracer(True)
        begin_fill()
        for i in range(5):
            forward(20)
            left(90)
            forward(20)
            right(90)
        end_fill()

    def demo2():
        "Demo of some new features."
        speed(1)
        st()
        pensize(3)
        setheading(towards(0, 0))
        radius = distance(0, 0) / 2.0
        rt(90)
        for _ in range(18):
            switchpen()
            circle(radius, 10)
        write("wait a moment...")
        while undobufferentries():
            undo()
        reset()
        lt(90)
        colormode(255)
        laenge = 10
        pencolor("green")
        pensize(3)
        lt(180)
        for i in range((-2), 16):
            if i > 0:
                begin_fill()
                fillcolor((255 - (15 * i)), 0, (15 * i))
            for _ in range(3):
                fd(laenge)
                lt(120)
            end_fill()
            laenge += 10
            lt(15)
            speed(((speed() + 1) % 12))
        lt(120)
        pu()
        fd(70)
        rt(30)
        pd()
        color("red", "yellow")
        speed(0)
        begin_fill()
        for _ in range(4):
            circle(50, 90)
            rt(90)
            fd(30)
            rt(90)
        end_fill()
        lt(90)
        pu()
        fd(30)
        pd()
        shape("turtle")
        tri = getturtle()
        tri.resizemode("auto")
        turtle = Turtle()
        turtle.resizemode("auto")
        turtle.shape("turtle")
        turtle.reset()
        turtle.left(90)
        turtle.speed(0)
        turtle.up()
        turtle.goto(280, 40)
        turtle.lt(30)
        turtle.down()
        turtle.speed(6)
        turtle.color("blue", "orange")
        turtle.pensize(2)
        tri.speed(6)
        setheading(towards(turtle))
        count = 1
        while tri.distance(turtle) > 4:
            turtle.fd(3.5)
            turtle.lt(0.6)
            tri.setheading(tri.towards(turtle))
            tri.fd(4)
            if (count % 20) == 0:
                turtle.stamp()
                tri.stamp()
                switchpen()
            count += 1
        tri.write("CAUGHT! ", font=("Arial", 16, "bold"), align="right")
        tri.pencolor("black")
        tri.pencolor("red")

        def baba(xdummy, ydummy):
            clearscreen()
            bye()

        time.sleep(2)
        while undobufferentries():
            tri.undo()
            turtle.undo()
        tri.fd(50)
        tri.write("  Click me!", font=("Courier", 12, "bold"))
        tri.onclick(baba, 1)

    demo1()
    demo2()
    exitonclick()
