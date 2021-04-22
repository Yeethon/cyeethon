"Test warnings replacement in pyshell.py and run.py.\n\nThis file could be expanded to include traceback overrides\n(in same two modules). If so, change name.\nRevise if output destination changes (http://bugs.python.org/issue18318).\nMake sure warnings module is left unaltered (http://bugs.python.org/issue18081).\n"
from idlelib import run
from idlelib import pyshell as shell
import unittest
from test.support import captured_stderr
import warnings

showwarning = warnings.showwarning
running_in_idle = "idle" in showwarning.__name__
idlemsg = '\nWarning (from warnings module):\n  File "test_warning.py", line 99\n    Line of code\nUserWarning: Test\n'
shellmsg = idlemsg + ">>> "


class RunWarnTest(unittest.TestCase):
    @unittest.skipIf(running_in_idle, "Does not work when run within Idle.")
    def test_showwarnings(self):
        self.assertIs(warnings.showwarning, showwarning)
        run.capture_warnings(True)
        self.assertIs(warnings.showwarning, run.idle_showwarning_subproc)
        run.capture_warnings(False)
        self.assertIs(warnings.showwarning, showwarning)

    def test_run_show(self):
        with captured_stderr() as f:
            run.idle_showwarning_subproc(
                "Test", UserWarning, "test_warning.py", 99, f, "Line of code"
            )
            self.assertEqual(idlemsg.splitlines(), f.getvalue().splitlines())


class ShellWarnTest(unittest.TestCase):
    @unittest.skipIf(running_in_idle, "Does not work when run within Idle.")
    def test_showwarnings(self):
        self.assertIs(warnings.showwarning, showwarning)
        shell.capture_warnings(True)
        self.assertIs(warnings.showwarning, shell.idle_showwarning)
        shell.capture_warnings(False)
        self.assertIs(warnings.showwarning, showwarning)

    def test_idle_formatter(self):
        s = shell.idle_formatwarning(
            "Test", UserWarning, "test_warning.py", 99, "Line of code"
        )
        self.assertEqual(idlemsg, s)

    def test_shell_show(self):
        with captured_stderr() as f:
            shell.idle_showwarning(
                "Test", UserWarning, "test_warning.py", 99, f, "Line of code"
            )
            self.assertEqual(shellmsg.splitlines(), f.getvalue().splitlines())


if __name__ == "__main__":
    unittest.main(verbosity=2)
