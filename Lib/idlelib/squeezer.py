'An IDLE extension to avoid having very long texts printed in the shell.\n\nA common problem in IDLE\'s interactive shell is printing of large amounts of\ntext into the shell. This makes looking at the previous history difficult.\nWorse, this can cause IDLE to become very slow, even to the point of being\ncompletely unusable.\n\nThis extension will automatically replace long texts with a small button.\nDouble-clicking this button will remove it and insert the original text instead.\nMiddle-clicking will copy the text to the clipboard. Right-clicking will open\nthe text in a separate viewing window.\n\nAdditionally, any output can be manually "squeezed" by the user. This includes\noutput written to the standard error stream ("stderr"), such as exception\nmessages and their tracebacks.\n'
import re
import tkinter as tk
from tkinter import messagebox
from idlelib.config import idleConf
from idlelib.textview import view_text
from idlelib.tooltip import Hovertip
from idlelib import macosx


def count_lines_with_wrapping(s, linewidth=80):
    "Count the number of lines in a given string.\n\n    Lines are counted as if the string was wrapped so that lines are never over\n    linewidth characters long.\n\n    Tabs are considered tabwidth characters long.\n    "
    tabwidth = 8
    pos = 0
    linecount = 1
    current_column = 0
    for m in re.finditer("[\\t\\n]", s):
        numchars = m.start() - pos
        pos += numchars
        current_column += numchars
        if s[pos] == "\n":
            if current_column > linewidth:
                linecount += (current_column - 1) // linewidth
            linecount += 1
            current_column = 0
        else:
            assert s[pos] == "\t"
            current_column += tabwidth - (current_column % tabwidth)
            if current_column > linewidth:
                linecount += 1
                current_column = tabwidth
        pos += 1
    current_column += len(s) - pos
    if current_column > 0:
        linecount += (current_column - 1) // linewidth
    else:
        linecount -= 1
    return linecount


class ExpandingButton(tk.Button):
    'Class for the "squeezed" text buttons used by Squeezer\n\n    These buttons are displayed inside a Tk Text widget in place of text. A\n    user can then use the button to replace it with the original text, copy\n    the original text to the clipboard or view the original text in a separate\n    window.\n\n    Each button is tied to a Squeezer instance, and it knows to update the\n    Squeezer instance when it is expanded (and therefore removed).\n    '

    def __init__(self, s, tags, numoflines, squeezer):
        self.s = s
        self.tags = tags
        self.numoflines = numoflines
        self.squeezer = squeezer
        self.editwin = editwin = squeezer.editwin
        self.text = text = editwin.text
        self.base_text = editwin.per.bottom
        line_plurality = "lines" if (numoflines != 1) else "line"
        button_text = f"Squeezed text ({numoflines} {line_plurality})."
        tk.Button.__init__(
            self,
            text,
            text=button_text,
            background="#FFFFC0",
            activebackground="#FFFFE0",
        )
        button_tooltip_text = "Double-click to expand, right-click for more options."
        Hovertip(self, button_tooltip_text, hover_delay=80)
        self.bind("<Double-Button-1>", self.expand)
        if macosx.isAquaTk():
            self.bind("<Button-2>", self.context_menu_event)
        else:
            self.bind("<Button-3>", self.context_menu_event)
        self.selection_handle(
            (lambda offset, length: s[int(offset) : (int(offset) + int(length))])
        )
        self.is_dangerous = None
        self.after_idle(self.set_is_dangerous)

    def set_is_dangerous(self):
        dangerous_line_len = 50 * self.text.winfo_width()
        self.is_dangerous = (
            (self.numoflines > 1000)
            or (len(self.s) > 50000)
            or any(
                (
                    (len(line_match.group(0)) >= dangerous_line_len)
                    for line_match in re.finditer("[^\\n]+", self.s)
                )
            )
        )

    def expand(self, event=None):
        "expand event handler\n\n        This inserts the original text in place of the button in the Text\n        widget, removes the button and updates the Squeezer instance.\n\n        If the original text is dangerously long, i.e. expanding it could\n        cause a performance degradation, ask the user for confirmation.\n        "
        if self.is_dangerous is None:
            self.set_is_dangerous()
        if self.is_dangerous:
            confirm = messagebox.askokcancel(
                title="Expand huge output?",
                message=(
                    "\n\n".join(
                        [
                            "The squeezed output is very long: %d lines, %d chars.",
                            "Expanding it could make IDLE slow or unresponsive.",
                            "It is recommended to view or copy the output instead.",
                            "Really expand?",
                        ]
                    )
                    % (self.numoflines, len(self.s))
                ),
                default=messagebox.CANCEL,
                parent=self.text,
            )
            if not confirm:
                return "break"
        self.base_text.insert(self.text.index(self), self.s, self.tags)
        self.base_text.delete(self)
        self.squeezer.expandingbuttons.remove(self)

    def copy(self, event=None):
        "copy event handler\n\n        Copy the original text to the clipboard.\n        "
        self.clipboard_clear()
        self.clipboard_append(self.s)

    def view(self, event=None):
        "view event handler\n\n        View the original text in a separate text viewer window.\n        "
        view_text(self.text, "Squeezed Output Viewer", self.s, modal=False, wrap="none")

    rmenu_specs = (("copy", "copy"), ("view", "view"))

    def context_menu_event(self, event):
        self.text.mark_set("insert", ("@%d,%d" % (event.x, event.y)))
        rmenu = tk.Menu(self.text, tearoff=0)
        for (label, method_name) in self.rmenu_specs:
            rmenu.add_command(label=label, command=getattr(self, method_name))
        rmenu.tk_popup(event.x_root, event.y_root)
        return "break"


