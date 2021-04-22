"\nGUI framework and application for use with Python unit testing framework.\nExecute tests written using the framework provided by the 'unittest' module.\n\nUpdated for unittest test discovery by Mark Roddy and Python 3\nsupport by Brian Curtin.\n\nBased on the original by Steve Purcell, from:\n\n  http://pyunit.sourceforge.net/\n\nCopyright (c) 1999, 2000, 2001 Steve Purcell\nThis module is free software, and you may redistribute it and/or modify\nit under the same terms as Python itself, so long as this copyright message\nand disclaimer are retained in their original form.\n\nIN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,\nSPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF\nTHIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH\nDAMAGE.\n\nTHE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT\nLIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A\nPARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN \"AS IS\" BASIS,\nAND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,\nSUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.\n"
__author__ = "Steve Purcell (stephen_purcell@yahoo.com)"
import sys
import traceback
import unittest
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import simpledialog


class BaseGUITestRunner(object):
    "Subclass this class to create a GUI TestRunner that uses a specific\n    windowing toolkit. The class takes care of running tests in the correct\n    manner, and making callbacks to the derived class to obtain information\n    or signal that events have occurred.\n    "

    def __init__(self, *args, **kwargs):
        self.currentResult = None
        self.running = 0
        self.__rollbackImporter = None
        self.__rollbackImporter = RollbackImporter()
        self.test_suite = None
        self.directory_to_read = ""
        self.top_level_dir = ""
        self.test_file_glob_pattern = "test*.py"
        self.initGUI(*args, **kwargs)

    def errorDialog(self, title, message):
        "Override to display an error arising from GUI usage"
        pass

    def getDirectoryToDiscover(self):
        "Override to prompt user for directory to perform test discovery"
        pass

    def runClicked(self):
        "To be called in response to user choosing to run a test"
        if self.running:
            return
        if not self.test_suite:
            self.errorDialog("Test Discovery", "You discover some tests first!")
            return
        self.currentResult = GUITestResult(self)
        self.totalTests = self.test_suite.countTestCases()
        self.running = 1
        self.notifyRunning()
        self.test_suite.run(self.currentResult)
        self.running = 0
        self.notifyStopped()

    def stopClicked(self):
        "To be called in response to user stopping the running of a test"
        if self.currentResult:
            self.currentResult.stop()

    def discoverClicked(self):
        self.__rollbackImporter.rollbackImports()
        directory = self.getDirectoryToDiscover()
        if not directory:
            return
        self.directory_to_read = directory
        try:
            top_level_dir = self.top_level_dir or None
            tests = unittest.defaultTestLoader.discover(
                directory, self.test_file_glob_pattern, top_level_dir
            )
            self.test_suite = tests
        except:
            (exc_type, exc_value, exc_tb) = sys.exc_info()
            traceback.print_exception(*sys.exc_info())
            self.errorDialog(
                ("Unable to run test '%s'" % directory),
                ("Error loading specified test: %s, %s" % (exc_type, exc_value)),
            )
            return
        self.notifyTestsDiscovered(self.test_suite)

    def notifyTestsDiscovered(self, test_suite):
        "Override to display information about the suite of discovered tests"
        pass

    def notifyRunning(self):
        "Override to set GUI in 'running' mode, enabling 'stop' button etc."
        pass

    def notifyStopped(self):
        "Override to set GUI in 'stopped' mode, enabling 'run' button etc."
        pass

    def notifyTestFailed(self, test, err):
        "Override to indicate that a test has just failed"
        pass

    def notifyTestErrored(self, test, err):
        "Override to indicate that a test has just errored"
        pass

    def notifyTestSkipped(self, test, reason):
        "Override to indicate that test was skipped"
        pass

    def notifyTestFailedExpectedly(self, test, err):
        "Override to indicate that test has just failed expectedly"
        pass

    def notifyTestStarted(self, test):
        "Override to indicate that a test is about to run"
        pass

    def notifyTestFinished(self, test):
        "Override to indicate that a test has finished (it may already have\n           failed or errored)"
        pass


