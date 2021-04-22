import unittest


class fake_filesystem_unittest:
    "\n    Stubbed version of the pyfakefs module\n    "

    class TestCase(unittest.TestCase):
        def setUpPyfakefs(self):
            self.skipTest("pyfakefs not available")
