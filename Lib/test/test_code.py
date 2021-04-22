"This module includes tests of the code object representation.\n\n>>> def f(x):\n...     def g(y):\n...         return x + y\n...     return g\n...\n\n>>> dump(f.__code__)\nname: f\nargcount: 1\nposonlyargcount: 0\nkwonlyargcount: 0\nnames: ()\nvarnames: ('x', 'g')\ncellvars: ('x',)\nfreevars: ()\nnlocals: 2\nflags: 3\nconsts: ('None', '<code object g>', \"'f.<locals>.g'\")\n\n>>> dump(f(4).__code__)\nname: g\nargcount: 1\nposonlyargcount: 0\nkwonlyargcount: 0\nnames: ()\nvarnames: ('y',)\ncellvars: ()\nfreevars: ('x',)\nnlocals: 1\nflags: 19\nconsts: ('None',)\n\n>>> def h(x, y):\n...     a = x + y\n...     b = x - y\n...     c = a * b\n...     return c\n...\n\n>>> dump(h.__code__)\nname: h\nargcount: 2\nposonlyargcount: 0\nkwonlyargcount: 0\nnames: ()\nvarnames: ('x', 'y', 'a', 'b', 'c')\ncellvars: ()\nfreevars: ()\nnlocals: 5\nflags: 67\nconsts: ('None',)\n\n>>> def attrs(obj):\n...     print(obj.attr1)\n...     print(obj.attr2)\n...     print(obj.attr3)\n\n>>> dump(attrs.__code__)\nname: attrs\nargcount: 1\nposonlyargcount: 0\nkwonlyargcount: 0\nnames: ('print', 'attr1', 'attr2', 'attr3')\nvarnames: ('obj',)\ncellvars: ()\nfreevars: ()\nnlocals: 1\nflags: 67\nconsts: ('None',)\n\n>>> def optimize_away():\n...     'doc string'\n...     'not a docstring'\n...     53\n...     0x53\n\n>>> dump(optimize_away.__code__)\nname: optimize_away\nargcount: 0\nposonlyargcount: 0\nkwonlyargcount: 0\nnames: ()\nvarnames: ()\ncellvars: ()\nfreevars: ()\nnlocals: 0\nflags: 67\nconsts: (\"'doc string'\", 'None')\n\n>>> def keywordonly_args(a,b,*,k1):\n...     return a,b,k1\n...\n\n>>> dump(keywordonly_args.__code__)\nname: keywordonly_args\nargcount: 2\nposonlyargcount: 0\nkwonlyargcount: 1\nnames: ()\nvarnames: ('a', 'b', 'k1')\ncellvars: ()\nfreevars: ()\nnlocals: 3\nflags: 67\nconsts: ('None',)\n\n>>> def posonly_args(a,b,/,c):\n...     return a,b,c\n...\n\n>>> dump(posonly_args.__code__)\nname: posonly_args\nargcount: 3\nposonlyargcount: 2\nkwonlyargcount: 0\nnames: ()\nvarnames: ('a', 'b', 'c')\ncellvars: ()\nfreevars: ()\nnlocals: 3\nflags: 67\nconsts: ('None',)\n\n"
import inspect
import sys
import threading
import unittest
import weakref

try:
    import ctypes
except ImportError:
    ctypes = None
from test.support import run_doctest, run_unittest, cpython_only, check_impl_detail


def consts(t):
    "Yield a doctest-safe sequence of object reprs."
    for elt in t:
        r = repr(elt)
        if r.startswith("<code object"):
            (yield ("<code object %s>" % elt.co_name))
        else:
            (yield r)


def dump(co):
    "Print out a text representation of a code object."
    for attr in [
        "name",
        "argcount",
        "posonlyargcount",
        "kwonlyargcount",
        "names",
        "varnames",
        "cellvars",
        "freevars",
        "nlocals",
        "flags",
    ]:
        print(("%s: %s" % (attr, getattr(co, ("co_" + attr)))))
    print("consts:", tuple(consts(co.co_consts)))


def external_getitem(self, i):
    return f"Foreign getitem: {super().__getitem__(i)}"


