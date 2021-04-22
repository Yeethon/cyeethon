"Test suite for distutils.\n\nThis test suite consists of a collection of test modules in the\ndistutils.tests package.  Each test module has a name starting with\n'test' and contains a function test_suite().  The function is expected\nto return an initialized unittest.TestSuite instance.\n\nTests for the command classes in the distutils.command package are\nincluded in distutils.tests as well, instead of using a separate\ndistutils.command.tests package, since command identification is done\nby import rather than matching pre-defined names.\n\n"
import os
import sys
import unittest
from test.support import run_unittest
from test.support.warnings_helper import save_restore_warnings_filters

here = os.path.dirname(__file__) or os.curdir


def test_suite():
    suite = unittest.TestSuite()
    for fn in os.listdir(here):
        if fn.startswith("test") and fn.endswith(".py"):
            modname = "distutils.tests." + fn[:(-3)]
            with save_restore_warnings_filters():
                __import__(modname)
            module = sys.modules[modname]
            suite.addTest(module.test_suite())
    return suite


if __name__ == "__main__":
    run_unittest(test_suite())
