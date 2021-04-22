"\nVery minimal unittests for parts of the readline module.\n"
from contextlib import ExitStack
from errno import EIO
import locale
import os
import selectors
import subprocess
import sys
import tempfile
import unittest
from test.support import verbose
from test.support.import_helper import import_module
from test.support.os_helper import unlink, temp_dir, TESTFN
from test.support.script_helper import assert_python_ok

readline = import_module("readline")
if hasattr(readline, "_READLINE_LIBRARY_VERSION"):
    is_editline = "EditLine wrapper" in readline._READLINE_LIBRARY_VERSION
else:
    is_editline = readline.__doc__ and ("libedit" in readline.__doc__)


def setUpModule():
    if verbose:
        if hasattr(readline, "_READLINE_VERSION"):
            print(f"readline version: {readline._READLINE_VERSION:#x}")
            print(f"readline runtime version: {readline._READLINE_RUNTIME_VERSION:#x}")
        if hasattr(readline, "_READLINE_LIBRARY_VERSION"):
            print(f"readline library version: {readline._READLINE_LIBRARY_VERSION!r}")
        print(f"use libedit emulation? {is_editline}")


@unittest.skipUnless(
    hasattr(readline, "clear_history"),
    "The history update test cannot be run because the clear_history method is not available.",
)
class TestHistoryManipulation(unittest.TestCase):
    '\n    These tests were added to check that the libedit emulation on OSX and the\n    "real" readline have the same interface for history manipulation. That\'s\n    why the tests cover only a small subset of the interface.\n    '

    def testHistoryUpdates(self):
        readline.clear_history()
        readline.add_history("first line")
        readline.add_history("second line")
        self.assertEqual(readline.get_history_item(0), None)
        self.assertEqual(readline.get_history_item(1), "first line")
        self.assertEqual(readline.get_history_item(2), "second line")
        readline.replace_history_item(0, "replaced line")
        self.assertEqual(readline.get_history_item(0), None)
        self.assertEqual(readline.get_history_item(1), "replaced line")
        self.assertEqual(readline.get_history_item(2), "second line")
        self.assertEqual(readline.get_current_history_length(), 2)
        readline.remove_history_item(0)
        self.assertEqual(readline.get_history_item(0), None)
        self.assertEqual(readline.get_history_item(1), "second line")
        self.assertEqual(readline.get_current_history_length(), 1)

    @unittest.skipUnless(
        hasattr(readline, "append_history_file"), "append_history not available"
    )
    def test_write_read_append(self):
        hfile = tempfile.NamedTemporaryFile(delete=False)
        hfile.close()
        hfilename = hfile.name
        self.addCleanup(unlink, hfilename)
        readline.clear_history()
        readline.add_history("first line")
        readline.add_history("second line")
        readline.write_history_file(hfilename)
        readline.clear_history()
        self.assertEqual(readline.get_current_history_length(), 0)
        readline.read_history_file(hfilename)
        self.assertEqual(readline.get_current_history_length(), 2)
        self.assertEqual(readline.get_history_item(1), "first line")
        self.assertEqual(readline.get_history_item(2), "second line")
        readline.append_history_file(1, hfilename)
        readline.clear_history()
        readline.read_history_file(hfilename)
        self.assertEqual(readline.get_current_history_length(), 3)
        self.assertEqual(readline.get_history_item(1), "first line")
        self.assertEqual(readline.get_history_item(2), "second line")
        self.assertEqual(readline.get_history_item(3), "second line")
        os.unlink(hfilename)
        try:
            readline.append_history_file(1, hfilename)
        except FileNotFoundError:
            pass
        else:
            os.unlink(hfilename)
        readline.write_history_file(hfilename)

    def test_nonascii_history(self):
        readline.clear_history()
        try:
            readline.add_history("entrée 1")
        except UnicodeEncodeError as err:
            self.skipTest(("Locale cannot encode test data: " + format(err)))
        readline.add_history("entrée 2")
        readline.replace_history_item(1, "entrée 22")
        readline.write_history_file(TESTFN)
        self.addCleanup(os.remove, TESTFN)
        readline.clear_history()
        readline.read_history_file(TESTFN)
        if is_editline:
            readline.add_history("dummy")
        self.assertEqual(readline.get_history_item(1), "entrée 1")
        self.assertEqual(readline.get_history_item(2), "entrée 22")


