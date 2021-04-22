import collections
import copyreg
import dbm
import io
import functools
import os
import math
import pickle
import pickletools
import shutil
import struct
import sys
import threading
import unittest
import weakref
from textwrap import dedent
from http.cookies import SimpleCookie

try:
    import _testbuffer
except ImportError:
    _testbuffer = None
from test import support
from test.support import os_helper
from test.support import TestFailed, run_with_locale, no_tracing, _2G, _4G, bigmemtest
from test.support.import_helper import forget
from test.support.os_helper import TESTFN
from test.support import threading_helper
from test.support.warnings_helper import save_restore_warnings_filters
from pickle import bytes_types

try:
    with save_restore_warnings_filters():
        import numpy as np
except ImportError:
    np = None
requires_32b = unittest.skipUnless(
    (sys.maxsize < (2 ** 32)), "test is only meaningful on 32-bit builds"
)
protocols = range((pickle.HIGHEST_PROTOCOL + 1))


def opcode_in_pickle(code, pickle):
    for (op, dummy, dummy) in pickletools.genops(pickle):
        if op.code == code.decode("latin-1"):
            return True
    return False


def count_opcode(code, pickle):
    n = 0
    for (op, dummy, dummy) in pickletools.genops(pickle):
        if op.code == code.decode("latin-1"):
            n += 1
    return n


def identity(x):
    return x


class UnseekableIO(io.BytesIO):
    def peek(self, *args):
        raise NotImplementedError

    def seekable(self):
        return False

    def seek(self, *args):
        raise io.UnsupportedOperation

    def tell(self):
        raise io.UnsupportedOperation


class MinimalIO(object):
    "\n    A file-like object that doesn't support readinto().\n    "

    def __init__(self, *args):
        self._bio = io.BytesIO(*args)
        self.getvalue = self._bio.getvalue
        self.read = self._bio.read
        self.readline = self._bio.readline
        self.write = self._bio.write


class ExtensionSaver:
    def __init__(self, code):
        self.code = code
        if code in copyreg._inverted_registry:
            self.pair = copyreg._inverted_registry[code]
            copyreg.remove_extension(self.pair[0], self.pair[1], code)
        else:
            self.pair = None

    def restore(self):
        code = self.code
        curpair = copyreg._inverted_registry.get(code)
        if curpair is not None:
            copyreg.remove_extension(curpair[0], curpair[1], code)
        pair = self.pair
        if pair is not None:
            copyreg.add_extension(pair[0], pair[1], code)


class C:
    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class D(C):
    def __init__(self, arg):
        pass


class E(C):
    def __getinitargs__(self):
        return ()


class Object:
    pass


class K:
    def __init__(self, value):
        self.value = value

    def __reduce__(self):
        return (K, (self.value,))


import __main__

__main__.C = C
C.__module__ = "__main__"
__main__.D = D
D.__module__ = "__main__"
__main__.E = E
E.__module__ = "__main__"


class myint(int):
    def __init__(self, x):
        self.str = str(x)


class initarg(C):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __getinitargs__(self):
        return (self.a, self.b)


class metaclass(type):
    pass


class use_metaclass(object, metaclass=metaclass):
    pass


class pickling_metaclass(type):
    def __eq__(self, other):
        return (type(self) == type(other)) and (self.reduce_args == other.reduce_args)

    def __reduce__(self):
        return (create_dynamic_class, self.reduce_args)


def create_dynamic_class(name, bases):
    result = pickling_metaclass(name, bases, dict())
    result.reduce_args = (name, bases)
    return result


class ZeroCopyBytes(bytes):
    readonly = True
    c_contiguous = True
    f_contiguous = True
    zero_copy_reconstruct = True

    def __reduce_ex__(self, protocol):
        if protocol >= 5:
            return (type(self)._reconstruct, (pickle.PickleBuffer(self),), None)
        else:
            return (type(self)._reconstruct, (bytes(self),))

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, bytes(self))

    __str__ = __repr__

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as m:
            obj = m.obj
            if type(obj) is cls:
                return obj
            else:
                return cls(obj)


class ZeroCopyBytearray(bytearray):
    readonly = False
    c_contiguous = True
    f_contiguous = True
    zero_copy_reconstruct = True

    def __reduce_ex__(self, protocol):
        if protocol >= 5:
            return (type(self)._reconstruct, (pickle.PickleBuffer(self),), None)
        else:
            return (type(self)._reconstruct, (bytes(self),))

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, bytes(self))

    __str__ = __repr__

    @classmethod
    def _reconstruct(cls, obj):
        with memoryview(obj) as m:
            obj = m.obj
            if type(obj) is cls:
                return obj
            else:
                return cls(obj)


if _testbuffer is not None:

    class PicklableNDArray:
        zero_copy_reconstruct = False

        def __init__(self, *args, **kwargs):
            self.array = _testbuffer.ndarray(*args, **kwargs)

        def __getitem__(self, idx):
            cls = type(self)
            new = cls.__new__(cls)
            new.array = self.array[idx]
            return new

        @property
        def readonly(self):
            return self.array.readonly

        @property
        def c_contiguous(self):
            return self.array.c_contiguous

        @property
        def f_contiguous(self):
            return self.array.f_contiguous

        def __eq__(self, other):
            if not isinstance(other, PicklableNDArray):
                return NotImplemented
            return (
                (other.array.format == self.array.format)
                and (other.array.shape == self.array.shape)
                and (other.array.strides == self.array.strides)
                and (other.array.readonly == self.array.readonly)
                and (other.array.tobytes() == self.array.tobytes())
            )

        def __ne__(self, other):
            if not isinstance(other, PicklableNDArray):
                return NotImplemented
            return not (self == other)

        def __repr__(self):
            return f"{type(self)}(shape={self.array.shape},strides={self.array.strides}, bytes={self.array.tobytes()})"

        def __reduce_ex__(self, protocol):
            if not self.array.contiguous:
                raise NotImplementedError(
                    "Reconstructing a non-contiguous ndarray does not seem possible"
                )
            ndarray_kwargs = {
                "shape": self.array.shape,
                "strides": self.array.strides,
                "format": self.array.format,
                "flags": (0 if self.readonly else _testbuffer.ND_WRITABLE),
            }
            pb = pickle.PickleBuffer(self.array)
            if protocol >= 5:
                return (type(self)._reconstruct, (pb, ndarray_kwargs))
            else:
                with pb.raw() as m:
                    return (type(self)._reconstruct, (m.tobytes(), ndarray_kwargs))

        @classmethod
        def _reconstruct(cls, obj, kwargs):
            with memoryview(obj) as m:
                items = list(m.tobytes())
            return cls(items, **kwargs)


