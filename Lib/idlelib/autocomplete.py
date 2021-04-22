"Complete either attribute names or file names.\n\nEither on demand or after a user-selected delay after a key character,\npop up a list of candidates.\n"
import __main__
import keyword
import os
import string
import sys

(ATTRS, FILES) = (0, 1)
from idlelib import autocomplete_w
from idlelib.config import idleConf
from idlelib.hyperparser import HyperParser

FORCE = (True, False, True, None)
TAB = (False, True, True, None)
TRY_A = (False, False, False, ATTRS)
TRY_F = (False, False, False, FILES)
ID_CHARS = (string.ascii_letters + string.digits) + "_"
SEPS = f"{os.sep}{(os.altsep if os.altsep else '')}"
TRIGGERS = f".{SEPS}"


class AutoComplete:
    def __init__(self, editwin=None):
        self.editwin = editwin
        if editwin is not None:
            self.text = editwin.text
        self.autocompletewindow = None
        self._delayed_completion_id = None
        self._delayed_completion_index = None

    @classmethod
    def reload(cls):
        cls.popupwait = idleConf.GetOption(
            "extensions", "AutoComplete", "popupwait", type="int", default=0
        )

    def _make_autocomplete_window(self):
        return autocomplete_w.AutoCompleteWindow(self.text)

    def _remove_autocomplete_window(self, event=None):
        if self.autocompletewindow:
            self.autocompletewindow.hide_window()
            self.autocompletewindow = None

    def force_open_completions_event(self, event):
        "(^space) Open completion list, even if a function call is needed."
        self.open_completions(FORCE)
        return "break"

    def autocomplete_event(self, event):
        "(tab) Complete word or open list if multiple options."
        if (hasattr(event, "mc_state") and event.mc_state) or (
            not self.text.get("insert linestart", "insert").strip()
        ):
            return None
        if self.autocompletewindow and self.autocompletewindow.is_active():
            self.autocompletewindow.complete()
            return "break"
        else:
            opened = self.open_completions(TAB)
            return "break" if opened else None

    def try_open_completions_event(self, event=None):
        "(./) Open completion list after pause with no movement."
        lastchar = self.text.get("insert-1c")
        if lastchar in TRIGGERS:
            args = TRY_A if (lastchar == ".") else TRY_F
            self._delayed_completion_index = self.text.index("insert")
            if self._delayed_completion_id is not None:
                self.text.after_cancel(self._delayed_completion_id)
            self._delayed_completion_id = self.text.after(
                self.popupwait, self._delayed_open_completions, args
            )

    def _delayed_open_completions(self, args):
        "Call open_completions if index unchanged."
        self._delayed_completion_id = None
        if self.text.index("insert") == self._delayed_completion_index:
            self.open_completions(args)

    def open_completions(self, args):
        "Find the completions and create the AutoCompleteWindow.\n        Return True if successful (no syntax error or so found).\n        If complete is True, then if there's nothing to complete and no\n        start of completion, won't open completions and return False.\n        If mode is given, will open a completion list only in this mode.\n        "
        (evalfuncs, complete, wantwin, mode) = args
        if self._delayed_completion_id is not None:
            self.text.after_cancel(self._delayed_completion_id)
            self._delayed_completion_id = None
        hp = HyperParser(self.editwin, "insert")
        curline = self.text.get("insert linestart", "insert")
        i = j = len(curline)
        if hp.is_in_string() and ((not mode) or (mode == FILES)):
            self._remove_autocomplete_window()
            mode = FILES
            while i and (curline[(i - 1)] not in ("'\"" + SEPS)):
                i -= 1
            comp_start = curline[i:j]
            j = i
            while i and (curline[(i - 1)] not in "'\""):
                i -= 1
            comp_what = curline[i:j]
        elif hp.is_in_code() and ((not mode) or (mode == ATTRS)):
            self._remove_autocomplete_window()
            mode = ATTRS
            while i and (
                (curline[(i - 1)] in ID_CHARS) or (ord(curline[(i - 1)]) > 127)
            ):
                i -= 1
            comp_start = curline[i:j]
            if i and (curline[(i - 1)] == "."):
                hp.set_index(("insert-%dc" % (len(curline) - (i - 1))))
                comp_what = hp.get_expression()
                if (not comp_what) or (
                    (not evalfuncs) and (comp_what.find("(") != (-1))
                ):
                    return None
            else:
                comp_what = ""
        else:
            return None
        if complete and (not comp_what) and (not comp_start):
            return None
        comp_lists = self.fetch_completions(comp_what, mode)
        if not comp_lists[0]:
            return None
        self.autocompletewindow = self._make_autocomplete_window()
        return not self.autocompletewindow.show_window(
            comp_lists, ("insert-%dc" % len(comp_start)), complete, mode, wantwin
        )

    def fetch_completions(self, what, mode):
        "Return a pair of lists of completions for something. The first list\n        is a sublist of the second. Both are sorted.\n\n        If there is a Python subprocess, get the comp. list there.  Otherwise,\n        either fetch_completions() is running in the subprocess itself or it\n        was called in an IDLE EditorWindow before any script had been run.\n\n        The subprocess environment is that of the most recently run script.  If\n        two unrelated modules are being edited some calltips in the current\n        module may be inoperative if the module was not the last to run.\n        "
        try:
            rpcclt = self.editwin.flist.pyshell.interp.rpcclt
        except:
            rpcclt = None
        if rpcclt:
            return rpcclt.remotecall(
                "exec", "get_the_completion_list", (what, mode), {}
            )
        else:
            if mode == ATTRS:
                if what == "":
                    namespace = {**__main__.__builtins__.__dict__, **__main__.__dict__}
                    bigl = eval("dir()", namespace)
                    kwds = (
                        s
                        for s in keyword.kwlist
                        if (s not in {"True", "False", "None"})
                    )
                    bigl.extend(kwds)
                    bigl.sort()
                    if "__all__" in bigl:
                        smalll = sorted(eval("__all__", namespace))
                    else:
                        smalll = [s for s in bigl if (s[:1] != "_")]
                else:
                    try:
                        entity = self.get_entity(what)
                        bigl = dir(entity)
                        bigl.sort()
                        if "__all__" in bigl:
                            smalll = sorted(entity.__all__)
                        else:
                            smalll = [s for s in bigl if (s[:1] != "_")]
                    except:
                        return ([], [])
            elif mode == FILES:
                if what == "":
                    what = "."
                try:
                    expandedpath = os.path.expanduser(what)
                    bigl = os.listdir(expandedpath)
                    bigl.sort()
                    smalll = [s for s in bigl if (s[:1] != ".")]
                except OSError:
                    return ([], [])
            if not smalll:
                smalll = bigl
            return (smalll, bigl)

    def get_entity(self, name):
        "Lookup name in a namespace spanning sys.modules and __main.dict__."
        return eval(name, {**sys.modules, **__main__.__dict__})


AutoComplete.reload()
if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_autocomplete", verbosity=2)
