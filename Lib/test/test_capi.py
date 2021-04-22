from collections import OrderedDict
import importlib.machinery
import importlib.util
import os
import pickle
import random
import re
import subprocess
import sys
import textwrap
import threading
import time
import unittest
import weakref
from test import support
from test.support import MISSING_C_DOCSTRINGS
from test.support import import_helper
from test.support import threading_helper
from test.support import warnings_helper
from test.support.script_helper import assert_python_failure, assert_python_ok

try:
    import _posixsubprocess
except ImportError:
    _posixsubprocess = None
_testcapi = import_helper.import_module("_testcapi")
import _testinternalcapi

Py_DEBUG = hasattr(sys, "gettotalrefcount")


def decode_stderr(err):
    return err.decode("utf-8", "replace").replace("\r", "")


def testfunction(self):
    "some doc"
    return self


class InstanceMethod:
    id = _testcapi.instancemethod(id)
    testfunction = _testcapi.instancemethod(testfunction)


class CAPITest(unittest.TestCase):
    def test_instancemethod(self):
        inst = InstanceMethod()
        self.assertEqual(id(inst), inst.id())
        self.assertTrue((inst.testfunction() is inst))
        self.assertEqual(inst.testfunction.__doc__, testfunction.__doc__)
        self.assertEqual(InstanceMethod.testfunction.__doc__, testfunction.__doc__)
        InstanceMethod.testfunction.attribute = "test"
        self.assertEqual(testfunction.attribute, "test")
        self.assertRaises(
            AttributeError, setattr, inst.testfunction, "attribute", "test"
        )

    def test_no_FatalError_infinite_loop(self):
        with support.SuppressCrashReport():
            p = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import _testcapi;_testcapi.crash_no_current_thread()",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        (out, err) = p.communicate()
        self.assertEqual(out, b"")
        self.assertTrue(
            err.rstrip().startswith(
                b"Fatal Python error: PyThreadState_Get: the function must be called with the GIL held, but the GIL is released (the current Python thread state is NULL)"
            ),
            err,
        )

    def test_memoryview_from_NULL_pointer(self):
        self.assertRaises(ValueError, _testcapi.make_memoryview_from_NULL_pointer)

    def test_exc_info(self):
        raised_exception = ValueError("5")
        new_exc = TypeError("TEST")
        try:
            raise raised_exception
        except ValueError as e:
            tb = e.__traceback__
            orig_sys_exc_info = sys.exc_info()
            orig_exc_info = _testcapi.set_exc_info(new_exc.__class__, new_exc, None)
            new_sys_exc_info = sys.exc_info()
            new_exc_info = _testcapi.set_exc_info(*orig_exc_info)
            reset_sys_exc_info = sys.exc_info()
            self.assertEqual(orig_exc_info[1], e)
            self.assertSequenceEqual(
                orig_exc_info, (raised_exception.__class__, raised_exception, tb)
            )
            self.assertSequenceEqual(orig_sys_exc_info, orig_exc_info)
            self.assertSequenceEqual(reset_sys_exc_info, orig_exc_info)
            self.assertSequenceEqual(new_exc_info, (new_exc.__class__, new_exc, None))
            self.assertSequenceEqual(new_sys_exc_info, new_exc_info)
        else:
            self.assertTrue(False)

    @unittest.skipUnless(_posixsubprocess, "_posixsubprocess required for this test.")
    def test_seq_bytes_to_charp_array(self):
        class Z(object):
            def __len__(self):
                return 1

        self.assertRaises(
            TypeError,
            _posixsubprocess.fork_exec,
            1,
            Z(),
            3,
            (1, 2),
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
        )

        class Z(object):
            def __len__(self):
                return sys.maxsize

            def __getitem__(self, i):
                return b"x"

        self.assertRaises(
            MemoryError,
            _posixsubprocess.fork_exec,
            1,
            Z(),
            3,
            (1, 2),
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
        )

    @unittest.skipUnless(_posixsubprocess, "_posixsubprocess required for this test.")
    def test_subprocess_fork_exec(self):
        class Z(object):
            def __len__(self):
                return 1

        self.assertRaises(
            TypeError,
            _posixsubprocess.fork_exec,
            Z(),
            [b"1"],
            3,
            (1, 2),
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
        )

    @unittest.skipIf(
        MISSING_C_DOCSTRINGS, "Signature information for builtins requires docstrings"
    )
    def test_docstring_signature_parsing(self):
        self.assertEqual(_testcapi.no_docstring.__doc__, None)
        self.assertEqual(_testcapi.no_docstring.__text_signature__, None)
        self.assertEqual(_testcapi.docstring_empty.__doc__, None)
        self.assertEqual(_testcapi.docstring_empty.__text_signature__, None)
        self.assertEqual(
            _testcapi.docstring_no_signature.__doc__, "This docstring has no signature."
        )
        self.assertEqual(_testcapi.docstring_no_signature.__text_signature__, None)
        self.assertEqual(
            _testcapi.docstring_with_invalid_signature.__doc__,
            "docstring_with_invalid_signature($module, /, boo)\n\nThis docstring has an invalid signature.",
        )
        self.assertEqual(
            _testcapi.docstring_with_invalid_signature.__text_signature__, None
        )
        self.assertEqual(
            _testcapi.docstring_with_invalid_signature2.__doc__,
            "docstring_with_invalid_signature2($module, /, boo)\n\n--\n\nThis docstring also has an invalid signature.",
        )
        self.assertEqual(
            _testcapi.docstring_with_invalid_signature2.__text_signature__, None
        )
        self.assertEqual(
            _testcapi.docstring_with_signature.__doc__,
            "This docstring has a valid signature.",
        )
        self.assertEqual(
            _testcapi.docstring_with_signature.__text_signature__, "($module, /, sig)"
        )
        self.assertEqual(_testcapi.docstring_with_signature_but_no_doc.__doc__, None)
        self.assertEqual(
            _testcapi.docstring_with_signature_but_no_doc.__text_signature__,
            "($module, /, sig)",
        )
        self.assertEqual(
            _testcapi.docstring_with_signature_and_extra_newlines.__doc__,
            "\nThis docstring has a valid signature and some extra newlines.",
        )
        self.assertEqual(
            _testcapi.docstring_with_signature_and_extra_newlines.__text_signature__,
            "($module, /, parameter)",
        )

    def test_c_type_with_matrix_multiplication(self):
        M = _testcapi.matmulType
        m1 = M()
        m2 = M()
        self.assertEqual((m1 @ m2), ("matmul", m1, m2))
        self.assertEqual((m1 @ 42), ("matmul", m1, 42))
        self.assertEqual((42 @ m1), ("matmul", 42, m1))
        o = m1
        o @= m2
        self.assertEqual(o, ("imatmul", m1, m2))
        o = m1
        o @= 42
        self.assertEqual(o, ("imatmul", m1, 42))
        o = 42
        o @= m1
        self.assertEqual(o, ("matmul", 42, m1))

    def test_c_type_with_ipow(self):
        o = _testcapi.ipowType()
        self.assertEqual(o.__ipow__(1), (1, None))
        self.assertEqual(o.__ipow__(2, 2), (2, 2))

    def test_return_null_without_error(self):
        if Py_DEBUG:
            code = textwrap.dedent(
                "\n                import _testcapi\n                from test import support\n\n                with support.SuppressCrashReport():\n                    _testcapi.return_null_without_error()\n            "
            )
            (rc, out, err) = assert_python_failure("-c", code)
            err = decode_stderr(err)
            self.assertRegex(
                err,
                'Fatal Python error: _Py_CheckFunctionResult: a function returned NULL without setting an exception\\nPython runtime state: initialized\\nSystemError: <built-in function return_null_without_error> returned NULL without setting an exception\\n\\nCurrent thread.*:\\n  File .*", line 6 in <module>\\n',
            )
        else:
            with self.assertRaises(SystemError) as cm:
                _testcapi.return_null_without_error()
            self.assertRegex(
                str(cm.exception),
                "return_null_without_error.* returned NULL without setting an exception",
            )

    def test_return_result_with_error(self):
        if Py_DEBUG:
            code = textwrap.dedent(
                "\n                import _testcapi\n                from test import support\n\n                with support.SuppressCrashReport():\n                    _testcapi.return_result_with_error()\n            "
            )
            (rc, out, err) = assert_python_failure("-c", code)
            err = decode_stderr(err)
            self.assertRegex(
                err,
                "Fatal Python error: _Py_CheckFunctionResult: a function returned a result with an exception set\\nPython runtime state: initialized\\nValueError\\n\\nThe above exception was the direct cause of the following exception:\\n\\nSystemError: <built-in function return_result_with_error> returned a result with an exception set\\n\\nCurrent thread.*:\\n  File .*, line 6 in <module>\\n",
            )
        else:
            with self.assertRaises(SystemError) as cm:
                _testcapi.return_result_with_error()
            self.assertRegex(
                str(cm.exception),
                "return_result_with_error.* returned a result with an exception set",
            )

    def test_getitem_with_error(self):
        code = textwrap.dedent(
            "\n            import _testcapi\n            from test import support\n\n            with support.SuppressCrashReport():\n                _testcapi.getitem_with_error({1: 2}, 1)\n        "
        )
        (rc, out, err) = assert_python_failure("-c", code)
        err = decode_stderr(err)
        if "SystemError: " not in err:
            self.assertRegex(
                err,
                "Fatal Python error: _Py_CheckSlotResult: Slot __getitem__ of type dict succeeded with an exception set\\nPython runtime state: initialized\\nValueError: bug\\n\\nCurrent thread .* \\(most recent call first\\):\\n  File .*, line 6 in <module>\\n\\nExtension modules: _testcapi \\(total: 1\\)\\n",
            )
        else:
            self.assertIn("returned a result with an exception set", err)

    def test_buildvalue_N(self):
        _testcapi.test_buildvalue_N()

    def test_set_nomemory(self):
        code = "if 1:\n            import _testcapi\n\n            class C(): pass\n\n            # The first loop tests both functions and that remove_mem_hooks()\n            # can be called twice in a row. The second loop checks a call to\n            # set_nomemory() after a call to remove_mem_hooks(). The third\n            # loop checks the start and stop arguments of set_nomemory().\n            for outer_cnt in range(1, 4):\n                start = 10 * outer_cnt\n                for j in range(100):\n                    if j == 0:\n                        if outer_cnt != 3:\n                            _testcapi.set_nomemory(start)\n                        else:\n                            _testcapi.set_nomemory(start, start + 1)\n                    try:\n                        C()\n                    except MemoryError as e:\n                        if outer_cnt != 3:\n                            _testcapi.remove_mem_hooks()\n                        print('MemoryError', outer_cnt, j)\n                        _testcapi.remove_mem_hooks()\n                        break\n        "
        (rc, out, err) = assert_python_ok("-c", code)
        self.assertIn(b"MemoryError 1 10", out)
        self.assertIn(b"MemoryError 2 20", out)
        self.assertIn(b"MemoryError 3 30", out)

    def test_mapping_keys_values_items(self):
        class Mapping1(dict):
            def keys(self):
                return list(super().keys())

            def values(self):
                return list(super().values())

            def items(self):
                return list(super().items())

        class Mapping2(dict):
            def keys(self):
                return tuple(super().keys())

            def values(self):
                return tuple(super().values())

            def items(self):
                return tuple(super().items())

        dict_obj = {"foo": 1, "bar": 2, "spam": 3}
        for mapping in [
            {},
            OrderedDict(),
            Mapping1(),
            Mapping2(),
            dict_obj,
            OrderedDict(dict_obj),
            Mapping1(dict_obj),
            Mapping2(dict_obj),
        ]:
            self.assertListEqual(
                _testcapi.get_mapping_keys(mapping), list(mapping.keys())
            )
            self.assertListEqual(
                _testcapi.get_mapping_values(mapping), list(mapping.values())
            )
            self.assertListEqual(
                _testcapi.get_mapping_items(mapping), list(mapping.items())
            )

    def test_mapping_keys_values_items_bad_arg(self):
        self.assertRaises(AttributeError, _testcapi.get_mapping_keys, None)
        self.assertRaises(AttributeError, _testcapi.get_mapping_values, None)
        self.assertRaises(AttributeError, _testcapi.get_mapping_items, None)

        class BadMapping:
            def keys(self):
                return None

            def values(self):
                return None

            def items(self):
                return None

        bad_mapping = BadMapping()
        self.assertRaises(TypeError, _testcapi.get_mapping_keys, bad_mapping)
        self.assertRaises(TypeError, _testcapi.get_mapping_values, bad_mapping)
        self.assertRaises(TypeError, _testcapi.get_mapping_items, bad_mapping)

    @unittest.skipUnless(
        hasattr(_testcapi, "negative_refcount"), "need _testcapi.negative_refcount"
    )
    def test_negative_refcount(self):
        code = textwrap.dedent(
            "\n            import _testcapi\n            from test import support\n\n            with support.SuppressCrashReport():\n                _testcapi.negative_refcount()\n        "
        )
        (rc, out, err) = assert_python_failure("-c", code)
        self.assertRegex(
            err,
            b"_testcapimodule\\.c:[0-9]+: _Py_NegativeRefcount: Assertion failed: object has negative ref count",
        )

    def test_trashcan_subclass(self):
        from _testcapi import MyList

        L = None
        for i in range(1000):
            L = MyList((L,))

    @support.requires_resource("cpu")
    def test_trashcan_python_class1(self):
        self.do_test_trashcan_python_class(list)

    @support.requires_resource("cpu")
    def test_trashcan_python_class2(self):
        from _testcapi import MyList

        self.do_test_trashcan_python_class(MyList)

    def do_test_trashcan_python_class(self, base):
        class PyList(base):
            num = 0

            def __init__(self, *args):
                __class__.num += 1
                super().__init__(*args)

            def __del__(self):
                __class__.num -= 1

        for parity in (0, 1):
            L = None
            for i in range((2 ** 20)):
                L = PyList((L,))
                L.attr = i
            if parity:
                L = (L,)
            self.assertGreater(PyList.num, 0)
            del L
            self.assertEqual(PyList.num, 0)

    def test_heap_ctype_doc_and_text_signature(self):
        self.assertEqual(_testcapi.HeapDocCType.__doc__, "somedoc")
        self.assertEqual(_testcapi.HeapDocCType.__text_signature__, "(arg1, arg2)")

    def test_null_type_doc(self):
        self.assertEqual(_testcapi.NullTpDocType.__doc__, None)

    def test_subclass_of_heap_gc_ctype_with_tpdealloc_decrefs_once(self):
        class HeapGcCTypeSubclass(_testcapi.HeapGcCType):
            def __init__(self):
                self.value2 = 20
                super().__init__()

        subclass_instance = HeapGcCTypeSubclass()
        type_refcnt = sys.getrefcount(HeapGcCTypeSubclass)
        self.assertEqual(subclass_instance.value, 10)
        self.assertEqual(subclass_instance.value2, 20)
        del subclass_instance
        self.assertEqual((type_refcnt - 1), sys.getrefcount(HeapGcCTypeSubclass))

    def test_subclass_of_heap_gc_ctype_with_del_modifying_dunder_class_only_decrefs_once(
        self,
    ):
        class A(_testcapi.HeapGcCType):
            def __init__(self):
                self.value2 = 20
                super().__init__()

        class B(A):
            def __init__(self):
                super().__init__()

            def __del__(self):
                self.__class__ = A
                A.refcnt_in_del = sys.getrefcount(A)
                B.refcnt_in_del = sys.getrefcount(B)

        subclass_instance = B()
        type_refcnt = sys.getrefcount(B)
        new_type_refcnt = sys.getrefcount(A)
        self.assertEqual(subclass_instance.value, 10)
        self.assertEqual(subclass_instance.value2, 20)
        del subclass_instance
        self.assertEqual((type_refcnt - 1), B.refcnt_in_del)
        self.assertEqual((new_type_refcnt + 1), A.refcnt_in_del)
        self.assertEqual((type_refcnt - 1), sys.getrefcount(B))
        self.assertEqual(new_type_refcnt, sys.getrefcount(A))

    def test_heaptype_with_dict(self):
        inst = _testcapi.HeapCTypeWithDict()
        inst.foo = 42
        self.assertEqual(inst.foo, 42)
        self.assertEqual(inst.dictobj, inst.__dict__)
        self.assertEqual(inst.dictobj, {"foo": 42})
        inst = _testcapi.HeapCTypeWithDict()
        self.assertEqual({}, inst.__dict__)

    def test_heaptype_with_negative_dict(self):
        inst = _testcapi.HeapCTypeWithNegativeDict()
        inst.foo = 42
        self.assertEqual(inst.foo, 42)
        self.assertEqual(inst.dictobj, inst.__dict__)
        self.assertEqual(inst.dictobj, {"foo": 42})
        inst = _testcapi.HeapCTypeWithNegativeDict()
        self.assertEqual({}, inst.__dict__)

    def test_heaptype_with_weakref(self):
        inst = _testcapi.HeapCTypeWithWeakref()
        ref = weakref.ref(inst)
        self.assertEqual(ref(), inst)
        self.assertEqual(inst.weakreflist, ref)

    def test_heaptype_with_buffer(self):
        inst = _testcapi.HeapCTypeWithBuffer()
        b = bytes(inst)
        self.assertEqual(b, b"1234")

    def test_c_subclass_of_heap_ctype_with_tpdealloc_decrefs_once(self):
        subclass_instance = _testcapi.HeapCTypeSubclass()
        type_refcnt = sys.getrefcount(_testcapi.HeapCTypeSubclass)
        self.assertEqual(subclass_instance.value, 10)
        self.assertEqual(subclass_instance.value2, 20)
        del subclass_instance
        self.assertEqual(
            (type_refcnt - 1), sys.getrefcount(_testcapi.HeapCTypeSubclass)
        )

    def test_c_subclass_of_heap_ctype_with_del_modifying_dunder_class_only_decrefs_once(
        self,
    ):
        subclass_instance = _testcapi.HeapCTypeSubclassWithFinalizer()
        type_refcnt = sys.getrefcount(_testcapi.HeapCTypeSubclassWithFinalizer)
        new_type_refcnt = sys.getrefcount(_testcapi.HeapCTypeSubclass)
        self.assertEqual(subclass_instance.value, 10)
        self.assertEqual(subclass_instance.value2, 20)
        del subclass_instance
        self.assertEqual(
            (type_refcnt - 1), _testcapi.HeapCTypeSubclassWithFinalizer.refcnt_in_del
        )
        self.assertEqual(
            (new_type_refcnt + 1), _testcapi.HeapCTypeSubclass.refcnt_in_del
        )
        self.assertEqual(
            (type_refcnt - 1), sys.getrefcount(_testcapi.HeapCTypeSubclassWithFinalizer)
        )
        self.assertEqual(new_type_refcnt, sys.getrefcount(_testcapi.HeapCTypeSubclass))

    def test_heaptype_with_setattro(self):
        obj = _testcapi.HeapCTypeSetattr()
        self.assertEqual(obj.pvalue, 10)
        obj.value = 12
        self.assertEqual(obj.pvalue, 12)
        del obj.value
        self.assertEqual(obj.pvalue, 0)

    def test_pynumber_tobase(self):
        from _testcapi import pynumber_tobase

        self.assertEqual(pynumber_tobase(123, 2), "0b1111011")
        self.assertEqual(pynumber_tobase(123, 8), "0o173")
        self.assertEqual(pynumber_tobase(123, 10), "123")
        self.assertEqual(pynumber_tobase(123, 16), "0x7b")
        self.assertEqual(pynumber_tobase((-123), 2), "-0b1111011")
        self.assertEqual(pynumber_tobase((-123), 8), "-0o173")
        self.assertEqual(pynumber_tobase((-123), 10), "-123")
        self.assertEqual(pynumber_tobase((-123), 16), "-0x7b")
        self.assertRaises(TypeError, pynumber_tobase, 123.0, 10)
        self.assertRaises(TypeError, pynumber_tobase, "123", 10)
        self.assertRaises(SystemError, pynumber_tobase, 123, 0)

    def check_fatal_error(self, code, expected, not_expected=()):
        with support.SuppressCrashReport():
            (rc, out, err) = assert_python_failure("-sSI", "-c", code)
        err = decode_stderr(err)
        self.assertIn("Fatal Python error: test_fatal_error: MESSAGE\n", err)
        match = re.search(
            "^Extension modules:(.*) \\(total: ([0-9]+)\\)$", err, re.MULTILINE
        )
        if not match:
            self.fail(f"Cannot find 'Extension modules:' in {err!r}")
        modules = set(match.group(1).strip().split(", "))
        total = int(match.group(2))
        for name in expected:
            self.assertIn(name, modules)
        for name in not_expected:
            self.assertNotIn(name, modules)
        self.assertEqual(len(modules), total)

    def test_fatal_error(self):
        expected = ("_testcapi",)
        not_expected = ("sys",)
        code = 'import _testcapi, sys; _testcapi.fatal_error(b"MESSAGE")'
        self.check_fatal_error(code, expected, not_expected)
        expected = ("sys",)
        not_expected = ("_testcapi",)
        code = textwrap.dedent(
            '\n            import _testcapi, sys\n            sys.stdlib_module_names = frozenset({"_testcapi"})\n            _testcapi.fatal_error(b"MESSAGE")\n        '
        )
        self.check_fatal_error(code, expected)


