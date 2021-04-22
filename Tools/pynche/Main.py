"Pynche -- The PYthon Natural Color and Hue Editor.\n\nContact: %(AUTHNAME)s\nEmail:   %(AUTHEMAIL)s\nVersion: %(__version__)s\n\nPynche is based largely on a similar color editor I wrote years ago for the\nSunView window system.  That editor was called ICE: the Interactive Color\nEditor.  I'd always wanted to port the editor to X but didn't feel like\nhacking X and C code to do it.  Fast forward many years, to where Python +\nTkinter provides such a nice programming environment, with enough power, that\nI finally buckled down and implemented it.  I changed the name because these\ndays, too many other systems have the acronym `ICE'.\n\nThis program currently requires Python 2.2 with Tkinter.\n\nUsage: %(PROGRAM)s [-d file] [-i file] [-X] [-v] [-h] [initialcolor]\n\nWhere:\n    --database file\n    -d file\n        Alternate location of a color database file\n\n    --initfile file\n    -i file\n        Alternate location of the initialization file.  This file contains a\n        persistent database of the current Pynche options and color.  This\n        means that Pynche restores its option settings and current color when\n        it restarts, using this file (unless the -X option is used).  The\n        default is ~/.pynche\n\n    --ignore\n    -X\n        Ignore the initialization file when starting up.  Pynche will still\n        write the current option settings to this file when it quits.\n\n    --version\n    -v\n        print the version number and exit\n\n    --help\n    -h\n        print this message\n\n    initialcolor\n        initial color, as a color name or #RRGGBB format\n"
__version__ = "1.4.1"
import sys
import os
import getopt
import ColorDB
from PyncheWidget import PyncheWidget
from Switchboard import Switchboard
from StripViewer import StripViewer
from ChipViewer import ChipViewer
from TypeinViewer import TypeinViewer

PROGRAM = sys.argv[0]
AUTHNAME = "Barry Warsaw"
AUTHEMAIL = "barry@python.org"
RGB_TXT = [
    "/usr/openwin/lib/rgb.txt",
    "/usr/lib/X11/rgb.txt",
    os.path.join(sys.path[0], "X/rgb.txt"),
]


def docstring():
    return __doc__ % globals()


def usage(code, msg=""):
    print(docstring())
    if msg:
        print(msg)
    sys.exit(code)


def initial_color(s, colordb):
    def scan_color(s, colordb=colordb):
        try:
            (r, g, b) = colordb.find_byname(s)
        except ColorDB.BadColor:
            try:
                (r, g, b) = ColorDB.rrggbb_to_triplet(s)
            except ColorDB.BadColor:
                return (None, None, None)
        return (r, g, b)

    (r, g, b) = scan_color(s)
    if r is None:
        (r, g, b) = scan_color(("#" + s))
    if r is None:
        print("Bad initial color, using gray50:", s)
        (r, g, b) = scan_color("gray50")
    if r is None:
        usage(1, "Cannot find an initial color to use")
    return (r, g, b)


def build(master=None, initialcolor=None, initfile=None, ignore=None, dbfile=None):
    s = Switchboard(((not ignore) and initfile))
    if dbfile is None:
        dbfile = s.optiondb().get("DBFILE")
    colordb = None
    files = RGB_TXT[:]
    if dbfile is None:
        dbfile = files.pop()
    while colordb is None:
        try:
            colordb = ColorDB.get_colordb(dbfile)
        except (KeyError, IOError):
            pass
        if colordb is None:
            if not files:
                break
            dbfile = files.pop(0)
    if not colordb:
        usage(1, "No color database file found, see the -d option.")
    s.set_colordb(colordb)
    app = PyncheWidget(__version__, s, master=master)
    w = app.window()
    s.add_view(StripViewer(s, w))
    s.add_view(ChipViewer(s, w))
    s.add_view(TypeinViewer(s, w))
    if initialcolor is None:
        optiondb = s.optiondb()
        red = optiondb.get("RED")
        green = optiondb.get("GREEN")
        blue = optiondb.get("BLUE")
        if (red is None) or (blue is None) or (green is None):
            (red, green, blue) = initial_color("grey50", colordb)
    else:
        (red, green, blue) = initial_color(initialcolor, colordb)
    s.update_views(red, green, blue)
    return (app, s)


def run(app, s):
    try:
        app.start()
    except KeyboardInterrupt:
        pass


def main():
    try:
        (opts, args) = getopt.getopt(
            sys.argv[1:],
            "hd:i:Xv",
            ["database=", "initfile=", "ignore", "help", "version"],
        )
    except getopt.error as msg:
        usage(1, msg)
    if len(args) == 0:
        initialcolor = None
    elif len(args) == 1:
        initialcolor = args[0]
    else:
        usage(1)
    ignore = False
    dbfile = None
    initfile = os.path.expanduser("~/.pynche")
    for (opt, arg) in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-v", "--version"):
            print(
                (
                    "Pynche -- The PYthon Natural Color and Hue Editor.\nContact: %(AUTHNAME)s\nEmail:   %(AUTHEMAIL)s\nVersion: %(__version__)s"
                    % globals()
                )
            )
            sys.exit(0)
        elif opt in ("-d", "--database"):
            dbfile = arg
        elif opt in ("-X", "--ignore"):
            ignore = True
        elif opt in ("-i", "--initfile"):
            initfile = arg
    (app, sb) = build(
        initialcolor=initialcolor, initfile=initfile, ignore=ignore, dbfile=dbfile
    )
    run(app, sb)
    sb.save_views()


if __name__ == "__main__":
    main()
