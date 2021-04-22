from tkinter import TclError


class WidgetRedirector:
    "Support for redirecting arbitrary widget subcommands.\n\n    Some Tk operations don't normally pass through tkinter.  For example, if a\n    character is inserted into a Text widget by pressing a key, a default Tk\n    binding to the widget's 'insert' operation is activated, and the Tk library\n    processes the insert without calling back into tkinter.\n\n    Although a binding to <Key> could be made via tkinter, what we really want\n    to do is to hook the Tk 'insert' operation itself.  For one thing, we want\n    a text.insert call in idle code to have the same effect as a key press.\n\n    When a widget is instantiated, a Tcl command is created whose name is the\n    same as the pathname widget._w.  This command is used to invoke the various\n    widget operations, e.g. insert (for a Text widget). We are going to hook\n    this command and provide a facility ('register') to intercept the widget\n    operation.  We will also intercept method calls on the tkinter class\n    instance that represents the tk widget.\n\n    In IDLE, WidgetRedirector is used in Percolator to intercept Text\n    commands.  The function being registered provides access to the top\n    of a Percolator chain.  At the bottom of the chain is a call to the\n    original Tk widget operation.\n    "

    def __init__(self, widget):
        "Initialize attributes and setup redirection.\n\n        _operations: dict mapping operation name to new function.\n        widget: the widget whose tcl command is to be intercepted.\n        tk: widget.tk, a convenience attribute, probably not needed.\n        orig: new name of the original tcl command.\n\n        Since renaming to orig fails with TclError when orig already\n        exists, only one WidgetDirector can exist for a given widget.\n        "
        self._operations = {}
        self.widget = widget
        self.tk = tk = widget.tk
        w = widget._w
        self.orig = w + "_orig"
        tk.call("rename", w, self.orig)
        tk.createcommand(w, self.dispatch)

    def __repr__(self):
        return "%s(%s<%s>)" % (
            self.__class__.__name__,
            self.widget.__class__.__name__,
            self.widget._w,
        )

    def close(self):
        "Unregister operations and revert redirection created by .__init__."
        for operation in list(self._operations):
            self.unregister(operation)
        widget = self.widget
        tk = widget.tk
        w = widget._w
        tk.deletecommand(w)
        tk.call("rename", self.orig, w)
        del self.widget, self.tk

    def register(self, operation, function):
        "Return OriginalCommand(operation) after registering function.\n\n        Registration adds an operation: function pair to ._operations.\n        It also adds a widget function attribute that masks the tkinter\n        class instance method.  Method masking operates independently\n        from command dispatch.\n\n        If a second function is registered for the same operation, the\n        first function is replaced in both places.\n        "
        self._operations[operation] = function
        setattr(self.widget, operation, function)
        return OriginalCommand(self, operation)

    def unregister(self, operation):
        "Return the function for the operation, or None.\n\n        Deleting the instance attribute unmasks the class attribute.\n        "
        if operation in self._operations:
            function = self._operations[operation]
            del self._operations[operation]
            try:
                delattr(self.widget, operation)
            except AttributeError:
                pass
            return function
        else:
            return None

    def dispatch(self, operation, *args):
        "Callback from Tcl which runs when the widget is referenced.\n\n        If an operation has been registered in self._operations, apply the\n        associated function to the args passed into Tcl. Otherwise, pass the\n        operation through to Tk via the original Tcl function.\n\n        Note that if a registered function is called, the operation is not\n        passed through to Tk.  Apply the function returned by self.register()\n        to *args to accomplish that.  For an example, see colorizer.py.\n\n        "
        m = self._operations.get(operation)
        try:
            if m:
                return m(*args)
            else:
                return self.tk.call(((self.orig, operation) + args))
        except TclError:
            return ""


class OriginalCommand:
    'Callable for original tk command that has been redirected.\n\n    Returned by .register; can be used in the function registered.\n    redir = WidgetRedirector(text)\n    def my_insert(*args):\n        print("insert", args)\n        original_insert(*args)\n    original_insert = redir.register("insert", my_insert)\n    '

    def __init__(self, redir, operation):
        "Create .tk_call and .orig_and_operation for .__call__ method.\n\n        .redir and .operation store the input args for __repr__.\n        .tk and .orig copy attributes of .redir (probably not needed).\n        "
        self.redir = redir
        self.operation = operation
        self.tk = redir.tk
        self.orig = redir.orig
        self.tk_call = redir.tk.call
        self.orig_and_operation = (redir.orig, operation)

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.redir, self.operation)

    def __call__(self, *args):
        return self.tk_call((self.orig_and_operation + args))


def _widget_redirector(parent):
    from tkinter import Toplevel, Text

    top = Toplevel(parent)
    top.title("Test WidgetRedirector")
    (x, y) = map(int, parent.geometry().split("+")[1:])
    top.geometry(("+%d+%d" % (x, (y + 175))))
    text = Text(top)
    text.pack()
    text.focus_set()
    redir = WidgetRedirector(text)

    def my_insert(*args):
        print("insert", args)
        original_insert(*args)

    original_insert = redir.register("insert", my_insert)


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_redirector", verbosity=2, exit=False)
    from idlelib.idle_test.htest import run

    run(_widget_redirector)
