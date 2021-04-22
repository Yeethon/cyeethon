import unittest
from test import string_tests
from collections import UserString


class UserStringTest(
    string_tests.CommonTest,
    string_tests.MixinStrUnicodeUserStringTest,
    unittest.TestCase,
):
    type2test = UserString

    def checkequal(self, result, object, methodname, *args, **kwargs):
        result = self.fixtype(result)
        object = self.fixtype(object)
        realresult = getattr(object, methodname)(*args, **kwargs)
        self.assertEqual(result, realresult)

    def checkraises(self, exc, obj, methodname, *args):
        obj = self.fixtype(obj)
        with self.assertRaises(exc) as cm:
            getattr(obj, methodname)(*args)
        self.assertNotEqual(str(cm.exception), "")

    def checkcall(self, object, methodname, *args):
        object = self.fixtype(object)
        getattr(object, methodname)(*args)

    def test_rmod(self):
        class ustr2(UserString):
            pass

        class ustr3(ustr2):
            def __rmod__(self, other):
                return super().__rmod__(other)

        fmt2 = ustr2("value is %s")
        str3 = ustr3("TEST")
        self.assertEqual((fmt2 % str3), "value is TEST")

    def test_encode_default_args(self):
        self.checkequal(b"hello", "hello", "encode")
        self.checkequal(b"\xf0\xa3\x91\x96", "𣑖", "encode")
        self.checkraises(UnicodeError, "\ud800", "encode")

    def test_encode_explicit_none_args(self):
        self.checkequal(b"hello", "hello", "encode", None, None)
        self.checkequal(b"\xf0\xa3\x91\x96", "𣑖", "encode", None, None)
        self.checkraises(UnicodeError, "\ud800", "encode", None, None)


if __name__ == "__main__":
    unittest.main()
