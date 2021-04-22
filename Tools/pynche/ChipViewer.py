"Chip viewer and widget.\n\nIn the lower left corner of the main Pynche window, you will see two\nChipWidgets, one for the selected color and one for the nearest color.  The\nselected color is the actual RGB value expressed as an X11 #COLOR name. The\nnearest color is the named color from the X11 database that is closest to the\nselected color in 3D space.  There may be other colors equally close, but the\nnearest one is the first one found.\n\nClicking on the nearest color chip selects that named color.\n\nThe ChipViewer class includes the entire lower left quandrant; i.e. both the\nselected and nearest ChipWidgets.\n"
from tkinter import *
import ColorDB


class ChipWidget:
    _WIDTH = 150
    _HEIGHT = 80

    def __init__(
        self,
        master=None,
        width=_WIDTH,
        height=_HEIGHT,
        text="Color",
        initialcolor="blue",
        presscmd=None,
        releasecmd=None,
    ):
        self.__label = Label(master, text=text)
        self.__label.grid(row=0, column=0)
        self.__chip = Frame(
            master,
            relief=RAISED,
            borderwidth=2,
            width=width,
            height=height,
            background=initialcolor,
        )
        self.__chip.grid(row=1, column=0)
        self.__namevar = StringVar()
        self.__namevar.set(initialcolor)
        self.__name = Entry(
            master,
            textvariable=self.__namevar,
            relief=FLAT,
            justify=CENTER,
            state=DISABLED,
            font=self.__label["font"],
        )
        self.__name.grid(row=2, column=0)
        self.__msgvar = StringVar()
        self.__name = Entry(
            master,
            textvariable=self.__msgvar,
            relief=FLAT,
            justify=CENTER,
            state=DISABLED,
            font=self.__label["font"],
        )
        self.__name.grid(row=3, column=0)
        if presscmd:
            self.__chip.bind("<ButtonPress-1>", presscmd)
        if releasecmd:
            self.__chip.bind("<ButtonRelease-1>", releasecmd)

    def set_color(self, color):
        self.__chip.config(background=color)

    def get_color(self):
        return self.__chip["background"]

    def set_name(self, colorname):
        self.__namevar.set(colorname)

    def set_message(self, message):
        self.__msgvar.set(message)

    def press(self):
        self.__chip.configure(relief=SUNKEN)

    def release(self):
        self.__chip.configure(relief=RAISED)


class ChipViewer:
    def __init__(self, switchboard, master=None):
        self.__sb = switchboard
        self.__frame = Frame(master, relief=RAISED, borderwidth=1)
        self.__frame.grid(row=3, column=0, ipadx=5, sticky="NSEW")
        self.__sframe = Frame(self.__frame)
        self.__sframe.grid(row=0, column=0)
        self.__selected = ChipWidget(self.__sframe, text="Selected")
        self.__nframe = Frame(self.__frame)
        self.__nframe.grid(row=0, column=1)
        self.__nearest = ChipWidget(
            self.__nframe,
            text="Nearest",
            presscmd=self.__buttonpress,
            releasecmd=self.__buttonrelease,
        )

    def update_yourself(self, red, green, blue):
        colordb = self.__sb.colordb()
        rgbtuple = (red, green, blue)
        rrggbb = ColorDB.triplet_to_rrggbb(rgbtuple)
        nearest = colordb.nearest(red, green, blue)
        nearest_tuple = colordb.find_byname(nearest)
        nearest_rrggbb = ColorDB.triplet_to_rrggbb(nearest_tuple)
        self.__selected.set_color(rrggbb)
        self.__nearest.set_color(nearest_rrggbb)
        self.__selected.set_name(rrggbb)
        if rrggbb == nearest_rrggbb:
            self.__selected.set_message(nearest)
        else:
            self.__selected.set_message("")
        self.__nearest.set_name(nearest_rrggbb)
        self.__nearest.set_message(nearest)

    def __buttonpress(self, event=None):
        self.__nearest.press()

    def __buttonrelease(self, event=None):
        self.__nearest.release()
        rrggbb = self.__nearest.get_color()
        (red, green, blue) = ColorDB.rrggbb_to_triplet(rrggbb)
        self.__sb.update_views(red, green, blue)