class TestReadline(unittest.TestCase):
    @unittest.skipIf(
        ((readline._READLINE_VERSION < 1537) and (not is_editline)),
        "not supported in this library version",
    )
    def test_init(self):
        (rc, stdout, stderr) = assert_python_ok(
            "-c", "import readline", TERM="xterm-256color"
        )
        self.assertEqual(stdout, b"")

    auto_history_script = 'import readline\nreadline.set_auto_history({})\ninput()\nprint("History length:", readline.get_current_history_length())\n'

    def test_auto_history_enabled(self):
        output = run_pty(self.auto_history_script.format(True))
        self.assertIn(b"History length: 1\r\n", output)

    def test_auto_history_disabled(self):
        output = run_pty(self.auto_history_script.format(False))
        self.assertIn(b"History length: 0\r\n", output)

    def test_nonascii(self):
        loc = locale.setlocale(locale.LC_CTYPE, None)
        if loc in ("C", "POSIX"):
            self.skipTest(f"the LC_CTYPE locale is {loc!r}")
        try:
            readline.add_history("ëï")
        except UnicodeEncodeError as err:
            self.skipTest(("Locale cannot encode test data: " + format(err)))
        script = 'import readline\n\nis_editline = readline.__doc__ and "libedit" in readline.__doc__\ninserted = "[\\xEFnserted]"\nmacro = "|t\\xEB[after]"\nset_pre_input_hook = getattr(readline, "set_pre_input_hook", None)\nif is_editline or not set_pre_input_hook:\n    # The insert_line() call via pre_input_hook() does nothing with Editline,\n    # so include the extra text that would have been inserted here\n    macro = inserted + macro\n\nif is_editline:\n    readline.parse_and_bind(r\'bind ^B ed-prev-char\')\n    readline.parse_and_bind(r\'bind "\\t" rl_complete\')\n    readline.parse_and_bind(r\'bind -s ^A "{}"\'.format(macro))\nelse:\n    readline.parse_and_bind(r\'Control-b: backward-char\')\n    readline.parse_and_bind(r\'"\\t": complete\')\n    readline.parse_and_bind(r\'set disable-completion off\')\n    readline.parse_and_bind(r\'set show-all-if-ambiguous off\')\n    readline.parse_and_bind(r\'set show-all-if-unmodified off\')\n    readline.parse_and_bind(r\'Control-a: "{}"\'.format(macro))\n\ndef pre_input_hook():\n    readline.insert_text(inserted)\n    readline.redisplay()\nif set_pre_input_hook:\n    set_pre_input_hook(pre_input_hook)\n\ndef completer(text, state):\n    if text == "t\\xEB":\n        if state == 0:\n            print("text", ascii(text))\n            print("line", ascii(readline.get_line_buffer()))\n            print("indexes", readline.get_begidx(), readline.get_endidx())\n            return "t\\xEBnt"\n        if state == 1:\n            return "t\\xEBxt"\n    if text == "t\\xEBx" and state == 0:\n        return "t\\xEBxt"\n    return None\nreadline.set_completer(completer)\n\ndef display(substitution, matches, longest_match_length):\n    print("substitution", ascii(substitution))\n    print("matches", ascii(matches))\nreadline.set_completion_display_matches_hook(display)\n\nprint("result", ascii(input()))\nprint("history", ascii(readline.get_history_item(1)))\n'
        input = b"\x01"
        input += b"\x02" * len("[after]")
        input += b"\t\t"
        input += b"x\t"
        input += b"\r"
        output = run_pty(script, input)
        self.assertIn(b"text 't\\xeb'\r\n", output)
        self.assertIn(b"line '[\\xefnserted]|t\\xeb[after]'\r\n", output)
        if (sys.platform == "darwin") or (not is_editline):
            self.assertIn(b"indexes 11 13\r\n", output)
        if (not is_editline) and hasattr(readline, "set_pre_input_hook"):
            self.assertIn(b"substitution 't\\xeb'\r\n", output)
            self.assertIn(b"matches ['t\\xebnt', 't\\xebxt']\r\n", output)
        expected = b"'[\\xefnserted]|t\\xebxt[after]'"
        self.assertIn(((b"result " + expected) + b"\r\n"), output)
        self.assertIn(((b"history " + expected) + b"\r\n"), output)

    @unittest.skipIf(
        (readline._READLINE_VERSION < 1536),
        "this readline version does not support history-size",
    )
    @unittest.skipIf(is_editline, "editline history size configuration is broken")
    def test_history_size(self):
        history_size = 10
        with temp_dir() as test_dir:
            inputrc = os.path.join(test_dir, "inputrc")
            with open(inputrc, "wb") as f:
                f.write((b"set history-size %d\n" % history_size))
            history_file = os.path.join(test_dir, "history")
            with open(history_file, "wb") as f:
                data = b"".join(((b"item %d\n" % i) for i in range((history_size * 2))))
                f.write(data)
            script = '\nimport os\nimport readline\n\nhistory_file = os.environ["HISTORY_FILE"]\nreadline.read_history_file(history_file)\ninput()\nreadline.write_history_file(history_file)\n'
            env = dict(os.environ)
            env["INPUTRC"] = inputrc
            env["HISTORY_FILE"] = history_file
            run_pty(script, input=b"last input\r", env=env)
            with open(history_file, "rb") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), history_size)
            self.assertEqual(lines[(-1)].strip(), b"last input")


def run_pty(script, input=b"dummy input\r", env=None):
    pty = import_module("pty")
    output = bytearray()
    [master, slave] = pty.openpty()
    args = (sys.executable, "-c", script)
    proc = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave, env=env)
    os.close(slave)
    with ExitStack() as cleanup:
        cleanup.enter_context(proc)

        def terminate(proc):
            try:
                proc.terminate()
            except ProcessLookupError:
                pass

        cleanup.callback(terminate, proc)
        cleanup.callback(os.close, master)
        sel = cleanup.enter_context(selectors.SelectSelector())
        sel.register(master, (selectors.EVENT_READ | selectors.EVENT_WRITE))
        os.set_blocking(master, False)
        while True:
            for [_, events] in sel.select():
                if events & selectors.EVENT_READ:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError as err:
                        if err.errno != EIO:
                            raise
                        chunk = b""
                    if not chunk:
                        return output
                    output.extend(chunk)
                if events & selectors.EVENT_WRITE:
                    try:
                        input = input[os.write(master, input) :]
                    except OSError as err:
                        if err.errno != EIO:
                            raise
                        input = b""
                    if not input:
                        sel.modify(master, selectors.EVENT_READ)


if __name__ == "__main__":
    unittest.main()
