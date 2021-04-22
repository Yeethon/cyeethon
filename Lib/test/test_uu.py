"\nTests for uu module.\nNick Mathewson\n"
import unittest
from test.support import os_helper
import os
import stat
import sys
import uu
import io

plaintext = b"The symbols on top of your keyboard are !@#$%^&*()_+|~\n"
encodedtext = b"M5&AE('-Y;6)O;',@;VX@=&]P(&]F('EO=7(@:V5Y8F]A<F0@87)E(\"% (R0E\n*7B8J*\"E?*WQ^\"@  "


class FakeIO(io.TextIOWrapper):
    "Text I/O implementation using an in-memory buffer.\n\n    Can be a used as a drop-in replacement for sys.stdin and sys.stdout.\n    "

    def __init__(
        self, initial_value="", encoding="utf-8", errors="strict", newline="\n"
    ):
        super(FakeIO, self).__init__(
            io.BytesIO(), encoding=encoding, errors=errors, newline=newline
        )
        self._encoding = encoding
        self._errors = errors
        if initial_value:
            if not isinstance(initial_value, str):
                initial_value = str(initial_value)
            self.write(initial_value)
            self.seek(0)

    def getvalue(self):
        self.flush()
        return self.buffer.getvalue().decode(self._encoding, self._errors)


def encodedtextwrapped(mode, filename, backtick=False):
    if backtick:
        res = (
            bytes(("begin %03o %s\n" % (mode, filename)), "ascii")
            + encodedtext.replace(b" ", b"`")
        ) + b"\n`\nend\n"
    else:
        res = (
            bytes(("begin %03o %s\n" % (mode, filename)), "ascii") + encodedtext
        ) + b"\n \nend\n"
    return res


class UUTest(unittest.TestCase):
    def test_encode(self):
        inp = io.BytesIO(plaintext)
        out = io.BytesIO()
        uu.encode(inp, out, "t1")
        self.assertEqual(out.getvalue(), encodedtextwrapped(438, "t1"))
        inp = io.BytesIO(plaintext)
        out = io.BytesIO()
        uu.encode(inp, out, "t1", 420)
        self.assertEqual(out.getvalue(), encodedtextwrapped(420, "t1"))
        inp = io.BytesIO(plaintext)
        out = io.BytesIO()
        uu.encode(inp, out, "t1", backtick=True)
        self.assertEqual(out.getvalue(), encodedtextwrapped(438, "t1", True))
        with self.assertRaises(TypeError):
            uu.encode(inp, out, "t1", 420, True)

    def test_decode(self):
        for backtick in (True, False):
            inp = io.BytesIO(encodedtextwrapped(438, "t1", backtick=backtick))
            out = io.BytesIO()
            uu.decode(inp, out)
            self.assertEqual(out.getvalue(), plaintext)
            inp = io.BytesIO(
                (
                    (
                        b"UUencoded files may contain many lines,\n"
                        + b"even some that have 'begin' in them.\n"
                    )
                    + encodedtextwrapped(438, "t1", backtick=backtick)
                )
            )
            out = io.BytesIO()
            uu.decode(inp, out)
            self.assertEqual(out.getvalue(), plaintext)

    def test_truncatedinput(self):
        inp = io.BytesIO((b"begin 644 t1\n" + encodedtext))
        out = io.BytesIO()
        try:
            uu.decode(inp, out)
            self.fail("No exception raised")
        except uu.Error as e:
            self.assertEqual(str(e), "Truncated input file")

    def test_missingbegin(self):
        inp = io.BytesIO(b"")
        out = io.BytesIO()
        try:
            uu.decode(inp, out)
            self.fail("No exception raised")
        except uu.Error as e:
            self.assertEqual(str(e), "No valid begin line found in input file")

    def test_garbage_padding(self):
        encodedtext1 = b"begin 644 file\n!,___\n \nend\n"
        encodedtext2 = b"begin 644 file\n!,___\n`\nend\n"
        plaintext = b"3"
        for encodedtext in (encodedtext1, encodedtext2):
            with self.subTest("uu.decode()"):
                inp = io.BytesIO(encodedtext)
                out = io.BytesIO()
                uu.decode(inp, out, quiet=True)
                self.assertEqual(out.getvalue(), plaintext)
            with self.subTest("uu_codec"):
                import codecs

                decoded = codecs.decode(encodedtext, "uu_codec")
                self.assertEqual(decoded, plaintext)

    def test_newlines_escaped(self):
        inp = io.BytesIO(plaintext)
        out = io.BytesIO()
        filename = "test.txt\n\roverflow.txt"
        safefilename = b"test.txt\\n\\roverflow.txt"
        uu.encode(inp, out, filename)
        self.assertIn(safefilename, out.getvalue())


