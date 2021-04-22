import unittest
import weakref
from test.support import gc_collect
from test.support.script_helper import assert_python_ok
import sys

ModuleType = type(sys)


class FullLoader:
    @classmethod
    def module_repr(cls, m):
        return "<module '{}' (crafted)>".format(m.__name__)


class BareLoader:
    pass


class ModuleTests(unittest.TestCase):
    def test_uninitialized(self):
        foo = ModuleType.__new__(ModuleType)
        self.assertTrue((foo.__dict__ is None))
        self.assertRaises(SystemError, dir, foo)
        try:
            s = foo.__name__
            self.fail(("__name__ = %s" % repr(s)))
        except AttributeError:
            pass
        self.assertEqual(foo.__doc__, ModuleType.__doc__)

    def test_uninitialized_missing_getattr(self):
        foo = ModuleType.__new__(ModuleType)
        self.assertRaisesRegex(
            AttributeError,
            "module has no attribute 'not_here'",
            getattr,
            foo,
            "not_here",
        )

    def test_missing_getattr(self):
        foo = ModuleType("foo")
        self.assertRaisesRegex(
            AttributeError,
            "module 'foo' has no attribute 'not_here'",
            getattr,
            foo,
            "not_here",
        )

    def test_no_docstring(self):
        foo = ModuleType("foo")
        self.assertEqual(foo.__name__, "foo")
        self.assertEqual(foo.__doc__, None)
        self.assertIs(foo.__loader__, None)
        self.assertIs(foo.__package__, None)
        self.assertIs(foo.__spec__, None)
        self.assertEqual(
            foo.__dict__,
            {
                "__name__": "foo",
                "__doc__": None,
                "__loader__": None,
                "__package__": None,
                "__spec__": None,
            },
        )

    def test_ascii_docstring(self):
        foo = ModuleType("foo", "foodoc")
        self.assertEqual(foo.__name__, "foo")
        self.assertEqual(foo.__doc__, "foodoc")
        self.assertEqual(
            foo.__dict__,
            {
                "__name__": "foo",
                "__doc__": "foodoc",
                "__loader__": None,
                "__package__": None,
                "__spec__": None,
            },
        )

    def test_unicode_docstring(self):
        foo = ModuleType("foo", "foodocሴ")
        self.assertEqual(foo.__name__, "foo")
        self.assertEqual(foo.__doc__, "foodocሴ")
        self.assertEqual(
            foo.__dict__,
            {
                "__name__": "foo",
                "__doc__": "foodocሴ",
                "__loader__": None,
                "__package__": None,
                "__spec__": None,
            },
        )

    def test_reinit(self):
        foo = ModuleType("foo", "foodocሴ")
        foo.bar = 42
        d = foo.__dict__
        foo.__init__("foo", "foodoc")
        self.assertEqual(foo.__name__, "foo")
        self.assertEqual(foo.__doc__, "foodoc")
        self.assertEqual(foo.bar, 42)
        self.assertEqual(
            foo.__dict__,
            {
                "__name__": "foo",
                "__doc__": "foodoc",
                "bar": 42,
                "__loader__": None,
                "__package__": None,
                "__spec__": None,
            },
        )
        self.assertTrue((foo.__dict__ is d))

    def test_dont_clear_dict(self):
        def f():
            foo = ModuleType("foo")
            foo.bar = 4
            return foo

        gc_collect()
        self.assertEqual(f().__dict__["bar"], 4)

    def test_clear_dict_in_ref_cycle(self):
        destroyed = []
        m = ModuleType("foo")
        m.destroyed = destroyed
        s = "class A:\n    def __init__(self, l):\n        self.l = l\n    def __del__(self):\n        self.l.append(1)\na = A(destroyed)"
        exec(s, m.__dict__)
        del m
        gc_collect()
        self.assertEqual(destroyed, [1])

    def test_weakref(self):
        m = ModuleType("foo")
        wr = weakref.ref(m)
        self.assertIs(wr(), m)
        del m
        gc_collect()
        self.assertIs(wr(), None)

    def test_module_getattr(self):
        import test.good_getattr as gga
        from test.good_getattr import test

        self.assertEqual(test, "There is test")
        self.assertEqual(gga.x, 1)
        self.assertEqual(gga.y, 2)
        with self.assertRaisesRegex(AttributeError, "Deprecated, use whatever instead"):
            gga.yolo
        self.assertEqual(gga.whatever, "There is whatever")
        del sys.modules["test.good_getattr"]

    def test_module_getattr_errors(self):
        import test.bad_getattr as bga
        from test import bad_getattr2

        self.assertEqual(bga.x, 1)
        self.assertEqual(bad_getattr2.x, 1)
        with self.assertRaises(TypeError):
            bga.nope
        with self.assertRaises(TypeError):
            bad_getattr2.nope
        del sys.modules["test.bad_getattr"]
        if "test.bad_getattr2" in sys.modules:
            del sys.modules["test.bad_getattr2"]

    def test_module_dir(self):
        import test.good_getattr as gga

        self.assertEqual(dir(gga), ["a", "b", "c"])
        del sys.modules["test.good_getattr"]

    def test_module_dir_errors(self):
        import test.bad_getattr as bga
        from test import bad_getattr2

        with self.assertRaises(TypeError):
            dir(bga)
        with self.assertRaises(TypeError):
            dir(bad_getattr2)
        del sys.modules["test.bad_getattr"]
        if "test.bad_getattr2" in sys.modules:
            del sys.modules["test.bad_getattr2"]

    def test_module_getattr_tricky(self):
        from test import bad_getattr3

        with self.assertRaises(AttributeError):
            bad_getattr3.one
        with self.assertRaises(AttributeError):
            bad_getattr3.delgetattr
        if "test.bad_getattr3" in sys.modules:
            del sys.modules["test.bad_getattr3"]

    def test_module_repr_minimal(self):
        m = ModuleType("foo")
        del m.__name__
        self.assertEqual(repr(m), "<module '?'>")

    def test_module_repr_with_name(self):
        m = ModuleType("foo")
        self.assertEqual(repr(m), "<module 'foo'>")

    def test_module_repr_with_name_and_filename(self):
        m = ModuleType("foo")
        m.__file__ = "/tmp/foo.py"
        self.assertEqual(repr(m), "<module 'foo' from '/tmp/foo.py'>")

    def test_module_repr_with_filename_only(self):
        m = ModuleType("foo")
        del m.__name__
        m.__file__ = "/tmp/foo.py"
        self.assertEqual(repr(m), "<module '?' from '/tmp/foo.py'>")

    def test_module_repr_with_loader_as_None(self):
        m = ModuleType("foo")
        assert m.__loader__ is None
        self.assertEqual(repr(m), "<module 'foo'>")

    def test_module_repr_with_bare_loader_but_no_name(self):
        m = ModuleType("foo")
        del m.__name__
        m.__loader__ = BareLoader
        loader_repr = repr(BareLoader)
        self.assertEqual(repr(m), "<module '?' ({})>".format(loader_repr))

    def test_module_repr_with_full_loader_but_no_name(self):
        m = ModuleType("foo")
        del m.__name__
        m.__loader__ = FullLoader
        loader_repr = repr(FullLoader)
        self.assertEqual(repr(m), "<module '?' ({})>".format(loader_repr))

    def test_module_repr_with_bare_loader(self):
        m = ModuleType("foo")
        m.__loader__ = BareLoader
        module_repr = repr(BareLoader)
        self.assertEqual(repr(m), "<module 'foo' ({})>".format(module_repr))

    def test_module_repr_with_full_loader(self):
        m = ModuleType("foo")
        m.__loader__ = FullLoader
        self.assertEqual(repr(m), "<module 'foo' (crafted)>")

    def test_module_repr_with_bare_loader_and_filename(self):
        m = ModuleType("foo")
        m.__loader__ = BareLoader
        m.__file__ = "/tmp/foo.py"
        self.assertEqual(repr(m), "<module 'foo' from '/tmp/foo.py'>")

    def test_module_repr_with_full_loader_and_filename(self):
        m = ModuleType("foo")
        m.__loader__ = FullLoader
        m.__file__ = "/tmp/foo.py"
        self.assertEqual(repr(m), "<module 'foo' (crafted)>")

    def test_module_repr_builtin(self):
        self.assertEqual(repr(sys), "<module 'sys' (built-in)>")

    def test_module_repr_source(self):
        r = repr(unittest)
        starts_with = "<module 'unittest' from '"
        ends_with = "__init__.py'>"
        self.assertEqual(
            r[: len(starts_with)],
            starts_with,
            "{!r} does not start with {!r}".format(r, starts_with),
        )
        self.assertEqual(
            r[(-len(ends_with)) :],
            ends_with,
            "{!r} does not end with {!r}".format(r, ends_with),
        )

    def test_module_finalization_at_shutdown(self):
        (rc, out, err) = assert_python_ok("-c", "from test import final_a")
        self.assertFalse(err)
        lines = out.splitlines()
        self.assertEqual(
            set(lines),
            {
                b"x = a",
                b"x = b",
                b"final_a.x = a",
                b"final_b.x = b",
                b"len = len",
                b"shutil.rmtree = rmtree",
            },
        )

    def test_descriptor_errors_propagate(self):
        class Descr:
            def __get__(self, o, t):
                raise RuntimeError

        class M(ModuleType):
            melon = Descr()

        self.assertRaises(RuntimeError, getattr, M("mymod"), "melon")


if __name__ == "__main__":
    unittest.main()
