"Test pyshell, coverage 12%."
from idlelib import pyshell
import unittest
from test.support import requires
from tkinter import Tk


class FunctionTest(unittest.TestCase):
    def test_restart_line_wide(self):
        eq = self.assertEqual
        for (file, mul, extra) in (("", 22, ""), ("finame", 21, "=")):
            width = 60
            bar = mul * "="
            with self.subTest(file=file, bar=bar):
                file = file or "Shell"
                line = pyshell.restart_line(width, file)
                eq(len(line), width)
                eq(line, f"{(bar + extra)} RESTART: {file} {bar}")

    def test_restart_line_narrow(self):
        (expect, taglen) = ("= RESTART: Shell", 16)
        for width in ((taglen - 1), taglen, (taglen + 1)):
            with self.subTest(width=width):
                self.assertEqual(pyshell.restart_line(width, ""), expect)
        self.assertEqual(pyshell.restart_line((taglen + 2), ""), (expect + " ="))


class PyShellFileListTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requires("gui")
        cls.root = Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        del cls.root

    def test_init(self):
        psfl = pyshell.PyShellFileList(self.root)
        self.assertEqual(psfl.EditorWindow, pyshell.PyShellEditorWindow)
        self.assertIsNone(psfl.pyshell)


if __name__ == "__main__":
    unittest.main(verbosity=2)
