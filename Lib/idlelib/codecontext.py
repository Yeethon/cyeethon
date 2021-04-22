"codecontext - display the block context above the edit window\n\nOnce code has scrolled off the top of a window, it can be difficult to\ndetermine which block you are in.  This extension implements a pane at the top\nof each IDLE edit window which provides block structure hints.  These hints are\nthe lines which contain the block opening keywords, e.g. 'if', for the\nenclosing block.  The number of hint lines is determined by the maxlines\nvariable in the codecontext section of config-extensions.def. Lines which do\nnot open blocks are not shown in the context hints pane.\n\nFor EditorWindows, <<toggle-code-context>> is bound to CodeContext(self).\ntoggle_code_context_event.\n"
import re
from sys import maxsize as INFINITY
from tkinter import Frame, Text, TclError
from tkinter.constants import NSEW, SUNKEN
from idlelib.config import idleConf

BLOCKOPENERS = {
    "class",
    "def",
    "if",
    "elif",
    "else",
    "while",
    "for",
    "try",
    "except",
    "finally",
    "with",
    "async",
}


def get_spaces_firstword(codeline, c=re.compile("^(\\s*)(\\w*)")):
    "Extract the beginning whitespace and first word from codeline."
    return c.match(codeline).groups()


def get_line_info(codeline):
    "Return tuple of (line indent value, codeline, block start keyword).\n\n    The indentation of empty lines (or comment lines) is INFINITY.\n    If the line does not start a block, the keyword value is False.\n    "
    (spaces, firstword) = get_spaces_firstword(codeline)
    indent = len(spaces)
    if (len(codeline) == indent) or (codeline[indent] == "#"):
        indent = INFINITY
    opener = (firstword in BLOCKOPENERS) and firstword
    return (indent, codeline, opener)