DATA0 = b"(lp0\nL0L\naL1L\naF2.0\nac__builtin__\ncomplex\np1\n(F3.0\nF0.0\ntp2\nRp3\naL1L\naL-1L\naL255L\naL-255L\naL-256L\naL65535L\naL-65535L\naL-65536L\naL2147483647L\naL-2147483647L\naL-2147483648L\na(Vabc\np4\ng4\nccopy_reg\n_reconstructor\np5\n(c__main__\nC\np6\nc__builtin__\nobject\np7\nNtp8\nRp9\n(dp10\nVfoo\np11\nL1L\nsVbar\np12\nL2L\nsbg9\ntp13\nag13\naL5L\na."
DATA0_DIS = "    0: (    MARK\n    1: l        LIST       (MARK at 0)\n    2: p    PUT        0\n    5: L    LONG       0\n    9: a    APPEND\n   10: L    LONG       1\n   14: a    APPEND\n   15: F    FLOAT      2.0\n   20: a    APPEND\n   21: c    GLOBAL     '__builtin__ complex'\n   42: p    PUT        1\n   45: (    MARK\n   46: F        FLOAT      3.0\n   51: F        FLOAT      0.0\n   56: t        TUPLE      (MARK at 45)\n   57: p    PUT        2\n   60: R    REDUCE\n   61: p    PUT        3\n   64: a    APPEND\n   65: L    LONG       1\n   69: a    APPEND\n   70: L    LONG       -1\n   75: a    APPEND\n   76: L    LONG       255\n   82: a    APPEND\n   83: L    LONG       -255\n   90: a    APPEND\n   91: L    LONG       -256\n   98: a    APPEND\n   99: L    LONG       65535\n  107: a    APPEND\n  108: L    LONG       -65535\n  117: a    APPEND\n  118: L    LONG       -65536\n  127: a    APPEND\n  128: L    LONG       2147483647\n  141: a    APPEND\n  142: L    LONG       -2147483647\n  156: a    APPEND\n  157: L    LONG       -2147483648\n  171: a    APPEND\n  172: (    MARK\n  173: V        UNICODE    'abc'\n  178: p        PUT        4\n  181: g        GET        4\n  184: c        GLOBAL     'copy_reg _reconstructor'\n  209: p        PUT        5\n  212: (        MARK\n  213: c            GLOBAL     '__main__ C'\n  225: p            PUT        6\n  228: c            GLOBAL     '__builtin__ object'\n  248: p            PUT        7\n  251: N            NONE\n  252: t            TUPLE      (MARK at 212)\n  253: p        PUT        8\n  256: R        REDUCE\n  257: p        PUT        9\n  260: (        MARK\n  261: d            DICT       (MARK at 260)\n  262: p        PUT        10\n  266: V        UNICODE    'foo'\n  271: p        PUT        11\n  275: L        LONG       1\n  279: s        SETITEM\n  280: V        UNICODE    'bar'\n  285: p        PUT        12\n  289: L        LONG       2\n  293: s        SETITEM\n  294: b        BUILD\n  295: g        GET        9\n  298: t        TUPLE      (MARK at 172)\n  299: p    PUT        13\n  303: a    APPEND\n  304: g    GET        13\n  308: a    APPEND\n  309: L    LONG       5\n  313: a    APPEND\n  314: .    STOP\nhighest protocol among opcodes = 0\n"
DATA1 = b"]q\x00(K\x00K\x01G@\x00\x00\x00\x00\x00\x00\x00c__builtin__\ncomplex\nq\x01(G@\x08\x00\x00\x00\x00\x00\x00G\x00\x00\x00\x00\x00\x00\x00\x00tq\x02Rq\x03K\x01J\xff\xff\xff\xffK\xffJ\x01\xff\xff\xffJ\x00\xff\xff\xffM\xff\xffJ\x01\x00\xff\xffJ\x00\x00\xff\xffJ\xff\xff\xff\x7fJ\x01\x00\x00\x80J\x00\x00\x00\x80(X\x03\x00\x00\x00abcq\x04h\x04ccopy_reg\n_reconstructor\nq\x05(c__main__\nC\nq\x06c__builtin__\nobject\nq\x07Ntq\x08Rq\t}q\n(X\x03\x00\x00\x00fooq\x0bK\x01X\x03\x00\x00\x00barq\x0cK\x02ubh\ttq\rh\rK\x05e."
DATA1_DIS = "    0: ]    EMPTY_LIST\n    1: q    BINPUT     0\n    3: (    MARK\n    4: K        BININT1    0\n    6: K        BININT1    1\n    8: G        BINFLOAT   2.0\n   17: c        GLOBAL     '__builtin__ complex'\n   38: q        BINPUT     1\n   40: (        MARK\n   41: G            BINFLOAT   3.0\n   50: G            BINFLOAT   0.0\n   59: t            TUPLE      (MARK at 40)\n   60: q        BINPUT     2\n   62: R        REDUCE\n   63: q        BINPUT     3\n   65: K        BININT1    1\n   67: J        BININT     -1\n   72: K        BININT1    255\n   74: J        BININT     -255\n   79: J        BININT     -256\n   84: M        BININT2    65535\n   87: J        BININT     -65535\n   92: J        BININT     -65536\n   97: J        BININT     2147483647\n  102: J        BININT     -2147483647\n  107: J        BININT     -2147483648\n  112: (        MARK\n  113: X            BINUNICODE 'abc'\n  121: q            BINPUT     4\n  123: h            BINGET     4\n  125: c            GLOBAL     'copy_reg _reconstructor'\n  150: q            BINPUT     5\n  152: (            MARK\n  153: c                GLOBAL     '__main__ C'\n  165: q                BINPUT     6\n  167: c                GLOBAL     '__builtin__ object'\n  187: q                BINPUT     7\n  189: N                NONE\n  190: t                TUPLE      (MARK at 152)\n  191: q            BINPUT     8\n  193: R            REDUCE\n  194: q            BINPUT     9\n  196: }            EMPTY_DICT\n  197: q            BINPUT     10\n  199: (            MARK\n  200: X                BINUNICODE 'foo'\n  208: q                BINPUT     11\n  210: K                BININT1    1\n  212: X                BINUNICODE 'bar'\n  220: q                BINPUT     12\n  222: K                BININT1    2\n  224: u                SETITEMS   (MARK at 199)\n  225: b            BUILD\n  226: h            BINGET     9\n  228: t            TUPLE      (MARK at 112)\n  229: q        BINPUT     13\n  231: h        BINGET     13\n  233: K        BININT1    5\n  235: e        APPENDS    (MARK at 3)\n  236: .    STOP\nhighest protocol among opcodes = 1\n"
DATA2 = b"\x80\x02]q\x00(K\x00K\x01G@\x00\x00\x00\x00\x00\x00\x00c__builtin__\ncomplex\nq\x01G@\x08\x00\x00\x00\x00\x00\x00G\x00\x00\x00\x00\x00\x00\x00\x00\x86q\x02Rq\x03K\x01J\xff\xff\xff\xffK\xffJ\x01\xff\xff\xffJ\x00\xff\xff\xffM\xff\xffJ\x01\x00\xff\xffJ\x00\x00\xff\xffJ\xff\xff\xff\x7fJ\x01\x00\x00\x80J\x00\x00\x00\x80(X\x03\x00\x00\x00abcq\x04h\x04c__main__\nC\nq\x05)\x81q\x06}q\x07(X\x03\x00\x00\x00fooq\x08K\x01X\x03\x00\x00\x00barq\tK\x02ubh\x06tq\nh\nK\x05e."
DATA2_DIS = "    0: \x80 PROTO      2\n    2: ]    EMPTY_LIST\n    3: q    BINPUT     0\n    5: (    MARK\n    6: K        BININT1    0\n    8: K        BININT1    1\n   10: G        BINFLOAT   2.0\n   19: c        GLOBAL     '__builtin__ complex'\n   40: q        BINPUT     1\n   42: G        BINFLOAT   3.0\n   51: G        BINFLOAT   0.0\n   60: \x86     TUPLE2\n   61: q        BINPUT     2\n   63: R        REDUCE\n   64: q        BINPUT     3\n   66: K        BININT1    1\n   68: J        BININT     -1\n   73: K        BININT1    255\n   75: J        BININT     -255\n   80: J        BININT     -256\n   85: M        BININT2    65535\n   88: J        BININT     -65535\n   93: J        BININT     -65536\n   98: J        BININT     2147483647\n  103: J        BININT     -2147483647\n  108: J        BININT     -2147483648\n  113: (        MARK\n  114: X            BINUNICODE 'abc'\n  122: q            BINPUT     4\n  124: h            BINGET     4\n  126: c            GLOBAL     '__main__ C'\n  138: q            BINPUT     5\n  140: )            EMPTY_TUPLE\n  141: \x81         NEWOBJ\n  142: q            BINPUT     6\n  144: }            EMPTY_DICT\n  145: q            BINPUT     7\n  147: (            MARK\n  148: X                BINUNICODE 'foo'\n  156: q                BINPUT     8\n  158: K                BININT1    1\n  160: X                BINUNICODE 'bar'\n  168: q                BINPUT     9\n  170: K                BININT1    2\n  172: u                SETITEMS   (MARK at 147)\n  173: b            BUILD\n  174: h            BINGET     6\n  176: t            TUPLE      (MARK at 113)\n  177: q        BINPUT     10\n  179: h        BINGET     10\n  181: K        BININT1    5\n  183: e        APPENDS    (MARK at 5)\n  184: .    STOP\nhighest protocol among opcodes = 2\n"
DATA3 = b"\x80\x03]q\x00(K\x00K\x01G@\x00\x00\x00\x00\x00\x00\x00cbuiltins\ncomplex\nq\x01G@\x08\x00\x00\x00\x00\x00\x00G\x00\x00\x00\x00\x00\x00\x00\x00\x86q\x02Rq\x03K\x01J\xff\xff\xff\xffK\xffJ\x01\xff\xff\xffJ\x00\xff\xff\xffM\xff\xffJ\x01\x00\xff\xffJ\x00\x00\xff\xffJ\xff\xff\xff\x7fJ\x01\x00\x00\x80J\x00\x00\x00\x80(X\x03\x00\x00\x00abcq\x04h\x04c__main__\nC\nq\x05)\x81q\x06}q\x07(X\x03\x00\x00\x00barq\x08K\x02X\x03\x00\x00\x00fooq\tK\x01ubh\x06tq\nh\nK\x05e."
DATA3_DIS = "    0: \x80 PROTO      3\n    2: ]    EMPTY_LIST\n    3: q    BINPUT     0\n    5: (    MARK\n    6: K        BININT1    0\n    8: K        BININT1    1\n   10: G        BINFLOAT   2.0\n   19: c        GLOBAL     'builtins complex'\n   37: q        BINPUT     1\n   39: G        BINFLOAT   3.0\n   48: G        BINFLOAT   0.0\n   57: \x86     TUPLE2\n   58: q        BINPUT     2\n   60: R        REDUCE\n   61: q        BINPUT     3\n   63: K        BININT1    1\n   65: J        BININT     -1\n   70: K        BININT1    255\n   72: J        BININT     -255\n   77: J        BININT     -256\n   82: M        BININT2    65535\n   85: J        BININT     -65535\n   90: J        BININT     -65536\n   95: J        BININT     2147483647\n  100: J        BININT     -2147483647\n  105: J        BININT     -2147483648\n  110: (        MARK\n  111: X            BINUNICODE 'abc'\n  119: q            BINPUT     4\n  121: h            BINGET     4\n  123: c            GLOBAL     '__main__ C'\n  135: q            BINPUT     5\n  137: )            EMPTY_TUPLE\n  138: \x81         NEWOBJ\n  139: q            BINPUT     6\n  141: }            EMPTY_DICT\n  142: q            BINPUT     7\n  144: (            MARK\n  145: X                BINUNICODE 'bar'\n  153: q                BINPUT     8\n  155: K                BININT1    2\n  157: X                BINUNICODE 'foo'\n  165: q                BINPUT     9\n  167: K                BININT1    1\n  169: u                SETITEMS   (MARK at 144)\n  170: b            BUILD\n  171: h            BINGET     6\n  173: t            TUPLE      (MARK at 110)\n  174: q        BINPUT     10\n  176: h        BINGET     10\n  178: K        BININT1    5\n  180: e        APPENDS    (MARK at 5)\n  181: .    STOP\nhighest protocol among opcodes = 2\n"
DATA4 = b"\x80\x04\x95\xa8\x00\x00\x00\x00\x00\x00\x00]\x94(K\x00K\x01G@\x00\x00\x00\x00\x00\x00\x00\x8c\x08builtins\x94\x8c\x07complex\x94\x93\x94G@\x08\x00\x00\x00\x00\x00\x00G\x00\x00\x00\x00\x00\x00\x00\x00\x86\x94R\x94K\x01J\xff\xff\xff\xffK\xffJ\x01\xff\xff\xffJ\x00\xff\xff\xffM\xff\xffJ\x01\x00\xff\xffJ\x00\x00\xff\xffJ\xff\xff\xff\x7fJ\x01\x00\x00\x80J\x00\x00\x00\x80(\x8c\x03abc\x94h\x06\x8c\x08__main__\x94\x8c\x01C\x94\x93\x94)\x81\x94}\x94(\x8c\x03bar\x94K\x02\x8c\x03foo\x94K\x01ubh\nt\x94h\x0eK\x05e."
DATA4_DIS = "    0: \x80 PROTO      4\n    2: \x95 FRAME      168\n   11: ]    EMPTY_LIST\n   12: \x94 MEMOIZE\n   13: (    MARK\n   14: K        BININT1    0\n   16: K        BININT1    1\n   18: G        BINFLOAT   2.0\n   27: \x8c     SHORT_BINUNICODE 'builtins'\n   37: \x94     MEMOIZE\n   38: \x8c     SHORT_BINUNICODE 'complex'\n   47: \x94     MEMOIZE\n   48: \x93     STACK_GLOBAL\n   49: \x94     MEMOIZE\n   50: G        BINFLOAT   3.0\n   59: G        BINFLOAT   0.0\n   68: \x86     TUPLE2\n   69: \x94     MEMOIZE\n   70: R        REDUCE\n   71: \x94     MEMOIZE\n   72: K        BININT1    1\n   74: J        BININT     -1\n   79: K        BININT1    255\n   81: J        BININT     -255\n   86: J        BININT     -256\n   91: M        BININT2    65535\n   94: J        BININT     -65535\n   99: J        BININT     -65536\n  104: J        BININT     2147483647\n  109: J        BININT     -2147483647\n  114: J        BININT     -2147483648\n  119: (        MARK\n  120: \x8c         SHORT_BINUNICODE 'abc'\n  125: \x94         MEMOIZE\n  126: h            BINGET     6\n  128: \x8c         SHORT_BINUNICODE '__main__'\n  138: \x94         MEMOIZE\n  139: \x8c         SHORT_BINUNICODE 'C'\n  142: \x94         MEMOIZE\n  143: \x93         STACK_GLOBAL\n  144: \x94         MEMOIZE\n  145: )            EMPTY_TUPLE\n  146: \x81         NEWOBJ\n  147: \x94         MEMOIZE\n  148: }            EMPTY_DICT\n  149: \x94         MEMOIZE\n  150: (            MARK\n  151: \x8c             SHORT_BINUNICODE 'bar'\n  156: \x94             MEMOIZE\n  157: K                BININT1    2\n  159: \x8c             SHORT_BINUNICODE 'foo'\n  164: \x94             MEMOIZE\n  165: K                BININT1    1\n  167: u                SETITEMS   (MARK at 150)\n  168: b            BUILD\n  169: h            BINGET     10\n  171: t            TUPLE      (MARK at 119)\n  172: \x94     MEMOIZE\n  173: h        BINGET     14\n  175: K        BININT1    5\n  177: e        APPENDS    (MARK at 13)\n  178: .    STOP\nhighest protocol among opcodes = 4\n"
DATA_SET = b"\x80\x02c__builtin__\nset\nq\x00]q\x01(K\x01K\x02e\x85q\x02Rq\x03."
DATA_XRANGE = b"\x80\x02c__builtin__\nxrange\nq\x00K\x00K\x05K\x01\x87q\x01Rq\x02."
DATA_COOKIE = b"\x80\x02cCookie\nSimpleCookie\nq\x00)\x81q\x01U\x03keyq\x02cCookie\nMorsel\nq\x03)\x81q\x04(U\x07commentq\x05U\x00q\x06U\x06domainq\x07h\x06U\x06secureq\x08h\x06U\x07expiresq\th\x06U\x07max-ageq\nh\x06U\x07versionq\x0bh\x06U\x04pathq\x0ch\x06U\x08httponlyq\rh\x06u}q\x0e(U\x0bcoded_valueq\x0fU\x05valueq\x10h\x10h\x10h\x02h\x02ubs}q\x11b."
DATA_SET2 = b"\x80\x02c__builtin__\nset\nq\x00]q\x01K\x03a\x85q\x02Rq\x03."
python2_exceptions_without_args = (
    ArithmeticError,
    AssertionError,
    AttributeError,
    BaseException,
    BufferError,
    BytesWarning,
    DeprecationWarning,
    EOFError,
    EnvironmentError,
    Exception,
    FloatingPointError,
    FutureWarning,
    GeneratorExit,
    IOError,
    ImportError,
    ImportWarning,
    IndentationError,
    IndexError,
    KeyError,
    KeyboardInterrupt,
    LookupError,
    MemoryError,
    NameError,
    NotImplementedError,
    OSError,
    OverflowError,
    PendingDeprecationWarning,
    ReferenceError,
    RuntimeError,
    RuntimeWarning,
    StopIteration,
    SyntaxError,
    SyntaxWarning,
    SystemError,
    SystemExit,
    TabError,
    TypeError,
    UnboundLocalError,
    UnicodeError,
    UnicodeWarning,
    UserWarning,
    ValueError,
    Warning,
    ZeroDivisionError,
)
exception_pickle = b"\x80\x02cexceptions\n?\nq\x00)Rq\x01."
DATA_UEERR = b"\x80\x02cexceptions\nUnicodeEncodeError\nq\x00(U\x05asciiq\x01X\x03\x00\x00\x00fooq\x02K\x00K\x01U\x03badq\x03tq\x04Rq\x05."


def create_data():
    c = C()
    c.foo = 1
    c.bar = 2
    x = [0, 1, 2.0, (3.0 + 0j)]
    uint1max = 255
    uint2max = 65535
    int4max = 2147483647
    x.extend(
        [
            1,
            (-1),
            uint1max,
            (-uint1max),
            ((-uint1max) - 1),
            uint2max,
            (-uint2max),
            ((-uint2max) - 1),
            int4max,
            (-int4max),
            ((-int4max) - 1),
        ]
    )
    y = ("abc", "abc", c, c)
    x.append(y)
    x.append(y)
    x.append(5)
    return x


