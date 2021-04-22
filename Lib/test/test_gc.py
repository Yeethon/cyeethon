import unittest
import unittest.mock
from test.support import verbose, refcount_test, run_unittest, cpython_only
from test.support.import_helper import import_module
from test.support.os_helper import temp_dir, TESTFN, unlink
from test.support.script_helper import assert_python_ok, make_script
from test.support import threading_helper
import gc
import sys
import sysconfig
import textwrap
import threading
import time
import weakref

try:
    from _testcapi import with_tp_del
except ImportError:

    def with_tp_del(cls):
        class C(object):
            def __new__(cls, *args, **kwargs):
                raise TypeError("requires _testcapi.with_tp_del")

        return C


try:
    from _testcapi import ContainerNoGC
except ImportError:
    ContainerNoGC = None


class C1055820(object):
    def __init__(self, i):
        self.i = i
        self.loop = self


class GC_Detector(object):
    def __init__(self):
        self.gc_happened = False

        def it_happened(ignored):
            self.gc_happened = True

        self.wr = weakref.ref(C1055820(666), it_happened)


@with_tp_del
class Uncollectable(object):
    "Create a reference cycle with multiple __del__ methods.\n\n    An object in a reference cycle will never have zero references,\n    and so must be garbage collected.  If one or more objects in the\n    cycle have __del__ methods, the gc refuses to guess an order,\n    and leaves the cycle uncollected."

    def __init__(self, partner=None):
        if partner is None:
            self.partner = Uncollectable(partner=self)
        else:
            self.partner = partner

    def __tp_del__(self):
        pass


if sysconfig.get_config_vars().get("PY_CFLAGS", ""):
    BUILD_WITH_NDEBUG = "-DNDEBUG" in sysconfig.get_config_vars()["PY_CFLAGS"]
else:
    BUILD_WITH_NDEBUG = not hasattr(sys, "gettotalrefcount")