class CodeContext:
    "Display block context above the edit window."
    UPDATEINTERVAL = 100

    def __init__(self, editwin):
        "Initialize settings for context block.\n\n        editwin is the Editor window for the context block.\n        self.text is the editor window text widget.\n\n        self.context displays the code context text above the editor text.\n          Initially None, it is toggled via <<toggle-code-context>>.\n        self.topvisible is the number of the top text line displayed.\n        self.info is a list of (line number, indent level, line text,\n          block keyword) tuples for the block structure above topvisible.\n          self.info[0] is initialized with a 'dummy' line which\n          starts the toplevel 'block' of the module.\n\n        self.t1 and self.t2 are two timer events on the editor text widget to\n          monitor for changes to the context text or editor font.\n        "
        self.editwin = editwin
        self.text = editwin.text
        self._reset()

    def _reset(self):
        self.context = None
        self.cell00 = None
        self.t1 = None
        self.topvisible = 1
        self.info = [(0, (-1), "", False)]

    @classmethod
    def reload(cls):
        "Load class variables from config."
        cls.context_depth = idleConf.GetOption(
            "extensions", "CodeContext", "maxlines", type="int", default=15
        )

    def __del__(self):
        "Cancel scheduled events."
        if self.t1 is not None:
            try:
                self.text.after_cancel(self.t1)
            except TclError:
                pass
            self.t1 = None

    def toggle_code_context_event(self, event=None):
        "Toggle code context display.\n\n        If self.context doesn't exist, create it to match the size of the editor\n        window text (toggle on).  If it does exist, destroy it (toggle off).\n        Return 'break' to complete the processing of the binding.\n        "
        if self.context is None:
            widgets = (self.editwin.text, self.editwin.text_frame)
            padx = 0
            border = 0
            for widget in widgets:
                info = (
                    widget.grid_info()
                    if (widget is self.editwin.text)
                    else widget.pack_info()
                )
                padx += widget.tk.getint(info["padx"])
                padx += widget.tk.getint(widget.cget("padx"))
                border += widget.tk.getint(widget.cget("border"))
            context = self.context = Text(
                self.editwin.text_frame,
                height=1,
                width=1,
                highlightthickness=0,
                padx=padx,
                border=border,
                relief=SUNKEN,
                state="disabled",
            )
            self.update_font()
            self.update_highlight_colors()
            context.bind("<ButtonRelease-1>", self.jumptoline)
            self.timer_event()
            context.grid(row=0, column=1, sticky=NSEW)
            line_number_colors = idleConf.GetHighlight(
                idleConf.CurrentTheme(), "linenumber"
            )
            self.cell00 = Frame(
                self.editwin.text_frame, bg=line_number_colors["background"]
            )
            self.cell00.grid(row=0, column=0, sticky=NSEW)
            menu_status = "Hide"
        else:
            self.context.destroy()
            self.context = None
            self.cell00.destroy()
            self.cell00 = None
            self.text.after_cancel(self.t1)
            self._reset()
            menu_status = "Show"
        self.editwin.update_menu_label(
            menu="options", index="*ode*ontext", label=f"{menu_status} Code Context"
        )
        return "break"

    def get_context(self, new_topvisible, stopline=1, stopindent=0):
        "Return a list of block line tuples and the 'last' indent.\n\n        The tuple fields are (linenum, indent, text, opener).\n        The list represents header lines from new_topvisible back to\n        stopline with successively shorter indents > stopindent.\n        The list is returned ordered by line number.\n        Last indent returned is the smallest indent observed.\n        "
        assert stopline > 0
        lines = []
        lastindent = INFINITY
        for linenum in range(new_topvisible, (stopline - 1), (-1)):
            codeline = self.text.get(f"{linenum}.0", f"{linenum}.end")
            (indent, text, opener) = get_line_info(codeline)
            if indent < lastindent:
                lastindent = indent
                if opener in ("else", "elif"):
                    lastindent += 1
                if opener and (linenum < new_topvisible) and (indent >= stopindent):
                    lines.append((linenum, indent, text, opener))
                if lastindent <= stopindent:
                    break
        lines.reverse()
        return (lines, lastindent)

    def update_code_context(self):
        "Update context information and lines visible in the context pane.\n\n        No update is done if the text hasn't been scrolled.  If the text\n        was scrolled, the lines that should be shown in the context will\n        be retrieved and the context area will be updated with the code,\n        up to the number of maxlines.\n        "
        new_topvisible = self.editwin.getlineno("@0,0")
        if self.topvisible == new_topvisible:
            return
        if self.topvisible < new_topvisible:
            (lines, lastindent) = self.get_context(new_topvisible, self.topvisible)
            while self.info[(-1)][1] >= lastindent:
                del self.info[(-1)]
        else:
            stopindent = self.info[(-1)][1] + 1
            while self.info[(-1)][0] >= new_topvisible:
                stopindent = self.info[(-1)][1]
                del self.info[(-1)]
            (lines, lastindent) = self.get_context(
                new_topvisible, (self.info[(-1)][0] + 1), stopindent
            )
        self.info.extend(lines)
        self.topvisible = new_topvisible
        context_strings = [x[2] for x in self.info[(-self.context_depth) :]]
        showfirst = 0 if context_strings[0] else 1
        self.context["height"] = len(context_strings) - showfirst
        self.context["state"] = "normal"
        self.context.delete("1.0", "end")
        self.context.insert("end", "\n".join(context_strings[showfirst:]))
        self.context["state"] = "disabled"

    def jumptoline(self, event=None):
        " Show clicked context line at top of editor.\n\n        If a selection was made, don't jump; allow copying.\n        If no visible context, show the top line of the file.\n        "
        try:
            self.context.index("sel.first")
        except TclError:
            lines = len(self.info)
            if lines == 1:
                newtop = 1
            else:
                contextline = int(float(self.context.index("insert")))
                offset = max(1, (lines - self.context_depth)) - 1
                newtop = self.info[(offset + contextline)][0]
            self.text.yview(f"{newtop}.0")
            self.update_code_context()

    def timer_event(self):
        "Event on editor text widget triggered every UPDATEINTERVAL ms."
        if self.context is not None:
            self.update_code_context()
            self.t1 = self.text.after(self.UPDATEINTERVAL, self.timer_event)

    def update_font(self):
        if self.context is not None:
            font = idleConf.GetFont(self.text, "main", "EditorWindow")
            self.context["font"] = font

    def update_highlight_colors(self):
        if self.context is not None:
            colors = idleConf.GetHighlight(idleConf.CurrentTheme(), "context")
            self.context["background"] = colors["background"]
            self.context["foreground"] = colors["foreground"]
        if self.cell00 is not None:
            line_number_colors = idleConf.GetHighlight(
                idleConf.CurrentTheme(), "linenumber"
            )
            self.cell00.config(bg=line_number_colors["background"])


CodeContext.reload()
if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_codecontext", verbosity=2, exit=False)