class AbstractUnpickleTests(unittest.TestCase):
    _testdata = create_data()

    def assert_is_copy(self, obj, objcopy, msg=None):
        "Utility method to verify if two objects are copies of each others.\n        "
        if msg is None:
            msg = "{!r} is not a copy of {!r}".format(obj, objcopy)
        self.assertEqual(obj, objcopy, msg=msg)
        self.assertIs(type(obj), type(objcopy), msg=msg)
        if hasattr(obj, "__dict__"):
            self.assertDictEqual(obj.__dict__, objcopy.__dict__, msg=msg)
            self.assertIsNot(obj.__dict__, objcopy.__dict__, msg=msg)
        if hasattr(obj, "__slots__"):
            self.assertListEqual(obj.__slots__, objcopy.__slots__, msg=msg)
            for slot in obj.__slots__:
                self.assertEqual(hasattr(obj, slot), hasattr(objcopy, slot), msg=msg)
                self.assertEqual(
                    getattr(obj, slot, None), getattr(objcopy, slot, None), msg=msg
                )

    def check_unpickling_error(self, errors, data):
        with self.subTest(data=data), self.assertRaises(errors):
            try:
                self.loads(data)
            except BaseException as exc:
                if support.verbose > 1:
                    print(("%-32r - %s: %s" % (data, exc.__class__.__name__, exc)))
                raise

    def test_load_from_data0(self):
        self.assert_is_copy(self._testdata, self.loads(DATA0))

    def test_load_from_data1(self):
        self.assert_is_copy(self._testdata, self.loads(DATA1))

    def test_load_from_data2(self):
        self.assert_is_copy(self._testdata, self.loads(DATA2))

    def test_load_from_data3(self):
        self.assert_is_copy(self._testdata, self.loads(DATA3))

    def test_load_from_data4(self):
        self.assert_is_copy(self._testdata, self.loads(DATA4))

    def test_load_classic_instance(self):
        for (X, args) in [(C, ()), (D, ("x",)), (E, ())]:
            xname = X.__name__.encode("ascii")
            "\n             0: (    MARK\n             1: i        INST       '__main__ X' (MARK at 0)\n            13: p    PUT        0\n            16: (    MARK\n            17: d        DICT       (MARK at 16)\n            18: p    PUT        1\n            21: b    BUILD\n            22: .    STOP\n            "
            pickle0 = b"(i__main__\nX\np0\n(dp1\nb.".replace(b"X", xname)
            self.assert_is_copy(X(*args), self.loads(pickle0))
            "\n             0: (    MARK\n             1: c        GLOBAL     '__main__ X'\n            13: q        BINPUT     0\n            15: o        OBJ        (MARK at 0)\n            16: q    BINPUT     1\n            18: }    EMPTY_DICT\n            19: q    BINPUT     2\n            21: b    BUILD\n            22: .    STOP\n            "
            pickle1 = b"(c__main__\nX\nq\x00oq\x01}q\x02b.".replace(b"X", xname)
            self.assert_is_copy(X(*args), self.loads(pickle1))
            "\n             0: \x80 PROTO      2\n             2: (    MARK\n             3: c        GLOBAL     '__main__ X'\n            15: q        BINPUT     0\n            17: o        OBJ        (MARK at 2)\n            18: q    BINPUT     1\n            20: }    EMPTY_DICT\n            21: q    BINPUT     2\n            23: b    BUILD\n            24: .    STOP\n            "
            pickle2 = b"\x80\x02(c__main__\nX\nq\x00oq\x01}q\x02b.".replace(b"X", xname)
            self.assert_is_copy(X(*args), self.loads(pickle2))

    def test_maxint64(self):
        maxint64 = (1 << 63) - 1
        data = (b"I" + str(maxint64).encode("ascii")) + b"\n."
        got = self.loads(data)
        self.assert_is_copy(maxint64, got)
        data = (b"I" + str(maxint64).encode("ascii")) + b"JUNK\n."
        self.check_unpickling_error(ValueError, data)

    def test_unpickle_from_2x(self):
        loaded = self.loads(DATA_SET)
        self.assertEqual(loaded, set([1, 2]))
        loaded = self.loads(DATA_XRANGE)
        self.assertEqual(type(loaded), type(range(0)))
        self.assertEqual(list(loaded), list(range(5)))
        loaded = self.loads(DATA_COOKIE)
        self.assertEqual(type(loaded), SimpleCookie)
        self.assertEqual(list(loaded.keys()), ["key"])
        self.assertEqual(loaded["key"].value, "value")
        for exc in python2_exceptions_without_args:
            data = exception_pickle.replace(b"?", exc.__name__.encode("ascii"))
            loaded = self.loads(data)
            self.assertIs(type(loaded), exc)
        loaded = self.loads(exception_pickle.replace(b"?", b"StandardError"))
        self.assertIs(type(loaded), Exception)
        loaded = self.loads(DATA_UEERR)
        self.assertIs(type(loaded), UnicodeEncodeError)
        self.assertEqual(loaded.object, "foo")
        self.assertEqual(loaded.encoding, "ascii")
        self.assertEqual(loaded.start, 0)
        self.assertEqual(loaded.end, 1)
        self.assertEqual(loaded.reason, "bad")

    def test_load_python2_str_as_bytes(self):
        self.assertEqual(
            self.loads(b"S'a\\x00\\xa0'\n.", encoding="bytes"), b"a\x00\xa0"
        )
        self.assertEqual(self.loads(b"U\x03a\x00\xa0.", encoding="bytes"), b"a\x00\xa0")
        self.assertEqual(
            self.loads(b"\x80\x02U\x03a\x00\xa0.", encoding="bytes"), b"a\x00\xa0"
        )

    def test_load_python2_unicode_as_str(self):
        self.assertEqual(self.loads(b"V\\u03c0\n.", encoding="bytes"), "π")
        self.assertEqual(
            self.loads(b"X\x02\x00\x00\x00\xcf\x80.", encoding="bytes"), "π"
        )
        self.assertEqual(
            self.loads(b"\x80\x02X\x02\x00\x00\x00\xcf\x80.", encoding="bytes"), "π"
        )

    def test_load_long_python2_str_as_bytes(self):
        self.assertEqual(
            self.loads(
                (
                    ((pickle.BINSTRING + struct.pack("<I", 300)) + (b"x" * 300))
                    + pickle.STOP
                ),
                encoding="bytes",
            ),
            (b"x" * 300),
        )

    def test_constants(self):
        self.assertIsNone(self.loads(b"N."))
        self.assertIs(self.loads(b"\x88."), True)
        self.assertIs(self.loads(b"\x89."), False)
        self.assertIs(self.loads(b"I01\n."), True)
        self.assertIs(self.loads(b"I00\n."), False)

    def test_empty_bytestring(self):
        empty = self.loads(b"\x80\x03U\x00q\x00.", encoding="koi8-r")
        self.assertEqual(empty, "")

    def test_short_binbytes(self):
        dumped = b"\x80\x03C\x04\xe2\x82\xac\x00."
        self.assertEqual(self.loads(dumped), b"\xe2\x82\xac\x00")

    def test_binbytes(self):
        dumped = b"\x80\x03B\x04\x00\x00\x00\xe2\x82\xac\x00."
        self.assertEqual(self.loads(dumped), b"\xe2\x82\xac\x00")

    @requires_32b
    def test_negative_32b_binbytes(self):
        dumped = b"\x80\x03B\xff\xff\xff\xffxyzq\x00."
        self.check_unpickling_error((pickle.UnpicklingError, OverflowError), dumped)

    @requires_32b
    def test_negative_32b_binunicode(self):
        dumped = b"\x80\x03X\xff\xff\xff\xffxyzq\x00."
        self.check_unpickling_error((pickle.UnpicklingError, OverflowError), dumped)

    def test_short_binunicode(self):
        dumped = b"\x80\x04\x8c\x04\xe2\x82\xac\x00."
        self.assertEqual(self.loads(dumped), "€\x00")

    def test_misc_get(self):
        self.check_unpickling_error(pickle.UnpicklingError, b"g0\np0")
        self.check_unpickling_error(pickle.UnpicklingError, b"jens:")
        self.check_unpickling_error(pickle.UnpicklingError, b"hens:")
        self.assert_is_copy([(100,), (100,)], self.loads(b"((Kdtp0\nh\x00l.))"))

    def test_binbytes8(self):
        dumped = b"\x80\x04\x8e\x04\x00\x00\x00\x00\x00\x00\x00\xe2\x82\xac\x00."
        self.assertEqual(self.loads(dumped), b"\xe2\x82\xac\x00")

    def test_binunicode8(self):
        dumped = b"\x80\x04\x8d\x04\x00\x00\x00\x00\x00\x00\x00\xe2\x82\xac\x00."
        self.assertEqual(self.loads(dumped), "€\x00")

    def test_bytearray8(self):
        dumped = b"\x80\x05\x96\x03\x00\x00\x00\x00\x00\x00\x00xxx."
        self.assertEqual(self.loads(dumped), bytearray(b"xxx"))

    @requires_32b
    def test_large_32b_binbytes8(self):
        dumped = b"\x80\x04\x8e\x04\x00\x00\x00\x01\x00\x00\x00\xe2\x82\xac\x00."
        self.check_unpickling_error((pickle.UnpicklingError, OverflowError), dumped)

    @requires_32b
    def test_large_32b_bytearray8(self):
        dumped = b"\x80\x05\x96\x04\x00\x00\x00\x01\x00\x00\x00\xe2\x82\xac\x00."
        self.check_unpickling_error((pickle.UnpicklingError, OverflowError), dumped)

    @requires_32b
    def test_large_32b_binunicode8(self):
        dumped = b"\x80\x04\x8d\x04\x00\x00\x00\x01\x00\x00\x00\xe2\x82\xac\x00."
        self.check_unpickling_error((pickle.UnpicklingError, OverflowError), dumped)

    def test_get(self):
        pickled = b"((lp100000\ng100000\nt."
        unpickled = self.loads(pickled)
        self.assertEqual(unpickled, (([],) * 2))
        self.assertIs(unpickled[0], unpickled[1])

    def test_binget(self):
        pickled = b"(]q\xffh\xfft."
        unpickled = self.loads(pickled)
        self.assertEqual(unpickled, (([],) * 2))
        self.assertIs(unpickled[0], unpickled[1])

    def test_long_binget(self):
        pickled = b"(]r\x00\x00\x01\x00j\x00\x00\x01\x00t."
        unpickled = self.loads(pickled)
        self.assertEqual(unpickled, (([],) * 2))
        self.assertIs(unpickled[0], unpickled[1])

    def test_dup(self):
        pickled = b"((l2t."
        unpickled = self.loads(pickled)
        self.assertEqual(unpickled, (([],) * 2))
        self.assertIs(unpickled[0], unpickled[1])

    def test_negative_put(self):
        dumped = b"Va\np-1\n."
        self.check_unpickling_error(ValueError, dumped)

    @requires_32b
    def test_negative_32b_binput(self):
        dumped = b"\x80\x03X\x01\x00\x00\x00ar\xff\xff\xff\xff."
        self.check_unpickling_error(ValueError, dumped)

    def test_badly_escaped_string(self):
        self.check_unpickling_error(ValueError, b"S'\\'\n.")

    def test_badly_quoted_string(self):
        badpickles = [
            b"S'\n.",
            b'S"\n.',
            b"S' \n.",
            b'S" \n.',
            b"S'\"\n.",
            b"S\"'\n.",
            b"S' ' \n.",
            b'S" " \n.',
            b"S ''\n.",
            b'S ""\n.',
            b"S \n.",
            b"S\n.",
            b"S.",
        ]
        for p in badpickles:
            self.check_unpickling_error(pickle.UnpicklingError, p)

    def test_correctly_quoted_string(self):
        goodpickles = [
            (b"S''\n.", ""),
            (b'S""\n.', ""),
            (b'S"\\n"\n.', "\n"),
            (b"S'\\n'\n.", "\n"),
        ]
        for (p, expected) in goodpickles:
            self.assertEqual(self.loads(p), expected)

    def test_frame_readline(self):
        pickled = b"\x80\x04\x95\x05\x00\x00\x00\x00\x00\x00\x00I42\n."
        self.assertEqual(self.loads(pickled), 42)

    def test_compat_unpickle(self):
        pickled = b"\x80\x02c__builtin__\nxrange\nK\x01K\x07K\x01\x87R."
        unpickled = self.loads(pickled)
        self.assertIs(type(unpickled), range)
        self.assertEqual(unpickled, range(1, 7))
        self.assertEqual(list(unpickled), [1, 2, 3, 4, 5, 6])
        pickled = b"\x80\x02c__builtin__\nreduce\n."
        self.assertIs(self.loads(pickled), functools.reduce)
        pickled = b"\x80\x02cwhichdb\nwhichdb\n."
        self.assertIs(self.loads(pickled), dbm.whichdb)
        for name in (b"Exception", b"StandardError"):
            pickled = (b"\x80\x02cexceptions\n" + name) + b"\nU\x03ugh\x85R."
            unpickled = self.loads(pickled)
            self.assertIs(type(unpickled), Exception)
            self.assertEqual(str(unpickled), "ugh")
        for name in (b"UserDict", b"IterableUserDict"):
            pickled = (b"\x80\x02(cUserDict\n" + name) + b"\no}U\x04data}K\x01K\x02ssb."
            unpickled = self.loads(pickled)
            self.assertIs(type(unpickled), collections.UserDict)
            self.assertEqual(unpickled, collections.UserDict({1: 2}))

    def test_bad_reduce(self):
        self.assertEqual(self.loads(b"cbuiltins\nint\n)R."), 0)
        self.check_unpickling_error(TypeError, b"N)R.")
        self.check_unpickling_error(TypeError, b"cbuiltins\nint\nNR.")

    def test_bad_newobj(self):
        error = (pickle.UnpicklingError, TypeError)
        self.assertEqual(self.loads(b"cbuiltins\nint\n)\x81."), 0)
        self.check_unpickling_error(error, b"cbuiltins\nlen\n)\x81.")
        self.check_unpickling_error(error, b"cbuiltins\nint\nN\x81.")

    def test_bad_newobj_ex(self):
        error = (pickle.UnpicklingError, TypeError)
        self.assertEqual(self.loads(b"cbuiltins\nint\n)}\x92."), 0)
        self.check_unpickling_error(error, b"cbuiltins\nlen\n)}\x92.")
        self.check_unpickling_error(error, b"cbuiltins\nint\nN}\x92.")
        self.check_unpickling_error(error, b"cbuiltins\nint\n)N\x92.")

    def test_bad_stack(self):
        badpickles = [
            b".",
            b"0",
            b"1",
            b"2",
            b"(2",
            b"R",
            b")R",
            b"a",
            b"Na",
            b"b",
            b"Nb",
            b"d",
            b"e",
            b"(e",
            b"ibuiltins\nlist\n",
            b"l",
            b"o",
            b"(o",
            b"p1\n",
            b"q\x00",
            b"r\x00\x00\x00\x00",
            b"s",
            b"Ns",
            b"NNs",
            b"t",
            b"u",
            b"(u",
            b"}(Nu",
            b"\x81",
            b")\x81",
            b"\x85",
            b"\x86",
            b"N\x86",
            b"\x87",
            b"N\x87",
            b"NN\x87",
            b"\x90",
            b"(\x90",
            b"\x91",
            b"\x92",
            b")}\x92",
            b"\x93",
            b"Vlist\n\x93",
            b"\x94",
        ]
        for p in badpickles:
            self.check_unpickling_error(self.bad_stack_errors, p)

    def test_bad_mark(self):
        badpickles = [
            b"N(.",
            b"N(2",
            b"cbuiltins\nlist\n)(R",
            b"cbuiltins\nlist\n()R",
            b"]N(a",
            b"cbuiltins\nValueError\n)R}(b",
            b"cbuiltins\nValueError\n)R(}b",
            b"(Nd",
            b"N(p1\n",
            b"N(q\x00",
            b"N(r\x00\x00\x00\x00",
            b"}NN(s",
            b"}N(Ns",
            b"}(NNs",
            b"}((u",
            b"cbuiltins\nlist\n)(\x81",
            b"cbuiltins\nlist\n()\x81",
            b"N(\x85",
            b"NN(\x86",
            b"N(N\x86",
            b"NNN(\x87",
            b"NN(N\x87",
            b"N(NN\x87",
            b"]((\x90",
            b"cbuiltins\nlist\n)}(\x92",
            b"cbuiltins\nlist\n)(}\x92",
            b"cbuiltins\nlist\n()}\x92",
            b"Vbuiltins\n(Vlist\n\x93",
            b"Vbuiltins\nVlist\n(\x93",
            b"N(\x94",
        ]
        for p in badpickles:
            self.check_unpickling_error(self.bad_stack_errors, p)

    def test_truncated_data(self):
        self.check_unpickling_error(EOFError, b"")
        self.check_unpickling_error(EOFError, b"N")
        badpickles = [
            b"B",
            b"B\x03\x00\x00",
            b"B\x03\x00\x00\x00",
            b"B\x03\x00\x00\x00ab",
            b"C",
            b"C\x03",
            b"C\x03ab",
            b"F",
            b"F0.0",
            b"F0.00",
            b"G",
            b"G\x00\x00\x00\x00\x00\x00\x00",
            b"I",
            b"I0",
            b"J",
            b"J\x00\x00\x00",
            b"K",
            b"L",
            b"L0",
            b"L10",
            b"L0L",
            b"L10L",
            b"M",
            b"M\x00",
            b"S",
            b"S'abc'",
            b"T",
            b"T\x03\x00\x00",
            b"T\x03\x00\x00\x00",
            b"T\x03\x00\x00\x00ab",
            b"U",
            b"U\x03",
            b"U\x03ab",
            b"V",
            b"Vabc",
            b"X",
            b"X\x03\x00\x00",
            b"X\x03\x00\x00\x00",
            b"X\x03\x00\x00\x00ab",
            b"(c",
            b"(cbuiltins",
            b"(cbuiltins\n",
            b"(cbuiltins\nlist",
            b"Ng",
            b"Ng0",
            b"(i",
            b"(ibuiltins",
            b"(ibuiltins\n",
            b"(ibuiltins\nlist",
            b"Nh",
            b"Nj",
            b"Nj\x00\x00\x00",
            b"Np",
            b"Np0",
            b"Nq",
            b"Nr",
            b"Nr\x00\x00\x00",
            b"\x80",
            b"\x82",
            b"\x83",
            b"\x84\x01",
            b"\x84",
            b"\x84\x01\x00\x00",
            b"\x8a",
            b"\x8b",
            b"\x8b\x00\x00\x00",
            b"\x8c",
            b"\x8c\x03",
            b"\x8c\x03ab",
            b"\x8d",
            b"\x8d\x03\x00\x00\x00\x00\x00\x00",
            b"\x8d\x03\x00\x00\x00\x00\x00\x00\x00",
            b"\x8d\x03\x00\x00\x00\x00\x00\x00\x00ab",
            b"\x8e",
            b"\x8e\x03\x00\x00\x00\x00\x00\x00",
            b"\x8e\x03\x00\x00\x00\x00\x00\x00\x00",
            b"\x8e\x03\x00\x00\x00\x00\x00\x00\x00ab",
            b"\x96",
            b"\x96\x03\x00\x00\x00\x00\x00\x00",
            b"\x96\x03\x00\x00\x00\x00\x00\x00\x00",
            b"\x96\x03\x00\x00\x00\x00\x00\x00\x00ab",
            b"\x95",
            b"\x95\x02\x00\x00\x00\x00\x00\x00",
            b"\x95\x02\x00\x00\x00\x00\x00\x00\x00",
            b"\x95\x02\x00\x00\x00\x00\x00\x00\x00N",
        ]
        for p in badpickles:
            self.check_unpickling_error(self.truncated_errors, p)

    @threading_helper.reap_threads
    def test_unpickle_module_race(self):
        locker_module = dedent(
            "\n        import threading\n        barrier = threading.Barrier(2)\n        "
        )
        locking_import_module = dedent(
            "\n        import locker\n        locker.barrier.wait()\n        class ToBeUnpickled(object):\n            pass\n        "
        )
        os.mkdir(TESTFN)
        self.addCleanup(shutil.rmtree, TESTFN)
        sys.path.insert(0, TESTFN)
        self.addCleanup(sys.path.remove, TESTFN)
        with open(os.path.join(TESTFN, "locker.py"), "wb") as f:
            f.write(locker_module.encode("utf-8"))
        with open(os.path.join(TESTFN, "locking_import.py"), "wb") as f:
            f.write(locking_import_module.encode("utf-8"))
        self.addCleanup(forget, "locker")
        self.addCleanup(forget, "locking_import")
        import locker

        pickle_bytes = b"\x80\x03clocking_import\nToBeUnpickled\nq\x00)\x81q\x01."
        results = []
        barrier = threading.Barrier(3)

        def t():
            barrier.wait()
            results.append(pickle.loads(pickle_bytes))

        t1 = threading.Thread(target=t)
        t2 = threading.Thread(target=t)
        t1.start()
        t2.start()
        barrier.wait()
        locker.barrier.wait()
        t1.join()
        t2.join()
        from locking_import import ToBeUnpickled

        self.assertEqual([type(x) for x in results], ([ToBeUnpickled] * 2))