class CodeTest(unittest.TestCase):
    @cpython_only
    def test_newempty(self):
        import _testcapi

        co = _testcapi.code_newempty("filename", "funcname", 15)
        self.assertEqual(co.co_filename, "filename")
        self.assertEqual(co.co_name, "funcname")
        self.assertEqual(co.co_firstlineno, 15)

    @cpython_only
    def test_closure_injection(self):
        from types import FunctionType

        def create_closure(__class__):
            return (lambda: __class__).__closure__

        def new_code(c):
            "A new code object with a __class__ cell added to freevars"
            return c.replace(co_freevars=(c.co_freevars + ("__class__",)))

        def add_foreign_method(cls, name, f):
            code = new_code(f.__code__)
            assert not f.__closure__
            closure = create_closure(cls)
            defaults = f.__defaults__
            setattr(cls, name, FunctionType(code, globals(), name, defaults, closure))

        class List(list):
            pass

        add_foreign_method(List, "__getitem__", external_getitem)
        function = List.__getitem__
        class_ref = function.__closure__[0].cell_contents
        self.assertIs(class_ref, List)
        self.assertFalse(
            (function.__code__.co_flags & inspect.CO_NOFREE),
            hex(function.__code__.co_flags),
        )
        obj = List([1, 2, 3])
        self.assertEqual(obj[0], "Foreign getitem: 1")

    def test_constructor(self):
        def func():
            pass

        co = func.__code__
        CodeType = type(co)
        return CodeType(
            co.co_argcount,
            co.co_posonlyargcount,
            co.co_kwonlyargcount,
            co.co_nlocals,
            co.co_stacksize,
            co.co_flags,
            co.co_code,
            co.co_consts,
            co.co_names,
            co.co_varnames,
            co.co_filename,
            co.co_name,
            co.co_firstlineno,
            co.co_lnotab,
            co.co_freevars,
            co.co_cellvars,
        )

    def test_replace(self):
        def func():
            x = 1
            return x

        code = func.__code__

        def func2():
            y = 2
            return y

        code2 = func2.__code__
        for (attr, value) in (
            ("co_argcount", 0),
            ("co_posonlyargcount", 0),
            ("co_kwonlyargcount", 0),
            ("co_nlocals", 0),
            ("co_stacksize", 0),
            ("co_flags", (code.co_flags | inspect.CO_COROUTINE)),
            ("co_firstlineno", 100),
            ("co_code", code2.co_code),
            ("co_consts", code2.co_consts),
            ("co_names", ("myname",)),
            ("co_varnames", code2.co_varnames),
            ("co_freevars", ("freevar",)),
            ("co_cellvars", ("cellvar",)),
            ("co_filename", "newfilename"),
            ("co_name", "newname"),
            ("co_linetable", code2.co_linetable),
        ):
            with self.subTest(attr=attr, value=value):
                new_code = code.replace(**{attr: value})
                self.assertEqual(getattr(new_code, attr), value)


def isinterned(s):
    return s is sys.intern((("_" + s) + "_")[1:(-1)])


class CodeConstsTest(unittest.TestCase):
    def find_const(self, consts, value):
        for v in consts:
            if v == value:
                return v
        self.assertIn(value, consts)
        self.fail("Should never be reached")

    def assertIsInterned(self, s):
        if not isinterned(s):
            self.fail(("String %r is not interned" % (s,)))

    def assertIsNotInterned(self, s):
        if isinterned(s):
            self.fail(("String %r is interned" % (s,)))

    @cpython_only
    def test_interned_string(self):
        co = compile('res = "str_value"', "?", "exec")
        v = self.find_const(co.co_consts, "str_value")
        self.assertIsInterned(v)

    @cpython_only
    def test_interned_string_in_tuple(self):
        co = compile('res = ("str_value",)', "?", "exec")
        v = self.find_const(co.co_consts, ("str_value",))
        self.assertIsInterned(v[0])

    @cpython_only
    def test_interned_string_in_frozenset(self):
        co = compile('res = a in {"str_value"}', "?", "exec")
        v = self.find_const(co.co_consts, frozenset(("str_value",)))
        self.assertIsInterned(tuple(v)[0])

    @cpython_only
    def test_interned_string_default(self):
        def f(a="str_value"):
            return a

        self.assertIsInterned(f())

    @cpython_only
    def test_interned_string_with_null(self):
        co = compile('res = "str\\0value!"', "?", "exec")
        v = self.find_const(co.co_consts, "str\x00value!")
        self.assertIsNotInterned(v)