class TestPendingCalls(unittest.TestCase):
    def pendingcalls_submit(self, l, n):
        def callback():
            l.append(None)

        for i in range(n):
            time.sleep((random.random() * 0.02))
            while True:
                if _testcapi._pending_threadfunc(callback):
                    break

    def pendingcalls_wait(self, l, n, context=None):
        count = 0
        while len(l) != n:
            if False and support.verbose:
                print(("(%i)" % (len(l),)))
            for i in range(1000):
                a = i * i
            if context and (not context.event.is_set()):
                continue
            count += 1
            self.assertTrue(
                (count < 10000),
                ("timeout waiting for %i callbacks, got %i" % (n, len(l))),
            )
        if False and support.verbose:
            print(("(%i)" % (len(l),)))

    def test_pendingcalls_threaded(self):
        n = 32
        threads = []

        class foo(object):
            pass

        context = foo()
        context.l = []
        context.n = 2
        context.nThreads = n // context.n
        context.nFinished = 0
        context.lock = threading.Lock()
        context.event = threading.Event()
        threads = [
            threading.Thread(target=self.pendingcalls_thread, args=(context,))
            for i in range(context.nThreads)
        ]
        with threading_helper.start_threads(threads):
            self.pendingcalls_wait(context.l, n, context)

    def pendingcalls_thread(self, context):
        try:
            self.pendingcalls_submit(context.l, context.n)
        finally:
            with context.lock:
                context.nFinished += 1
                nFinished = context.nFinished
                if False and support.verbose:
                    print("finished threads: ", nFinished)
            if nFinished == context.nThreads:
                context.event.set()

    def test_pendingcalls_non_threaded(self):
        l = []
        n = 64
        self.pendingcalls_submit(l, n)
        self.pendingcalls_wait(l, n)