class GUITestResult(unittest.TestResult):
    "A TestResult that makes callbacks to its associated GUI TestRunner.\n    Used by BaseGUITestRunner. Need not be created directly.\n    "

    def __init__(self, callback):
        unittest.TestResult.__init__(self)
        self.callback = callback

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self.callback.notifyTestErrored(test, err)

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self.callback.notifyTestFailed(test, err)

    def addSkip(self, test, reason):
        super(GUITestResult, self).addSkip(test, reason)
        self.callback.notifyTestSkipped(test, reason)

    def addExpectedFailure(self, test, err):
        super(GUITestResult, self).addExpectedFailure(test, err)
        self.callback.notifyTestFailedExpectedly(test, err)

    def stopTest(self, test):
        unittest.TestResult.stopTest(self, test)
        self.callback.notifyTestFinished(test)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.callback.notifyTestStarted(test)


class RollbackImporter:
    "This tricky little class is used to make sure that modules under test\n    will be reloaded the next time they are imported.\n    "

    def __init__(self):
        self.previousModules = sys.modules.copy()

    def rollbackImports(self):
        for modname in sys.modules.copy().keys():
            if not (modname in self.previousModules):
                del sys.modules[modname]


class DiscoverSettingsDialog(simpledialog.Dialog):
    "\n    Dialog box for prompting test discovery settings\n    "

    def __init__(self, master, top_level_dir, test_file_glob_pattern, *args, **kwargs):
        self.top_level_dir = top_level_dir
        self.dirVar = tk.StringVar()
        self.dirVar.set(top_level_dir)
        self.test_file_glob_pattern = test_file_glob_pattern
        self.testPatternVar = tk.StringVar()
        self.testPatternVar.set(test_file_glob_pattern)
        simpledialog.Dialog.__init__(
            self, master, *args, title="Discover Settings", **kwargs
        )

    def body(self, master):
        tk.Label(master, text="Top Level Directory").grid(row=0)
        self.e1 = tk.Entry(master, textvariable=self.dirVar)
        self.e1.grid(row=0, column=1)
        tk.Button(
            master, text="...", command=(lambda: self.selectDirClicked(master))
        ).grid(row=0, column=3)
        tk.Label(master, text="Test File Pattern").grid(row=1)
        self.e2 = tk.Entry(master, textvariable=self.testPatternVar)
        self.e2.grid(row=1, column=1)
        return None

    def selectDirClicked(self, master):
        dir_path = filedialog.askdirectory(parent=master)
        if dir_path:
            self.dirVar.set(dir_path)

    def apply(self):
        self.top_level_dir = self.dirVar.get()
        self.test_file_glob_pattern = self.testPatternVar.get()