class AbstractPickleTests(unittest.TestCase):
    optimized = False
    _testdata = AbstractUnpickleTests._testdata

    def setUp(self):
        pass

    assert_is_copy = AbstractUnpickleTests.assert_is_copy

    def test_misc(self):
        for proto in protocols:
            x = myint(4)
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            x = (1, ())
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            x = initarg(1, x)
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)

    def test_roundtrip_equality(self):
        expected = self._testdata
        for proto in protocols:
            s = self.dumps(expected, proto)
            got = self.loads(s)
            self.assert_is_copy(expected, got)

    def dont_test_disassembly(self):
        from io import StringIO
        from pickletools import dis

        for (proto, expected) in ((0, DATA0_DIS), (1, DATA1_DIS)):
            s = self.dumps(self._testdata, proto)
            filelike = StringIO()
            dis(s, out=filelike)
            got = filelike.getvalue()
            self.assertEqual(expected, got)

    def _test_recursive_list(self, cls, aslist=identity, minprotocol=0):
        l = cls()
        l.append(l)
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(l, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = aslist(x)
            self.assertEqual(len(y), 1)
            self.assertIs(y[0], x)

    def test_recursive_list(self):
        self._test_recursive_list(list)

    def test_recursive_list_subclass(self):
        self._test_recursive_list(MyList, minprotocol=2)

    def test_recursive_list_like(self):
        self._test_recursive_list(REX_six, aslist=(lambda x: x.items))

    def _test_recursive_tuple_and_list(self, cls, aslist=identity, minprotocol=0):
        t = (cls(),)
        t[0].append(t)
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, tuple)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(x[0], cls)
            y = aslist(x[0])
            self.assertEqual(len(y), 1)
            self.assertIs(y[0], x)
        (t,) = t
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = aslist(x)
            self.assertEqual(len(y), 1)
            self.assertIsInstance(y[0], tuple)
            self.assertEqual(len(y[0]), 1)
            self.assertIs(y[0][0], x)

    def test_recursive_tuple_and_list(self):
        self._test_recursive_tuple_and_list(list)

    def test_recursive_tuple_and_list_subclass(self):
        self._test_recursive_tuple_and_list(MyList, minprotocol=2)

    def test_recursive_tuple_and_list_like(self):
        self._test_recursive_tuple_and_list(REX_six, aslist=(lambda x: x.items))

    def _test_recursive_dict(self, cls, asdict=identity, minprotocol=0):
        d = cls()
        d[1] = d
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(d, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = asdict(x)
            self.assertEqual(list(y.keys()), [1])
            self.assertIs(y[1], x)

    def test_recursive_dict(self):
        self._test_recursive_dict(dict)

    def test_recursive_dict_subclass(self):
        self._test_recursive_dict(MyDict, minprotocol=2)

    def test_recursive_dict_like(self):
        self._test_recursive_dict(REX_seven, asdict=(lambda x: x.table))

    def _test_recursive_tuple_and_dict(self, cls, asdict=identity, minprotocol=0):
        t = (cls(),)
        t[0][1] = t
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, tuple)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(x[0], cls)
            y = asdict(x[0])
            self.assertEqual(list(y), [1])
            self.assertIs(y[1], x)
        (t,) = t
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = asdict(x)
            self.assertEqual(list(y), [1])
            self.assertIsInstance(y[1], tuple)
            self.assertEqual(len(y[1]), 1)
            self.assertIs(y[1][0], x)

    def test_recursive_tuple_and_dict(self):
        self._test_recursive_tuple_and_dict(dict)

    def test_recursive_tuple_and_dict_subclass(self):
        self._test_recursive_tuple_and_dict(MyDict, minprotocol=2)

    def test_recursive_tuple_and_dict_like(self):
        self._test_recursive_tuple_and_dict(REX_seven, asdict=(lambda x: x.table))

    def _test_recursive_dict_key(self, cls, asdict=identity, minprotocol=0):
        d = cls()
        d[K(d)] = 1
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(d, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = asdict(x)
            self.assertEqual(len(y.keys()), 1)
            self.assertIsInstance(list(y.keys())[0], K)
            self.assertIs(list(y.keys())[0].value, x)

    def test_recursive_dict_key(self):
        self._test_recursive_dict_key(dict)

    def test_recursive_dict_subclass_key(self):
        self._test_recursive_dict_key(MyDict, minprotocol=2)

    def test_recursive_dict_like_key(self):
        self._test_recursive_dict_key(REX_seven, asdict=(lambda x: x.table))

    def _test_recursive_tuple_and_dict_key(self, cls, asdict=identity, minprotocol=0):
        t = (cls(),)
        t[0][K(t)] = 1
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, tuple)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(x[0], cls)
            y = asdict(x[0])
            self.assertEqual(len(y), 1)
            self.assertIsInstance(list(y.keys())[0], K)
            self.assertIs(list(y.keys())[0].value, x)
        (t,) = t
        for proto in range(minprotocol, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, cls)
            y = asdict(x)
            self.assertEqual(len(y), 1)
            self.assertIsInstance(list(y.keys())[0], K)
            self.assertIs(list(y.keys())[0].value[0], x)

    def test_recursive_tuple_and_dict_key(self):
        self._test_recursive_tuple_and_dict_key(dict)

    def test_recursive_tuple_and_dict_subclass_key(self):
        self._test_recursive_tuple_and_dict_key(MyDict, minprotocol=2)

    def test_recursive_tuple_and_dict_like_key(self):
        self._test_recursive_tuple_and_dict_key(REX_seven, asdict=(lambda x: x.table))

    def test_recursive_set(self):
        y = set()
        y.add(K(y))
        for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(y, proto)
            x = self.loads(s)
            self.assertIsInstance(x, set)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(list(x)[0], K)
            self.assertIs(list(x)[0].value, x)
        (y,) = y
        for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
            s = self.dumps(y, proto)
            x = self.loads(s)
            self.assertIsInstance(x, K)
            self.assertIsInstance(x.value, set)
            self.assertEqual(len(x.value), 1)
            self.assertIs(list(x.value)[0], x)

    def test_recursive_inst(self):
        i = Object()
        i.attr = i
        for proto in protocols:
            s = self.dumps(i, proto)
            x = self.loads(s)
            self.assertIsInstance(x, Object)
            self.assertEqual(dir(x), dir(i))
            self.assertIs(x.attr, x)

    def test_recursive_multi(self):
        l = []
        d = {1: l}
        i = Object()
        i.attr = d
        l.append(i)
        for proto in protocols:
            s = self.dumps(l, proto)
            x = self.loads(s)
            self.assertIsInstance(x, list)
            self.assertEqual(len(x), 1)
            self.assertEqual(dir(x[0]), dir(i))
            self.assertEqual(list(x[0].attr.keys()), [1])
            self.assertIs(x[0].attr[1], x)

    def _test_recursive_collection_and_inst(self, factory):
        o = Object()
        o.attr = factory([o])
        t = type(o.attr)
        for proto in protocols:
            s = self.dumps(o, proto)
            x = self.loads(s)
            self.assertIsInstance(x.attr, t)
            self.assertEqual(len(x.attr), 1)
            self.assertIsInstance(list(x.attr)[0], Object)
            self.assertIs(list(x.attr)[0], x)
        o = o.attr
        for proto in protocols:
            s = self.dumps(o, proto)
            x = self.loads(s)
            self.assertIsInstance(x, t)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(list(x)[0], Object)
            self.assertIs(list(x)[0].attr, x)

    def test_recursive_list_and_inst(self):
        self._test_recursive_collection_and_inst(list)

    def test_recursive_tuple_and_inst(self):
        self._test_recursive_collection_and_inst(tuple)

    def test_recursive_dict_and_inst(self):
        self._test_recursive_collection_and_inst(dict.fromkeys)

    def test_recursive_set_and_inst(self):
        self._test_recursive_collection_and_inst(set)

    def test_recursive_frozenset_and_inst(self):
        self._test_recursive_collection_and_inst(frozenset)

    def test_recursive_list_subclass_and_inst(self):
        self._test_recursive_collection_and_inst(MyList)

    def test_recursive_tuple_subclass_and_inst(self):
        self._test_recursive_collection_and_inst(MyTuple)

    def test_recursive_dict_subclass_and_inst(self):
        self._test_recursive_collection_and_inst(MyDict.fromkeys)

    def test_recursive_set_subclass_and_inst(self):
        self._test_recursive_collection_and_inst(MySet)

    def test_recursive_frozenset_subclass_and_inst(self):
        self._test_recursive_collection_and_inst(MyFrozenSet)

    def test_recursive_inst_state(self):
        y = REX_state()
        y.state = y
        for proto in protocols:
            s = self.dumps(y, proto)
            x = self.loads(s)
            self.assertIsInstance(x, REX_state)
            self.assertIs(x.state, x)

    def test_recursive_tuple_and_inst_state(self):
        t = (REX_state(),)
        t[0].state = t
        for proto in protocols:
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, tuple)
            self.assertEqual(len(x), 1)
            self.assertIsInstance(x[0], REX_state)
            self.assertIs(x[0].state, x)
        (t,) = t
        for proto in protocols:
            s = self.dumps(t, proto)
            x = self.loads(s)
            self.assertIsInstance(x, REX_state)
            self.assertIsInstance(x.state, tuple)
            self.assertEqual(len(x.state), 1)
            self.assertIs(x.state[0], x)

    def test_unicode(self):
        endcases = ["", "<\\u>", "<\\ሴ>", "<\n>", "<\\>", "<\\𒍅>", "<\udc80>"]
        for proto in protocols:
            for u in endcases:
                p = self.dumps(u, proto)
                u2 = self.loads(p)
                self.assert_is_copy(u, u2)

    def test_unicode_high_plane(self):
        t = "𒍅"
        for proto in protocols:
            p = self.dumps(t, proto)
            t2 = self.loads(p)
            self.assert_is_copy(t, t2)

    def test_bytes(self):
        for proto in protocols:
            for s in (b"", b"xyz", (b"xyz" * 100)):
                p = self.dumps(s, proto)
                self.assert_is_copy(s, self.loads(p))
            for s in [bytes([i]) for i in range(256)]:
                p = self.dumps(s, proto)
                self.assert_is_copy(s, self.loads(p))
            for s in [bytes([i, i]) for i in range(256)]:
                p = self.dumps(s, proto)
                self.assert_is_copy(s, self.loads(p))

    def test_bytearray(self):
        for proto in protocols:
            for s in (b"", b"xyz", (b"xyz" * 100)):
                b = bytearray(s)
                p = self.dumps(b, proto)
                bb = self.loads(p)
                self.assertIsNot(bb, b)
                self.assert_is_copy(b, bb)
                if proto <= 3:
                    self.assertIn(b"bytearray", p)
                    self.assertTrue(opcode_in_pickle(pickle.GLOBAL, p))
                elif proto == 4:
                    self.assertIn(b"bytearray", p)
                    self.assertTrue(opcode_in_pickle(pickle.STACK_GLOBAL, p))
                elif proto == 5:
                    self.assertNotIn(b"bytearray", p)
                    self.assertTrue(opcode_in_pickle(pickle.BYTEARRAY8, p))

    def test_ints(self):
        for proto in protocols:
            n = sys.maxsize
            while n:
                for expected in ((-n), n):
                    s = self.dumps(expected, proto)
                    n2 = self.loads(s)
                    self.assert_is_copy(expected, n2)
                n = n >> 1

    def test_long(self):
        for proto in protocols:
            for nbits in (1, 8, (8 * 254), (8 * 255), (8 * 256), (8 * 257)):
                nbase = 1 << nbits
                for npos in ((nbase - 1), nbase, (nbase + 1)):
                    for n in (npos, (-npos)):
                        pickle = self.dumps(n, proto)
                        got = self.loads(pickle)
                        self.assert_is_copy(n, got)
        nbase = int("deadbeeffeedface", 16)
        nbase += nbase << 1000000
        for n in (nbase, (-nbase)):
            p = self.dumps(n, 2)
            got = self.loads(p)
            self.assertIs(type(got), int)
            self.assertEqual(n, got)

    def test_float(self):
        test_values = [
            0.0,
            5e-324,
            1e-310,
            7e-308,
            6.626e-34,
            0.1,
            0.5,
            3.14,
            263.44582062374053,
            6.022e23,
            1e30,
        ]
        test_values = test_values + [(-x) for x in test_values]
        for proto in protocols:
            for value in test_values:
                pickle = self.dumps(value, proto)
                got = self.loads(pickle)
                self.assert_is_copy(value, got)

    @run_with_locale("LC_ALL", "de_DE", "fr_FR")
    def test_float_format(self):
        self.assertEqual(self.dumps(1.2, 0)[0:3], b"F1.")

    def test_reduce(self):
        for proto in protocols:
            inst = AAA()
            dumped = self.dumps(inst, proto)
            loaded = self.loads(dumped)
            self.assertEqual(loaded, REDUCE_A)

    def test_getinitargs(self):
        for proto in protocols:
            inst = initarg(1, 2)
            dumped = self.dumps(inst, proto)
            loaded = self.loads(dumped)
            self.assert_is_copy(inst, loaded)

    def test_metaclass(self):
        a = use_metaclass()
        for proto in protocols:
            s = self.dumps(a, proto)
            b = self.loads(s)
            self.assertEqual(a.__class__, b.__class__)

    def test_dynamic_class(self):
        a = create_dynamic_class("my_dynamic_class", (object,))
        copyreg.pickle(pickling_metaclass, pickling_metaclass.__reduce__)
        for proto in protocols:
            s = self.dumps(a, proto)
            b = self.loads(s)
            self.assertEqual(a, b)
            self.assertIs(type(a), type(b))

    def test_structseq(self):
        import time
        import os

        t = time.localtime()
        for proto in protocols:
            s = self.dumps(t, proto)
            u = self.loads(s)
            self.assert_is_copy(t, u)
            t = os.stat(os.curdir)
            s = self.dumps(t, proto)
            u = self.loads(s)
            self.assert_is_copy(t, u)
            if hasattr(os, "statvfs"):
                t = os.statvfs(os.curdir)
                s = self.dumps(t, proto)
                u = self.loads(s)
                self.assert_is_copy(t, u)

    def test_ellipsis(self):
        for proto in protocols:
            s = self.dumps(..., proto)
            u = self.loads(s)
            self.assertIs(..., u)

    def test_notimplemented(self):
        for proto in protocols:
            s = self.dumps(NotImplemented, proto)
            u = self.loads(s)
            self.assertIs(NotImplemented, u)

    def test_singleton_types(self):
        singletons = [None, ..., NotImplemented]
        for singleton in singletons:
            for proto in protocols:
                s = self.dumps(type(singleton), proto)
                u = self.loads(s)
                self.assertIs(type(singleton), u)

    def test_proto(self):
        for proto in protocols:
            pickled = self.dumps(None, proto)
            if proto >= 2:
                proto_header = pickle.PROTO + bytes([proto])
                self.assertTrue(pickled.startswith(proto_header))
            else:
                self.assertEqual(count_opcode(pickle.PROTO, pickled), 0)
        oob = protocols[(-1)] + 1
        build_none = pickle.NONE + pickle.STOP
        badpickle = (pickle.PROTO + bytes([oob])) + build_none
        try:
            self.loads(badpickle)
        except ValueError as err:
            self.assertIn("unsupported pickle protocol", str(err))
        else:
            self.fail("expected bad protocol number to raise ValueError")

    def test_long1(self):
        x = 12345678910111213141516178920
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            self.assertEqual(opcode_in_pickle(pickle.LONG1, s), (proto >= 2))

    def test_long4(self):
        x = 12345678910111213141516178920 << (256 * 8)
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            self.assertEqual(opcode_in_pickle(pickle.LONG4, s), (proto >= 2))

    def test_short_tuples(self):
        expected_opcode = {
            (0, 0): pickle.TUPLE,
            (0, 1): pickle.TUPLE,
            (0, 2): pickle.TUPLE,
            (0, 3): pickle.TUPLE,
            (0, 4): pickle.TUPLE,
            (1, 0): pickle.EMPTY_TUPLE,
            (1, 1): pickle.TUPLE,
            (1, 2): pickle.TUPLE,
            (1, 3): pickle.TUPLE,
            (1, 4): pickle.TUPLE,
            (2, 0): pickle.EMPTY_TUPLE,
            (2, 1): pickle.TUPLE1,
            (2, 2): pickle.TUPLE2,
            (2, 3): pickle.TUPLE3,
            (2, 4): pickle.TUPLE,
            (3, 0): pickle.EMPTY_TUPLE,
            (3, 1): pickle.TUPLE1,
            (3, 2): pickle.TUPLE2,
            (3, 3): pickle.TUPLE3,
            (3, 4): pickle.TUPLE,
        }
        a = ()
        b = (1,)
        c = (1, 2)
        d = (1, 2, 3)
        e = (1, 2, 3, 4)
        for proto in protocols:
            for x in (a, b, c, d, e):
                s = self.dumps(x, proto)
                y = self.loads(s)
                self.assert_is_copy(x, y)
                expected = expected_opcode[(min(proto, 3), len(x))]
                self.assertTrue(opcode_in_pickle(expected, s))

    def test_singletons(self):
        expected_opcode = {
            (0, None): pickle.NONE,
            (1, None): pickle.NONE,
            (2, None): pickle.NONE,
            (3, None): pickle.NONE,
            (0, True): pickle.INT,
            (1, True): pickle.INT,
            (2, True): pickle.NEWTRUE,
            (3, True): pickle.NEWTRUE,
            (0, False): pickle.INT,
            (1, False): pickle.INT,
            (2, False): pickle.NEWFALSE,
            (3, False): pickle.NEWFALSE,
        }
        for proto in protocols:
            for x in (None, False, True):
                s = self.dumps(x, proto)
                y = self.loads(s)
                self.assertTrue((x is y), (proto, x, s, y))
                expected = expected_opcode[(min(proto, 3), x)]
                self.assertTrue(opcode_in_pickle(expected, s))

    def test_newobj_tuple(self):
        x = MyTuple([1, 2, 3])
        x.foo = 42
        x.bar = "hello"
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)

    def test_newobj_list(self):
        x = MyList([1, 2, 3])
        x.foo = 42
        x.bar = "hello"
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)

    def test_newobj_generic(self):
        for proto in protocols:
            for C in myclasses:
                B = C.__base__
                x = C(C.sample)
                x.foo = 42
                s = self.dumps(x, proto)
                y = self.loads(s)
                detail = (proto, C, B, x, y, type(y))
                self.assert_is_copy(x, y)
                self.assertEqual(B(x), B(y), detail)
                self.assertEqual(x.__dict__, y.__dict__, detail)

    def test_newobj_proxies(self):
        classes = myclasses[:]
        for c in (MyInt, MyTuple):
            classes.remove(c)
        for proto in protocols:
            for C in classes:
                B = C.__base__
                x = C(C.sample)
                x.foo = 42
                p = weakref.proxy(x)
                s = self.dumps(p, proto)
                y = self.loads(s)
                self.assertEqual(type(y), type(x))
                detail = (proto, C, B, x, y, type(y))
                self.assertEqual(B(x), B(y), detail)
                self.assertEqual(x.__dict__, y.__dict__, detail)

    def test_newobj_overridden_new(self):
        for proto in protocols:
            x = MyIntWithNew2(1)
            x.foo = 42
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assertIs(type(y), MyIntWithNew2)
            self.assertEqual(int(y), 1)
            self.assertEqual(y.foo, 42)

    def test_newobj_not_class(self):
        global SimpleNewObj
        save = SimpleNewObj
        o = SimpleNewObj.__new__(SimpleNewObj)
        b = self.dumps(o, 4)
        try:
            SimpleNewObj = 42
            self.assertRaises((TypeError, pickle.UnpicklingError), self.loads, b)
        finally:
            SimpleNewObj = save

    def produce_global_ext(self, extcode, opcode):
        e = ExtensionSaver(extcode)
        try:
            copyreg.add_extension(__name__, "MyList", extcode)
            x = MyList([1, 2, 3])
            x.foo = 42
            x.bar = "hello"
            s1 = self.dumps(x, 1)
            self.assertIn(__name__.encode("utf-8"), s1)
            self.assertIn(b"MyList", s1)
            self.assertFalse(opcode_in_pickle(opcode, s1))
            y = self.loads(s1)
            self.assert_is_copy(x, y)
            s2 = self.dumps(x, 2)
            self.assertNotIn(__name__.encode("utf-8"), s2)
            self.assertNotIn(b"MyList", s2)
            self.assertEqual(opcode_in_pickle(opcode, s2), True, repr(s2))
            y = self.loads(s2)
            self.assert_is_copy(x, y)
        finally:
            e.restore()

    def test_global_ext1(self):
        self.produce_global_ext(1, pickle.EXT1)
        self.produce_global_ext(255, pickle.EXT1)

    def test_global_ext2(self):
        self.produce_global_ext(256, pickle.EXT2)
        self.produce_global_ext(65535, pickle.EXT2)
        self.produce_global_ext(43981, pickle.EXT2)

    def test_global_ext4(self):
        self.produce_global_ext(65536, pickle.EXT4)
        self.produce_global_ext(2147483647, pickle.EXT4)
        self.produce_global_ext(313249263, pickle.EXT4)

    def test_list_chunking(self):
        n = 10
        x = list(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_appends = count_opcode(pickle.APPENDS, s)
            self.assertEqual(num_appends, (proto > 0))
        n = 2500
        x = list(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_appends = count_opcode(pickle.APPENDS, s)
            if proto == 0:
                self.assertEqual(num_appends, 0)
            else:
                self.assertTrue((num_appends >= 2))

    def test_dict_chunking(self):
        n = 10
        x = dict.fromkeys(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            self.assertIsInstance(s, bytes_types)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_setitems = count_opcode(pickle.SETITEMS, s)
            self.assertEqual(num_setitems, (proto > 0))
        n = 2500
        x = dict.fromkeys(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_setitems = count_opcode(pickle.SETITEMS, s)
            if proto == 0:
                self.assertEqual(num_setitems, 0)
            else:
                self.assertTrue((num_setitems >= 2))

    def test_set_chunking(self):
        n = 10
        x = set(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_additems = count_opcode(pickle.ADDITEMS, s)
            if proto < 4:
                self.assertEqual(num_additems, 0)
            else:
                self.assertEqual(num_additems, 1)
        n = 2500
        x = set(range(n))
        for proto in protocols:
            s = self.dumps(x, proto)
            y = self.loads(s)
            self.assert_is_copy(x, y)
            num_additems = count_opcode(pickle.ADDITEMS, s)
            if proto < 4:
                self.assertEqual(num_additems, 0)
            else:
                self.assertGreaterEqual(num_additems, 2)

    def test_simple_newobj(self):
        x = SimpleNewObj.__new__(SimpleNewObj, 64206)
        x.abc = 666
        for proto in protocols:
            with self.subTest(proto=proto):
                s = self.dumps(x, proto)
                if proto < 1:
                    self.assertIn(b"\nI64206", s)
                else:
                    self.assertIn(b"M\xce\xfa", s)
                self.assertEqual(opcode_in_pickle(pickle.NEWOBJ, s), (2 <= proto))
                self.assertFalse(opcode_in_pickle(pickle.NEWOBJ_EX, s))
                y = self.loads(s)
                self.assert_is_copy(x, y)

    def test_complex_newobj(self):
        x = ComplexNewObj.__new__(ComplexNewObj, 64206)
        x.abc = 666
        for proto in protocols:
            with self.subTest(proto=proto):
                s = self.dumps(x, proto)
                if proto < 1:
                    self.assertIn(b"\nI64206", s)
                elif proto < 2:
                    self.assertIn(b"M\xce\xfa", s)
                elif proto < 4:
                    self.assertIn(b"X\x04\x00\x00\x00FACE", s)
                else:
                    self.assertIn(b"\x8c\x04FACE", s)
                self.assertEqual(opcode_in_pickle(pickle.NEWOBJ, s), (2 <= proto))
                self.assertFalse(opcode_in_pickle(pickle.NEWOBJ_EX, s))
                y = self.loads(s)
                self.assert_is_copy(x, y)

    def test_complex_newobj_ex(self):
        x = ComplexNewObjEx.__new__(ComplexNewObjEx, 64206)
        x.abc = 666
        for proto in protocols:
            with self.subTest(proto=proto):
                s = self.dumps(x, proto)
                if proto < 1:
                    self.assertIn(b"\nI64206", s)
                elif proto < 2:
                    self.assertIn(b"M\xce\xfa", s)
                elif proto < 4:
                    self.assertIn(b"X\x04\x00\x00\x00FACE", s)
                else:
                    self.assertIn(b"\x8c\x04FACE", s)
                self.assertFalse(opcode_in_pickle(pickle.NEWOBJ, s))
                self.assertEqual(opcode_in_pickle(pickle.NEWOBJ_EX, s), (4 <= proto))
                y = self.loads(s)
                self.assert_is_copy(x, y)

    def test_newobj_list_slots(self):
        x = SlotList([1, 2, 3])
        x.foo = 42
        x.bar = "hello"
        s = self.dumps(x, 2)
        y = self.loads(s)
        self.assert_is_copy(x, y)

    def test_reduce_overrides_default_reduce_ex(self):
        for proto in protocols:
            x = REX_one()
            self.assertEqual(x._reduce_called, 0)
            s = self.dumps(x, proto)
            self.assertEqual(x._reduce_called, 1)
            y = self.loads(s)
            self.assertEqual(y._reduce_called, 0)

    def test_reduce_ex_called(self):
        for proto in protocols:
            x = REX_two()
            self.assertEqual(x._proto, None)
            s = self.dumps(x, proto)
            self.assertEqual(x._proto, proto)
            y = self.loads(s)
            self.assertEqual(y._proto, None)

    def test_reduce_ex_overrides_reduce(self):
        for proto in protocols:
            x = REX_three()
            self.assertEqual(x._proto, None)
            s = self.dumps(x, proto)
            self.assertEqual(x._proto, proto)
            y = self.loads(s)
            self.assertEqual(y._proto, None)

    def test_reduce_ex_calls_base(self):
        for proto in protocols:
            x = REX_four()
            self.assertEqual(x._proto, None)
            s = self.dumps(x, proto)
            self.assertEqual(x._proto, proto)
            y = self.loads(s)
            self.assertEqual(y._proto, proto)

    def test_reduce_calls_base(self):
        for proto in protocols:
            x = REX_five()
            self.assertEqual(x._reduce_called, 0)
            s = self.dumps(x, proto)
            self.assertEqual(x._reduce_called, 1)
            y = self.loads(s)
            self.assertEqual(y._reduce_called, 1)

    @no_tracing
    def test_bad_getattr(self):
        x = BadGetattr()
        for proto in protocols:
            self.assertRaises(RuntimeError, self.dumps, x, proto)

    def test_reduce_bad_iterator(self):
        class C(object):
            def __reduce__(self):
                return (list, (), None, [], None)

        class D(object):
            def __reduce__(self):
                return (dict, (), None, None, [])

        for proto in protocols:
            try:
                self.dumps(C(), proto)
            except pickle.PicklingError:
                pass
            try:
                self.dumps(D(), proto)
            except pickle.PicklingError:
                pass

    def test_many_puts_and_gets(self):
        keys = (("aaa" + str(i)) for i in range(100))
        large_dict = dict(((k, [4, 5, 6]) for k in keys))
        obj = [dict(large_dict), dict(large_dict), dict(large_dict)]
        for proto in protocols:
            with self.subTest(proto=proto):
                dumped = self.dumps(obj, proto)
                loaded = self.loads(dumped)
                self.assert_is_copy(obj, loaded)

    def test_attribute_name_interning(self):
        for proto in protocols:
            x = C()
            x.foo = 42
            x.bar = "hello"
            s = self.dumps(x, proto)
            y = self.loads(s)
            x_keys = sorted(x.__dict__)
            y_keys = sorted(y.__dict__)
            for (x_key, y_key) in zip(x_keys, y_keys):
                self.assertIs(x_key, y_key)

    def test_pickle_to_2x(self):
        dumped = self.dumps(range(5), 2)
        self.assertEqual(dumped, DATA_XRANGE)
        dumped = self.dumps(set([3]), 2)
        self.assertEqual(dumped, DATA_SET2)

    def test_large_pickles(self):
        for proto in protocols:
            data = (1, min, (b"xy" * (30 * 1024)), len)
            dumped = self.dumps(data, proto)
            loaded = self.loads(dumped)
            self.assertEqual(len(loaded), len(data))
            self.assertEqual(loaded, data)

    def test_int_pickling_efficiency(self):
        for proto in protocols:
            with self.subTest(proto=proto):
                pickles = [self.dumps((2 ** n), proto) for n in range(70)]
                sizes = list(map(len, pickles))
                self.assertEqual(sorted(sizes), sizes)
                if proto >= 2:
                    for p in pickles:
                        self.assertFalse(opcode_in_pickle(pickle.LONG, p))

    def _check_pickling_with_opcode(self, obj, opcode, proto):
        pickled = self.dumps(obj, proto)
        self.assertTrue(opcode_in_pickle(opcode, pickled))
        unpickled = self.loads(pickled)
        self.assertEqual(obj, unpickled)

    def test_appends_on_non_lists(self):
        obj = REX_six([1, 2, 3])
        for proto in protocols:
            if proto == 0:
                self._check_pickling_with_opcode(obj, pickle.APPEND, proto)
            else:
                self._check_pickling_with_opcode(obj, pickle.APPENDS, proto)

    def test_setitems_on_non_dicts(self):
        obj = REX_seven({1: (-1), 2: (-2), 3: (-3)})
        for proto in protocols:
            if proto == 0:
                self._check_pickling_with_opcode(obj, pickle.SETITEM, proto)
            else:
                self._check_pickling_with_opcode(obj, pickle.SETITEMS, proto)

    FRAME_SIZE_MIN = 4
    FRAME_SIZE_TARGET = 64 * 1024

    def check_frame_opcodes(self, pickled):
        "\n        Check the arguments of FRAME opcodes in a protocol 4+ pickle.\n\n        Note that binary objects that are larger than FRAME_SIZE_TARGET are not\n        framed by default and are therefore considered a frame by themselves in\n        the following consistency check.\n        "
        frame_end = frameless_start = None
        frameless_opcodes = {
            "BINBYTES",
            "BINUNICODE",
            "BINBYTES8",
            "BINUNICODE8",
            "BYTEARRAY8",
        }
        for (op, arg, pos) in pickletools.genops(pickled):
            if frame_end is not None:
                self.assertLessEqual(pos, frame_end)
                if pos == frame_end:
                    frame_end = None
            if frame_end is not None:
                self.assertNotEqual(op.name, "FRAME")
                if op.name in frameless_opcodes:
                    self.assertLessEqual(len(arg), self.FRAME_SIZE_TARGET)
            elif (op.name == "FRAME") or (
                (op.name in frameless_opcodes) and (len(arg) > self.FRAME_SIZE_TARGET)
            ):
                if frameless_start is not None:
                    self.assertLess((pos - frameless_start), self.FRAME_SIZE_MIN)
                    frameless_start = None
            elif (frameless_start is None) and (op.name != "PROTO"):
                frameless_start = pos
            if op.name == "FRAME":
                self.assertGreaterEqual(arg, self.FRAME_SIZE_MIN)
                frame_end = (pos + 9) + arg
        pos = len(pickled)
        if frame_end is not None:
            self.assertEqual(frame_end, pos)
        elif frameless_start is not None:
            self.assertLess((pos - frameless_start), self.FRAME_SIZE_MIN)

    @support.skip_if_pgo_task
    def test_framing_many_objects(self):
        obj = list(range((10 ** 5)))
        for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.subTest(proto=proto):
                pickled = self.dumps(obj, proto)
                unpickled = self.loads(pickled)
                self.assertEqual(obj, unpickled)
                bytes_per_frame = len(pickled) / count_opcode(pickle.FRAME, pickled)
                self.assertGreater(bytes_per_frame, (self.FRAME_SIZE_TARGET / 2))
                self.assertLessEqual(bytes_per_frame, (self.FRAME_SIZE_TARGET * 1))
                self.check_frame_opcodes(pickled)

    def test_framing_large_objects(self):
        N = 1024 * 1024
        small_items = [[i] for i in range(10)]
        obj = [(b"x" * N), *small_items, (b"y" * N), ("z" * N)]
        for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
            for fast in [False, True]:
                with self.subTest(proto=proto, fast=fast):
                    if not fast:
                        pickled = self.dumps(obj, proto)
                    else:
                        if not hasattr(self, "pickler"):
                            continue
                        buf = io.BytesIO()
                        pickler = self.pickler(buf, protocol=proto)
                        pickler.fast = fast
                        pickler.dump(obj)
                        pickled = buf.getvalue()
                    unpickled = self.loads(pickled)
                    self.assertEqual([len(x) for x in obj], [len(x) for x in unpickled])
                    self.assertEqual(obj, unpickled)
                    n_frames = count_opcode(pickle.FRAME, pickled)
                    self.assertEqual(n_frames, 1)
                    self.check_frame_opcodes(pickled)

    def test_optional_frames(self):
        if pickle.HIGHEST_PROTOCOL < 4:
            return

        def remove_frames(pickled, keep_frame=None):
            "Remove frame opcodes from the given pickle."
            frame_starts = []
            frame_opcode_size = 9
            for (opcode, _, pos) in pickletools.genops(pickled):
                if opcode.name == "FRAME":
                    frame_starts.append(pos)
            newpickle = bytearray()
            last_frame_end = 0
            for (i, pos) in enumerate(frame_starts):
                if keep_frame and keep_frame(i):
                    continue
                newpickle += pickled[last_frame_end:pos]
                last_frame_end = pos + frame_opcode_size
            newpickle += pickled[last_frame_end:]
            return newpickle

        frame_size = self.FRAME_SIZE_TARGET
        num_frames = 20
        for bytes_type in (bytes, bytearray):
            obj = {i: (bytes_type([i]) * frame_size) for i in range(num_frames)}
            for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
                pickled = self.dumps(obj, proto)
                frameless_pickle = remove_frames(pickled)
                self.assertEqual(count_opcode(pickle.FRAME, frameless_pickle), 0)
                self.assertEqual(obj, self.loads(frameless_pickle))
                some_frames_pickle = remove_frames(pickled, (lambda i: (i % 2)))
                self.assertLess(
                    count_opcode(pickle.FRAME, some_frames_pickle),
                    count_opcode(pickle.FRAME, pickled),
                )
                self.assertEqual(obj, self.loads(some_frames_pickle))

    @support.skip_if_pgo_task
    def test_framed_write_sizes_with_delayed_writer(self):
        class ChunkAccumulator:
            "Accumulate pickler output in a list of raw chunks."

            def __init__(self):
                self.chunks = []

            def write(self, chunk):
                self.chunks.append(chunk)

            def concatenate_chunks(self):
                return b"".join(self.chunks)

        for proto in range(4, (pickle.HIGHEST_PROTOCOL + 1)):
            objects = [
                (str(i).encode("ascii"), (i % 42), {"i": str(i)})
                for i in range(int(10000.0))
            ]
            objects.append(("0123456789abcdef" * ((self.FRAME_SIZE_TARGET // 16) + 1)))
            writer = ChunkAccumulator()
            self.pickler(writer, proto).dump(objects)
            pickled = writer.concatenate_chunks()
            reconstructed = self.loads(pickled)
            self.assertEqual(reconstructed, objects)
            self.assertGreater(len(writer.chunks), 1)
            del objects
            support.gc_collect()
            self.assertEqual(writer.concatenate_chunks(), pickled)
            n_frames = ((len(pickled) - 1) // self.FRAME_SIZE_TARGET) + 1
            self.assertGreaterEqual(len(writer.chunks), n_frames)
            self.assertLessEqual(len(writer.chunks), ((2 * n_frames) + 3))
            chunk_sizes = [len(c) for c in writer.chunks]
            large_sizes = [s for s in chunk_sizes if (s >= self.FRAME_SIZE_TARGET)]
            medium_sizes = [s for s in chunk_sizes if (9 < s < self.FRAME_SIZE_TARGET)]
            small_sizes = [s for s in chunk_sizes if (s <= 9)]
            for chunk_size in large_sizes:
                self.assertLess(chunk_size, (2 * self.FRAME_SIZE_TARGET), chunk_sizes)
            self.assertLessEqual(
                len(small_sizes),
                ((len(large_sizes) + len(medium_sizes)) + 3),
                chunk_sizes,
            )

    def test_nested_names(self):
        global Nested

        class Nested:
            class A:
                class B:
                    class C:
                        pass

        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            for obj in [Nested.A, Nested.A.B, Nested.A.B.C]:
                with self.subTest(proto=proto, obj=obj):
                    unpickled = self.loads(self.dumps(obj, proto))
                    self.assertIs(obj, unpickled)

    def test_recursive_nested_names(self):
        global Recursive

        class Recursive:
            pass

        Recursive.mod = sys.modules[Recursive.__module__]
        Recursive.__qualname__ = "Recursive.mod.Recursive"
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            with self.subTest(proto=proto):
                unpickled = self.loads(self.dumps(Recursive, proto))
                self.assertIs(unpickled, Recursive)
        del Recursive.mod

    def test_py_methods(self):
        global PyMethodsTest

        class PyMethodsTest:
            @staticmethod
            def cheese():
                return "cheese"

            @classmethod
            def wine(cls):
                assert cls is PyMethodsTest
                return "wine"

            def biscuits(self):
                assert isinstance(self, PyMethodsTest)
                return "biscuits"

            class Nested:
                "Nested class"

                @staticmethod
                def ketchup():
                    return "ketchup"

                @classmethod
                def maple(cls):
                    assert cls is PyMethodsTest.Nested
                    return "maple"

                def pie(self):
                    assert isinstance(self, PyMethodsTest.Nested)
                    return "pie"

        py_methods = (
            PyMethodsTest.cheese,
            PyMethodsTest.wine,
            PyMethodsTest().biscuits,
            PyMethodsTest.Nested.ketchup,
            PyMethodsTest.Nested.maple,
            PyMethodsTest.Nested().pie,
        )
        py_unbound_methods = (
            (PyMethodsTest.biscuits, PyMethodsTest),
            (PyMethodsTest.Nested.pie, PyMethodsTest.Nested),
        )
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            for method in py_methods:
                with self.subTest(proto=proto, method=method):
                    unpickled = self.loads(self.dumps(method, proto))
                    self.assertEqual(method(), unpickled())
            for (method, cls) in py_unbound_methods:
                obj = cls()
                with self.subTest(proto=proto, method=method):
                    unpickled = self.loads(self.dumps(method, proto))
                    self.assertEqual(method(obj), unpickled(obj))

    def test_c_methods(self):
        global Subclass

        class Subclass(tuple):
            class Nested(str):
                pass

        c_methods = (
            ("abcd".index, ("c",)),
            (str.index, ("abcd", "c")),
            ([1, 2, 3].__len__, ()),
            (list.__len__, ([1, 2, 3],)),
            ({1, 2}.__contains__, (2,)),
            (set.__contains__, ({1, 2}, 2)),
            (dict.fromkeys, (("a", 1), ("b", 2))),
            (bytearray.maketrans, (b"abc", b"xyz")),
            (Subclass([1, 2, 2]).count, (2,)),
            (Subclass.count, (Subclass([1, 2, 2]), 2)),
            (Subclass.Nested("sweet").count, ("e",)),
            (Subclass.Nested.count, (Subclass.Nested("sweet"), "e")),
        )
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            for (method, args) in c_methods:
                with self.subTest(proto=proto, method=method):
                    unpickled = self.loads(self.dumps(method, proto))
                    self.assertEqual(method(*args), unpickled(*args))

    def test_compat_pickle(self):
        tests = [
            (range(1, 7), "__builtin__", "xrange"),
            (map(int, "123"), "itertools", "imap"),
            (functools.reduce, "__builtin__", "reduce"),
            (dbm.whichdb, "whichdb", "whichdb"),
            (Exception(), "exceptions", "Exception"),
            (collections.UserDict(), "UserDict", "IterableUserDict"),
            (collections.UserList(), "UserList", "UserList"),
            (collections.defaultdict(), "collections", "defaultdict"),
        ]
        for (val, mod, name) in tests:
            for proto in range(3):
                with self.subTest(type=type(val), proto=proto):
                    pickled = self.dumps(val, proto)
                    self.assertIn(("c%s\n%s" % (mod, name)).encode(), pickled)
                    self.assertIs(type(self.loads(pickled)), type(val))

    def test_local_lookup_error(self):
        def f():
            pass

        for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.assertRaises((AttributeError, pickle.PicklingError)):
                pickletools.dis(self.dumps(f, proto))
        del f.__module__
        for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.assertRaises((AttributeError, pickle.PicklingError)):
                pickletools.dis(self.dumps(f, proto))
        f.__name__ = f.__qualname__
        for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.assertRaises((AttributeError, pickle.PicklingError)):
                pickletools.dis(self.dumps(f, proto))

    def buffer_like_objects(self):
        bytestring = b"abcdefgh"
        (yield ZeroCopyBytes(bytestring))
        (yield ZeroCopyBytearray(bytestring))
        if _testbuffer is not None:
            items = list(bytestring)
            value = int.from_bytes(bytestring, byteorder="little")
            for flags in (0, _testbuffer.ND_WRITABLE):
                (yield PicklableNDArray(items, format="B", shape=(8,), flags=flags))
                (
                    yield PicklableNDArray(
                        items, format="B", shape=(4, 2), strides=(2, 1), flags=flags
                    )
                )
                (
                    yield PicklableNDArray(
                        items, format="B", shape=(4, 2), strides=(1, 4), flags=flags
                    )
                )

    def test_in_band_buffers(self):
        for obj in self.buffer_like_objects():
            for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
                data = self.dumps(obj, proto)
                if obj.c_contiguous and (proto >= 5):
                    self.assertIn(b"abcdefgh", data)
                self.assertEqual(count_opcode(pickle.NEXT_BUFFER, data), 0)
                if proto >= 5:
                    self.assertEqual(
                        count_opcode(pickle.SHORT_BINBYTES, data),
                        (1 if obj.readonly else 0),
                    )
                    self.assertEqual(
                        count_opcode(pickle.BYTEARRAY8, data),
                        (0 if obj.readonly else 1),
                    )

                    def buffer_callback(obj):
                        return True

                    data2 = self.dumps(obj, proto, buffer_callback=buffer_callback)
                    self.assertEqual(data2, data)
                new = self.loads(data)
                self.assertIsNot(new, obj)
                self.assertIs(type(new), type(obj))
                self.assertEqual(new, obj)

    def test_oob_buffers(self):
        for obj in self.buffer_like_objects():
            for proto in range(0, 5):
                with self.assertRaises(ValueError):
                    self.dumps(obj, proto, buffer_callback=[].append)
            for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
                buffers = []
                buffer_callback = lambda pb: buffers.append(pb.raw())
                data = self.dumps(obj, proto, buffer_callback=buffer_callback)
                self.assertNotIn(b"abcdefgh", data)
                self.assertEqual(count_opcode(pickle.SHORT_BINBYTES, data), 0)
                self.assertEqual(count_opcode(pickle.BYTEARRAY8, data), 0)
                self.assertEqual(count_opcode(pickle.NEXT_BUFFER, data), 1)
                self.assertEqual(
                    count_opcode(pickle.READONLY_BUFFER, data),
                    (1 if obj.readonly else 0),
                )
                if obj.c_contiguous:
                    self.assertEqual(bytes(buffers[0]), b"abcdefgh")
                with self.assertRaises(pickle.UnpicklingError):
                    self.loads(data)
                new = self.loads(data, buffers=buffers)
                if obj.zero_copy_reconstruct:
                    self.assertIs(new, obj)
                else:
                    self.assertIs(type(new), type(obj))
                    self.assertEqual(new, obj)
                new = self.loads(data, buffers=iter(buffers))
                if obj.zero_copy_reconstruct:
                    self.assertIs(new, obj)
                else:
                    self.assertIs(type(new), type(obj))
                    self.assertEqual(new, obj)

    def test_oob_buffers_writable_to_readonly(self):
        obj = ZeroCopyBytes(b"foobar")
        for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
            buffers = []
            buffer_callback = buffers.append
            data = self.dumps(obj, proto, buffer_callback=buffer_callback)
            buffers = map(bytearray, buffers)
            new = self.loads(data, buffers=buffers)
            self.assertIs(type(new), type(obj))
            self.assertEqual(new, obj)

    def test_picklebuffer_error(self):
        pb = pickle.PickleBuffer(b"foobar")
        for proto in range(0, 5):
            with self.assertRaises(pickle.PickleError):
                self.dumps(pb, proto)

    def test_buffer_callback_error(self):
        def buffer_callback(buffers):
            (1 / 0)

        pb = pickle.PickleBuffer(b"foobar")
        with self.assertRaises(ZeroDivisionError):
            self.dumps(pb, 5, buffer_callback=buffer_callback)

    def test_buffers_error(self):
        pb = pickle.PickleBuffer(b"foobar")
        for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
            data = self.dumps(pb, proto, buffer_callback=[].append)
            with self.assertRaises(TypeError):
                self.loads(data, buffers=object())
            with self.assertRaises(pickle.UnpicklingError):
                self.loads(data, buffers=[])

    def test_inband_accept_default_buffers_argument(self):
        for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
            data_pickled = self.dumps(1, proto, buffer_callback=None)
            data = self.loads(data_pickled, buffers=None)

    @unittest.skipIf((np is None), "Test needs Numpy")
    def test_buffers_numpy(self):
        def check_no_copy(x, y):
            np.testing.assert_equal(x, y)
            self.assertEqual(x.ctypes.data, y.ctypes.data)

        def check_copy(x, y):
            np.testing.assert_equal(x, y)
            self.assertNotEqual(x.ctypes.data, y.ctypes.data)

        def check_array(arr):
            for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
                data = self.dumps(arr, proto)
                new = self.loads(data)
                check_copy(arr, new)
            for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
                buffer_callback = lambda _: True
                data = self.dumps(arr, proto, buffer_callback=buffer_callback)
                new = self.loads(data)
                check_copy(arr, new)
            for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
                buffers = []
                buffer_callback = buffers.append
                data = self.dumps(arr, proto, buffer_callback=buffer_callback)
                new = self.loads(data, buffers=buffers)
                if arr.flags.c_contiguous or arr.flags.f_contiguous:
                    check_no_copy(arr, new)
                else:
                    check_copy(arr, new)

        arr = np.arange(6)
        check_array(arr)
        check_array(arr[::2])
        arr = np.arange(12).reshape((3, 4))
        check_array(arr)
        check_array(arr.T)
        check_array(arr[::2])


class BigmemPickleTests(unittest.TestCase):
    @bigmemtest(size=_2G, memuse=3.6, dry_run=False)
    def test_huge_long_32b(self, size):
        data = 1 << (8 * size)
        try:
            for proto in protocols:
                if proto < 2:
                    continue
                with self.subTest(proto=proto):
                    with self.assertRaises((ValueError, OverflowError)):
                        self.dumps(data, protocol=proto)
        finally:
            data = None

    @bigmemtest(size=_2G, memuse=2.5, dry_run=False)
    def test_huge_bytes_32b(self, size):
        data = b"abcd" * (size // 4)
        try:
            for proto in protocols:
                if proto < 3:
                    continue
                with self.subTest(proto=proto):
                    try:
                        pickled = self.dumps(data, protocol=proto)
                        header = pickle.BINBYTES + struct.pack("<I", len(data))
                        data_start = pickled.index(data)
                        self.assertEqual(
                            header, pickled[(data_start - len(header)) : data_start]
                        )
                    finally:
                        pickled = None
        finally:
            data = None

    @bigmemtest(size=_4G, memuse=2.5, dry_run=False)
    def test_huge_bytes_64b(self, size):
        data = b"acbd" * (size // 4)
        try:
            for proto in protocols:
                if proto < 3:
                    continue
                with self.subTest(proto=proto):
                    if proto == 3:
                        with self.assertRaises((ValueError, OverflowError)):
                            self.dumps(data, protocol=proto)
                        continue
                    try:
                        pickled = self.dumps(data, protocol=proto)
                        header = pickle.BINBYTES8 + struct.pack("<Q", len(data))
                        data_start = pickled.index(data)
                        self.assertEqual(
                            header, pickled[(data_start - len(header)) : data_start]
                        )
                    finally:
                        pickled = None
        finally:
            data = None

    @bigmemtest(size=_2G, memuse=8, dry_run=False)
    def test_huge_str_32b(self, size):
        data = "abcd" * (size // 4)
        try:
            for proto in protocols:
                if proto == 0:
                    continue
                with self.subTest(proto=proto):
                    try:
                        pickled = self.dumps(data, protocol=proto)
                        header = pickle.BINUNICODE + struct.pack("<I", len(data))
                        data_start = pickled.index(b"abcd")
                        self.assertEqual(
                            header, pickled[(data_start - len(header)) : data_start]
                        )
                        self.assertEqual(
                            (
                                (pickled.rindex(b"abcd") + len(b"abcd"))
                                - pickled.index(b"abcd")
                            ),
                            len(data),
                        )
                    finally:
                        pickled = None
        finally:
            data = None

    @bigmemtest(size=_4G, memuse=8, dry_run=False)
    def test_huge_str_64b(self, size):
        data = "abcd" * (size // 4)
        try:
            for proto in protocols:
                if proto == 0:
                    continue
                with self.subTest(proto=proto):
                    if proto < 4:
                        with self.assertRaises((ValueError, OverflowError)):
                            self.dumps(data, protocol=proto)
                        continue
                    try:
                        pickled = self.dumps(data, protocol=proto)
                        header = pickle.BINUNICODE8 + struct.pack("<Q", len(data))
                        data_start = pickled.index(b"abcd")
                        self.assertEqual(
                            header, pickled[(data_start - len(header)) : data_start]
                        )
                        self.assertEqual(
                            (
                                (pickled.rindex(b"abcd") + len(b"abcd"))
                                - pickled.index(b"abcd")
                            ),
                            len(data),
                        )
                    finally:
                        pickled = None
        finally:
            data = None


class REX_one(object):
    "No __reduce_ex__ here, but inheriting it from object"
    _reduce_called = 0

    def __reduce__(self):
        self._reduce_called = 1
        return (REX_one, ())


class REX_two(object):
    "No __reduce__ here, but inheriting it from object"
    _proto = None

    def __reduce_ex__(self, proto):
        self._proto = proto
        return (REX_two, ())


class REX_three(object):
    _proto = None

    def __reduce_ex__(self, proto):
        self._proto = proto
        return (REX_two, ())

    def __reduce__(self):
        raise TestFailed("This __reduce__ shouldn't be called")


class REX_four(object):
    "Calling base class method should succeed"
    _proto = None

    def __reduce_ex__(self, proto):
        self._proto = proto
        return object.__reduce_ex__(self, proto)


class REX_five(object):
    "This one used to fail with infinite recursion"
    _reduce_called = 0

    def __reduce__(self):
        self._reduce_called = 1
        return object.__reduce__(self)


class REX_six(object):
    "This class is used to check the 4th argument (list iterator) of\n    the reduce protocol.\n    "

    def __init__(self, items=None):
        self.items = items if (items is not None) else []

    def __eq__(self, other):
        return (type(self) is type(other)) and (self.items == other.items)

    def append(self, item):
        self.items.append(item)

    def __reduce__(self):
        return (type(self), (), None, iter(self.items), None)


class REX_seven(object):
    "This class is used to check the 5th argument (dict iterator) of\n    the reduce protocol.\n    "

    def __init__(self, table=None):
        self.table = table if (table is not None) else {}

    def __eq__(self, other):
        return (type(self) is type(other)) and (self.table == other.table)

    def __setitem__(self, key, value):
        self.table[key] = value

    def __reduce__(self):
        return (type(self), (), None, None, iter(self.table.items()))


class REX_state(object):
    "This class is used to check the 3th argument (state) of\n    the reduce protocol.\n    "

    def __init__(self, state=None):
        self.state = state

    def __eq__(self, other):
        return (type(self) is type(other)) and (self.state == other.state)

    def __setstate__(self, state):
        self.state = state

    def __reduce__(self):
        return (type(self), (), self.state)


class MyInt(int):
    sample = 1


class MyFloat(float):
    sample = 1.0


class MyComplex(complex):
    sample = 1.0 + 0j


class MyStr(str):
    sample = "hello"


class MyUnicode(str):
    sample = "hello ሴ"


class MyTuple(tuple):
    sample = (1, 2, 3)


class MyList(list):
    sample = [1, 2, 3]


class MyDict(dict):
    sample = {"a": 1, "b": 2}


class MySet(set):
    sample = {"a", "b"}


class MyFrozenSet(frozenset):
    sample = frozenset({"a", "b"})


myclasses = [
    MyInt,
    MyFloat,
    MyComplex,
    MyStr,
    MyUnicode,
    MyTuple,
    MyList,
    MyDict,
    MySet,
    MyFrozenSet,
]


class MyIntWithNew(int):
    def __new__(cls, value):
        raise AssertionError


class MyIntWithNew2(MyIntWithNew):
    __new__ = int.__new__


class SlotList(MyList):
    __slots__ = ["foo"]


class SimpleNewObj(int):
    def __init__(self, *args, **kwargs):
        raise TypeError("SimpleNewObj.__init__() didn't expect to get called")

    def __eq__(self, other):
        return (int(self) == int(other)) and (self.__dict__ == other.__dict__)


class ComplexNewObj(SimpleNewObj):
    def __getnewargs__(self):
        return (("%X" % self), 16)


class ComplexNewObjEx(SimpleNewObj):
    def __getnewargs_ex__(self):
        return ((("%X" % self),), {"base": 16})


class BadGetattr:
    def __getattr__(self, key):
        self.foo


class AbstractPickleModuleTests(unittest.TestCase):
    def test_dump_closed_file(self):
        f = open(TESTFN, "wb")
        try:
            f.close()
            self.assertRaises(ValueError, self.dump, 123, f)
        finally:
            os_helper.unlink(TESTFN)

    def test_load_closed_file(self):
        f = open(TESTFN, "wb")
        try:
            f.close()
            self.assertRaises(ValueError, self.dump, 123, f)
        finally:
            os_helper.unlink(TESTFN)

    def test_load_from_and_dump_to_file(self):
        stream = io.BytesIO()
        data = [123, {}, 124]
        self.dump(data, stream)
        stream.seek(0)
        unpickled = self.load(stream)
        self.assertEqual(unpickled, data)

    def test_highest_protocol(self):
        self.assertEqual(pickle.HIGHEST_PROTOCOL, 5)

    def test_callapi(self):
        f = io.BytesIO()
        self.dump(123, f, (-1))
        self.dump(123, file=f, protocol=(-1))
        self.dumps(123, (-1))
        self.dumps(123, protocol=(-1))
        self.Pickler(f, (-1))
        self.Pickler(f, protocol=(-1))

    def test_dump_text_file(self):
        f = open(TESTFN, "w")
        try:
            for proto in protocols:
                self.assertRaises(TypeError, self.dump, 123, f, proto)
        finally:
            f.close()
            os_helper.unlink(TESTFN)

    def test_incomplete_input(self):
        s = io.BytesIO(b"X''.")
        self.assertRaises(
            (EOFError, struct.error, pickle.UnpicklingError), self.load, s
        )

    def test_bad_init(self):
        class BadPickler(self.Pickler):
            def __init__(self):
                pass

        class BadUnpickler(self.Unpickler):
            def __init__(self):
                pass

        self.assertRaises(pickle.PicklingError, BadPickler().dump, 0)
        self.assertRaises(pickle.UnpicklingError, BadUnpickler().load)

    def check_dumps_loads_oob_buffers(self, dumps, loads):
        obj = ZeroCopyBytes(b"foo")
        for proto in range(0, 5):
            with self.assertRaises(ValueError):
                dumps(obj, protocol=proto, buffer_callback=[].append)
        for proto in range(5, (pickle.HIGHEST_PROTOCOL + 1)):
            buffers = []
            buffer_callback = buffers.append
            data = dumps(obj, protocol=proto, buffer_callback=buffer_callback)
            self.assertNotIn(b"foo", data)
            self.assertEqual(bytes(buffers[0]), b"foo")
            with self.assertRaises(pickle.UnpicklingError):
                loads(data)
            new = loads(data, buffers=buffers)
            self.assertIs(new, obj)

    def test_dumps_loads_oob_buffers(self):
        self.check_dumps_loads_oob_buffers(self.dumps, self.loads)

    def test_dump_load_oob_buffers(self):
        def dumps(obj, **kwargs):
            f = io.BytesIO()
            self.dump(obj, f, **kwargs)
            return f.getvalue()

        def loads(data, **kwargs):
            f = io.BytesIO(data)
            return self.load(f, **kwargs)

        self.check_dumps_loads_oob_buffers(dumps, loads)


class AbstractPersistentPicklerTests(unittest.TestCase):
    def persistent_id(self, object):
        if isinstance(object, int) and ((object % 2) == 0):
            self.id_count += 1
            return str(object)
        elif object == "test_false_value":
            self.false_count += 1
            return ""
        else:
            return None

    def persistent_load(self, oid):
        if not oid:
            self.load_false_count += 1
            return "test_false_value"
        else:
            self.load_count += 1
            object = int(oid)
            assert (object % 2) == 0
            return object

    def test_persistence(self):
        L = list(range(10)) + ["test_false_value"]
        for proto in protocols:
            self.id_count = 0
            self.false_count = 0
            self.load_false_count = 0
            self.load_count = 0
            self.assertEqual(self.loads(self.dumps(L, proto)), L)
            self.assertEqual(self.id_count, 5)
            self.assertEqual(self.false_count, 1)
            self.assertEqual(self.load_count, 5)
            self.assertEqual(self.load_false_count, 1)


class AbstractIdentityPersistentPicklerTests(unittest.TestCase):
    def persistent_id(self, obj):
        return obj

    def persistent_load(self, pid):
        return pid

    def _check_return_correct_type(self, obj, proto):
        unpickled = self.loads(self.dumps(obj, proto))
        self.assertIsInstance(unpickled, type(obj))
        self.assertEqual(unpickled, obj)

    def test_return_correct_type(self):
        for proto in protocols:
            if proto == 0:
                self._check_return_correct_type("abc", 0)
            else:
                for obj in [b"abc\n", "abc\n", (-1), ((-1.1) * 0.1), str]:
                    self._check_return_correct_type(obj, proto)

    def test_protocol0_is_ascii_only(self):
        non_ascii_str = "∅"
        self.assertRaises(pickle.PicklingError, self.dumps, non_ascii_str, 0)
        pickled = (pickle.PERSID + non_ascii_str.encode("utf-8")) + b"\n."
        self.assertRaises(pickle.UnpicklingError, self.loads, pickled)


class AbstractPicklerUnpicklerObjectTests(unittest.TestCase):
    pickler_class = None
    unpickler_class = None

    def setUp(self):
        assert self.pickler_class
        assert self.unpickler_class

    def test_clear_pickler_memo(self):
        data = ["abcdefg", "abcdefg", 44]
        for proto in protocols:
            f = io.BytesIO()
            pickler = self.pickler_class(f, proto)
            pickler.dump(data)
            first_pickled = f.getvalue()
            f.seek(0)
            f.truncate()
            pickler.dump(data)
            second_pickled = f.getvalue()
            pickler.clear_memo()
            f.seek(0)
            f.truncate()
            pickler.dump(data)
            third_pickled = f.getvalue()
            self.assertNotEqual(first_pickled, second_pickled)
            self.assertEqual(first_pickled, third_pickled)

    def test_priming_pickler_memo(self):
        data = ["abcdefg", "abcdefg", 44]
        f = io.BytesIO()
        pickler = self.pickler_class(f)
        pickler.dump(data)
        first_pickled = f.getvalue()
        f = io.BytesIO()
        primed = self.pickler_class(f)
        primed.memo = pickler.memo
        primed.dump(data)
        primed_pickled = f.getvalue()
        self.assertNotEqual(first_pickled, primed_pickled)

    def test_priming_unpickler_memo(self):
        data = ["abcdefg", "abcdefg", 44]
        f = io.BytesIO()
        pickler = self.pickler_class(f)
        pickler.dump(data)
        first_pickled = f.getvalue()
        f = io.BytesIO()
        primed = self.pickler_class(f)
        primed.memo = pickler.memo
        primed.dump(data)
        primed_pickled = f.getvalue()
        unpickler = self.unpickler_class(io.BytesIO(first_pickled))
        unpickled_data1 = unpickler.load()
        self.assertEqual(unpickled_data1, data)
        primed = self.unpickler_class(io.BytesIO(primed_pickled))
        primed.memo = unpickler.memo
        unpickled_data2 = primed.load()
        primed.memo.clear()
        self.assertEqual(unpickled_data2, data)
        self.assertTrue((unpickled_data2 is unpickled_data1))

    def test_reusing_unpickler_objects(self):
        data1 = ["abcdefg", "abcdefg", 44]
        f = io.BytesIO()
        pickler = self.pickler_class(f)
        pickler.dump(data1)
        pickled1 = f.getvalue()
        data2 = ["abcdefg", 44, 44]
        f = io.BytesIO()
        pickler = self.pickler_class(f)
        pickler.dump(data2)
        pickled2 = f.getvalue()
        f = io.BytesIO()
        f.write(pickled1)
        f.seek(0)
        unpickler = self.unpickler_class(f)
        self.assertEqual(unpickler.load(), data1)
        f.seek(0)
        f.truncate()
        f.write(pickled2)
        f.seek(0)
        self.assertEqual(unpickler.load(), data2)

    def _check_multiple_unpicklings(self, ioclass, *, seekable=True):
        for proto in protocols:
            with self.subTest(proto=proto):
                data1 = [(x, str(x)) for x in range(2000)] + [b"abcde", len]
                f = ioclass()
                pickler = self.pickler_class(f, protocol=proto)
                pickler.dump(data1)
                pickled = f.getvalue()
                N = 5
                f = ioclass((pickled * N))
                unpickler = self.unpickler_class(f)
                for i in range(N):
                    if seekable:
                        pos = f.tell()
                    self.assertEqual(unpickler.load(), data1)
                    if seekable:
                        self.assertEqual(f.tell(), (pos + len(pickled)))
                self.assertRaises(EOFError, unpickler.load)

    def test_multiple_unpicklings_seekable(self):
        self._check_multiple_unpicklings(io.BytesIO)

    def test_multiple_unpicklings_unseekable(self):
        self._check_multiple_unpicklings(UnseekableIO, seekable=False)

    def test_multiple_unpicklings_minimal(self):
        self._check_multiple_unpicklings(MinimalIO, seekable=False)

    def test_unpickling_buffering_readline(self):
        data = list(range(10))
        for proto in protocols:
            for buf_size in range(1, 11):
                f = io.BufferedRandom(io.BytesIO(), buffer_size=buf_size)
                pickler = self.pickler_class(f, protocol=proto)
                pickler.dump(data)
                f.seek(0)
                unpickler = self.unpickler_class(f)
                self.assertEqual(unpickler.load(), data)


REDUCE_A = "reduce_A"


class AAA(object):
    def __reduce__(self):
        return (str, (REDUCE_A,))


class BBB(object):
    def __init__(self):
        self.a = "some attribute"

    def __setstate__(self, state):
        self.a = "BBB.__setstate__"


def setstate_bbb(obj, state):
    "Custom state setter for BBB objects\n\n    Such callable may be created by other persons than the ones who created the\n    BBB class. If passed as the state_setter item of a custom reducer, this\n    allows for custom state setting behavior of BBB objects. One can think of\n    it as the analogous of list_setitems or dict_setitems but for foreign\n    classes/functions.\n    "
    obj.a = "custom state_setter"


class AbstractCustomPicklerClass:
    "Pickler implementing a reducing hook using reducer_override."

    def reducer_override(self, obj):
        obj_name = getattr(obj, "__name__", None)
        if obj_name == "f":
            return (int, (5,))
        if obj_name == "MyClass":
            return (str, ("some str",))
        elif obj_name == "g":
            return False
        elif obj_name == "h":
            raise ValueError("The reducer just failed")
        return NotImplemented


class AbstractHookTests(unittest.TestCase):
    def test_pickler_hook(self):
        def f():
            pass

        def g():
            pass

        def h():
            pass

        class MyClass:
            pass

        for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.subTest(proto=proto):
                bio = io.BytesIO()
                p = self.pickler_class(bio, proto)
                p.dump([f, MyClass, math.log])
                (new_f, some_str, math_log) = pickle.loads(bio.getvalue())
                self.assertEqual(new_f, 5)
                self.assertEqual(some_str, "some str")
                self.assertIs(math_log, math.log)
                with self.assertRaises(pickle.PicklingError):
                    p.dump(g)
                with self.assertRaisesRegex(ValueError, "The reducer just failed"):
                    p.dump(h)

    @support.cpython_only
    def test_reducer_override_no_reference_cycle(self):
        for proto in range(0, (pickle.HIGHEST_PROTOCOL + 1)):
            with self.subTest(proto=proto):

                def f():
                    pass

                wr = weakref.ref(f)
                bio = io.BytesIO()
                p = self.pickler_class(bio, proto)
                p.dump(f)
                new_f = pickle.loads(bio.getvalue())
                assert new_f == 5
                del p
                del f
                self.assertIsNone(wr())


class AbstractDispatchTableTests(unittest.TestCase):
    def test_default_dispatch_table(self):
        f = io.BytesIO()
        p = self.pickler_class(f, 0)
        with self.assertRaises(AttributeError):
            p.dispatch_table
        self.assertFalse(hasattr(p, "dispatch_table"))

    def test_class_dispatch_table(self):
        dt = self.get_dispatch_table()

        class MyPickler(self.pickler_class):
            dispatch_table = dt

        def dumps(obj, protocol=None):
            f = io.BytesIO()
            p = MyPickler(f, protocol)
            self.assertEqual(p.dispatch_table, dt)
            p.dump(obj)
            return f.getvalue()

        self._test_dispatch_table(dumps, dt)

    def test_instance_dispatch_table(self):
        dt = self.get_dispatch_table()

        def dumps(obj, protocol=None):
            f = io.BytesIO()
            p = self.pickler_class(f, protocol)
            p.dispatch_table = dt
            self.assertEqual(p.dispatch_table, dt)
            p.dump(obj)
            return f.getvalue()

        self._test_dispatch_table(dumps, dt)

    def _test_dispatch_table(self, dumps, dispatch_table):
        def custom_load_dump(obj):
            return pickle.loads(dumps(obj, 0))

        def default_load_dump(obj):
            return pickle.loads(pickle.dumps(obj, 0))

        z = 1 + 2j
        self.assertEqual(custom_load_dump(z), z)
        self.assertEqual(default_load_dump(z), z)
        REDUCE_1 = "reduce_1"

        def reduce_1(obj):
            return (str, (REDUCE_1,))

        dispatch_table[complex] = reduce_1
        self.assertEqual(custom_load_dump(z), REDUCE_1)
        self.assertEqual(default_load_dump(z), z)
        a = AAA()
        b = BBB()
        self.assertEqual(custom_load_dump(a), REDUCE_A)
        self.assertIsInstance(custom_load_dump(b), BBB)
        self.assertEqual(default_load_dump(a), REDUCE_A)
        self.assertIsInstance(default_load_dump(b), BBB)
        dispatch_table[BBB] = reduce_1
        self.assertEqual(custom_load_dump(a), REDUCE_A)
        self.assertEqual(custom_load_dump(b), REDUCE_1)
        self.assertEqual(default_load_dump(a), REDUCE_A)
        self.assertIsInstance(default_load_dump(b), BBB)
        REDUCE_2 = "reduce_2"

        def reduce_2(obj):
            return (str, (REDUCE_2,))

        dispatch_table[AAA] = reduce_2
        del dispatch_table[BBB]
        self.assertEqual(custom_load_dump(a), REDUCE_2)
        self.assertIsInstance(custom_load_dump(b), BBB)
        self.assertEqual(default_load_dump(a), REDUCE_A)
        self.assertIsInstance(default_load_dump(b), BBB)
        self.assertEqual(default_load_dump(b).a, "BBB.__setstate__")

        def reduce_bbb(obj):
            return (BBB, (), obj.__dict__, None, None, setstate_bbb)

        dispatch_table[BBB] = reduce_bbb
        self.assertEqual(custom_load_dump(b).a, "custom state_setter")


if __name__ == "__main__":
    from pickletools import dis

    x = create_data()
    for i in range((pickle.HIGHEST_PROTOCOL + 1)):
        p = pickle.dumps(x, i)
        print("DATA{0} = (".format(i))
        for j in range(0, len(p), 20):
            b = bytes(p[j : (j + 20)])
            print("    {0!r}".format(b))
        print(")")
        print()
        print("# Disassembly of DATA{0}".format(i))
        print('DATA{0}_DIS = """\\'.format(i))
        dis(p)
        print('"""')
        print()