class UUStdIOTest(unittest.TestCase):
    def setUp(self):
        self.stdin = sys.stdin
        self.stdout = sys.stdout

    def tearDown(self):
        sys.stdin = self.stdin
        sys.stdout = self.stdout

    def test_encode(self):
        sys.stdin = FakeIO(plaintext.decode("ascii"))
        sys.stdout = FakeIO()
        uu.encode("-", "-", "t1", 438)
        self.assertEqual(
            sys.stdout.getvalue(), encodedtextwrapped(438, "t1").decode("ascii")
        )

    def test_decode(self):
        sys.stdin = FakeIO(encodedtextwrapped(438, "t1").decode("ascii"))
        sys.stdout = FakeIO()
        uu.decode("-", "-")
        stdout = sys.stdout
        sys.stdout = self.stdout
        sys.stdin = self.stdin
        self.assertEqual(stdout.getvalue(), plaintext.decode("ascii"))


class UUFileTest(unittest.TestCase):
    def setUp(self):
        self.tmpin = os_helper.TESTFN_ASCII + "i"
        self.tmpout = os_helper.TESTFN_ASCII + "o"
        self.addCleanup(os_helper.unlink, self.tmpin)
        self.addCleanup(os_helper.unlink, self.tmpout)

    def test_encode(self):
        with open(self.tmpin, "wb") as fin:
            fin.write(plaintext)
        with open(self.tmpin, "rb") as fin:
            with open(self.tmpout, "wb") as fout:
                uu.encode(fin, fout, self.tmpin, mode=420)
        with open(self.tmpout, "rb") as fout:
            s = fout.read()
        self.assertEqual(s, encodedtextwrapped(420, self.tmpin))
        uu.encode(self.tmpin, self.tmpout, self.tmpin, mode=420)
        with open(self.tmpout, "rb") as fout:
            s = fout.read()
        self.assertEqual(s, encodedtextwrapped(420, self.tmpin))

    def test_decode(self):
        with open(self.tmpin, "wb") as f:
            f.write(encodedtextwrapped(420, self.tmpout))
        with open(self.tmpin, "rb") as f:
            uu.decode(f)
        with open(self.tmpout, "rb") as f:
            s = f.read()
        self.assertEqual(s, plaintext)

    def test_decode_filename(self):
        with open(self.tmpin, "wb") as f:
            f.write(encodedtextwrapped(420, self.tmpout))
        uu.decode(self.tmpin)
        with open(self.tmpout, "rb") as f:
            s = f.read()
        self.assertEqual(s, plaintext)

    def test_decodetwice(self):
        with open(self.tmpin, "wb") as f:
            f.write(encodedtextwrapped(420, self.tmpout))
        with open(self.tmpin, "rb") as f:
            uu.decode(f)
        with open(self.tmpin, "rb") as f:
            self.assertRaises(uu.Error, uu.decode, f)

    def test_decode_mode(self):
        expected_mode = 292
        with open(self.tmpin, "wb") as f:
            f.write(encodedtextwrapped(expected_mode, self.tmpout))
        self.addCleanup(os.chmod, self.tmpout, (expected_mode | stat.S_IWRITE))
        with open(self.tmpin, "rb") as f:
            uu.decode(f)
        self.assertEqual(stat.S_IMODE(os.stat(self.tmpout).st_mode), expected_mode)


if __name__ == "__main__":
    unittest.main()