class TkTestRunner(BaseGUITestRunner):
    "An implementation of BaseGUITestRunner using Tkinter.\n    "

    def initGUI(self, root, initialTestName):
        "Set up the GUI inside the given root window. The test name entry\n        field will be pre-filled with the given initialTestName.\n        "
        self.root = root
        self.statusVar = tk.StringVar()
        self.statusVar.set("Idle")
        self.runCountVar = tk.IntVar()
        self.failCountVar = tk.IntVar()
        self.errorCountVar = tk.IntVar()
        self.skipCountVar = tk.IntVar()
        self.expectFailCountVar = tk.IntVar()
        self.remainingCountVar = tk.IntVar()
        self.top = tk.Frame()
        self.top.pack(fill=tk.BOTH, expand=1)
        self.createWidgets()

    def getDirectoryToDiscover(self):
        return filedialog.askdirectory()

    def settingsClicked(self):
        d = DiscoverSettingsDialog(
            self.top, self.top_level_dir, self.test_file_glob_pattern
        )
        self.top_level_dir = d.top_level_dir
        self.test_file_glob_pattern = d.test_file_glob_pattern

    def notifyTestsDiscovered(self, test_suite):
        discovered = test_suite.countTestCases()
        self.runCountVar.set(0)
        self.failCountVar.set(0)
        self.errorCountVar.set(0)
        self.remainingCountVar.set(discovered)
        self.progressBar.setProgressFraction(0.0)
        self.errorListbox.delete(0, tk.END)
        self.statusVar.set(
            (
                "Discovering tests from %s. Found: %s"
                % (self.directory_to_read, discovered)
            )
        )
        self.stopGoButton["state"] = tk.NORMAL

    def createWidgets(self):
        "Creates and packs the various widgets.\n\n        Why is it that GUI code always ends up looking a mess, despite all the\n        best intentions to keep it tidy? Answers on a postcard, please.\n        "
        statusFrame = tk.Frame(self.top, relief=tk.SUNKEN, borderwidth=2)
        statusFrame.pack(anchor=tk.SW, fill=tk.X, side=tk.BOTTOM)
        tk.Label(statusFrame, width=1, textvariable=self.statusVar).pack(
            side=tk.TOP, fill=tk.X
        )
        leftFrame = tk.Frame(self.top, borderwidth=3)
        leftFrame.pack(fill=tk.BOTH, side=tk.LEFT, anchor=tk.NW, expand=1)
        suiteNameFrame = tk.Frame(leftFrame, borderwidth=3)
        suiteNameFrame.pack(fill=tk.X)
        progressFrame = tk.Frame(leftFrame, relief=tk.GROOVE, borderwidth=2)
        progressFrame.pack(fill=tk.X, expand=0, anchor=tk.NW)
        tk.Label(progressFrame, text="Progress:").pack(anchor=tk.W)
        self.progressBar = ProgressBar(progressFrame, relief=tk.SUNKEN, borderwidth=2)
        self.progressBar.pack(fill=tk.X, expand=1)
        buttonFrame = tk.Frame(self.top, borderwidth=3)
        buttonFrame.pack(side=tk.LEFT, anchor=tk.NW, fill=tk.Y)
        tk.Button(
            buttonFrame, text="Discover Tests", command=self.discoverClicked
        ).pack(fill=tk.X)
        self.stopGoButton = tk.Button(
            buttonFrame, text="Start", command=self.runClicked, state=tk.DISABLED
        )
        self.stopGoButton.pack(fill=tk.X)
        tk.Button(buttonFrame, text="Close", command=self.top.quit).pack(
            side=tk.BOTTOM, fill=tk.X
        )
        tk.Button(buttonFrame, text="Settings", command=self.settingsClicked).pack(
            side=tk.BOTTOM, fill=tk.X
        )
        for (label, var) in (
            ("Run:", self.runCountVar),
            ("Failures:", self.failCountVar),
            ("Errors:", self.errorCountVar),
            ("Skipped:", self.skipCountVar),
            ("Expected Failures:", self.expectFailCountVar),
            ("Remaining:", self.remainingCountVar),
        ):
            tk.Label(progressFrame, text=label).pack(side=tk.LEFT)
            tk.Label(progressFrame, textvariable=var, foreground="blue").pack(
                side=tk.LEFT, fill=tk.X, expand=1, anchor=tk.W
            )
        tk.Label(leftFrame, text="Failures and errors:").pack(anchor=tk.W)
        listFrame = tk.Frame(leftFrame, relief=tk.SUNKEN, borderwidth=2)
        listFrame.pack(fill=tk.BOTH, anchor=tk.NW, expand=1)
        self.errorListbox = tk.Listbox(
            listFrame, foreground="red", selectmode=tk.SINGLE, selectborderwidth=0
        )
        self.errorListbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, anchor=tk.NW)
        listScroll = tk.Scrollbar(listFrame, command=self.errorListbox.yview)
        listScroll.pack(side=tk.LEFT, fill=tk.Y, anchor=tk.N)
        self.errorListbox.bind(
            "<Double-1>", (lambda e, self=self: self.showSelectedError())
        )
        self.errorListbox.configure(yscrollcommand=listScroll.set)

    def errorDialog(self, title, message):
        messagebox.showerror(parent=self.root, title=title, message=message)

    def notifyRunning(self):
        self.runCountVar.set(0)
        self.failCountVar.set(0)
        self.errorCountVar.set(0)
        self.remainingCountVar.set(self.totalTests)
        self.errorInfo = []
        while self.errorListbox.size():
            self.errorListbox.delete(0)
        self.stopGoButton.config(state=tk.DISABLED)
        self.progressBar.setProgressFraction(0.0)
        self.top.update_idletasks()

    def notifyStopped(self):
        self.stopGoButton.config(state=tk.DISABLED)
        self.statusVar.set("Idle")

    def notifyTestStarted(self, test):
        self.statusVar.set(str(test))
        self.top.update_idletasks()

    def notifyTestFailed(self, test, err):
        self.failCountVar.set((1 + self.failCountVar.get()))
        self.errorListbox.insert(tk.END, ("Failure: %s" % test))
        self.errorInfo.append((test, err))

    def notifyTestErrored(self, test, err):
        self.errorCountVar.set((1 + self.errorCountVar.get()))
        self.errorListbox.insert(tk.END, ("Error: %s" % test))
        self.errorInfo.append((test, err))

    def notifyTestSkipped(self, test, reason):
        super(TkTestRunner, self).notifyTestSkipped(test, reason)
        self.skipCountVar.set((1 + self.skipCountVar.get()))

    def notifyTestFailedExpectedly(self, test, err):
        super(TkTestRunner, self).notifyTestFailedExpectedly(test, err)
        self.expectFailCountVar.set((1 + self.expectFailCountVar.get()))

    def notifyTestFinished(self, test):
        self.remainingCountVar.set((self.remainingCountVar.get() - 1))
        self.runCountVar.set((1 + self.runCountVar.get()))
        fractionDone = float(self.runCountVar.get()) / float(self.totalTests)
        fillColor = (len(self.errorInfo) and "red") or "green"
        self.progressBar.setProgressFraction(fractionDone, fillColor)

    def showSelectedError(self):
        selection = self.errorListbox.curselection()
        if not selection:
            return
        selected = int(selection[0])
        txt = self.errorListbox.get(selected)
        window = tk.Toplevel(self.root)
        window.title(txt)
        window.protocol("WM_DELETE_WINDOW", window.quit)
        (test, error) = self.errorInfo[selected]
        tk.Label(window, text=str(test), foreground="red", justify=tk.LEFT).pack(
            anchor=tk.W
        )
        tracebackLines = traceback.format_exception(*error)
        tracebackText = "".join(tracebackLines)
        tk.Label(window, text=tracebackText, justify=tk.LEFT).pack()
        tk.Button(window, text="Close", command=window.quit).pack(side=tk.BOTTOM)
        window.bind("<Key-Return>", (lambda e, w=window: w.quit()))
        window.mainloop()
        window.destroy()


