"Grep dialog for Find in Files functionality.\n\n   Inherits from SearchDialogBase for GUI and uses searchengine\n   to prepare search pattern.\n"
import fnmatch
import os
import sys
from tkinter import StringVar, BooleanVar
from tkinter.ttk import Checkbutton
from idlelib.searchbase import SearchDialogBase
from idlelib import searchengine


def grep(text, io=None, flist=None):
    "Open the Find in Files dialog.\n\n    Module-level function to access the singleton GrepDialog\n    instance and open the dialog.  If text is selected, it is\n    used as the search phrase; otherwise, the previous entry\n    is used.\n\n    Args:\n        text: Text widget that contains the selected text for\n              default search phrase.\n        io: iomenu.IOBinding instance with default path to search.\n        flist: filelist.FileList instance for OutputWindow parent.\n    "
    root = text._root()
    engine = searchengine.get(root)
    if not hasattr(engine, "_grepdialog"):
        engine._grepdialog = GrepDialog(root, engine, flist)
    dialog = engine._grepdialog
    searchphrase = text.get("sel.first", "sel.last")
    dialog.open(text, searchphrase, io)


def walk_error(msg):
    "Handle os.walk error."
    print(msg)


def findfiles(folder, pattern, recursive):
    "Generate file names in dir that match pattern.\n\n    Args:\n        folder: Root directory to search.\n        pattern: File pattern to match.\n        recursive: True to include subdirectories.\n    "
    for (dirpath, _, filenames) in os.walk(folder, onerror=walk_error):
        (
            yield from (
                os.path.join(dirpath, name)
                for name in filenames
                if fnmatch.fnmatch(name, pattern)
            )
        )
        if not recursive:
            break


class GrepDialog(SearchDialogBase):
    "Dialog for searching multiple files."
    title = "Find in Files Dialog"
    icon = "Grep"
    needwrapbutton = 0

    def __init__(self, root, engine, flist):
        "Create search dialog for searching for a phrase in the file system.\n\n        Uses SearchDialogBase as the basis for the GUI and a\n        searchengine instance to prepare the search.\n\n        Attributes:\n            flist: filelist.Filelist instance for OutputWindow parent.\n            globvar: String value of Entry widget for path to search.\n            globent: Entry widget for globvar.  Created in\n                create_entries().\n            recvar: Boolean value of Checkbutton widget for\n                traversing through subdirectories.\n        "
        super().__init__(root, engine)
        self.flist = flist
        self.globvar = StringVar(root)
        self.recvar = BooleanVar(root)

    def open(self, text, searchphrase, io=None):
        "Make dialog visible on top of others and ready to use.\n\n        Extend the SearchDialogBase open() to set the initial value\n        for globvar.\n\n        Args:\n            text: Multicall object containing the text information.\n            searchphrase: String phrase to search.\n            io: iomenu.IOBinding instance containing file path.\n        "
        SearchDialogBase.open(self, text, searchphrase)
        if io:
            path = io.filename or ""
        else:
            path = ""
        (dir, base) = os.path.split(path)
        (head, tail) = os.path.splitext(base)
        if not tail:
            tail = ".py"
        self.globvar.set(os.path.join(dir, ("*" + tail)))

    def create_entries(self):
        "Create base entry widgets and add widget for search path."
        SearchDialogBase.create_entries(self)
        self.globent = self.make_entry("In files:", self.globvar)[0]

    def create_other_buttons(self):
        "Add check button to recurse down subdirectories."
        btn = Checkbutton(
            self.make_frame()[0],
            variable=self.recvar,
            text="Recurse down subdirectories",
        )
        btn.pack(side="top", fill="both")

    def create_command_buttons(self):
        "Create base command buttons and add button for Search Files."
        SearchDialogBase.create_command_buttons(self)
        self.make_button("Search Files", self.default_command, isdef=True)

    def default_command(self, event=None):
        "Grep for search pattern in file path. The default command is bound\n        to <Return>.\n\n        If entry values are populated, set OutputWindow as stdout\n        and perform search.  The search dialog is closed automatically\n        when the search begins.\n        "
        prog = self.engine.getprog()
        if not prog:
            return
        path = self.globvar.get()
        if not path:
            self.top.bell()
            return
        from idlelib.outwin import OutputWindow

        save = sys.stdout
        try:
            sys.stdout = OutputWindow(self.flist)
            self.grep_it(prog, path)
        finally:
            sys.stdout = save

    def grep_it(self, prog, path):
        "Search for prog within the lines of the files in path.\n\n        For the each file in the path directory, open the file and\n        search each line for the matching pattern.  If the pattern is\n        found,  write the file and line information to stdout (which\n        is an OutputWindow).\n\n        Args:\n            prog: The compiled, cooked search pattern.\n            path: String containing the search path.\n        "
        (folder, filepat) = os.path.split(path)
        if not folder:
            folder = os.curdir
        filelist = sorted(findfiles(folder, filepat, self.recvar.get()))
        self.close()
        pat = self.engine.getpat()
        print(f"Searching {pat!r} in {path} ...")
        hits = 0
        try:
            for fn in filelist:
                try:
                    with open(fn, errors="replace") as f:
                        for (lineno, line) in enumerate(f, 1):
                            if line[(-1):] == "\n":
                                line = line[:(-1)]
                            if prog.search(line):
                                sys.stdout.write(
                                    f"""{fn}: {lineno}: {line}
"""
                                )
                                hits += 1
                except OSError as msg:
                    print(msg)
            print(
                (
                    f"""Hits found: {hits}
(Hint: right-click to open locations.)"""
                    if hits
                    else "No hits."
                )
            )
        except AttributeError:
            pass


def _grep_dialog(parent):
    from tkinter import Toplevel, Text, SEL, END
    from tkinter.ttk import Frame, Button
    from idlelib.pyshell import PyShellFileList

    top = Toplevel(parent)
    top.title("Test GrepDialog")
    (x, y) = map(int, parent.geometry().split("+")[1:])
    top.geometry(f"+{x}+{(y + 175)}")
    flist = PyShellFileList(top)
    frame = Frame(top)
    frame.pack()
    text = Text(frame, height=5)
    text.pack()

    def show_grep_dialog():
        text.tag_add(SEL, "1.0", END)
        grep(text, flist=flist)
        text.tag_remove(SEL, "1.0", END)

    button = Button(frame, text="Show GrepDialog", command=show_grep_dialog)
    button.pack()


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_grep", verbosity=2, exit=False)
    from idlelib.idle_test.htest import run

    run(_grep_dialog)
