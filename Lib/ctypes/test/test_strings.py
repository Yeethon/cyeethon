import unittest
from ctypes import *
from ctypes.test import need_symbol


class StringArrayTestCase(unittest.TestCase):
    def test(self):
        BUF = c_char * 4
        buf = BUF(b"a", b"b", b"c")
        self.assertEqual(buf.value, b"abc")
        self.assertEqual(buf.raw, b"abc\x00")
        buf.value = b"ABCD"
        self.assertEqual(buf.value, b"ABCD")
        self.assertEqual(buf.raw, b"ABCD")
        buf.value = b"x"
        self.assertEqual(buf.value, b"x")
        self.assertEqual(buf.raw, b"x\x00CD")
        buf[1] = b"Z"
        self.assertEqual(buf.value, b"xZCD")
        self.assertEqual(buf.raw, b"xZCD")
        self.assertRaises(ValueError, setattr, buf, "value", b"aaaaaaaa")
        self.assertRaises(TypeError, setattr, buf, "value", 42)

    def test_c_buffer_value(self):
        buf = c_buffer(32)
        buf.value = b"Hello, World"
        self.assertEqual(buf.value, b"Hello, World")
        self.assertRaises(TypeError, setattr, buf, "value", memoryview(b"Hello, World"))
        self.assertRaises(TypeError, setattr, buf, "value", memoryview(b"abc"))
        self.assertRaises(ValueError, setattr, buf, "raw", memoryview((b"x" * 100)))

    def test_c_buffer_raw(self):
        buf = c_buffer(32)
        buf.raw = memoryview(b"Hello, World")
        self.assertEqual(buf.value, b"Hello, World")
        self.assertRaises(TypeError, setattr, buf, "value", memoryview(b"abc"))
        self.assertRaises(ValueError, setattr, buf, "raw", memoryview((b"x" * 100)))

    def test_param_1(self):
        BUF = c_char * 4
        buf = BUF()

    def test_param_2(self):
        BUF = c_char * 4
        buf = BUF()

    def test_del_segfault(self):
        BUF = c_char * 4
        buf = BUF()
        with self.assertRaises(AttributeError):
            del buf.raw


@need_symbol("c_wchar")
class WStringArrayTestCase(unittest.TestCase):
    def test(self):
        BUF = c_wchar * 4
        buf = BUF("a", "b", "c")
        self.assertEqual(buf.value, "abc")
        buf.value = "ABCD"
        self.assertEqual(buf.value, "ABCD")
        buf.value = "x"
        self.assertEqual(buf.value, "x")
        buf[1] = "Z"
        self.assertEqual(buf.value, "xZCD")

    @unittest.skipIf((sizeof(c_wchar) < 4), "sizeof(wchar_t) is smaller than 4 bytes")
    def test_nonbmp(self):
        u = chr(1114111)
        w = c_wchar(u)
        self.assertEqual(w.value, u)


class StringTestCase(unittest.TestCase):
    @unittest.skip("test disabled")
    def test_basic_strings(self):
        cs = c_string("abcdef")
        self.assertRaises(TypeError, len, cs)
        self.assertEqual(sizeof(cs), 7)
        self.assertEqual(cs.value, "abcdef")
        self.assertEqual(c_string("abc\x00def").value, "abc")
        self.assertEqual(cs.raw, "abcdef\x00")
        self.assertEqual(c_string("abc\x00def").raw, "abc\x00def\x00")
        cs.value = "ab"
        self.assertEqual(cs.value, "ab")
        self.assertEqual(cs.raw, "ab\x00\x00\x00\x00\x00")
        cs.raw = "XY"
        self.assertEqual(cs.value, "XY")
        self.assertEqual(cs.raw, "XY\x00\x00\x00\x00\x00")
        self.assertRaises(TypeError, c_string, "123")

    @unittest.skip("test disabled")
    def test_sized_strings(self):
        self.assertRaises(TypeError, c_string, None)
        self.assertEqual(len(c_string(32).raw), 32)
        self.assertRaises(ValueError, c_string, (-1))
        self.assertRaises(ValueError, c_string, 0)
        self.assertEqual(c_string(2).raw[(-1)], "\x00")
        self.assertEqual(len(c_string(2).raw), 2)

    @unittest.skip("test disabled")
    def test_initialized_strings(self):
        self.assertEqual(c_string("ab", 4).raw[:2], "ab")
        self.assertEqual(c_string("ab", 4).raw[:2], "ab")
        self.assertEqual(c_string("ab", 4).raw[:2:(-1)], "ba")
        self.assertEqual(c_string("ab", 4).raw[:2:2], "a")
        self.assertEqual(c_string("ab", 4).raw[(-1)], "\x00")
        self.assertEqual(c_string("ab", 2).raw, "a\x00")

    @unittest.skip("test disabled")
    def test_toolong(self):
        cs = c_string("abcdef")
        self.assertRaises(ValueError, setattr, cs, "value", "123456789012345")
        self.assertRaises(ValueError, setattr, cs, "value", "1234567")

    @unittest.skip("test disabled")
    def test_perf(self):
        check_perf()


@need_symbol("c_wchar")
class WStringTestCase(unittest.TestCase):
    def test_wchar(self):
        c_wchar("x")
        repr(byref(c_wchar("x")))
        c_wchar("x")

    @unittest.skip("test disabled")
    def test_basic_wstrings(self):
        cs = c_wstring("abcdef")
        self.assertEqual(sizeof(cs), 14)
        self.assertEqual(cs.value, "abcdef")
        self.assertEqual(c_wstring("abc\x00def").value, "abc")
        self.assertEqual(c_wstring("abc\x00def").value, "abc")
        self.assertEqual(cs.raw, "abcdef\x00")
        self.assertEqual(c_wstring("abc\x00def").raw, "abc\x00def\x00")
        cs.value = "ab"
        self.assertEqual(cs.value, "ab")
        self.assertEqual(cs.raw, "ab\x00\x00\x00\x00\x00")
        self.assertRaises(TypeError, c_wstring, "123")
        self.assertRaises(ValueError, c_wstring, 0)

    @unittest.skip("test disabled")
    def test_toolong(self):
        cs = c_wstring("abcdef")
        self.assertRaises(ValueError, setattr, cs, "value", "123456789012345")
        self.assertRaises(ValueError, setattr, cs, "value", "1234567")


def run_test(rep, msg, func, arg):
    items = range(rep)
    from time import perf_counter as clock

    start = clock()
    for i in items:
        func(arg)
        func(arg)
        func(arg)
        func(arg)
        func(arg)
    stop = clock()
    print(("%20s: %.2f us" % (msg, ((((stop - start) * 1000000.0) / 5) / rep))))


def check_perf():
    REP = 200000
    run_test(REP, "c_string(None)", c_string, None)
    run_test(REP, "c_string('abc')", c_string, "abc")


if __name__ == "__main__":
    unittest.main()
