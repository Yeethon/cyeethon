import os
import textwrap
import unittest
from test.support import os_helper
from test.support.script_helper import assert_python_ok


class TestLLTrace(unittest.TestCase):
    def test_lltrace_does_not_crash_on_subscript_operator(self):
        with open(os_helper.TESTFN, "w", encoding="utf-8") as fd:
            self.addCleanup(os_helper.unlink, os_helper.TESTFN)
            fd.write(
                textwrap.dedent(
                    "            import code\n\n            console = code.InteractiveConsole()\n            console.push('__ltrace__ = 1')\n            console.push('a = [1, 2, 3]')\n            console.push('a[0] = 1')\n            print('unreachable if bug exists')\n            "
                )
            )
            assert_python_ok(os_helper.TESTFN)


if __name__ == "__main__":
    unittest.main()