class SubinterpreterTest(unittest.TestCase):
    def test_subinterps(self):
        import builtins

        (r, w) = os.pipe()
        code = 'if 1:\n            import sys, builtins, pickle\n            with open({:d}, "wb") as f:\n                pickle.dump(id(sys.modules), f)\n                pickle.dump(id(builtins), f)\n            '.format(
            w
        )
        with open(r, "rb") as f:
            ret = support.run_in_subinterp(code)
            self.assertEqual(ret, 0)
            self.assertNotEqual(pickle.load(f), id(sys.modules))
            self.assertNotEqual(pickle.load(f), id(builtins))

    def test_subinterps_recent_language_features(self):
        (r, w) = os.pipe()
        code = "if 1:\n            import pickle\n            with open({:d}, \"wb\") as f:\n\n                @(lambda x:x)  # Py 3.9\n                def noop(x): return x\n\n                a = (b := f'1{{2}}3') + noop('x')  # Py 3.8 (:=) / 3.6 (f'')\n\n                async def foo(arg): return await arg  # Py 3.5\n\n                pickle.dump(dict(a=a, b=b), f)\n            ".format(
            w
        )
        with open(r, "rb") as f:
            ret = support.run_in_subinterp(code)
            self.assertEqual(ret, 0)
            self.assertEqual(pickle.load(f), {"a": "123x", "b": "123"})

    def test_mutate_exception(self):
        "\n        Exceptions saved in global module state get shared between\n        individual module instances. This test checks whether or not\n        a change in one interpreter's module gets reflected into the\n        other ones.\n        "
        import binascii

        support.run_in_subinterp("import binascii; binascii.Error.foobar = 'foobar'")
        self.assertFalse(hasattr(binascii.Error, "foobar"))


