import atexit
import os
import sys
import textwrap
import unittest
from test import support
from test.support import script_helper


class GeneralTest(unittest.TestCase):
    def test_general(self):
        script = support.findfile("_test_atexit.py")
        script_helper.run_test_script(script)


class FunctionalTest(unittest.TestCase):
    def test_shutdown(self):
        code = textwrap.dedent(
            '\n            import atexit\n\n            def f(msg):\n                print(msg)\n\n            atexit.register(f, "one")\n            atexit.register(f, "two")\n        '
        )
        res = script_helper.assert_python_ok("-c", code)
        self.assertEqual(res.out.decode().splitlines(), ["two", "one"])
        self.assertFalse(res.err)

    def test_atexit_instances(self):
        code = textwrap.dedent(
            "\n            import sys\n            import atexit as atexit1\n            del sys.modules['atexit']\n            import atexit as atexit2\n            del sys.modules['atexit']\n\n            assert atexit2 is not atexit1\n\n            atexit1.register(print, \"atexit1\")\n            atexit2.register(print, \"atexit2\")\n        "
        )
        res = script_helper.assert_python_ok("-c", code)
        self.assertEqual(res.out.decode().splitlines(), ["atexit2", "atexit1"])
        self.assertFalse(res.err)


@support.cpython_only
class SubinterpreterTest(unittest.TestCase):
    def test_callbacks_leak(self):
        n = atexit._ncallbacks()
        code = textwrap.dedent(
            "\n            import atexit\n            def f():\n                pass\n            atexit.register(f)\n            del atexit\n        "
        )
        ret = support.run_in_subinterp(code)
        self.assertEqual(ret, 0)
        self.assertEqual(atexit._ncallbacks(), n)

    def test_callbacks_leak_refcycle(self):
        n = atexit._ncallbacks()
        code = textwrap.dedent(
            "\n            import atexit\n            def f():\n                pass\n            atexit.register(f)\n            atexit.__atexit = atexit\n        "
        )
        ret = support.run_in_subinterp(code)
        self.assertEqual(ret, 0)
        self.assertEqual(atexit._ncallbacks(), n)

    def test_callback_on_subinterpreter_teardown(self):
        expected = b"The test has passed!"
        (r, w) = os.pipe()
        code = textwrap.dedent(
            '\n            import os\n            import atexit\n            def callback():\n                os.write({:d}, b"The test has passed!")\n            atexit.register(callback)\n        '.format(
                w
            )
        )
        ret = support.run_in_subinterp(code)
        os.close(w)
        self.assertEqual(os.read(r, len(expected)), expected)
        os.close(r)


if __name__ == "__main__":
    unittest.main()