class Squeezer:
    "Replace long outputs in the shell with a simple button.\n\n    This avoids IDLE's shell slowing down considerably, and even becoming\n    completely unresponsive, when very long outputs are written.\n    "

    @classmethod
    def reload(cls):
        "Load class variables from config."
        cls.auto_squeeze_min_lines = idleConf.GetOption(
            "main", "PyShell", "auto-squeeze-min-lines", type="int", default=50
        )

    def __init__(self, editwin):
        "Initialize settings for Squeezer.\n\n        editwin is the shell's Editor window.\n        self.text is the editor window text widget.\n        self.base_test is the actual editor window Tk text widget, rather than\n            EditorWindow's wrapper.\n        self.expandingbuttons is the list of all buttons representing\n            \"squeezed\" output.\n        "
        self.editwin = editwin
        self.text = text = editwin.text
        self.base_text = editwin.per.bottom
        self.window_width_delta = 2 * (
            int(text.cget("border")) + int(text.cget("padx"))
        )
        self.expandingbuttons = []

        def mywrite(s, tags=(), write=editwin.write):
            if tags != "stdout":
                return write(s, tags)
            auto_squeeze_min_lines = self.auto_squeeze_min_lines
            if len(s) < auto_squeeze_min_lines:
                return write(s, tags)
            numoflines = self.count_lines(s)
            if numoflines < auto_squeeze_min_lines:
                return write(s, tags)
            expandingbutton = ExpandingButton(s, tags, numoflines, self)
            text.mark_gravity("iomark", tk.RIGHT)
            text.window_create("iomark", window=expandingbutton, padx=3, pady=5)
            text.see("iomark")
            text.update()
            text.mark_gravity("iomark", tk.LEFT)
            self.expandingbuttons.append(expandingbutton)

        editwin.write = mywrite

    def count_lines(self, s):
        "Count the number of lines in a given text.\n\n        Before calculation, the tab width and line length of the text are\n        fetched, so that up-to-date values are used.\n\n        Lines are counted as if the string was wrapped so that lines are never\n        over linewidth characters long.\n\n        Tabs are considered tabwidth characters long.\n        "
        return count_lines_with_wrapping(s, self.editwin.width)

    def squeeze_current_text_event(self, event):
        'squeeze-current-text event handler\n\n        Squeeze the block of text inside which contains the "insert" cursor.\n\n        If the insert cursor is not in a squeezable block of text, give the\n        user a small warning and do nothing.\n        '
        tag_names = self.text.tag_names(tk.INSERT)
        for tag_name in ("stdout", "stderr"):
            if tag_name in tag_names:
                break
        else:
            self.text.bell()
            return "break"
        (start, end) = self.text.tag_prevrange(tag_name, (tk.INSERT + "+1c"))
        s = self.text.get(start, end)
        if (len(s) > 0) and (s[(-1)] == "\n"):
            end = self.text.index(("%s-1c" % end))
            s = s[:(-1)]
        self.base_text.delete(start, end)
        numoflines = self.count_lines(s)
        expandingbutton = ExpandingButton(s, tag_name, numoflines, self)
        self.text.window_create(start, window=expandingbutton, padx=3, pady=5)
        i = len(self.expandingbuttons)
        while (i > 0) and self.text.compare(
            self.expandingbuttons[(i - 1)], ">", expandingbutton
        ):
            i -= 1
        self.expandingbuttons.insert(i, expandingbutton)
        return "break"


Squeezer.reload()
if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_squeezer", verbosity=2, exit=False)
