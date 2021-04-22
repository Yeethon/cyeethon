from tkinter.commondialog import Dialog

__all__ = ["Chooser", "askcolor"]


class Chooser(Dialog):
    "Create a dialog for the tk_chooseColor command.\n\n    Args:\n        master: The master widget for this dialog.  If not provided,\n            defaults to options['parent'] (if defined).\n        options: Dictionary of options for the tk_chooseColor call.\n            initialcolor: Specifies the selected color when the\n                dialog is first displayed.  This can be a tk color\n                string or a 3-tuple of ints in the range (0, 255)\n                for an RGB triplet.\n            parent: The parent window of the color dialog.  The\n                color dialog is displayed on top of this.\n            title: A string for the title of the dialog box.\n    "
    command = "tk_chooseColor"

    def _fixoptions(self):
        "Ensure initialcolor is a tk color string.\n\n        Convert initialcolor from a RGB triplet to a color string.\n        "
        try:
            color = self.options["initialcolor"]
            if isinstance(color, tuple):
                self.options["initialcolor"] = "#%02x%02x%02x" % color
        except KeyError:
            pass

    def _fixresult(self, widget, result):
        "Adjust result returned from call to tk_chooseColor.\n\n        Return both an RGB tuple of ints in the range (0, 255) and the\n        tk color string in the form #rrggbb.\n        "
        if (not result) or (not str(result)):
            return (None, None)
        (r, g, b) = widget.winfo_rgb(result)
        return (((r // 256), (g // 256), (b // 256)), str(result))


def askcolor(color=None, **options):
    "Display dialog window for selection of a color.\n\n    Convenience wrapper for the Chooser class.  Displays the color\n    chooser dialog with color as the initial value.\n    "
    if color:
        options = options.copy()
        options["initialcolor"] = color
    return Chooser(**options).show()


if __name__ == "__main__":
    print("color", askcolor())
