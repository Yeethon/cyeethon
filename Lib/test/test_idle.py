import unittest
from test.support.import_helper import import_module

tk = import_module("tkinter")
if tk.TkVersion < 8.5:
    raise unittest.SkipTest("IDLE requires tk 8.5 or later.")
idlelib = import_module("idlelib")
idlelib.testing = True
from idlelib.idle_test import load_tests

if __name__ == "__main__":
    tk.NoDefaultRoot()
    unittest.main(exit=False)
    tk._support_default_root = True
    tk._default_root = None