class TestThreadState(unittest.TestCase):
    @threading_helper.reap_threads
    def test_thread_state(self):
        def target():
            idents = []

            def callback():
                idents.append(threading.get_ident())

            _testcapi._test_thread_state(callback)
            a = b = callback
            time.sleep(1)
            self.assertEqual(
                idents.count(threading.get_ident()),
                3,
                "Couldn't find main thread correctly in the list",
            )

        target()
        t = threading.Thread(target=target)
        t.start()
        t.join()


class Test_testcapi(unittest.TestCase):
    locals().update(
        (
            (name, getattr(_testcapi, name))
            for name in dir(_testcapi)
            if (name.startswith("test_") and (not name.endswith("_code")))
        )
    )

    @warnings_helper.ignore_warnings(category=DeprecationWarning)
    def test_widechar(self):
        _testcapi.test_widechar()


class Test_testinternalcapi(unittest.TestCase):
    locals().update(
        (
            (name, getattr(_testinternalcapi, name))
            for name in dir(_testinternalcapi)
            if name.startswith("test_")
        )
    )


class PyMemDebugTests(unittest.TestCase):
    PYTHONMALLOC = "debug"
    PTR_REGEX = "(?:0x)?[0-9a-fA-F]+"

    def check(self, code):
        with support.SuppressCrashReport():
            out = assert_python_failure("-c", code, PYTHONMALLOC=self.PYTHONMALLOC)
        stderr = out.err
        return stderr.decode("ascii", "replace")

    def test_buffer_overflow(self):
        out = self.check("import _testcapi; _testcapi.pymem_buffer_overflow()")
        regex = "Debug memory block at address p={ptr}: API 'm'\\n    16 bytes originally requested\\n    The [0-9] pad bytes at p-[0-9] are FORBIDDENBYTE, as expected.\\n    The [0-9] pad bytes at tail={ptr} are not all FORBIDDENBYTE \\(0x[0-9a-f]{{2}}\\):\\n        at tail\\+0: 0x78 \\*\\*\\* OUCH\\n        at tail\\+1: 0xfd\\n        at tail\\+2: 0xfd\\n        .*\\n(    The block was made by call #[0-9]+ to debug malloc/realloc.\\n)?    Data at p: cd cd cd .*\\n\\nEnable tracemalloc to get the memory block allocation traceback\\n\\nFatal Python error: _PyMem_DebugRawFree: bad trailing pad byte"
        regex = regex.format(ptr=self.PTR_REGEX)
        regex = re.compile(regex, flags=re.DOTALL)
        self.assertRegex(out, regex)

    def test_api_misuse(self):
        out = self.check("import _testcapi; _testcapi.pymem_api_misuse()")
        regex = "Debug memory block at address p={ptr}: API 'm'\\n    16 bytes originally requested\\n    The [0-9] pad bytes at p-[0-9] are FORBIDDENBYTE, as expected.\\n    The [0-9] pad bytes at tail={ptr} are FORBIDDENBYTE, as expected.\\n(    The block was made by call #[0-9]+ to debug malloc/realloc.\\n)?    Data at p: cd cd cd .*\\n\\nEnable tracemalloc to get the memory block allocation traceback\\n\\nFatal Python error: _PyMem_DebugRawFree: bad ID: Allocated using API 'm', verified using API 'r'\\n"
        regex = regex.format(ptr=self.PTR_REGEX)
        self.assertRegex(out, regex)

    def check_malloc_without_gil(self, code):
        out = self.check(code)
        expected = "Fatal Python error: _PyMem_DebugMalloc: Python memory allocator called without holding the GIL"
        self.assertIn(expected, out)

    def test_pymem_malloc_without_gil(self):
        code = "import _testcapi; _testcapi.pymem_malloc_without_gil()"
        self.check_malloc_without_gil(code)

    def test_pyobject_malloc_without_gil(self):
        code = "import _testcapi; _testcapi.pyobject_malloc_without_gil()"
        self.check_malloc_without_gil(code)

    def check_pyobject_is_freed(self, func_name):
        code = textwrap.dedent(
            f"""
            import gc, os, sys, _testcapi
            # Disable the GC to avoid crash on GC collection
            gc.disable()
            try:
                _testcapi.{func_name}()
                # Exit immediately to avoid a crash while deallocating
                # the invalid object
                os._exit(0)
            except _testcapi.error:
                os._exit(1)
        """
        )
        assert_python_ok("-c", code, PYTHONMALLOC=self.PYTHONMALLOC)

    def test_pyobject_null_is_freed(self):
        self.check_pyobject_is_freed("check_pyobject_null_is_freed")

    def test_pyobject_uninitialized_is_freed(self):
        self.check_pyobject_is_freed("check_pyobject_uninitialized_is_freed")

    def test_pyobject_forbidden_bytes_is_freed(self):
        self.check_pyobject_is_freed("check_pyobject_forbidden_bytes_is_freed")

    def test_pyobject_freed_is_freed(self):
        self.check_pyobject_is_freed("check_pyobject_freed_is_freed")