class GCTests(unittest.TestCase):
    def test_list(self):
        l = []
        l.append(l)
        gc.collect()
        del l
        self.assertEqual(gc.collect(), 1)

    def test_dict(self):
        d = {}
        d[1] = d
        gc.collect()
        del d
        self.assertEqual(gc.collect(), 1)

    def test_tuple(self):
        l = []
        t = (l,)
        l.append(t)
        gc.collect()
        del t
        del l
        self.assertEqual(gc.collect(), 2)

    def test_class(self):
        class A:
            pass

        A.a = A
        gc.collect()
        del A
        self.assertNotEqual(gc.collect(), 0)

    def test_newstyleclass(self):
        class A(object):
            pass

        gc.collect()
        del A
        self.assertNotEqual(gc.collect(), 0)

    def test_instance(self):
        class A:
            pass

        a = A()
        a.a = a
        gc.collect()
        del a
        self.assertNotEqual(gc.collect(), 0)

    def test_newinstance(self):
        class A(object):
            pass

        a = A()
        a.a = a
        gc.collect()
        del a
        self.assertNotEqual(gc.collect(), 0)

        class B(list):
            pass

        class C(B, A):
            pass

        a = C()
        a.a = a
        gc.collect()
        del a
        self.assertNotEqual(gc.collect(), 0)
        del B, C
        self.assertNotEqual(gc.collect(), 0)
        A.a = A()
        del A
        self.assertNotEqual(gc.collect(), 0)
        self.assertEqual(gc.collect(), 0)

    def test_method(self):
        class A:
            def __init__(self):
                self.init = self.__init__

        a = A()
        gc.collect()
        del a
        self.assertNotEqual(gc.collect(), 0)

    @cpython_only
    def test_legacy_finalizer(self):
        @with_tp_del
        class A:
            def __tp_del__(self):
                pass

        class B:
            pass

        a = A()
        a.a = a
        id_a = id(a)
        b = B()
        b.b = b
        gc.collect()
        del a
        del b
        self.assertNotEqual(gc.collect(), 0)
        for obj in gc.garbage:
            if id(obj) == id_a:
                del obj.a
                break
        else:
            self.fail("didn't find obj in garbage (finalizer)")
        gc.garbage.remove(obj)

    @cpython_only
    def test_legacy_finalizer_newclass(self):
        @with_tp_del
        class A(object):
            def __tp_del__(self):
                pass

        class B(object):
            pass

        a = A()
        a.a = a
        id_a = id(a)
        b = B()
        b.b = b
        gc.collect()
        del a
        del b
        self.assertNotEqual(gc.collect(), 0)
        for obj in gc.garbage:
            if id(obj) == id_a:
                del obj.a
                break
        else:
            self.fail("didn't find obj in garbage (finalizer)")
        gc.garbage.remove(obj)

    def test_function(self):
        d = {}
        exec("def f(): pass\n", d)
        gc.collect()
        del d
        self.assertEqual(gc.collect(), 2)

    @refcount_test
    def test_frame(self):
        def f():
            frame = sys._getframe()

        gc.collect()
        f()
        self.assertEqual(gc.collect(), 1)

    def test_saveall(self):
        gc.collect()
        self.assertEqual(gc.garbage, [])
        L = []
        L.append(L)
        id_L = id(L)
        debug = gc.get_debug()
        gc.set_debug((debug | gc.DEBUG_SAVEALL))
        del L
        gc.collect()
        gc.set_debug(debug)
        self.assertEqual(len(gc.garbage), 1)
        obj = gc.garbage.pop()
        self.assertEqual(id(obj), id_L)

    def test_del(self):
        thresholds = gc.get_threshold()
        gc.enable()
        gc.set_threshold(1)

        class A:
            def __del__(self):
                dir(self)

        a = A()
        del a
        gc.disable()
        gc.set_threshold(*thresholds)

    def test_del_newclass(self):
        thresholds = gc.get_threshold()
        gc.enable()
        gc.set_threshold(1)

        class A(object):
            def __del__(self):
                dir(self)

        a = A()
        del a
        gc.disable()
        gc.set_threshold(*thresholds)

    @refcount_test
    def test_get_count(self):
        gc.collect()
        (a, b, c) = gc.get_count()
        x = []
        (d, e, f) = gc.get_count()
        self.assertEqual((b, c), (0, 0))
        self.assertEqual((e, f), (0, 0))
        self.assertLess(a, 5)
        self.assertGreater(d, a)

    @refcount_test
    def test_collect_generations(self):
        gc.collect()
        x = []
        gc.collect(0)
        (a, b, c) = gc.get_count()
        gc.collect(1)
        (d, e, f) = gc.get_count()
        gc.collect(2)
        (g, h, i) = gc.get_count()
        self.assertEqual((b, c), (1, 0))
        self.assertEqual((e, f), (0, 1))
        self.assertEqual((h, i), (0, 0))

    def test_trashcan(self):
        class Ouch:
            n = 0

            def __del__(self):
                Ouch.n = Ouch.n + 1
                if (Ouch.n % 17) == 0:
                    gc.collect()

        gc.enable()
        N = 150
        for count in range(2):
            t = []
            for i in range(N):
                t = [t, Ouch()]
            u = []
            for i in range(N):
                u = [u, Ouch()]
            v = {}
            for i in range(N):
                v = {1: v, 2: Ouch()}
        gc.disable()

    def test_trashcan_threads(self):
        NESTING = 60
        N_THREADS = 2

        def sleeper_gen():
            "A generator that releases the GIL when closed or dealloc'ed."
            try:
                (yield)
            finally:
                time.sleep(1e-06)

        class C(list):
            inits = []
            dels = []

            def __init__(self, alist):
                self[:] = alist
                C.inits.append(None)

            def __del__(self):
                C.dels.append(None)
                g = sleeper_gen()
                next(g)

        def make_nested():
            "Create a sufficiently nested container object so that the\n            trashcan mechanism is invoked when deallocating it."
            x = C([])
            for i in range(NESTING):
                x = [C([x])]
            del x

        def run_thread():
            "Exercise make_nested() in a loop."
            while not exit:
                make_nested()

        old_switchinterval = sys.getswitchinterval()
        sys.setswitchinterval(1e-05)
        try:
            exit = []
            threads = []
            for i in range(N_THREADS):
                t = threading.Thread(target=run_thread)
                threads.append(t)
            with threading_helper.start_threads(threads, (lambda: exit.append(1))):
                time.sleep(1.0)
        finally:
            sys.setswitchinterval(old_switchinterval)
        gc.collect()
        self.assertEqual(len(C.inits), len(C.dels))

    def test_boom(self):
        class Boom:
            def __getattr__(self, someattribute):
                del self.attr
                raise AttributeError

        a = Boom()
        b = Boom()
        a.attr = b
        b.attr = a
        gc.collect()
        garbagelen = len(gc.garbage)
        del a, b
        self.assertEqual(gc.collect(), 4)
        self.assertEqual(len(gc.garbage), garbagelen)

    def test_boom2(self):
        class Boom2:
            def __init__(self):
                self.x = 0

            def __getattr__(self, someattribute):
                self.x += 1
                if self.x > 1:
                    del self.attr
                raise AttributeError

        a = Boom2()
        b = Boom2()
        a.attr = b
        b.attr = a
        gc.collect()
        garbagelen = len(gc.garbage)
        del a, b
        self.assertEqual(gc.collect(), 4)
        self.assertEqual(len(gc.garbage), garbagelen)

    def test_boom_new(self):
        class Boom_New(object):
            def __getattr__(self, someattribute):
                del self.attr
                raise AttributeError

        a = Boom_New()
        b = Boom_New()
        a.attr = b
        b.attr = a
        gc.collect()
        garbagelen = len(gc.garbage)
        del a, b
        self.assertEqual(gc.collect(), 4)
        self.assertEqual(len(gc.garbage), garbagelen)

    def test_boom2_new(self):
        class Boom2_New(object):
            def __init__(self):
                self.x = 0

            def __getattr__(self, someattribute):
                self.x += 1
                if self.x > 1:
                    del self.attr
                raise AttributeError

        a = Boom2_New()
        b = Boom2_New()
        a.attr = b
        b.attr = a
        gc.collect()
        garbagelen = len(gc.garbage)
        del a, b
        self.assertEqual(gc.collect(), 4)
        self.assertEqual(len(gc.garbage), garbagelen)

    def test_get_referents(self):
        alist = [1, 3, 5]
        got = gc.get_referents(alist)
        got.sort()
        self.assertEqual(got, alist)
        atuple = tuple(alist)
        got = gc.get_referents(atuple)
        got.sort()
        self.assertEqual(got, alist)
        adict = {1: 3, 5: 7}
        expected = [1, 3, 5, 7]
        got = gc.get_referents(adict)
        got.sort()
        self.assertEqual(got, expected)
        got = gc.get_referents([1, 2], {3: 4}, (0, 0, 0))
        got.sort()
        self.assertEqual(got, ([0, 0] + list(range(5))))
        self.assertEqual(gc.get_referents(1, "a", 4j), [])

    def test_is_tracked(self):
        self.assertFalse(gc.is_tracked(None))
        self.assertFalse(gc.is_tracked(1))
        self.assertFalse(gc.is_tracked(1.0))
        self.assertFalse(gc.is_tracked((1.0 + 5j)))
        self.assertFalse(gc.is_tracked(True))
        self.assertFalse(gc.is_tracked(False))
        self.assertFalse(gc.is_tracked(b"a"))
        self.assertFalse(gc.is_tracked("a"))
        self.assertFalse(gc.is_tracked(bytearray(b"a")))
        self.assertFalse(gc.is_tracked(type))
        self.assertFalse(gc.is_tracked(int))
        self.assertFalse(gc.is_tracked(object))
        self.assertFalse(gc.is_tracked(object()))

        class UserClass:
            pass

        class UserInt(int):
            pass

        class UserClassSlots:
            __slots__ = ()

        class UserFloatSlots(float):
            __slots__ = ()

        class UserIntSlots(int):
            __slots__ = ()

        self.assertTrue(gc.is_tracked(gc))
        self.assertTrue(gc.is_tracked(UserClass))
        self.assertTrue(gc.is_tracked(UserClass()))
        self.assertTrue(gc.is_tracked(UserInt()))
        self.assertTrue(gc.is_tracked([]))
        self.assertTrue(gc.is_tracked(set()))
        self.assertTrue(gc.is_tracked(UserClassSlots()))
        self.assertTrue(gc.is_tracked(UserFloatSlots()))
        self.assertTrue(gc.is_tracked(UserIntSlots()))

    def test_is_finalized(self):
        self.assertFalse(gc.is_finalized(3))
        storage = []

        class Lazarus:
            def __del__(self):
                storage.append(self)

        lazarus = Lazarus()
        self.assertFalse(gc.is_finalized(lazarus))
        del lazarus
        gc.collect()
        lazarus = storage.pop()
        self.assertTrue(gc.is_finalized(lazarus))

    def test_bug1055820b(self):
        ouch = []

        def callback(ignored):
            ouch[:] = [wr() for wr in WRs]

        Cs = [C1055820(i) for i in range(2)]
        WRs = [weakref.ref(c, callback) for c in Cs]
        c = None
        gc.collect()
        self.assertEqual(len(ouch), 0)
        Cs = None
        gc.collect()
        self.assertEqual(len(ouch), 2)
        for x in ouch:
            self.assertEqual(x, None)

    def test_bug21435(self):
        gc.collect()

        class A:
            pass

        class B:
            def __init__(self, x):
                self.x = x

            def __del__(self):
                self.attr = None

        def do_work():
            a = A()
            b = B(A())
            a.attr = b
            b.attr = a

        do_work()
        gc.collect()

    @cpython_only
    def test_garbage_at_shutdown(self):
        import subprocess

        code = "if 1:\n            import gc\n            import _testcapi\n            @_testcapi.with_tp_del\n            class X:\n                def __init__(self, name):\n                    self.name = name\n                def __repr__(self):\n                    return \"<X %%r>\" %% self.name\n                def __tp_del__(self):\n                    pass\n\n            x = X('first')\n            x.x = x\n            x.y = X('second')\n            del x\n            gc.set_debug(%s)\n        "

        def run_command(code):
            p = subprocess.Popen(
                [sys.executable, "-Wd", "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            (stdout, stderr) = p.communicate()
            p.stdout.close()
            p.stderr.close()
            self.assertEqual(p.returncode, 0)
            self.assertEqual(stdout, b"")
            return stderr

        stderr = run_command((code % "0"))
        self.assertIn(
            b"ResourceWarning: gc: 2 uncollectable objects at shutdown; use", stderr
        )
        self.assertNotIn(b"<X 'first'>", stderr)
        stderr = run_command((code % "gc.DEBUG_UNCOLLECTABLE"))
        self.assertIn(
            b"ResourceWarning: gc: 2 uncollectable objects at shutdown", stderr
        )
        self.assertTrue(
            (
                (b"[<X 'first'>, <X 'second'>]" in stderr)
                or (b"[<X 'second'>, <X 'first'>]" in stderr)
            ),
            stderr,
        )
        stderr = run_command((code % "gc.DEBUG_SAVEALL"))
        self.assertNotIn(b"uncollectable objects at shutdown", stderr)

    def test_gc_main_module_at_shutdown(self):
        code = "if 1:\n            class C:\n                def __del__(self):\n                    print('__del__ called')\n            l = [C()]\n            l.append(l)\n            "
        (rc, out, err) = assert_python_ok("-c", code)
        self.assertEqual(out.strip(), b"__del__ called")

    def test_gc_ordinary_module_at_shutdown(self):
        with temp_dir() as script_dir:
            module = "if 1:\n                class C:\n                    def __del__(self):\n                        print('__del__ called')\n                l = [C()]\n                l.append(l)\n                "
            code = (
                "if 1:\n                import sys\n                sys.path.insert(0, %r)\n                import gctest\n                "
                % (script_dir,)
            )
            make_script(script_dir, "gctest", module)
            (rc, out, err) = assert_python_ok("-c", code)
            self.assertEqual(out.strip(), b"__del__ called")

    def test_global_del_SystemExit(self):
        code = "if 1:\n            class ClassWithDel:\n                def __del__(self):\n                    print('__del__ called')\n            a = ClassWithDel()\n            a.link = a\n            raise SystemExit(0)"
        self.addCleanup(unlink, TESTFN)
        with open(TESTFN, "w", encoding="utf-8") as script:
            script.write(code)
        (rc, out, err) = assert_python_ok(TESTFN)
        self.assertEqual(out.strip(), b"__del__ called")

    def test_get_stats(self):
        stats = gc.get_stats()
        self.assertEqual(len(stats), 3)
        for st in stats:
            self.assertIsInstance(st, dict)
            self.assertEqual(set(st), {"collected", "collections", "uncollectable"})
            self.assertGreaterEqual(st["collected"], 0)
            self.assertGreaterEqual(st["collections"], 0)
            self.assertGreaterEqual(st["uncollectable"], 0)
        if gc.isenabled():
            self.addCleanup(gc.enable)
            gc.disable()
        old = gc.get_stats()
        gc.collect(0)
        new = gc.get_stats()
        self.assertEqual(new[0]["collections"], (old[0]["collections"] + 1))
        self.assertEqual(new[1]["collections"], old[1]["collections"])
        self.assertEqual(new[2]["collections"], old[2]["collections"])
        gc.collect(2)
        new = gc.get_stats()
        self.assertEqual(new[0]["collections"], (old[0]["collections"] + 1))
        self.assertEqual(new[1]["collections"], old[1]["collections"])
        self.assertEqual(new[2]["collections"], (old[2]["collections"] + 1))

    def test_freeze(self):
        gc.freeze()
        self.assertGreater(gc.get_freeze_count(), 0)
        gc.unfreeze()
        self.assertEqual(gc.get_freeze_count(), 0)

    def test_get_objects(self):
        gc.collect()
        l = []
        l.append(l)
        self.assertTrue(
            any(((l is element) for element in gc.get_objects(generation=0)))
        )
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=1)))
        )
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=2)))
        )
        gc.collect(generation=0)
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=0)))
        )
        self.assertTrue(
            any(((l is element) for element in gc.get_objects(generation=1)))
        )
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=2)))
        )
        gc.collect(generation=1)
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=0)))
        )
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=1)))
        )
        self.assertTrue(
            any(((l is element) for element in gc.get_objects(generation=2)))
        )
        gc.collect(generation=2)
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=0)))
        )
        self.assertFalse(
            any(((l is element) for element in gc.get_objects(generation=1)))
        )
        self.assertTrue(
            any(((l is element) for element in gc.get_objects(generation=2)))
        )
        del l
        gc.collect()

    def test_get_objects_arguments(self):
        gc.collect()
        self.assertEqual(len(gc.get_objects()), len(gc.get_objects(generation=None)))
        self.assertRaises(ValueError, gc.get_objects, 1000)
        self.assertRaises(ValueError, gc.get_objects, (-1000))
        self.assertRaises(TypeError, gc.get_objects, "1")
        self.assertRaises(TypeError, gc.get_objects, 1.234)

    def test_resurrection_only_happens_once_per_object(self):
        class A:
            def __init__(self):
                self.me = self

        class Lazarus(A):
            resurrected = 0
            resurrected_instances = []

            def __del__(self):
                Lazarus.resurrected += 1
                Lazarus.resurrected_instances.append(self)

        gc.collect()
        gc.disable()
        laz = Lazarus()
        self.assertEqual(Lazarus.resurrected, 0)
        del laz
        gc.collect()
        self.assertEqual(Lazarus.resurrected, 1)
        self.assertEqual(len(Lazarus.resurrected_instances), 1)
        Lazarus.resurrected_instances.clear()
        self.assertEqual(Lazarus.resurrected, 1)
        gc.collect()
        self.assertEqual(Lazarus.resurrected, 1)
        gc.enable()

    def test_resurrection_is_transitive(self):
        class Cargo:
            def __init__(self):
                self.me = self

        class Lazarus:
            resurrected_instances = []

            def __del__(self):
                Lazarus.resurrected_instances.append(self)

        gc.collect()
        gc.disable()
        laz = Lazarus()
        cargo = Cargo()
        cargo_id = id(cargo)
        laz.cargo = cargo
        cargo.laz = laz
        del laz, cargo
        gc.collect()
        self.assertEqual(len(Lazarus.resurrected_instances), 1)
        instance = Lazarus.resurrected_instances.pop()
        self.assertTrue(hasattr(instance, "cargo"))
        self.assertEqual(id(instance.cargo), cargo_id)
        gc.collect()
        gc.enable()

    def test_resurrection_does_not_block_cleanup_of_other_objects(self):
        N = 100

        class A:
            def __init__(self):
                self.me = self

        class Z(A):
            def __del__(self):
                zs.append(self)

        zs = []

        def getstats():
            d = gc.get_stats()[(-1)]
            return (d["collected"], d["uncollectable"])

        gc.collect()
        gc.disable()
        (oldc, oldnc) = getstats()
        for i in range(N):
            A()
        t = gc.collect()
        (c, nc) = getstats()
        self.assertEqual(t, (2 * N))
        self.assertEqual((c - oldc), (2 * N))
        self.assertEqual((nc - oldnc), 0)
        (oldc, oldnc) = (c, nc)
        Z()
        t = gc.collect()
        (c, nc) = getstats()
        self.assertEqual(t, 0)
        self.assertEqual((c - oldc), 0)
        self.assertEqual((nc - oldnc), 0)
        (oldc, oldnc) = (c, nc)
        for i in range(N):
            A()
        Z()
        t = gc.collect()
        (c, nc) = getstats()
        self.assertEqual(t, (2 * N))
        self.assertEqual((c - oldc), (2 * N))
        self.assertEqual((nc - oldnc), 0)
        (oldc, oldnc) = (c, nc)
        zs.clear()
        t = gc.collect()
        (c, nc) = getstats()
        self.assertEqual(t, 4)
        self.assertEqual((c - oldc), 4)
        self.assertEqual((nc - oldnc), 0)
        gc.enable()

    @unittest.skipIf((ContainerNoGC is None), "requires ContainerNoGC extension type")
    def test_trash_weakref_clear(self):
        callback = unittest.mock.Mock()

        class A:
            __slots__ = ["a", "y", "wz"]

        class Z:
            pass

        a = A()
        a.a = a
        a.y = ContainerNoGC(Z())
        a.wz = weakref.ref(a.y.value, callback)
        wr_cycle = [a.wz]
        wr_cycle.append(wr_cycle)
        gc.collect()
        gc.disable()
        del a, wr_cycle
        gc.collect()
        callback.assert_not_called()
        gc.enable()


