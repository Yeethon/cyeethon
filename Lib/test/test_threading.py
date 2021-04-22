"\nTests for the threading module.\n"
import test.support
from test.support import threading_helper
from test.support import verbose, cpython_only
from test.support.import_helper import import_module
from test.support.script_helper import assert_python_ok, assert_python_failure
import random
import sys
import _thread
import threading
import time
import unittest
import weakref
import os
import subprocess
import signal
import textwrap
from unittest import mock
from test import lock_tests
from test import support

platforms_to_skip = ("netbsd5", "hp-ux11")


def restore_default_excepthook(testcase):
    testcase.addCleanup(setattr, threading, "excepthook", threading.excepthook)
    threading.excepthook = threading.__excepthook__


class Counter(object):
    def __init__(self):
        self.value = 0

    def inc(self):
        self.value += 1

    def dec(self):
        self.value -= 1

    def get(self):
        return self.value


class TestThread(threading.Thread):
    def __init__(self, name, testcase, sema, mutex, nrunning):
        threading.Thread.__init__(self, name=name)
        self.testcase = testcase
        self.sema = sema
        self.mutex = mutex
        self.nrunning = nrunning

    def run(self):
        delay = random.random() / 10000.0
        if verbose:
            print(("task %s will run for %.1f usec" % (self.name, (delay * 1000000.0))))
        with self.sema:
            with self.mutex:
                self.nrunning.inc()
                if verbose:
                    print(self.nrunning.get(), "tasks are running")
                self.testcase.assertLessEqual(self.nrunning.get(), 3)
            time.sleep(delay)
            if verbose:
                print("task", self.name, "done")
            with self.mutex:
                self.nrunning.dec()
                self.testcase.assertGreaterEqual(self.nrunning.get(), 0)
                if verbose:
                    print(
                        (
                            "%s is finished. %d tasks are running"
                            % (self.name, self.nrunning.get())
                        )
                    )


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self._threads = threading_helper.threading_setup()

    def tearDown(self):
        threading_helper.threading_cleanup(*self._threads)
        test.support.reap_children()


