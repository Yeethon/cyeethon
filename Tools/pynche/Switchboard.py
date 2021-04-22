"Switchboard class.\n\nThis class is used to coordinate updates among all Viewers.  Every Viewer must\nconform to the following interface:\n\n    - it must include a method called update_yourself() which takes three\n      arguments; the red, green, and blue values of the selected color.\n\n    - When a Viewer selects a color and wishes to update all other Views, it\n      should call update_views() on the Switchboard object.  Note that the\n      Viewer typically does *not* update itself before calling update_views(),\n      since this would cause it to get updated twice.\n\nOptionally, Viewers can also implement:\n\n    - save_options() which takes an optiondb (a dictionary).  Store into this\n      dictionary any values the Viewer wants to save in the persistent\n      ~/.pynche file.  This dictionary is saved using marshal.  The namespace\n      for the keys is ad-hoc; make sure you don't clobber some other Viewer's\n      keys!\n\n    - withdraw() which takes no arguments.  This is called when Pynche is\n      unmapped.  All Viewers should implement this.\n\n    - colordb_changed() which takes a single argument, an instance of\n      ColorDB.  This is called whenever the color name database is changed and\n      gives a chance for the Viewers to do something on those events.  See\n      ListViewer for details.\n\nExternal Viewers are found dynamically.  Viewer modules should have names such\nas FooViewer.py.  If such a named module has a module global variable called\nADDTOVIEW and this variable is true, the Viewer will be added dynamically to\nthe `View' menu.  ADDTOVIEW contains a string which is used as the menu item\nto display the Viewer (one kludge: if the string contains a `%', this is used\nto indicate that the next character will get an underline in the menu,\notherwise the first character is underlined).\n\nFooViewer.py should contain a class called FooViewer, and its constructor\nshould take two arguments, an instance of Switchboard, and optionally a Tk\nmaster window.\n\n"
import sys
import marshal


class Switchboard:
    def __init__(self, initfile):
        self.__initfile = initfile
        self.__colordb = None
        self.__optiondb = {}
        self.__views = []
        self.__red = 0
        self.__green = 0
        self.__blue = 0
        self.__canceled = 0
        fp = None
        if initfile:
            try:
                try:
                    fp = open(initfile, "rb")
                    self.__optiondb = marshal.load(fp)
                    if not isinstance(self.__optiondb, dict):
                        print(
                            "Problem reading options from file:",
                            initfile,
                            file=sys.stderr,
                        )
                        self.__optiondb = {}
                except (IOError, EOFError, ValueError):
                    pass
            finally:
                if fp:
                    fp.close()

    def add_view(self, view):
        self.__views.append(view)

    def update_views(self, red, green, blue):
        self.__red = red
        self.__green = green
        self.__blue = blue
        for v in self.__views:
            v.update_yourself(red, green, blue)

    def update_views_current(self):
        self.update_views(self.__red, self.__green, self.__blue)

    def current_rgb(self):
        return (self.__red, self.__green, self.__blue)

    def colordb(self):
        return self.__colordb

    def set_colordb(self, colordb):
        self.__colordb = colordb
        for v in self.__views:
            if hasattr(v, "colordb_changed"):
                v.colordb_changed(colordb)
        self.update_views_current()

    def optiondb(self):
        return self.__optiondb

    def save_views(self):
        self.__optiondb["RED"] = self.__red
        self.__optiondb["GREEN"] = self.__green
        self.__optiondb["BLUE"] = self.__blue
        for v in self.__views:
            if hasattr(v, "save_options"):
                v.save_options(self.__optiondb)
        self.__optiondb["DBFILE"] = self.__colordb.filename()
        fp = None
        try:
            try:
                fp = open(self.__initfile, "wb")
            except IOError:
                print("Cannot write options to file:", self.__initfile, file=sys.stderr)
            else:
                marshal.dump(self.__optiondb, fp)
        finally:
            if fp:
                fp.close()

    def withdraw_views(self):
        for v in self.__views:
            if hasattr(v, "withdraw"):
                v.withdraw()

    def canceled(self, flag=1):
        self.__canceled = flag

    def canceled_p(self):
        return self.__canceled