class GCCallbackTests(unittest.TestCase):
    def setUp(self):
        self.enabled = gc.isenabled()
        gc.disable()
        self.debug = gc.get_debug()
        gc.set_debug(0)
        gc.callbacks.append(self.cb1)
        gc.callbacks.append(self.cb2)
        self.othergarbage = []

    def tearDown(self):
        del self.visit
        gc.callbacks.remove(self.cb1)
        gc.callbacks.remove(self.cb2)
        gc.set_debug(self.debug)
        if self.enabled:
            gc.enable()
        gc.collect()
        for obj in gc.garbage:
            if isinstance(obj, Uncollectable):
                obj.partner = None
        del gc.garbage[:]
        del self.othergarbage
        gc.collect()

    def preclean(self):
        self.visit = []
        gc.collect()
        (garbage, gc.garbage[:]) = (gc.garbage[:], [])
        self.othergarbage.append(garbage)
        self.visit = []

    def cb1(self, phase, info):
        self.visit.append((1, phase, dict(info)))

    def cb2(self, phase, info):
        self.visit.append((2, phase, dict(info)))
        if (phase == "stop") and hasattr(self, "cleanup"):
            uc = [e for e in gc.garbage if isinstance(e, Uncollectable)]
            gc.garbage[:] = [
                e for e in gc.garbage if (not isinstance(e, Uncollectable))
            ]
            for e in uc:
                e.partner = None

    def test_collect(self):
        self.preclean()
        gc.collect()
        n = [v[0] for v in self.visit]
        n1 = [i for i in n if (i == 1)]
        n2 = [i for i in n if (i == 2)]
        self.assertEqual(n1, ([1] * 2))
        self.assertEqual(n2, ([2] * 2))
        n = [v[1] for v in self.visit]
        n1 = [i for i in n if (i == "start")]
        n2 = [i for i in n if (i == "stop")]
        self.assertEqual(n1, (["start"] * 2))
        self.assertEqual(n2, (["stop"] * 2))
        for v in self.visit:
            info = v[2]
            self.assertTrue(("generation" in info))
            self.assertTrue(("collected" in info))
            self.assertTrue(("uncollectable" in info))

    def test_collect_generation(self):
        self.preclean()
        gc.collect(2)
        for v in self.visit:
            info = v[2]
            self.assertEqual(info["generation"], 2)

    @cpython_only
    def test_collect_garbage(self):
        self.preclean()
        Uncollectable()
        Uncollectable()
        C1055820(666)
        gc.collect()
        for v in self.visit:
            if v[1] != "stop":
                continue
            info = v[2]
            self.assertEqual(info["collected"], 2)
            self.assertEqual(info["uncollectable"], 8)
        self.assertEqual(len(gc.garbage), 4)
        for e in gc.garbage:
            self.assertIsInstance(e, Uncollectable)
        self.cleanup = True
        self.visit = []
        gc.garbage[:] = []
        gc.collect()
        for v in self.visit:
            if v[1] != "stop":
                continue
            info = v[2]
            self.assertEqual(info["collected"], 0)
            self.assertEqual(info["uncollectable"], 4)
        self.assertEqual(len(gc.garbage), 0)

    @unittest.skipIf(BUILD_WITH_NDEBUG, "built with -NDEBUG")
    def test_refcount_errors(self):
        self.preclean()
        import_module("ctypes")
        import subprocess

        code = textwrap.dedent(
            '\n            from test.support import gc_collect, SuppressCrashReport\n\n            a = [1, 2, 3]\n            b = [a]\n\n            # Avoid coredump when Py_FatalError() calls abort()\n            SuppressCrashReport().__enter__()\n\n            # Simulate the refcount of "a" being too low (compared to the\n            # references held on it by live data), but keeping it above zero\n            # (to avoid deallocating it):\n            import ctypes\n            ctypes.pythonapi.Py_DecRef(ctypes.py_object(a))\n\n            # The garbage collector should now have a fatal error\n            # when it reaches the broken object\n            gc_collect()\n        '
        )
        p = subprocess.Popen(
            [sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        (stdout, stderr) = p.communicate()
        p.stdout.close()
        p.stderr.close()
        self.assertRegex(
            stderr,
            b'gcmodule\\.c:[0-9]+: gc_decref: Assertion "gc_get_refs\\(g\\) > 0" failed.',
        )
        self.assertRegex(stderr, b"refcount is too small")
        address_regex = b"[0-9a-fA-Fx]+"
        self.assertRegex(stderr, (b"object address  : " + address_regex))
        self.assertRegex(stderr, b"object refcount : 1")
        self.assertRegex(stderr, (b"object type     : " + address_regex))
        self.assertRegex(stderr, b"object type name: list")
        self.assertRegex(stderr, b"object repr     : \\[1, 2, 3\\]")


class GCTogglingTests(unittest.TestCase):
    def setUp(self):
        gc.enable()

    def tearDown(self):
        gc.disable()

    def test_bug1055820c(self):
        c0 = C1055820(0)
        gc.collect()
        c1 = C1055820(1)
        c1.keep_c0_alive = c0
        del c0.loop
        c2 = C1055820(2)
        c2wr = weakref.ref(c2)
        ouch = []

        def callback(ignored):
            ouch[:] = [c2wr()]

        c0wr = weakref.ref(c0, callback)
        c0 = c1 = c2 = None
        junk = []
        i = 0
        detector = GC_Detector()
        while not detector.gc_happened:
            i += 1
            if i > 10000:
                self.fail("gc didn't happen after 10000 iterations")
            self.assertEqual(len(ouch), 0)
            junk.append([])
        self.assertEqual(len(ouch), 1)
        for x in ouch:
            self.assertEqual(x, None)

    def test_bug1055820d(self):
        ouch = []

        class D(C1055820):
            def __del__(self):
                ouch[:] = [c2wr()]

        d0 = D(0)
        gc.collect()
        c1 = C1055820(1)
        c1.keep_d0_alive = d0
        del d0.loop
        c2 = C1055820(2)
        c2wr = weakref.ref(c2)
        d0 = c1 = c2 = None
        detector = GC_Detector()
        junk = []
        i = 0
        while not detector.gc_happened:
            i += 1
            if i > 10000:
                self.fail("gc didn't happen after 10000 iterations")
            self.assertEqual(len(ouch), 0)
            junk.append([])
        self.assertEqual(len(ouch), 1)
        for x in ouch:
            self.assertEqual(x, None)


def test_main():
    enabled = gc.isenabled()
    gc.disable()
    assert not gc.isenabled()
    debug = gc.get_debug()
    gc.set_debug((debug & (~gc.DEBUG_LEAK)))
    try:
        gc.collect()
        run_unittest(GCTests, GCTogglingTests, GCCallbackTests)
    finally:
        gc.set_debug(debug)
        if verbose:
            print("restoring automatic collection")
        gc.enable()
        assert gc.isenabled()
        if not enabled:
            gc.disable()


if __name__ == "__main__":
    test_main()
