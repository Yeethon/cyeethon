"\nOptionMenu widget modified to allow dynamic menu reconfiguration\nand setting of highlightthickness\n"
import copy
from tkinter import OptionMenu, _setit, StringVar, Button


class DynOptionMenu(OptionMenu):
    "\n    unlike OptionMenu, our kwargs can include highlightthickness\n    "

    def __init__(self, master, variable, value, *values, **kwargs):
        kwargsCopy = copy.copy(kwargs)
        if "highlightthickness" in list(kwargs.keys()):
            del kwargs["highlightthickness"]
        OptionMenu.__init__(self, master, variable, value, *values, **kwargs)
        self.config(highlightthickness=kwargsCopy.get("highlightthickness"))
        self.variable = variable
        self.command = kwargs.get("command")

    def SetMenu(self, valueList, value=None):
        "\n        clear and reload the menu with a new set of options.\n        valueList - list of new options\n        value - initial value to set the optionmenu's menubutton to\n        "
        self["menu"].delete(0, "end")
        for item in valueList:
            self["menu"].add_command(
                label=item, command=_setit(self.variable, item, self.command)
            )
        if value:
            self.variable.set(value)


def _dyn_option_menu(parent):
    from tkinter import Toplevel

    top = Toplevel(parent)
    top.title("Tets dynamic option menu")
    (x, y) = map(int, parent.geometry().split("+")[1:])
    top.geometry(("200x100+%d+%d" % ((x + 250), (y + 175))))
    top.focus_set()
    var = StringVar(top)
    var.set("Old option set")
    dyn = DynOptionMenu(top, var, "old1", "old2", "old3", "old4")
    dyn.pack()

    def update():
        dyn.SetMenu(["new1", "new2", "new3", "new4"], value="new option set")

    button = Button(top, text="Change option set", command=update)
    button.pack()


if __name__ == "__main__":
    from idlelib.idle_test.htest import run

    run(_dyn_option_menu)
