"\nThis tests the '_objects' attribute of ctypes instances.  '_objects'\nholds references to objects that must be kept alive as long as the\nctypes instance, to make sure that the memory buffer is valid.\n\nWARNING: The '_objects' attribute is exposed ONLY for debugging ctypes itself,\nit MUST NEVER BE MODIFIED!\n\n'_objects' is initialized to a dictionary on first use, before that it\nis None.\n\nHere is an array of string pointers:\n\n>>> from ctypes import *\n>>> array = (c_char_p * 5)()\n>>> print(array._objects)\nNone\n>>>\n\nThe memory block stores pointers to strings, and the strings itself\nassigned from Python must be kept.\n\n>>> array[4] = b'foo bar'\n>>> array._objects\n{'4': b'foo bar'}\n>>> array[4]\nb'foo bar'\n>>>\n\nIt gets more complicated when the ctypes instance itself is contained\nin a 'base' object.\n\n>>> class X(Structure):\n...     _fields_ = [(\"x\", c_int), (\"y\", c_int), (\"array\", c_char_p * 5)]\n...\n>>> x = X()\n>>> print(x._objects)\nNone\n>>>\n\nThe'array' attribute of the 'x' object shares part of the memory buffer\nof 'x' ('_b_base_' is either None, or the root object owning the memory block):\n\n>>> print(x.array._b_base_) # doctest: +ELLIPSIS\n<ctypes.test.test_objects.X object at 0x...>\n>>>\n\n>>> x.array[0] = b'spam spam spam'\n>>> x._objects\n{'0:2': b'spam spam spam'}\n>>> x.array._b_base_._objects\n{'0:2': b'spam spam spam'}\n>>>\n\n"
import unittest, doctest
import ctypes.test.test_objects


class TestCase(unittest.TestCase):
    def test(self):
        (failures, tests) = doctest.testmod(ctypes.test.test_objects)
        self.assertFalse(failures, "doctests failed, see output above")


if __name__ == "__main__":
    doctest.testmod(ctypes.test.test_objects)
