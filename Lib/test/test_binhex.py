"Test script for the binhex C module\n\n   Uses the mechanism of the python binhex module\n   Based on an original test by Roger E. Masse.\n"
import unittest
from test import support
from test.support import import_helper
from test.support import os_helper
from test.support import warnings_helper

with warnings_helper.check_warnings(("", DeprecationWarning)):
    binhex = import_helper.import_fresh_module("binhex")


class BinHexTestCase(unittest.TestCase):
    def setUp(self):
        self.fname1 = os_helper.TESTFN_ASCII + "1"
        self.fname2 = os_helper.TESTFN_ASCII + "2"
        self.fname3 = (
            os_helper.TESTFN_ASCII
            + "very_long_filename__very_long_filename__very_long_filename__very_long_filename__"
        )

    def tearDown(self):
        os_helper.unlink(self.fname1)
        os_helper.unlink(self.fname2)
        os_helper.unlink(self.fname3)

    DATA = b"Jack is my hero"

    def test_binhex(self):
        with open(self.fname1, "wb") as f:
            f.write(self.DATA)
        binhex.binhex(self.fname1, self.fname2)
        binhex.hexbin(self.fname2, self.fname1)
        with open(self.fname1, "rb") as f:
            finish = f.readline()
        self.assertEqual(self.DATA, finish)

    def test_binhex_error_on_long_filename(self):
        "\n        The testcase fails if no exception is raised when a filename parameter provided to binhex.binhex()\n        is too long, or if the exception raised in binhex.binhex() is not an instance of binhex.Error.\n        "
        f3 = open(self.fname3, "wb")
        f3.close()
        self.assertRaises(binhex.Error, binhex.binhex, self.fname3, self.fname2)

    def test_binhex_line_endings(self):
        with open(self.fname1, "wb") as f:
            f.write(self.DATA)
        binhex.binhex(self.fname1, self.fname2)
        with open(self.fname2, "rb") as fp:
            contents = fp.read()
        self.assertNotIn(b"\n", contents)


def test_main():
    support.run_unittest(BinHexTestCase)


if __name__ == "__main__":
    test_main()
