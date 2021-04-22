"Basic test of the frozen module (source is in Python/frozen.c)."
import sys
import unittest
from test.support import captured_stdout


class TestFrozen(unittest.TestCase):
    def test_frozen(self):
        name = "__hello__"
        if name in sys.modules:
            del sys.modules[name]
        with captured_stdout() as out:
            import __hello__
        self.assertEqual(out.getvalue(), "Hello world!\n")


if __name__ == "__main__":
    unittest.main()
