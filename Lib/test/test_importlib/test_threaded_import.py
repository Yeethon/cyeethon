import _imp as imp
import os
import importlib
import sys
import time
import shutil
import threading
import unittest
from unittest import mock
from test.support import verbose, run_unittest
from test.support.import_helper import forget
from test.support.os_helper import TESTFN, unlink, rmtree
from test.support import script_helper, threading_helper


def task(N, done, done_tasks, errors):
    try:
        if len(done_tasks) % 2:
            import modulefinder
            import random
        else:
            import random
            import modulefinder
        x = random.randrange(1, 3)
    except Exception as e:
        errors.append(e.with_traceback(None))
    finally:
        done_tasks.append(threading.get_ident())
        finished = len(done_tasks) == N
        if finished:
            done.set()


def mock_register_at_fork(func):
    return mock.patch("os.register_at_fork", create=True)(func)


circular_imports_modules = {
    "A": "if 1:\n        import time\n        time.sleep(%(delay)s)\n        x = 'a'\n        import C\n        ",
    "B": "if 1:\n        import time\n        time.sleep(%(delay)s)\n        x = 'b'\n        import D\n        ",
    "C": "import B",
    "D": "import A",
}


class Finder:
    "A dummy finder to detect concurrent access to its find_spec()\n    method."

    def __init__(self):
        self.numcalls = 0
        self.x = 0
        self.lock = threading.Lock()

    def find_spec(self, name, path=None, target=None):
        assert imp.lock_held()
        with self.lock:
            self.numcalls += 1
        x = self.x
        time.sleep(0.01)
        self.x = x + 1


class FlushingFinder:
    "A dummy finder which flushes sys.path_importer_cache when it gets\n    called."

    def find_spec(self, name, path=None, target=None):
        sys.path_importer_cache.clear()


class ThreadedImportTests(unittest.TestCase):
    def setUp(self):
        self.old_random = sys.modules.pop("random", None)

    def tearDown(self):
        if self.old_random is not None:
            sys.modules["random"] = self.old_random

    @mock_register_at_fork
    def check_parallel_module_init(self, mock_os):
        if imp.lock_held():
            raise unittest.SkipTest("can't run when import lock is held")
        done = threading.Event()
        for N in (20, 50) * 3:
            if verbose:
                print("Trying", N, "threads ...", end=" ")
            for modname in ["random", "modulefinder"]:
                try:
                    del sys.modules[modname]
                except KeyError:
                    pass
            errors = []
            done_tasks = []
            done.clear()
            t0 = time.monotonic()
            with threading_helper.start_threads(
                (
                    threading.Thread(target=task, args=(N, done, done_tasks, errors))
                    for i in range(N)
                )
            ):
                pass
            completed = done.wait((10 * 60))
            dt = time.monotonic() - t0
            if verbose:
                print(("%.1f ms" % (dt * 1000.0)), flush=True, end=" ")
            dbg_info = "done: %s/%s" % (len(done_tasks), N)
            self.assertFalse(errors, dbg_info)
            self.assertTrue(completed, dbg_info)
            if verbose:
                print("OK.")

    def test_parallel_module_init(self):
        self.check_parallel_module_init()

    def test_parallel_meta_path(self):
        finder = Finder()
        sys.meta_path.insert(0, finder)
        try:
            self.check_parallel_module_init()
            self.assertGreater(finder.numcalls, 0)
            self.assertEqual(finder.x, finder.numcalls)
        finally:
            sys.meta_path.remove(finder)

    def test_parallel_path_hooks(self):
        finder = Finder()
        flushing_finder = FlushingFinder()

        def path_hook(path):
            finder.find_spec("")
            raise ImportError

        sys.path_hooks.insert(0, path_hook)
        sys.meta_path.append(flushing_finder)
        try:
            flushing_finder.find_spec("")
            numtests = self.check_parallel_module_init()
            self.assertGreater(finder.numcalls, 0)
            self.assertEqual(finder.x, finder.numcalls)
        finally:
            sys.meta_path.remove(flushing_finder)
            sys.path_hooks.remove(path_hook)

    def test_import_hangers(self):
        try:
            del sys.modules["test.test_importlib.threaded_import_hangers"]
        except KeyError:
            pass
        import test.test_importlib.threaded_import_hangers

        self.assertFalse(test.test_importlib.threaded_import_hangers.errors)

    def test_circular_imports(self):
        delay = 0.5
        os.mkdir(TESTFN)
        self.addCleanup(shutil.rmtree, TESTFN)
        sys.path.insert(0, TESTFN)
        self.addCleanup(sys.path.remove, TESTFN)
        for (name, contents) in circular_imports_modules.items():
            contents = contents % {"delay": delay}
            with open(os.path.join(TESTFN, (name + ".py")), "wb") as f:
                f.write(contents.encode("utf-8"))
            self.addCleanup(forget, name)
        importlib.invalidate_caches()
        results = []

        def import_ab():
            import A

            results.append(getattr(A, "x", None))

        def import_ba():
            import B

            results.append(getattr(B, "x", None))

        t1 = threading.Thread(target=import_ab)
        t2 = threading.Thread(target=import_ba)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(set(results), {"a", "b"})

    @mock_register_at_fork
    def test_side_effect_import(self, mock_os):
        code = "if 1:\n            import threading\n            def target():\n                import random\n            t = threading.Thread(target=target)\n            t.start()\n            t.join()\n            t = None"
        sys.path.insert(0, os.curdir)
        self.addCleanup(sys.path.remove, os.curdir)
        filename = TESTFN + ".py"
        with open(filename, "wb") as f:
            f.write(code.encode("utf-8"))
        self.addCleanup(unlink, filename)
        self.addCleanup(forget, TESTFN)
        self.addCleanup(rmtree, "__pycache__")
        importlib.invalidate_caches()
        __import__(TESTFN)
        del sys.modules[TESTFN]

    def test_concurrent_futures_circular_import(self):
        fn = os.path.join(os.path.dirname(__file__), "partial", "cfimport.py")
        script_helper.assert_python_ok(fn)

    def test_multiprocessing_pool_circular_import(self):
        fn = os.path.join(os.path.dirname(__file__), "partial", "pool_in_threads.py")
        script_helper.assert_python_ok(fn)


@threading_helper.reap_threads
def test_main():
    old_switchinterval = None
    try:
        old_switchinterval = sys.getswitchinterval()
        sys.setswitchinterval(1e-05)
    except AttributeError:
        pass
    try:
        run_unittest(ThreadedImportTests)
    finally:
        if old_switchinterval is not None:
            sys.setswitchinterval(old_switchinterval)


if __name__ == "__main__":
    test_main()
