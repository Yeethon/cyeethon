"\nPython unit testing framework, based on Erich Gamma's JUnit and Kent Beck's\nSmalltalk testing framework (used with permission).\n\nThis module contains the core framework classes that form the basis of\nspecific test cases and suites (TestCase, TestSuite etc.), and also a\ntext-based utility class for running the tests and reporting the results\n (TextTestRunner).\n\nSimple usage:\n\n    import unittest\n\n    class IntegerArithmeticTestCase(unittest.TestCase):\n        def testAdd(self):  # test method names begin with 'test'\n            self.assertEqual((1 + 2), 3)\n            self.assertEqual(0 + 1, 1)\n        def testMultiply(self):\n            self.assertEqual((0 * 10), 0)\n            self.assertEqual((5 * 8), 40)\n\n    if __name__ == '__main__':\n        unittest.main()\n\nFurther information is available in the bundled documentation, and from\n\n  http://docs.python.org/library/unittest.html\n\nCopyright (c) 1999-2003 Steve Purcell\nCopyright (c) 2003-2010 Python Software Foundation\nThis module is free software, and you may redistribute it and/or modify\nit under the same terms as Python itself, so long as this copyright message\nand disclaimer are retained in their original form.\n\nIN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,\nSPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF\nTHIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH\nDAMAGE.\n\nTHE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT\nLIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A\nPARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN \"AS IS\" BASIS,\nAND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,\nSUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.\n"
__all__ = [
    "TestResult",
    "TestCase",
    "IsolatedAsyncioTestCase",
    "TestSuite",
    "TextTestRunner",
    "TestLoader",
    "FunctionTestCase",
    "main",
    "defaultTestLoader",
    "SkipTest",
    "skip",
    "skipIf",
    "skipUnless",
    "expectedFailure",
    "TextTestResult",
    "installHandler",
    "registerResult",
    "removeResult",
    "removeHandler",
    "addModuleCleanup",
]
__all__.extend(["getTestCaseNames", "makeSuite", "findTestCases"])
__unittest = True
from .result import TestResult
from .case import (
    addModuleCleanup,
    TestCase,
    FunctionTestCase,
    SkipTest,
    skip,
    skipIf,
    skipUnless,
    expectedFailure,
)
from .suite import BaseTestSuite, TestSuite
from .loader import (
    TestLoader,
    defaultTestLoader,
    makeSuite,
    getTestCaseNames,
    findTestCases,
)
from .main import TestProgram, main
from .runner import TextTestRunner, TextTestResult
from .signals import installHandler, registerResult, removeResult, removeHandler

_TextTestResult = TextTestResult


def load_tests(loader, tests, pattern):
    import os.path

    this_dir = os.path.dirname(__file__)
    return loader.discover(start_dir=this_dir, pattern=pattern)


def __dir__():
    return globals().keys() | {"IsolatedAsyncioTestCase"}


def __getattr__(name):
    if name == "IsolatedAsyncioTestCase":
        global IsolatedAsyncioTestCase
        from .async_case import IsolatedAsyncioTestCase

        return IsolatedAsyncioTestCase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
