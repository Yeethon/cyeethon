import errno
import os
import sys
import textwrap
import unittest
import subprocess
from test import support
from test.support import os_helper
from test.support.script_helper import assert_python_ok


class TestTool(unittest.TestCase):
    data = '\n\n        [["blorpie"],[ "whoops" ] , [\n                                 ],\t"d-shtaeou",\r"d-nthiouh",\n        "i-vhbjkhnth", {"nifty":87}, {"morefield" :\tfalse,"field"\n            :"yes"}  ]\n           '
    expect_without_sort_keys = textwrap.dedent(
        '    [\n        [\n            "blorpie"\n        ],\n        [\n            "whoops"\n        ],\n        [],\n        "d-shtaeou",\n        "d-nthiouh",\n        "i-vhbjkhnth",\n        {\n            "nifty": 87\n        },\n        {\n            "field": "yes",\n            "morefield": false\n        }\n    ]\n    '
    )
    expect = textwrap.dedent(
        '    [\n        [\n            "blorpie"\n        ],\n        [\n            "whoops"\n        ],\n        [],\n        "d-shtaeou",\n        "d-nthiouh",\n        "i-vhbjkhnth",\n        {\n            "nifty": 87\n        },\n        {\n            "morefield": false,\n            "field": "yes"\n        }\n    ]\n    '
    )
    jsonlines_raw = textwrap.dedent(
        '    {"ingredients":["frog", "water", "chocolate", "glucose"]}\n    {"ingredients":["chocolate","steel bolts"]}\n    '
    )
    jsonlines_expect = textwrap.dedent(
        '    {\n        "ingredients": [\n            "frog",\n            "water",\n            "chocolate",\n            "glucose"\n        ]\n    }\n    {\n        "ingredients": [\n            "chocolate",\n            "steel bolts"\n        ]\n    }\n    '
    )

    def test_stdin_stdout(self):
        args = (sys.executable, "-m", "json.tool")
        process = subprocess.run(
            args, input=self.data, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, self.expect)
        self.assertEqual(process.stderr, "")

    def _create_infile(self, data=None):
        infile = os_helper.TESTFN
        with open(infile, "w", encoding="utf-8") as fp:
            self.addCleanup(os.remove, infile)
            fp.write((data or self.data))
        return infile

    def test_infile_stdout(self):
        infile = self._create_infile()
        (rc, out, err) = assert_python_ok("-m", "json.tool", infile)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(), self.expect.encode().splitlines())
        self.assertEqual(err, b"")

    def test_non_ascii_infile(self):
        data = '{"msg": "こんにちは"}'
        expect = textwrap.dedent(
            '        {\n            "msg": "\\u3053\\u3093\\u306b\\u3061\\u306f"\n        }\n        '
        ).encode()
        infile = self._create_infile(data)
        (rc, out, err) = assert_python_ok("-m", "json.tool", infile)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(), expect.splitlines())
        self.assertEqual(err, b"")

    def test_infile_outfile(self):
        infile = self._create_infile()
        outfile = os_helper.TESTFN + ".out"
        (rc, out, err) = assert_python_ok("-m", "json.tool", infile, outfile)
        self.addCleanup(os.remove, outfile)
        with open(outfile, "r", encoding="utf-8") as fp:
            self.assertEqual(fp.read(), self.expect)
        self.assertEqual(rc, 0)
        self.assertEqual(out, b"")
        self.assertEqual(err, b"")

    def test_jsonlines(self):
        args = (sys.executable, "-m", "json.tool", "--json-lines")
        process = subprocess.run(
            args, input=self.jsonlines_raw, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, self.jsonlines_expect)
        self.assertEqual(process.stderr, "")

    def test_help_flag(self):
        (rc, out, err) = assert_python_ok("-m", "json.tool", "-h")
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith(b"usage: "))
        self.assertEqual(err, b"")

    def test_sort_keys_flag(self):
        infile = self._create_infile()
        (rc, out, err) = assert_python_ok("-m", "json.tool", "--sort-keys", infile)
        self.assertEqual(rc, 0)
        self.assertEqual(
            out.splitlines(), self.expect_without_sort_keys.encode().splitlines()
        )
        self.assertEqual(err, b"")

    def test_indent(self):
        input_ = "[1, 2]"
        expect = textwrap.dedent(
            "        [\n          1,\n          2\n        ]\n        "
        )
        args = (sys.executable, "-m", "json.tool", "--indent", "2")
        process = subprocess.run(
            args, input=input_, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, expect)
        self.assertEqual(process.stderr, "")

    def test_no_indent(self):
        input_ = "[1,\n2]"
        expect = "[1, 2]\n"
        args = (sys.executable, "-m", "json.tool", "--no-indent")
        process = subprocess.run(
            args, input=input_, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, expect)
        self.assertEqual(process.stderr, "")

    def test_tab(self):
        input_ = "[1, 2]"
        expect = "[\n\t1,\n\t2\n]\n"
        args = (sys.executable, "-m", "json.tool", "--tab")
        process = subprocess.run(
            args, input=input_, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, expect)
        self.assertEqual(process.stderr, "")

    def test_compact(self):
        input_ = "[ 1 ,\n 2]"
        expect = "[1,2]\n"
        args = (sys.executable, "-m", "json.tool", "--compact")
        process = subprocess.run(
            args, input=input_, capture_output=True, text=True, check=True
        )
        self.assertEqual(process.stdout, expect)
        self.assertEqual(process.stderr, "")

    def test_no_ensure_ascii_flag(self):
        infile = self._create_infile('{"key":"💩"}')
        outfile = os_helper.TESTFN + ".out"
        self.addCleanup(os.remove, outfile)
        assert_python_ok("-m", "json.tool", "--no-ensure-ascii", infile, outfile)
        with open(outfile, "rb") as f:
            lines = f.read().splitlines()
        expected = [b"{", b'    "key": "\xf0\x9f\x92\xa9"', b"}"]
        self.assertEqual(lines, expected)

    def test_ensure_ascii_default(self):
        infile = self._create_infile('{"key":"💩"}')
        outfile = os_helper.TESTFN + ".out"
        self.addCleanup(os.remove, outfile)
        assert_python_ok("-m", "json.tool", infile, outfile)
        with open(outfile, "rb") as f:
            lines = f.read().splitlines()
        expected = [b"{", b'    "key": "\\ud83d\\udca9"', b"}"]
        self.assertEqual(lines, expected)

    @unittest.skipIf(
        (sys.platform == "win32"), "The test is failed with ValueError on Windows"
    )
    def test_broken_pipe_error(self):
        cmd = [sys.executable, "-m", "json.tool"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        proc.stdout.close()
        proc.communicate(b'"{}"')
        self.assertEqual(proc.returncode, errno.EPIPE)