class ProgressBar(tk.Frame):
    "A simple progress bar that shows a percentage progress in\n    the given colour."

    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.canvas = tk.Canvas(
            self, height="20", width="60", background="white", borderwidth=3
        )
        self.canvas.pack(fill=tk.X, expand=1)
        self.rect = self.text = None
        self.canvas.bind("<Configure>", self.paint)
        self.setProgressFraction(0.0)

    def setProgressFraction(self, fraction, color="blue"):
        self.fraction = fraction
        self.color = color
        self.paint()
        self.canvas.update_idletasks()

    def paint(self, *args):
        totalWidth = self.canvas.winfo_width()
        width = int((self.fraction * float(totalWidth)))
        height = self.canvas.winfo_height()
        if self.rect is not None:
            self.canvas.delete(self.rect)
        if self.text is not None:
            self.canvas.delete(self.text)
        self.rect = self.canvas.create_rectangle(0, 0, width, height, fill=self.color)
        percentString = "%3.0f%%" % (100.0 * self.fraction)
        self.text = self.canvas.create_text(
            (totalWidth / 2), (height / 2), anchor=tk.CENTER, text=percentString
        )


def main(initialTestName=""):
    root = tk.Tk()
    root.title("PyUnit")
    runner = TkTestRunner(root, initialTestName)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main()
