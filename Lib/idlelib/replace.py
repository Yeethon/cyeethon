"Replace dialog for IDLE. Inherits SearchDialogBase for GUI.\nUses idlelib.searchengine.SearchEngine for search capability.\nDefines various replace related functions like replace, replace all,\nand replace+find.\n"
import re
from tkinter import StringVar, TclError
from idlelib.searchbase import SearchDialogBase
from idlelib import searchengine


def replace(text):
    "Create or reuse a singleton ReplaceDialog instance.\n\n    The singleton dialog saves user entries and preferences\n    across instances.\n\n    Args:\n        text: Text widget containing the text to be searched.\n    "
    root = text._root()
    engine = searchengine.get(root)
    if not hasattr(engine, "_replacedialog"):
        engine._replacedialog = ReplaceDialog(root, engine)
    dialog = engine._replacedialog
    dialog.open(text)


class ReplaceDialog(SearchDialogBase):
    "Dialog for finding and replacing a pattern in text."
    title = "Replace Dialog"
    icon = "Replace"

    def __init__(self, root, engine):
        "Create search dialog for finding and replacing text.\n\n        Uses SearchDialogBase as the basis for the GUI and a\n        searchengine instance to prepare the search.\n\n        Attributes:\n            replvar: StringVar containing 'Replace with:' value.\n            replent: Entry widget for replvar.  Created in\n                create_entries().\n            ok: Boolean used in searchengine.search_text to indicate\n                whether the search includes the selection.\n        "
        super().__init__(root, engine)
        self.replvar = StringVar(root)

    def open(self, text):
        "Make dialog visible on top of others and ready to use.\n\n        Also, highlight the currently selected text and set the\n        search to include the current selection (self.ok).\n\n        Args:\n            text: Text widget being searched.\n        "
        SearchDialogBase.open(self, text)
        try:
            first = text.index("sel.first")
        except TclError:
            first = None
        try:
            last = text.index("sel.last")
        except TclError:
            last = None
        first = first or text.index("insert")
        last = last or first
        self.show_hit(first, last)
        self.ok = True

    def create_entries(self):
        "Create base and additional label and text entry widgets."
        SearchDialogBase.create_entries(self)
        self.replent = self.make_entry("Replace with:", self.replvar)[0]

    def create_command_buttons(self):
        "Create base and additional command buttons.\n\n        The additional buttons are for Find, Replace,\n        Replace+Find, and Replace All.\n        "
        SearchDialogBase.create_command_buttons(self)
        self.make_button("Find", self.find_it)
        self.make_button("Replace", self.replace_it)
        self.make_button("Replace+Find", self.default_command, isdef=True)
        self.make_button("Replace All", self.replace_all)

    def find_it(self, event=None):
        "Handle the Find button."
        self.do_find(False)

    def replace_it(self, event=None):
        "Handle the Replace button.\n\n        If the find is successful, then perform replace.\n        "
        if self.do_find(self.ok):
            self.do_replace()

    def default_command(self, event=None):
        "Handle the Replace+Find button as the default command.\n\n        First performs a replace and then, if the replace was\n        successful, a find next.\n        "
        if self.do_find(self.ok):
            if self.do_replace():
                self.do_find(False)

    def _replace_expand(self, m, repl):
        "Expand replacement text if regular expression."
        if self.engine.isre():
            try:
                new = m.expand(repl)
            except re.error:
                self.engine.report_error(repl, "Invalid Replace Expression")
                new = None
        else:
            new = repl
        return new

    def replace_all(self, event=None):
        "Handle the Replace All button.\n\n        Search text for occurrences of the Find value and replace\n        each of them.  The 'wrap around' value controls the start\n        point for searching.  If wrap isn't set, then the searching\n        starts at the first occurrence after the current selection;\n        if wrap is set, the replacement starts at the first line.\n        The replacement is always done top-to-bottom in the text.\n        "
        prog = self.engine.getprog()
        if not prog:
            return
        repl = self.replvar.get()
        text = self.text
        res = self.engine.search_text(text, prog)
        if not res:
            self.bell()
            return
        text.tag_remove("sel", "1.0", "end")
        text.tag_remove("hit", "1.0", "end")
        line = res[0]
        col = res[1].start()
        if self.engine.iswrap():
            line = 1
            col = 0
        ok = True
        first = last = None
        text.undo_block_start()
        while True:
            res = self.engine.search_forward(text, prog, line, col, wrap=False, ok=ok)
            if not res:
                break
            (line, m) = res
            chars = text.get(("%d.0" % line), ("%d.0" % (line + 1)))
            orig = m.group()
            new = self._replace_expand(m, repl)
            if new is None:
                break
            (i, j) = m.span()
            first = "%d.%d" % (line, i)
            last = "%d.%d" % (line, j)
            if new == orig:
                text.mark_set("insert", last)
            else:
                text.mark_set("insert", first)
                if first != last:
                    text.delete(first, last)
                if new:
                    text.insert(first, new)
            col = i + len(new)
            ok = False
        text.undo_block_stop()
        if first and last:
            self.show_hit(first, last)
        self.close()

    def do_find(self, ok=False):
        "Search for and highlight next occurrence of pattern in text.\n\n        No text replacement is done with this option.\n        "
        if not self.engine.getprog():
            return False
        text = self.text
        res = self.engine.search_text(text, None, ok)
        if not res:
            self.bell()
            return False
        (line, m) = res
        (i, j) = m.span()
        first = "%d.%d" % (line, i)
        last = "%d.%d" % (line, j)
        self.show_hit(first, last)
        self.ok = True
        return True

    def do_replace(self):
        "Replace search pattern in text with replacement value."
        prog = self.engine.getprog()
        if not prog:
            return False
        text = self.text
        try:
            first = pos = text.index("sel.first")
            last = text.index("sel.last")
        except TclError:
            pos = None
        if not pos:
            first = last = pos = text.index("insert")
        (line, col) = searchengine.get_line_col(pos)
        chars = text.get(("%d.0" % line), ("%d.0" % (line + 1)))
        m = prog.match(chars, col)
        if not prog:
            return False
        new = self._replace_expand(m, self.replvar.get())
        if new is None:
            return False
        text.mark_set("insert", first)
        text.undo_block_start()
        if m.group():
            text.delete(first, last)
        if new:
            text.insert(first, new)
        text.undo_block_stop()
        self.show_hit(first, text.index("insert"))
        self.ok = False
        return True

    def show_hit(self, first, last):
        "Highlight text between first and last indices.\n\n        Text is highlighted via the 'hit' tag and the marked\n        section is brought into view.\n\n        The colors from the 'hit' tag aren't currently shown\n        when the text is displayed.  This is due to the 'sel'\n        tag being added first, so the colors in the 'sel'\n        config are seen instead of the colors for 'hit'.\n        "
        text = self.text
        text.mark_set("insert", first)
        text.tag_remove("sel", "1.0", "end")
        text.tag_add("sel", first, last)
        text.tag_remove("hit", "1.0", "end")
        if first == last:
            text.tag_add("hit", first)
        else:
            text.tag_add("hit", first, last)
        text.see("insert")
        text.update_idletasks()

    def close(self, event=None):
        "Close the dialog and remove hit tags."
        SearchDialogBase.close(self, event)
        self.text.tag_remove("hit", "1.0", "end")


def _replace_dialog(parent):
    from tkinter import Toplevel, Text, END, SEL
    from tkinter.ttk import Frame, Button

    top = Toplevel(parent)
    top.title("Test ReplaceDialog")
    (x, y) = map(int, parent.geometry().split("+")[1:])
    top.geometry(("+%d+%d" % (x, (y + 175))))

    def undo_block_start():
        pass

    def undo_block_stop():
        pass

    frame = Frame(top)
    frame.pack()
    text = Text(frame, inactiveselectbackground="gray")
    text.undo_block_start = undo_block_start
    text.undo_block_stop = undo_block_stop
    text.pack()
    text.insert("insert", "This is a sample sTring\nPlus MORE.")
    text.focus_set()

    def show_replace():
        text.tag_add(SEL, "1.0", END)
        replace(text)
        text.tag_remove(SEL, "1.0", END)

    button = Button(frame, text="Replace", command=show_replace)
    button.pack()


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_replace", verbosity=2, exit=False)
    from idlelib.idle_test.htest import run

    run(_replace_dialog)
