"Test the interactive interpreter."
import sys
import os
import unittest
import subprocess
from textwrap import dedent
from test.support import cpython_only, SuppressCrashReport
from test.support.script_helper import kill_python


def spawn_repl(*args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw):
    "Run the Python REPL with the given arguments.\n\n    kw is extra keyword args to pass to subprocess.Popen. Returns a Popen\n    object.\n    "
    stdin_fname = os.path.join(os.path.dirname(sys.executable), "<stdin>")
    cmd_line = [stdin_fname, "-E", "-i"]
    cmd_line.extend(args)
    env = kw.setdefault("env", dict(os.environ))
    env["TERM"] = "vt100"
    return subprocess.Popen(
        cmd_line,
        executable=sys.executable,
        text=True,
        stdin=subprocess.PIPE,
        stdout=stdout,
        stderr=stderr,
        **kw
    )


class TestInteractiveInterpreter(unittest.TestCase):
    @cpython_only
    def test_no_memory(self):
        user_input = "\n            import sys, _testcapi\n            1/0\n            print('After the exception.')\n            _testcapi.set_nomemory(0)\n            sys.exit(0)\n        "
        user_input = dedent(user_input)
        p = spawn_repl()
        with SuppressCrashReport():
            p.stdin.write(user_input)
        output = kill_python(p)
        self.assertIn("After the exception.", output)
        self.assertIn(p.returncode, (1, 120))

    @cpython_only
    def test_multiline_string_parsing(self):
        user_input = '        x = """<?xml version="1.0" encoding="iso-8859-1"?>\n        <test>\n            <Users>\n                <fun25>\n                    <limits>\n                        <total>0KiB</total>\n                        <kbps>0</kbps>\n                        <rps>1.3</rps>\n                        <connections>0</connections>\n                    </limits>\n                    <usages>\n                        <total>16738211KiB</total>\n                        <kbps>237.15</kbps>\n                        <rps>1.3</rps>\n                        <connections>0</connections>\n                    </usages>\n                    <time_to_refresh>never</time_to_refresh>\n                    <limit_exceeded_URL>none</limit_exceeded_URL>\n                </fun25>\n            </Users>\n        </test>"""\n        '
        user_input = dedent(user_input)
        p = spawn_repl()
        p.stdin.write(user_input)
        output = kill_python(p)
        self.assertEqual(p.returncode, 0)

    def test_close_stdin(self):
        user_input = dedent(
            '\n            import os\n            print("before close")\n            os.close(0)\n        '
        )
        prepare_repl = dedent(
            "\n            from test.support import suppress_msvcrt_asserts\n            suppress_msvcrt_asserts()\n        "
        )
        process = spawn_repl("-c", prepare_repl)
        output = process.communicate(user_input)[0]
        self.assertEqual(process.returncode, 0)
        self.assertIn("before close", output)


if __name__ == "__main__":
    unittest.main()
