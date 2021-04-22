"Tests for the pindent script in the Tools directory."
import os
import sys
import unittest
import subprocess
import textwrap
from test import support
from test.support import os_helper
from test.support.script_helper import assert_python_ok
from test.test_tools import scriptsdir, skip_if_missing

skip_if_missing()


class PindentTests(unittest.TestCase):
    script = os.path.join(scriptsdir, "pindent.py")

    def assertFileEqual(self, fn1, fn2):
        with open(fn1) as f1, open(fn2) as f2:
            self.assertEqual(f1.readlines(), f2.readlines())

    def pindent(self, source, *args):
        with subprocess.Popen(
            ((sys.executable, self.script) + args),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        ) as proc:
            (out, err) = proc.communicate(source)
        self.assertIsNone(err)
        return out

    def lstriplines(self, data):
        return "\n".join((line.lstrip() for line in data.splitlines())) + "\n"

    def test_selftest(self):
        self.maxDiff = None
        with os_helper.temp_dir() as directory:
            data_path = os.path.join(directory, "_test.py")
            with open(self.script) as f:
                closed = f.read()
            with open(data_path, "w") as f:
                f.write(closed)
            (rc, out, err) = assert_python_ok(self.script, "-d", data_path)
            self.assertEqual(out, b"")
            self.assertEqual(err, b"")
            backup = data_path + "~"
            self.assertTrue(os.path.exists(backup))
            with open(backup) as f:
                self.assertEqual(f.read(), closed)
            with open(data_path) as f:
                clean = f.read()
            compile(clean, "_test.py", "exec")
            self.assertEqual(self.pindent(clean, "-c"), closed)
            self.assertEqual(self.pindent(closed, "-d"), clean)
            (rc, out, err) = assert_python_ok(self.script, "-c", data_path)
            self.assertEqual(out, b"")
            self.assertEqual(err, b"")
            with open(backup) as f:
                self.assertEqual(f.read(), clean)
            with open(data_path) as f:
                self.assertEqual(f.read(), closed)
            broken = self.lstriplines(closed)
            with open(data_path, "w") as f:
                f.write(broken)
            (rc, out, err) = assert_python_ok(self.script, "-r", data_path)
            self.assertEqual(out, b"")
            self.assertEqual(err, b"")
            with open(backup) as f:
                self.assertEqual(f.read(), broken)
            with open(data_path) as f:
                indented = f.read()
            compile(indented, "_test.py", "exec")
            self.assertEqual(self.pindent(broken, "-r"), indented)

    def pindent_test(self, clean, closed):
        self.assertEqual(self.pindent(clean, "-c"), closed)
        self.assertEqual(self.pindent(closed, "-d"), clean)
        broken = self.lstriplines(closed)
        self.assertEqual(self.pindent(broken, "-r", "-e", "-s", "4"), closed)

    def test_statements(self):
        clean = textwrap.dedent(
            "            if a:\n                pass\n\n            if a:\n                pass\n            else:\n                pass\n\n            if a:\n                pass\n            elif:\n                pass\n            else:\n                pass\n\n            while a:\n                break\n\n            while a:\n                break\n            else:\n                pass\n\n            for i in a:\n                break\n\n            for i in a:\n                break\n            else:\n                pass\n\n            try:\n                pass\n            finally:\n                pass\n\n            try:\n                pass\n            except TypeError:\n                pass\n            except ValueError:\n                pass\n            else:\n                pass\n\n            try:\n                pass\n            except TypeError:\n                pass\n            except ValueError:\n                pass\n            finally:\n                pass\n\n            with a:\n                pass\n\n            class A:\n                pass\n\n            def f():\n                pass\n            "
        )
        closed = textwrap.dedent(
            "            if a:\n                pass\n            # end if\n\n            if a:\n                pass\n            else:\n                pass\n            # end if\n\n            if a:\n                pass\n            elif:\n                pass\n            else:\n                pass\n            # end if\n\n            while a:\n                break\n            # end while\n\n            while a:\n                break\n            else:\n                pass\n            # end while\n\n            for i in a:\n                break\n            # end for\n\n            for i in a:\n                break\n            else:\n                pass\n            # end for\n\n            try:\n                pass\n            finally:\n                pass\n            # end try\n\n            try:\n                pass\n            except TypeError:\n                pass\n            except ValueError:\n                pass\n            else:\n                pass\n            # end try\n\n            try:\n                pass\n            except TypeError:\n                pass\n            except ValueError:\n                pass\n            finally:\n                pass\n            # end try\n\n            with a:\n                pass\n            # end with\n\n            class A:\n                pass\n            # end class A\n\n            def f():\n                pass\n            # end def f\n            "
        )
        self.pindent_test(clean, closed)

    def test_multilevel(self):
        clean = textwrap.dedent(
            "            def foobar(a, b):\n                if a == b:\n                    a = a+1\n                elif a < b:\n                    b = b-1\n                    if b > a: a = a-1\n                else:\n                    print 'oops!'\n            "
        )
        closed = textwrap.dedent(
            "            def foobar(a, b):\n                if a == b:\n                    a = a+1\n                elif a < b:\n                    b = b-1\n                    if b > a: a = a-1\n                    # end if\n                else:\n                    print 'oops!'\n                # end if\n            # end def foobar\n            "
        )
        self.pindent_test(clean, closed)

    def test_preserve_indents(self):
        clean = textwrap.dedent(
            "            if a:\n                     if b:\n                              pass\n            "
        )
        closed = textwrap.dedent(
            "            if a:\n                     if b:\n                              pass\n                     # end if\n            # end if\n            "
        )
        self.assertEqual(self.pindent(clean, "-c"), closed)
        self.assertEqual(self.pindent(closed, "-d"), clean)
        broken = self.lstriplines(closed)
        self.assertEqual(self.pindent(broken, "-r", "-e", "-s", "9"), closed)
        clean = textwrap.dedent(
            "            if a:\n            \tif b:\n            \t\tpass\n            "
        )
        closed = textwrap.dedent(
            "            if a:\n            \tif b:\n            \t\tpass\n            \t# end if\n            # end if\n            "
        )
        self.assertEqual(self.pindent(clean, "-c"), closed)
        self.assertEqual(self.pindent(closed, "-d"), clean)
        broken = self.lstriplines(closed)
        self.assertEqual(self.pindent(broken, "-r"), closed)

    def test_escaped_newline(self):
        clean = textwrap.dedent(
            "            class\\\n            \\\n             A:\n               def            \\\n            f:\n                  pass\n            "
        )
        closed = textwrap.dedent(
            "            class\\\n            \\\n             A:\n               def            \\\n            f:\n                  pass\n               # end def f\n            # end class A\n            "
        )
        self.assertEqual(self.pindent(clean, "-c"), closed)
        self.assertEqual(self.pindent(closed, "-d"), clean)

    def test_empty_line(self):
        clean = textwrap.dedent(
            "            if a:\n\n                pass\n            "
        )
        closed = textwrap.dedent(
            "            if a:\n\n                pass\n            # end if\n            "
        )
        self.pindent_test(clean, closed)

    def test_oneline(self):
        clean = textwrap.dedent("            if a: pass\n            ")
        closed = textwrap.dedent(
            "            if a: pass\n            # end if\n            "
        )
        self.pindent_test(clean, closed)


if __name__ == "__main__":
    unittest.main()