class CodeWeakRefTest(unittest.TestCase):
    def test_basic(self):
        namespace = {}
        exec("def f(): pass", globals(), namespace)
        f = namespace["f"]
        del namespace
        self.called = False

        def callback(code):
            self.called = True

        coderef = weakref.ref(f.__code__, callback)
        self.assertTrue(bool(coderef()))
        del f
        self.assertFalse(bool(coderef()))
        self.assertTrue(self.called)


if check_impl_detail(cpython=True) and (ctypes is not None):
    py = ctypes.pythonapi
    freefunc = ctypes.CFUNCTYPE(None, ctypes.c_voidp)
    RequestCodeExtraIndex = py._PyEval_RequestCodeExtraIndex
    RequestCodeExtraIndex.argtypes = (freefunc,)
    RequestCodeExtraIndex.restype = ctypes.c_ssize_t
    SetExtra = py._PyCode_SetExtra
    SetExtra.argtypes = (ctypes.py_object, ctypes.c_ssize_t, ctypes.c_voidp)
    SetExtra.restype = ctypes.c_int
    GetExtra = py._PyCode_GetExtra
    GetExtra.argtypes = (
        ctypes.py_object,
        ctypes.c_ssize_t,
        ctypes.POINTER(ctypes.c_voidp),
    )
    GetExtra.restype = ctypes.c_int
    LAST_FREED = None

    def myfree(ptr):
        global LAST_FREED
        LAST_FREED = ptr

    FREE_FUNC = freefunc(myfree)
    FREE_INDEX = RequestCodeExtraIndex(FREE_FUNC)

    class CoExtra(unittest.TestCase):
        def get_func(self):
            return eval("lambda:42")

        def test_get_non_code(self):
            f = self.get_func()
            self.assertRaises(
                SystemError, SetExtra, 42, FREE_INDEX, ctypes.c_voidp(100)
            )
            self.assertRaises(
                SystemError, GetExtra, 42, FREE_INDEX, ctypes.c_voidp(100)
            )

        def test_bad_index(self):
            f = self.get_func()
            self.assertRaises(
                SystemError,
                SetExtra,
                f.__code__,
                (FREE_INDEX + 100),
                ctypes.c_voidp(100),
            )
            self.assertEqual(
                GetExtra(f.__code__, (FREE_INDEX + 100), ctypes.c_voidp(100)), 0
            )

        def test_free_called(self):
            f = self.get_func()
            SetExtra(f.__code__, FREE_INDEX, ctypes.c_voidp(100))
            del f
            self.assertEqual(LAST_FREED, 100)

        def test_get_set(self):
            f = self.get_func()
            extra = ctypes.c_voidp()
            SetExtra(f.__code__, FREE_INDEX, ctypes.c_voidp(200))
            SetExtra(f.__code__, FREE_INDEX, ctypes.c_voidp(300))
            self.assertEqual(LAST_FREED, 200)
            extra = ctypes.c_voidp()
            GetExtra(f.__code__, FREE_INDEX, extra)
            self.assertEqual(extra.value, 300)
            del f

        def test_free_different_thread(self):
            f = self.get_func()

            class ThreadTest(threading.Thread):
                def __init__(self, f, test):
                    super().__init__()
                    self.f = f
                    self.test = test

                def run(self):
                    del self.f
                    self.test.assertEqual(LAST_FREED, 500)

            SetExtra(f.__code__, FREE_INDEX, ctypes.c_voidp(500))
            tt = ThreadTest(f, self)
            del f
            tt.start()
            tt.join()
            self.assertEqual(LAST_FREED, 500)


def test_main(verbose=None):
    from test import test_code

    run_doctest(test_code, verbose)
    tests = [CodeTest, CodeConstsTest, CodeWeakRefTest]
    if check_impl_detail(cpython=True) and (ctypes is not None):
        tests.append(CoExtra)
    run_unittest(*tests)


if __name__ == "__main__":
    test_main()