class PyMemMallocDebugTests(PyMemDebugTests):
    PYTHONMALLOC = "malloc_debug"


@unittest.skipUnless(support.with_pymalloc(), "need pymalloc")
class PyMemPymallocDebugTests(PyMemDebugTests):
    PYTHONMALLOC = "pymalloc_debug"


@unittest.skipUnless(Py_DEBUG, "need Py_DEBUG")
class PyMemDefaultTests(PyMemDebugTests):
    PYTHONMALLOC = ""


class Test_ModuleStateAccess(unittest.TestCase):
    "Test access to module start (PEP 573)"

    def setUp(self):
        fullname = "_testmultiphase_meth_state_access"
        origin = importlib.util.find_spec("_testmultiphase").origin
        loader = importlib.machinery.ExtensionFileLoader(fullname, origin)
        spec = importlib.util.spec_from_loader(fullname, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        self.module = module

    def test_subclass_get_module(self):
        "PyType_GetModule for defining_class"

        class StateAccessType_Subclass(self.module.StateAccessType):
            pass

        instance = StateAccessType_Subclass()
        self.assertIs(instance.get_defining_module(), self.module)

    def test_subclass_get_module_with_super(self):
        class StateAccessType_Subclass(self.module.StateAccessType):
            def get_defining_module(self):
                return super().get_defining_module()

        instance = StateAccessType_Subclass()
        self.assertIs(instance.get_defining_module(), self.module)

    def test_state_access(self):
        "Checks methods defined with and without argument clinic\n\n        This tests a no-arg method (get_count) and a method with\n        both a positional and keyword argument.\n        "
        a = self.module.StateAccessType()
        b = self.module.StateAccessType()
        methods = {
            "clinic": a.increment_count_clinic,
            "noclinic": a.increment_count_noclinic,
        }
        for (name, increment_count) in methods.items():
            with self.subTest(name):
                self.assertEqual(a.get_count(), b.get_count())
                self.assertEqual(a.get_count(), 0)
                increment_count()
                self.assertEqual(a.get_count(), b.get_count())
                self.assertEqual(a.get_count(), 1)
                increment_count(3)
                self.assertEqual(a.get_count(), b.get_count())
                self.assertEqual(a.get_count(), 4)
                increment_count((-2), twice=True)
                self.assertEqual(a.get_count(), b.get_count())
                self.assertEqual(a.get_count(), 0)
                with self.assertRaises(TypeError):
                    increment_count(thrice=3)
                with self.assertRaises(TypeError):
                    increment_count(1, 2, 3)


if __name__ == "__main__":
    unittest.main()
