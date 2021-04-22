" !Changing this line will break Test_findfile.test_found!\nNon-gui unit tests for grep.GrepDialog methods.\ndummy_command calls grep_it calls findfiles.\nAn exception raised in one method will fail callers.\nOtherwise, tests are mostly independent.\nCurrently only test grep_it, coverage 51%.\n"
from idlelib import grep
import unittest
from test.support import captured_stdout
from idlelib.idle_test.mock_tk import Var
import os
import re


class Dummy_searchengine:
    "GrepDialog.__init__ calls parent SearchDiabolBase which attaches the\n    passed in SearchEngine instance as attribute 'engine'. Only a few of the\n    many possible self.engine.x attributes are needed here.\n    "

    def getpat(self):
        return self._pat


searchengine = Dummy_searchengine()


class Dummy_grep:
    grep_it = grep.GrepDialog.grep_it
    recvar = Var(False)
    engine = searchengine

    def close(self):
        pass


_grep = Dummy_grep()


class FindfilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.realpath = os.path.realpath(__file__)
        cls.path = os.path.dirname(cls.realpath)

    @classmethod
    def tearDownClass(cls):
        del cls.realpath, cls.path

    def test_invaliddir(self):
        with captured_stdout() as s:
            filelist = list(grep.findfiles("invaliddir", "*.*", False))
        self.assertEqual(filelist, [])
        self.assertIn("invalid", s.getvalue())

    def test_curdir(self):
        ff = grep.findfiles
        save_cwd = os.getcwd()
        os.chdir(self.path)
        filename = "test_grep.py"
        filelist = list(ff(os.curdir, filename, False))
        self.assertIn(os.path.join(os.curdir, filename), filelist)
        os.chdir(save_cwd)

    def test_base(self):
        ff = grep.findfiles
        readme = os.path.join(self.path, "README.txt")
        filelist = list(ff(self.path, "*.py", False))
        self.assertGreater(len(filelist), 10)
        self.assertIn(self.realpath, filelist)
        self.assertNotIn(readme, filelist)
        filelist = list(ff(self.path, "*.txt", False))
        self.assertNotEqual(len(filelist), 0)
        self.assertNotIn(self.realpath, filelist)
        self.assertIn(readme, filelist)
        filelist = list(ff(self.path, "grep.*", False))
        self.assertEqual(len(filelist), 0)
        self.assertNotIn(self.realpath, filelist)

    def test_recurse(self):
        ff = grep.findfiles
        parent = os.path.dirname(self.path)
        grepfile = os.path.join(parent, "grep.py")
        pat = "*.py"
        filelist = list(ff(parent, pat, False))
        parent_size = len(filelist)
        self.assertGreater(parent_size, 20)
        self.assertIn(grepfile, filelist)
        self.assertNotIn(self.realpath, filelist)
        filelist = list(ff(parent, pat, True))
        self.assertGreater(len(filelist), parent_size)
        self.assertIn(grepfile, filelist)
        self.assertIn(self.realpath, filelist)
        parent = os.path.dirname(parent)
        filelist = list(ff(parent, "*.py", True))
        self.assertIn(self.realpath, filelist)


class Grep_itTest(unittest.TestCase):
    def report(self, pat):
        _grep.engine._pat = pat
        with captured_stdout() as s:
            _grep.grep_it(re.compile(pat), __file__)
        lines = s.getvalue().split("\n")
        lines.pop()
        return lines

    def test_unfound(self):
        pat = "xyz*" * 7
        lines = self.report(pat)
        self.assertEqual(len(lines), 2)
        self.assertIn(pat, lines[0])
        self.assertEqual(lines[1], "No hits.")

    def test_found(self):
        pat = '""" !Changing this line will break Test_findfile.test_found!'
        lines = self.report(pat)
        self.assertEqual(len(lines), 5)
        self.assertIn(pat, lines[0])
        self.assertIn("py: 1:", lines[1])
        self.assertIn("2", lines[3])
        self.assertTrue(lines[4].startswith("(Hint:"))


class Default_commandTest(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
