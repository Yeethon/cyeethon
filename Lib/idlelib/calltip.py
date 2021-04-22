"Pop up a reminder of how to call a function.\n\nCall Tips are floating windows which display function, class, and method\nparameter and docstring information when you type an opening parenthesis, and\nwhich disappear when you type a closing parenthesis.\n"
import __main__
import inspect
import re
import sys
import textwrap
import types
from idlelib import calltip_w
from idlelib.hyperparser import HyperParser


class Calltip:
    def __init__(self, editwin=None):
        if editwin is None:
            self.editwin = None
        else:
            self.editwin = editwin
            self.text = editwin.text
            self.active_calltip = None
            self._calltip_window = self._make_tk_calltip_window

    def close(self):
        self._calltip_window = None

    def _make_tk_calltip_window(self):
        return calltip_w.CalltipWindow(self.text)

    def remove_calltip_window(self, event=None):
        if self.active_calltip:
            self.active_calltip.hidetip()
            self.active_calltip = None

    def force_open_calltip_event(self, event):
        "The user selected the menu entry or hotkey, open the tip."
        self.open_calltip(True)
        return "break"

    def try_open_calltip_event(self, event):
        "Happens when it would be nice to open a calltip, but not really\n        necessary, for example after an opening bracket, so function calls\n        won't be made.\n        "
        self.open_calltip(False)

    def refresh_calltip_event(self, event):
        if self.active_calltip and self.active_calltip.tipwindow:
            self.open_calltip(False)

    def open_calltip(self, evalfuncs):
        "Maybe close an existing calltip and maybe open a new calltip.\n\n        Called from (force_open|try_open|refresh)_calltip_event functions.\n        "
        hp = HyperParser(self.editwin, "insert")
        sur_paren = hp.get_surrounding_brackets("(")
        if not sur_paren:
            self.remove_calltip_window()
            return
        if self.active_calltip:
            (opener_line, opener_col) = map(int, sur_paren[0].split("."))
            if (opener_line, opener_col) == (
                self.active_calltip.parenline,
                self.active_calltip.parencol,
            ):
                return
        hp.set_index(sur_paren[0])
        try:
            expression = hp.get_expression()
        except ValueError:
            expression = None
        if not expression:
            return
        self.remove_calltip_window()
        if (not evalfuncs) and (expression.find("(") != (-1)):
            return
        argspec = self.fetch_tip(expression)
        if not argspec:
            return
        self.active_calltip = self._calltip_window()
        self.active_calltip.showtip(argspec, sur_paren[0], sur_paren[1])

    def fetch_tip(self, expression):
        "Return the argument list and docstring of a function or class.\n\n        If there is a Python subprocess, get the calltip there.  Otherwise,\n        either this fetch_tip() is running in the subprocess or it was\n        called in an IDLE running without the subprocess.\n\n        The subprocess environment is that of the most recently run script.  If\n        two unrelated modules are being edited some calltips in the current\n        module may be inoperative if the module was not the last to run.\n\n        To find methods, fetch_tip must be fed a fully qualified name.\n\n        "
        try:
            rpcclt = self.editwin.flist.pyshell.interp.rpcclt
        except AttributeError:
            rpcclt = None
        if rpcclt:
            return rpcclt.remotecall("exec", "get_the_calltip", (expression,), {})
        else:
            return get_argspec(get_entity(expression))


def get_entity(expression):
    "Return the object corresponding to expression evaluated\n    in a namespace spanning sys.modules and __main.dict__.\n    "
    if expression:
        namespace = {**sys.modules, **__main__.__dict__}
        try:
            return eval(expression, namespace)
        except BaseException:
            return None


_MAX_COLS = 85
_MAX_LINES = 5
_INDENT = " " * 4
_first_param = re.compile("(?<=\\()\\w*\\,?\\s*")
_default_callable_argspec = "See source or doc"
_invalid_method = "invalid method signature"


def get_argspec(ob):
    "Return a string describing the signature of a callable object, or ''.\n\n    For Python-coded functions and methods, the first line is introspected.\n    Delete 'self' parameter for classes (.__init__) and bound methods.\n    The next lines are the first lines of the doc string up to the first\n    empty line or _MAX_LINES.    For builtins, this typically includes\n    the arguments in addition to the return value.\n    "
    try:
        ob_call = ob.__call__
    except BaseException:
        return ""
    fob = ob_call if isinstance(ob_call, types.MethodType) else ob
    try:
        argspec = str(inspect.signature(fob))
    except Exception as err:
        msg = str(err)
        if msg.startswith(_invalid_method):
            return _invalid_method
        else:
            argspec = ""
    if isinstance(fob, type) and (argspec == "()"):
        argspec = _default_callable_argspec
    lines = (
        textwrap.wrap(argspec, _MAX_COLS, subsequent_indent=_INDENT)
        if (len(argspec) > _MAX_COLS)
        else ([argspec] if argspec else [])
    )
    doc = inspect.getdoc(ob)
    if doc:
        for line in doc.split("\n", _MAX_LINES)[:_MAX_LINES]:
            line = line.strip()
            if not line:
                break
            if len(line) > _MAX_COLS:
                line = line[: (_MAX_COLS - 3)] + "..."
            lines.append(line)
    argspec = "\n".join(lines)
    return argspec or _default_callable_argspec


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_calltip", verbosity=2)