class ThreadTests(BaseTestCase):
    @cpython_only
    def test_name(self):
        def func():
            pass

        thread = threading.Thread(name="myname1")
        self.assertEqual(thread.name, "myname1")
        thread = threading.Thread(name=123)
        self.assertEqual(thread.name, "123")
        thread = threading.Thread(target=func, name="myname2")
        self.assertEqual(thread.name, "myname2")
        with mock.patch.object(threading, "_counter", return_value=2):
            thread = threading.Thread(name="")
            self.assertEqual(thread.name, "Thread-2")
        with mock.patch.object(threading, "_counter", return_value=3):
            thread = threading.Thread()
            self.assertEqual(thread.name, "Thread-3")
        with mock.patch.object(threading, "_counter", return_value=5):
            thread = threading.Thread(target=func)
            self.assertEqual(thread.name, "Thread-5 (func)")

    def test_various_ops(self):
        NUMTASKS = 10
        sema = threading.BoundedSemaphore(value=3)
        mutex = threading.RLock()
        numrunning = Counter()
        threads = []
        for i in range(NUMTASKS):
            t = TestThread(("<thread %d>" % i), self, sema, mutex, numrunning)
            threads.append(t)
            self.assertIsNone(t.ident)
            self.assertRegex(repr(t), "^<TestThread\\(.*, initial\\)>$")
            t.start()
        if hasattr(threading, "get_native_id"):
            native_ids = set((t.native_id for t in threads)) | {
                threading.get_native_id()
            }
            self.assertNotIn(None, native_ids)
            self.assertEqual(len(native_ids), (NUMTASKS + 1))
        if verbose:
            print("waiting for all tasks to complete")
        for t in threads:
            t.join()
            self.assertFalse(t.is_alive())
            self.assertNotEqual(t.ident, 0)
            self.assertIsNotNone(t.ident)
            self.assertRegex(repr(t), "^<TestThread\\(.*, stopped -?\\d+\\)>$")
        if verbose:
            print("all tasks done")
        self.assertEqual(numrunning.get(), 0)

    def test_ident_of_no_threading_threads(self):
        self.assertIsNotNone(threading.current_thread().ident)

        def f():
            ident.append(threading.current_thread().ident)
            done.set()

        done = threading.Event()
        ident = []
        with threading_helper.wait_threads_exit():
            tid = _thread.start_new_thread(f, ())
            done.wait()
            self.assertEqual(ident[0], tid)
        del threading._active[ident[0]]

    def test_various_ops_small_stack(self):
        if verbose:
            print("with 256 KiB thread stack size...")
        try:
            threading.stack_size(262144)
        except _thread.error:
            raise unittest.SkipTest(
                "platform does not support changing thread stack size"
            )
        self.test_various_ops()
        threading.stack_size(0)

    def test_various_ops_large_stack(self):
        if verbose:
            print("with 1 MiB thread stack size...")
        try:
            threading.stack_size(1048576)
        except _thread.error:
            raise unittest.SkipTest(
                "platform does not support changing thread stack size"
            )
        self.test_various_ops()
        threading.stack_size(0)

    def test_foreign_thread(self):
        def f(mutex):
            threading.current_thread()
            mutex.release()

        mutex = threading.Lock()
        mutex.acquire()
        with threading_helper.wait_threads_exit():
            tid = _thread.start_new_thread(f, (mutex,))
            mutex.acquire()
        self.assertIn(tid, threading._active)
        self.assertIsInstance(threading._active[tid], threading._DummyThread)
        self.assertTrue(threading._active[tid].is_alive())
        self.assertRegex(repr(threading._active[tid]), "_DummyThread")
        del threading._active[tid]

    def test_PyThreadState_SetAsyncExc(self):
        ctypes = import_module("ctypes")
        set_async_exc = ctypes.pythonapi.PyThreadState_SetAsyncExc
        set_async_exc.argtypes = (ctypes.c_ulong, ctypes.py_object)

        class AsyncExc(Exception):
            pass

        exception = ctypes.py_object(AsyncExc)
        tid = threading.get_ident()
        self.assertIsInstance(tid, int)
        self.assertGreater(tid, 0)
        try:
            result = set_async_exc(tid, exception)
            while True:
                pass
        except AsyncExc:
            pass
        else:
            self.fail("AsyncExc not raised")
        try:
            self.assertEqual(result, 1)
        except UnboundLocalError:
            pass
        worker_started = threading.Event()
        worker_saw_exception = threading.Event()

        class Worker(threading.Thread):
            def run(self):
                self.id = threading.get_ident()
                self.finished = False
                try:
                    while True:
                        worker_started.set()
                        time.sleep(0.1)
                except AsyncExc:
                    self.finished = True
                    worker_saw_exception.set()

        t = Worker()
        t.daemon = True
        t.start()
        if verbose:
            print("    started worker thread")
        if verbose:
            print("    trying nonsensical thread id")
        result = set_async_exc((-1), exception)
        self.assertEqual(result, 0)
        if verbose:
            print("    waiting for worker thread to get started")
        ret = worker_started.wait()
        self.assertTrue(ret)
        if verbose:
            print("    verifying worker hasn't exited")
        self.assertFalse(t.finished)
        if verbose:
            print("    attempting to raise asynch exception in worker")
        result = set_async_exc(t.id, exception)
        self.assertEqual(result, 1)
        if verbose:
            print("    waiting for worker to say it caught the exception")
        worker_saw_exception.wait(timeout=support.SHORT_TIMEOUT)
        self.assertTrue(t.finished)
        if verbose:
            print("    all OK -- joining worker")
        if t.finished:
            t.join()

    def test_limbo_cleanup(self):
        def fail_new_thread(*args):
            raise threading.ThreadError()

        _start_new_thread = threading._start_new_thread
        threading._start_new_thread = fail_new_thread
        try:
            t = threading.Thread(target=(lambda: None))
            self.assertRaises(threading.ThreadError, t.start)
            self.assertFalse(
                (t in threading._limbo),
                "Failed to cleanup _limbo map on failure of Thread.start().",
            )
        finally:
            threading._start_new_thread = _start_new_thread

    def test_finalize_running_thread(self):
        import_module("ctypes")
        (rc, out, err) = assert_python_failure(
            "-c",
            "if 1:\n            import ctypes, sys, time, _thread\n\n            # This lock is used as a simple event variable.\n            ready = _thread.allocate_lock()\n            ready.acquire()\n\n            # Module globals are cleared before __del__ is run\n            # So we save the functions in class dict\n            class C:\n                ensure = ctypes.pythonapi.PyGILState_Ensure\n                release = ctypes.pythonapi.PyGILState_Release\n                def __del__(self):\n                    state = self.ensure()\n                    self.release(state)\n\n            def waitingThread():\n                x = C()\n                ready.release()\n                time.sleep(100)\n\n            _thread.start_new_thread(waitingThread, ())\n            ready.acquire()  # Be sure the other thread is waiting.\n            sys.exit(42)\n            ",
        )
        self.assertEqual(rc, 42)

    def test_finalize_with_trace(self):
        assert_python_ok(
            "-c",
            "if 1:\n            import sys, threading\n\n            # A deadlock-killer, to prevent the\n            # testsuite to hang forever\n            def killer():\n                import os, time\n                time.sleep(2)\n                print('program blocked; aborting')\n                os._exit(2)\n            t = threading.Thread(target=killer)\n            t.daemon = True\n            t.start()\n\n            # This is the trace function\n            def func(frame, event, arg):\n                threading.current_thread()\n                return func\n\n            sys.settrace(func)\n            ",
        )

    def test_join_nondaemon_on_shutdown(self):
        (rc, out, err) = assert_python_ok(
            "-c",
            'if 1:\n                import threading\n                from time import sleep\n\n                def child():\n                    sleep(1)\n                    # As a non-daemon thread we SHOULD wake up and nothing\n                    # should be torn down yet\n                    print("Woke up, sleep function is:", sleep)\n\n                threading.Thread(target=child).start()\n                raise SystemExit\n            ',
        )
        self.assertEqual(
            out.strip(), b"Woke up, sleep function is: <built-in function sleep>"
        )
        self.assertEqual(err, b"")

    def test_enumerate_after_join(self):
        enum = threading.enumerate
        old_interval = sys.getswitchinterval()
        try:
            for i in range(1, 100):
                sys.setswitchinterval((i * 0.0002))
                t = threading.Thread(target=(lambda: None))
                t.start()
                t.join()
                l = enum()
                self.assertNotIn(
                    t, l, ("#1703448 triggered after %d trials: %s" % (i, l))
                )
        finally:
            sys.setswitchinterval(old_interval)

    def test_no_refcycle_through_target(self):
        class RunSelfFunction(object):
            def __init__(self, should_raise):
                self.should_raise = should_raise
                self.thread = threading.Thread(
                    target=self._run, args=(self,), kwargs={"yet_another": self}
                )
                self.thread.start()

            def _run(self, other_ref, yet_another):
                if self.should_raise:
                    raise SystemExit

        restore_default_excepthook(self)
        cyclic_object = RunSelfFunction(should_raise=False)
        weak_cyclic_object = weakref.ref(cyclic_object)
        cyclic_object.thread.join()
        del cyclic_object
        self.assertIsNone(
            weak_cyclic_object(),
            msg=("%d references still around" % sys.getrefcount(weak_cyclic_object())),
        )
        raising_cyclic_object = RunSelfFunction(should_raise=True)
        weak_raising_cyclic_object = weakref.ref(raising_cyclic_object)
        raising_cyclic_object.thread.join()
        del raising_cyclic_object
        self.assertIsNone(
            weak_raising_cyclic_object(),
            msg=(
                "%d references still around"
                % sys.getrefcount(weak_raising_cyclic_object())
            ),
        )

    def test_old_threading_api(self):
        t = threading.Thread()
        with self.assertWarnsRegex(DeprecationWarning, "get the daemon attribute"):
            t.isDaemon()
        with self.assertWarnsRegex(DeprecationWarning, "set the daemon attribute"):
            t.setDaemon(True)
        with self.assertWarnsRegex(DeprecationWarning, "get the name attribute"):
            t.getName()
        with self.assertWarnsRegex(DeprecationWarning, "set the name attribute"):
            t.setName("name")
        e = threading.Event()
        with self.assertWarnsRegex(DeprecationWarning, "use is_set()"):
            e.isSet()
        cond = threading.Condition()
        cond.acquire()
        with self.assertWarnsRegex(DeprecationWarning, "use notify_all()"):
            cond.notifyAll()
        with self.assertWarnsRegex(DeprecationWarning, "use active_count()"):
            threading.activeCount()
        with self.assertWarnsRegex(DeprecationWarning, "use current_thread()"):
            threading.currentThread()

    def test_repr_daemon(self):
        t = threading.Thread()
        self.assertNotIn("daemon", repr(t))
        t.daemon = True
        self.assertIn("daemon", repr(t))

    def test_daemon_param(self):
        t = threading.Thread()
        self.assertFalse(t.daemon)
        t = threading.Thread(daemon=False)
        self.assertFalse(t.daemon)
        t = threading.Thread(daemon=True)
        self.assertTrue(t.daemon)

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    def test_fork_at_exit(self):
        code = textwrap.dedent(
            '\n            import atexit\n            import os\n            import sys\n            from test.support import wait_process\n\n            # Import the threading module to register its "at fork" callback\n            import threading\n\n            def exit_handler():\n                pid = os.fork()\n                if not pid:\n                    print("child process ok", file=sys.stderr, flush=True)\n                    # child process\n                else:\n                    wait_process(pid, exitcode=0)\n\n            # exit_handler() will be called after threading._shutdown()\n            atexit.register(exit_handler)\n        '
        )
        (_, out, err) = assert_python_ok("-c", code)
        self.assertEqual(out, b"")
        self.assertEqual(err.rstrip(), b"child process ok")

    @unittest.skipUnless(hasattr(os, "fork"), "test needs fork()")
    def test_dummy_thread_after_fork(self):
        code = "if 1:\n            import _thread, threading, os, time\n\n            def background_thread(evt):\n                # Creates and registers the _DummyThread instance\n                threading.current_thread()\n                evt.set()\n                time.sleep(10)\n\n            evt = threading.Event()\n            _thread.start_new_thread(background_thread, (evt,))\n            evt.wait()\n            assert threading.active_count() == 2, threading.active_count()\n            if os.fork() == 0:\n                assert threading.active_count() == 1, threading.active_count()\n                os._exit(0)\n            else:\n                os.wait()\n        "
        (_, out, err) = assert_python_ok("-c", code)
        self.assertEqual(out, b"")
        self.assertEqual(err, b"")

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    def test_is_alive_after_fork(self):
        old_interval = sys.getswitchinterval()
        self.addCleanup(sys.setswitchinterval, old_interval)
        test.support.setswitchinterval(1e-06)
        for i in range(20):
            t = threading.Thread(target=(lambda: None))
            t.start()
            pid = os.fork()
            if pid == 0:
                os._exit((11 if t.is_alive() else 10))
            else:
                t.join()
                support.wait_process(pid, exitcode=10)

    def test_main_thread(self):
        main = threading.main_thread()
        self.assertEqual(main.name, "MainThread")
        self.assertEqual(main.ident, threading.current_thread().ident)
        self.assertEqual(main.ident, threading.get_ident())

        def f():
            self.assertNotEqual(
                threading.main_thread().ident, threading.current_thread().ident
            )

        th = threading.Thread(target=f)
        th.start()
        th.join()

    @unittest.skipUnless(hasattr(os, "fork"), "test needs os.fork()")
    @unittest.skipUnless(hasattr(os, "waitpid"), "test needs os.waitpid()")
    def test_main_thread_after_fork(self):
        code = "if 1:\n            import os, threading\n            from test import support\n\n            pid = os.fork()\n            if pid == 0:\n                main = threading.main_thread()\n                print(main.name)\n                print(main.ident == threading.current_thread().ident)\n                print(main.ident == threading.get_ident())\n            else:\n                support.wait_process(pid, exitcode=0)\n        "
        (_, out, err) = assert_python_ok("-c", code)
        data = out.decode().replace("\r", "")
        self.assertEqual(err, b"")
        self.assertEqual(data, "MainThread\nTrue\nTrue\n")

    @unittest.skipIf((sys.platform in platforms_to_skip), "due to known OS bug")
    @unittest.skipUnless(hasattr(os, "fork"), "test needs os.fork()")
    @unittest.skipUnless(hasattr(os, "waitpid"), "test needs os.waitpid()")
    def test_main_thread_after_fork_from_nonmain_thread(self):
        code = "if 1:\n            import os, threading, sys\n            from test import support\n\n            def func():\n                pid = os.fork()\n                if pid == 0:\n                    main = threading.main_thread()\n                    print(main.name)\n                    print(main.ident == threading.current_thread().ident)\n                    print(main.ident == threading.get_ident())\n                    # stdout is fully buffered because not a tty,\n                    # we have to flush before exit.\n                    sys.stdout.flush()\n                else:\n                    support.wait_process(pid, exitcode=0)\n\n            th = threading.Thread(target=func)\n            th.start()\n            th.join()\n        "
        (_, out, err) = assert_python_ok("-c", code)
        data = out.decode().replace("\r", "")
        self.assertEqual(err, b"")
        self.assertEqual(data, "Thread-1 (func)\nTrue\nTrue\n")

    def test_main_thread_during_shutdown(self):
        code = 'if 1:\n            import gc, threading\n\n            main_thread = threading.current_thread()\n            assert main_thread is threading.main_thread()  # sanity check\n\n            class RefCycle:\n                def __init__(self):\n                    self.cycle = self\n\n                def __del__(self):\n                    print("GC:",\n                          threading.current_thread() is main_thread,\n                          threading.main_thread() is main_thread,\n                          threading.enumerate() == [main_thread])\n\n            RefCycle()\n            gc.collect()  # sanity check\n            x = RefCycle()\n        '
        (_, out, err) = assert_python_ok("-c", code)
        data = out.decode()
        self.assertEqual(err, b"")
        self.assertEqual(data.splitlines(), (["GC: True True True"] * 2))

    def test_finalization_shutdown(self):
        code = "if 1:\n            import os\n            import threading\n            import time\n            import random\n\n            def random_sleep():\n                seconds = random.random() * 0.010\n                time.sleep(seconds)\n\n            class Sleeper:\n                def __del__(self):\n                    random_sleep()\n\n            tls = threading.local()\n\n            def f():\n                # Sleep a bit so that the thread is still running when\n                # Py_Finalize() is called.\n                random_sleep()\n                tls.x = Sleeper()\n                random_sleep()\n\n            threading.Thread(target=f).start()\n            random_sleep()\n        "
        (rc, out, err) = assert_python_ok("-c", code)
        self.assertEqual(err, b"")

    def test_tstate_lock(self):
        started = _thread.allocate_lock()
        finish = _thread.allocate_lock()
        started.acquire()
        finish.acquire()

        def f():
            started.release()
            finish.acquire()
            time.sleep(0.01)

        t = threading.Thread(target=f)
        self.assertIs(t._tstate_lock, None)
        t.start()
        started.acquire()
        self.assertTrue(t.is_alive())
        tstate_lock = t._tstate_lock
        self.assertFalse(tstate_lock.acquire(timeout=0), False)
        finish.release()
        self.assertTrue(tstate_lock.acquire(timeout=support.SHORT_TIMEOUT), False)
        self.assertTrue(t.is_alive())
        tstate_lock.release()
        self.assertFalse(t.is_alive())
        self.assertIsNone(t._tstate_lock)
        t.join()

    def test_repr_stopped(self):
        started = _thread.allocate_lock()
        finish = _thread.allocate_lock()
        started.acquire()
        finish.acquire()

        def f():
            started.release()
            finish.acquire()

        t = threading.Thread(target=f)
        t.start()
        started.acquire()
        self.assertIn("started", repr(t))
        finish.release()
        LOOKING_FOR = "stopped"
        for i in range(500):
            if LOOKING_FOR in repr(t):
                break
            time.sleep(0.01)
        self.assertIn(LOOKING_FOR, repr(t))
        t.join()

    def test_BoundedSemaphore_limit(self):
        for limit in range(1, 10):
            bs = threading.BoundedSemaphore(limit)
            threads = [threading.Thread(target=bs.acquire) for _ in range(limit)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            threads = [threading.Thread(target=bs.release) for _ in range(limit)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertRaises(ValueError, bs.release)

    @cpython_only
    def test_frame_tstate_tracing(self):
        def noop_trace(frame, event, arg):
            return noop_trace

        def generator():
            while 1:
                (yield "generator")

        def callback():
            if callback.gen is None:
                callback.gen = generator()
            return next(callback.gen)

        callback.gen = None
        old_trace = sys.gettrace()
        sys.settrace(noop_trace)
        try:
            threading.settrace(noop_trace)
            import _testcapi

            _testcapi.call_in_temporary_c_thread(callback)
            for test in range(3):
                callback()
        finally:
            sys.settrace(old_trace)

    def test_gettrace(self):
        def noop_trace(frame, event, arg):
            return noop_trace

        old_trace = threading.gettrace()
        try:
            threading.settrace(noop_trace)
            trace_func = threading.gettrace()
            self.assertEqual(noop_trace, trace_func)
        finally:
            threading.settrace(old_trace)

    def test_getprofile(self):
        def fn(*args):
            pass

        old_profile = threading.getprofile()
        try:
            threading.setprofile(fn)
            self.assertEqual(fn, threading.getprofile())
        finally:
            threading.setprofile(old_profile)

    @cpython_only
    def test_shutdown_locks(self):
        for daemon in (False, True):
            with self.subTest(daemon=daemon):
                event = threading.Event()
                thread = threading.Thread(target=event.wait, daemon=daemon)
                thread.start()
                tstate_lock = thread._tstate_lock
                if not daemon:
                    self.assertIn(tstate_lock, threading._shutdown_locks)
                else:
                    self.assertNotIn(tstate_lock, threading._shutdown_locks)
                event.set()
                thread.join()
                self.assertNotIn(tstate_lock, threading._shutdown_locks)

    def test_locals_at_exit(self):
        (rc, out, err) = assert_python_ok(
            "-c",
            'if 1:\n            import threading\n\n            class Atexit:\n                def __del__(self):\n                    print("thread_dict.atexit = %r" % thread_dict.atexit)\n\n            thread_dict = threading.local()\n            thread_dict.atexit = "value"\n\n            atexit = Atexit()\n        ',
        )
        self.assertEqual(out.rstrip(), b"thread_dict.atexit = 'value'")

    def test_boolean_target(self):
        class BooleanTarget(object):
            def __init__(self):
                self.ran = False

            def __bool__(self):
                return False

            def __call__(self):
                self.ran = True

        target = BooleanTarget()
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        self.assertTrue(target.ran)


class ThreadJoinOnShutdown(BaseTestCase):
    def _run_and_join(self, script):
        script = (
            "if 1:\n            import sys, os, time, threading\n\n            # a thread, which waits for the main program to terminate\n            def joiningfunc(mainthread):\n                mainthread.join()\n                print('end of thread')\n                # stdout is fully buffered because not a tty, we have to flush\n                # before exit.\n                sys.stdout.flush()\n        \n"
            + script
        )
        (rc, out, err) = assert_python_ok("-c", script)
        data = out.decode().replace("\r", "")
        self.assertEqual(data, "end of main\nend of thread\n")

    def test_1_join_on_shutdown(self):
        script = "if 1:\n            import os\n            t = threading.Thread(target=joiningfunc,\n                                 args=(threading.current_thread(),))\n            t.start()\n            time.sleep(0.1)\n            print('end of main')\n            "
        self._run_and_join(script)

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    @unittest.skipIf((sys.platform in platforms_to_skip), "due to known OS bug")
    def test_2_join_in_forked_process(self):
        script = "if 1:\n            from test import support\n\n            childpid = os.fork()\n            if childpid != 0:\n                # parent process\n                support.wait_process(childpid, exitcode=0)\n                sys.exit(0)\n\n            # child process\n            t = threading.Thread(target=joiningfunc,\n                                 args=(threading.current_thread(),))\n            t.start()\n            print('end of main')\n            "
        self._run_and_join(script)

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    @unittest.skipIf((sys.platform in platforms_to_skip), "due to known OS bug")
    def test_3_join_in_forked_from_thread(self):
        script = "if 1:\n            from test import support\n\n            main_thread = threading.current_thread()\n            def worker():\n                childpid = os.fork()\n                if childpid != 0:\n                    # parent process\n                    support.wait_process(childpid, exitcode=0)\n                    sys.exit(0)\n\n                # child process\n                t = threading.Thread(target=joiningfunc,\n                                     args=(main_thread,))\n                print('end of main')\n                t.start()\n                t.join() # Should not block: main_thread is already stopped\n\n            w = threading.Thread(target=worker)\n            w.start()\n            "
        self._run_and_join(script)

    @unittest.skipIf((sys.platform in platforms_to_skip), "due to known OS bug")
    def test_4_daemon_threads(self):
        script = "if True:\n            import os\n            import random\n            import sys\n            import time\n            import threading\n\n            thread_has_run = set()\n\n            def random_io():\n                '''Loop for a while sleeping random tiny amounts and doing some I/O.'''\n                while True:\n                    with open(os.__file__, 'rb') as in_f:\n                        stuff = in_f.read(200)\n                        with open(os.devnull, 'wb') as null_f:\n                            null_f.write(stuff)\n                            time.sleep(random.random() / 1995)\n                    thread_has_run.add(threading.current_thread())\n\n            def main():\n                count = 0\n                for _ in range(40):\n                    new_thread = threading.Thread(target=random_io)\n                    new_thread.daemon = True\n                    new_thread.start()\n                    count += 1\n                while len(thread_has_run) < count:\n                    time.sleep(0.001)\n                # Trigger process shutdown\n                sys.exit(0)\n\n            main()\n            "
        (rc, out, err) = assert_python_ok("-c", script)
        self.assertFalse(err)

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    @unittest.skipIf((sys.platform in platforms_to_skip), "due to known OS bug")
    def test_reinit_tls_after_fork(self):
        def do_fork_and_wait():
            pid = os.fork()
            if pid > 0:
                support.wait_process(pid, exitcode=50)
            else:
                os._exit(50)

        threads = []
        for i in range(16):
            t = threading.Thread(target=do_fork_and_wait)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    @unittest.skipUnless(hasattr(os, "fork"), "needs os.fork()")
    def test_clear_threads_states_after_fork(self):
        threads = []
        for i in range(16):
            t = threading.Thread(target=(lambda: time.sleep(0.3)))
            threads.append(t)
            t.start()
        pid = os.fork()
        if pid == 0:
            if len(sys._current_frames()) == 1:
                os._exit(51)
            else:
                os._exit(52)
        else:
            support.wait_process(pid, exitcode=51)
        for t in threads:
            t.join()


class SubinterpThreadingTests(BaseTestCase):
    def pipe(self):
        (r, w) = os.pipe()
        self.addCleanup(os.close, r)
        self.addCleanup(os.close, w)
        if hasattr(os, "set_blocking"):
            os.set_blocking(r, False)
        return (r, w)

    def test_threads_join(self):
        (r, w) = self.pipe()
        code = textwrap.dedent(
            (
                '\n            import os\n            import random\n            import threading\n            import time\n\n            def random_sleep():\n                seconds = random.random() * 0.010\n                time.sleep(seconds)\n\n            def f():\n                # Sleep a bit so that the thread is still running when\n                # Py_EndInterpreter is called.\n                random_sleep()\n                os.write(%d, b"x")\n\n            threading.Thread(target=f).start()\n            random_sleep()\n        '
                % (w,)
            )
        )
        ret = test.support.run_in_subinterp(code)
        self.assertEqual(ret, 0)
        self.assertEqual(os.read(r, 1), b"x")

    def test_threads_join_2(self):
        (r, w) = self.pipe()
        code = textwrap.dedent(
            (
                '\n            import os\n            import random\n            import threading\n            import time\n\n            def random_sleep():\n                seconds = random.random() * 0.010\n                time.sleep(seconds)\n\n            class Sleeper:\n                def __del__(self):\n                    random_sleep()\n\n            tls = threading.local()\n\n            def f():\n                # Sleep a bit so that the thread is still running when\n                # Py_EndInterpreter is called.\n                random_sleep()\n                tls.x = Sleeper()\n                os.write(%d, b"x")\n\n            threading.Thread(target=f).start()\n            random_sleep()\n        '
                % (w,)
            )
        )
        ret = test.support.run_in_subinterp(code)
        self.assertEqual(ret, 0)
        self.assertEqual(os.read(r, 1), b"x")

    @cpython_only
    def test_daemon_threads_fatal_error(self):
        subinterp_code = f"""if 1:
            import os
            import threading
            import time

            def f():
                # Make sure the daemon thread is still running when
                # Py_EndInterpreter is called.
                time.sleep({test.support.SHORT_TIMEOUT})
            threading.Thread(target=f, daemon=True).start()
            """
        script = (
            "if 1:\n            import _testcapi\n\n            _testcapi.run_in_subinterp(%r)\n            "
            % (subinterp_code,)
        )
        with test.support.SuppressCrashReport():
            (rc, out, err) = assert_python_failure("-c", script)
        self.assertIn(
            "Fatal Python error: Py_EndInterpreter: not the last thread", err.decode()
        )


class ThreadingExceptionTests(BaseTestCase):
    def test_start_thread_again(self):
        thread = threading.Thread()
        thread.start()
        self.assertRaises(RuntimeError, thread.start)
        thread.join()

    def test_joining_current_thread(self):
        current_thread = threading.current_thread()
        self.assertRaises(RuntimeError, current_thread.join)

    def test_joining_inactive_thread(self):
        thread = threading.Thread()
        self.assertRaises(RuntimeError, thread.join)

    def test_daemonize_active_thread(self):
        thread = threading.Thread()
        thread.start()
        self.assertRaises(RuntimeError, setattr, thread, "daemon", True)
        thread.join()

    def test_releasing_unacquired_lock(self):
        lock = threading.Lock()
        self.assertRaises(RuntimeError, lock.release)

    def test_recursion_limit(self):
        script = "if True:\n            import threading\n\n            def recurse():\n                return recurse()\n\n            def outer():\n                try:\n                    recurse()\n                except RecursionError:\n                    pass\n\n            w = threading.Thread(target=outer)\n            w.start()\n            w.join()\n            print('end of main thread')\n            "
        expected_output = "end of main thread\n"
        p = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        (stdout, stderr) = p.communicate()
        data = stdout.decode().replace("\r", "")
        self.assertEqual(p.returncode, 0, ("Unexpected error: " + stderr.decode()))
        self.assertEqual(data, expected_output)

    def test_print_exception(self):
        script = "if True:\n            import threading\n            import time\n\n            running = False\n            def run():\n                global running\n                running = True\n                while running:\n                    time.sleep(0.01)\n                1/0\n            t = threading.Thread(target=run)\n            t.start()\n            while not running:\n                time.sleep(0.01)\n            running = False\n            t.join()\n            "
        (rc, out, err) = assert_python_ok("-c", script)
        self.assertEqual(out, b"")
        err = err.decode()
        self.assertIn("Exception in thread", err)
        self.assertIn("Traceback (most recent call last):", err)
        self.assertIn("ZeroDivisionError", err)
        self.assertNotIn("Unhandled exception", err)

    def test_print_exception_stderr_is_none_1(self):
        script = "if True:\n            import sys\n            import threading\n            import time\n\n            running = False\n            def run():\n                global running\n                running = True\n                while running:\n                    time.sleep(0.01)\n                1/0\n            t = threading.Thread(target=run)\n            t.start()\n            while not running:\n                time.sleep(0.01)\n            sys.stderr = None\n            running = False\n            t.join()\n            "
        (rc, out, err) = assert_python_ok("-c", script)
        self.assertEqual(out, b"")
        err = err.decode()
        self.assertIn("Exception in thread", err)
        self.assertIn("Traceback (most recent call last):", err)
        self.assertIn("ZeroDivisionError", err)
        self.assertNotIn("Unhandled exception", err)

    def test_print_exception_stderr_is_none_2(self):
        script = "if True:\n            import sys\n            import threading\n            import time\n\n            running = False\n            def run():\n                global running\n                running = True\n                while running:\n                    time.sleep(0.01)\n                1/0\n            sys.stderr = None\n            t = threading.Thread(target=run)\n            t.start()\n            while not running:\n                time.sleep(0.01)\n            running = False\n            t.join()\n            "
        (rc, out, err) = assert_python_ok("-c", script)
        self.assertEqual(out, b"")
        self.assertNotIn("Unhandled exception", err.decode())

    def test_bare_raise_in_brand_new_thread(self):
        def bare_raise():
            raise

        class Issue27558(threading.Thread):
            exc = None

            def run(self):
                try:
                    bare_raise()
                except Exception as exc:
                    self.exc = exc

        thread = Issue27558()
        thread.start()
        thread.join()
        self.assertIsNotNone(thread.exc)
        self.assertIsInstance(thread.exc, RuntimeError)
        thread.exc = None


class ThreadRunFail(threading.Thread):
    def run(self):
        raise ValueError("run failed")


class ExceptHookTests(BaseTestCase):
    def setUp(self):
        restore_default_excepthook(self)
        super().setUp()

    def test_excepthook(self):
        with support.captured_output("stderr") as stderr:
            thread = ThreadRunFail(name="excepthook thread")
            thread.start()
            thread.join()
        stderr = stderr.getvalue().strip()
        self.assertIn(
            f"""Exception in thread {thread.name}:
""",
            stderr,
        )
        self.assertIn("Traceback (most recent call last):\n", stderr)
        self.assertIn('  raise ValueError("run failed")', stderr)
        self.assertIn("ValueError: run failed", stderr)

    @support.cpython_only
    def test_excepthook_thread_None(self):
        with support.captured_output("stderr") as stderr:
            try:
                raise ValueError("bug")
            except Exception as exc:
                args = threading.ExceptHookArgs([*sys.exc_info(), None])
                try:
                    threading.excepthook(args)
                finally:
                    args = None
        stderr = stderr.getvalue().strip()
        self.assertIn(
            f"""Exception in thread {threading.get_ident()}:
""",
            stderr,
        )
        self.assertIn("Traceback (most recent call last):\n", stderr)
        self.assertIn('  raise ValueError("bug")', stderr)
        self.assertIn("ValueError: bug", stderr)

    def test_system_exit(self):
        class ThreadExit(threading.Thread):
            def run(self):
                sys.exit(1)

        with support.captured_output("stderr") as stderr:
            thread = ThreadExit()
            thread.start()
            thread.join()
        self.assertEqual(stderr.getvalue(), "")

    def test_custom_excepthook(self):
        args = None

        def hook(hook_args):
            nonlocal args
            args = hook_args

        try:
            with support.swap_attr(threading, "excepthook", hook):
                thread = ThreadRunFail()
                thread.start()
                thread.join()
            self.assertEqual(args.exc_type, ValueError)
            self.assertEqual(str(args.exc_value), "run failed")
            self.assertEqual(args.exc_traceback, args.exc_value.__traceback__)
            self.assertIs(args.thread, thread)
        finally:
            args = None

    def test_custom_excepthook_fail(self):
        def threading_hook(args):
            raise ValueError("threading_hook failed")

        err_str = None

        def sys_hook(exc_type, exc_value, exc_traceback):
            nonlocal err_str
            err_str = str(exc_value)

        with support.swap_attr(
            threading, "excepthook", threading_hook
        ), support.swap_attr(sys, "excepthook", sys_hook), support.captured_output(
            "stderr"
        ) as stderr:
            thread = ThreadRunFail()
            thread.start()
            thread.join()
        self.assertEqual(stderr.getvalue(), "Exception in threading.excepthook:\n")
        self.assertEqual(err_str, "threading_hook failed")

    def test_original_excepthook(self):
        def run_thread():
            with support.captured_output("stderr") as output:
                thread = ThreadRunFail(name="excepthook thread")
                thread.start()
                thread.join()
            return output.getvalue()

        def threading_hook(args):
            print("Running a thread failed", file=sys.stderr)

        default_output = run_thread()
        with support.swap_attr(threading, "excepthook", threading_hook):
            custom_hook_output = run_thread()
            threading.excepthook = threading.__excepthook__
            recovered_output = run_thread()
        self.assertEqual(default_output, recovered_output)
        self.assertNotEqual(default_output, custom_hook_output)
        self.assertEqual(custom_hook_output, "Running a thread failed\n")


class TimerTests(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.callback_args = []
        self.callback_event = threading.Event()

    def test_init_immutable_default_args(self):
        timer1 = threading.Timer(0.01, self._callback_spy)
        timer1.start()
        self.callback_event.wait()
        timer1.args.append("blah")
        timer1.kwargs["foo"] = "bar"
        self.callback_event.clear()
        timer2 = threading.Timer(0.01, self._callback_spy)
        timer2.start()
        self.callback_event.wait()
        self.assertEqual(len(self.callback_args), 2)
        self.assertEqual(self.callback_args, [((), {}), ((), {})])
        timer1.join()
        timer2.join()

    def _callback_spy(self, *args, **kwargs):
        self.callback_args.append((args[:], kwargs.copy()))
        self.callback_event.set()


class LockTests(lock_tests.LockTests):
    locktype = staticmethod(threading.Lock)


class PyRLockTests(lock_tests.RLockTests):
    locktype = staticmethod(threading._PyRLock)


@unittest.skipIf((threading._CRLock is None), "RLock not implemented in C")
class CRLockTests(lock_tests.RLockTests):
    locktype = staticmethod(threading._CRLock)


class EventTests(lock_tests.EventTests):
    eventtype = staticmethod(threading.Event)


class ConditionAsRLockTests(lock_tests.RLockTests):
    locktype = staticmethod(threading.Condition)


class ConditionTests(lock_tests.ConditionTests):
    condtype = staticmethod(threading.Condition)


class SemaphoreTests(lock_tests.SemaphoreTests):
    semtype = staticmethod(threading.Semaphore)


class BoundedSemaphoreTests(lock_tests.BoundedSemaphoreTests):
    semtype = staticmethod(threading.BoundedSemaphore)


class BarrierTests(lock_tests.BarrierTests):
    barriertype = staticmethod(threading.Barrier)


class MiscTestCase(unittest.TestCase):
    def test__all__(self):
        restore_default_excepthook(self)
        extra = {"ThreadError"}
        not_exported = {"currentThread", "activeCount"}
        support.check__all__(
            self,
            threading,
            ("threading", "_thread"),
            extra=extra,
            not_exported=not_exported,
        )


class InterruptMainTests(unittest.TestCase):
    def check_interrupt_main_with_signal_handler(self, signum):
        def handler(signum, frame):
            (1 / 0)

        old_handler = signal.signal(signum, handler)
        self.addCleanup(signal.signal, signum, old_handler)
        with self.assertRaises(ZeroDivisionError):
            _thread.interrupt_main()

    def check_interrupt_main_noerror(self, signum):
        handler = signal.getsignal(signum)
        try:
            signal.signal(signum, signal.SIG_IGN)
            _thread.interrupt_main(signum)
            signal.signal(signum, signal.SIG_DFL)
            _thread.interrupt_main(signum)
        finally:
            signal.signal(signum, handler)

    def test_interrupt_main_subthread(self):
        def call_interrupt():
            _thread.interrupt_main()

        t = threading.Thread(target=call_interrupt)
        with self.assertRaises(KeyboardInterrupt):
            t.start()
            t.join()
        t.join()

    def test_interrupt_main_mainthread(self):
        with self.assertRaises(KeyboardInterrupt):
            _thread.interrupt_main()

    def test_interrupt_main_with_signal_handler(self):
        self.check_interrupt_main_with_signal_handler(signal.SIGINT)
        self.check_interrupt_main_with_signal_handler(signal.SIGTERM)

    def test_interrupt_main_noerror(self):
        self.check_interrupt_main_noerror(signal.SIGINT)
        self.check_interrupt_main_noerror(signal.SIGTERM)

    def test_interrupt_main_invalid_signal(self):
        self.assertRaises(ValueError, _thread.interrupt_main, (-1))
        self.assertRaises(ValueError, _thread.interrupt_main, signal.NSIG)
        self.assertRaises(ValueError, _thread.interrupt_main, 1000000)


class AtexitTests(unittest.TestCase):
    def test_atexit_output(self):
        (rc, out, err) = assert_python_ok(
            "-c",
            "if True:\n            import threading\n\n            def run_last():\n                print('parrot')\n\n            threading._register_atexit(run_last)\n        ",
        )
        self.assertFalse(err)
        self.assertEqual(out.strip(), b"parrot")

    def test_atexit_called_once(self):
        (rc, out, err) = assert_python_ok(
            "-c",
            "if True:\n            import threading\n            from unittest.mock import Mock\n\n            mock = Mock()\n            threading._register_atexit(mock)\n            mock.assert_not_called()\n            # force early shutdown to ensure it was called once\n            threading._shutdown()\n            mock.assert_called_once()\n        ",
        )
        self.assertFalse(err)

    def test_atexit_after_shutdown(self):
        (rc, out, err) = assert_python_ok(
            "-c",
            "if True:\n            import threading\n\n            def func():\n                pass\n\n            def run_last():\n                threading._register_atexit(func)\n\n            threading._register_atexit(run_last)\n        ",
        )
        self.assertTrue(err)
        self.assertIn(
            "RuntimeError: can't register atexit after shutdown", err.decode()
        )


if __name__ == "__main__":
    unittest.main()
