"\nVarious tests for synchronization primitives.\n"
import os
import sys
import time
from _thread import start_new_thread, TIMEOUT_MAX
import threading
import unittest
import weakref
from test import support
from test.support import threading_helper

requires_fork = unittest.skipUnless(
    hasattr(os, "fork"), "platform doesn't support fork (no _at_fork_reinit method)"
)


def _wait():
    time.sleep(0.01)


class Bunch(object):
    "\n    A bunch of threads.\n    "

    def __init__(self, f, n, wait_before_exit=False):
        "\n        Construct a bunch of `n` threads running the same function `f`.\n        If `wait_before_exit` is True, the threads won't terminate until\n        do_finish() is called.\n        "
        self.f = f
        self.n = n
        self.started = []
        self.finished = []
        self._can_exit = not wait_before_exit
        self.wait_thread = threading_helper.wait_threads_exit()
        self.wait_thread.__enter__()

        def task():
            tid = threading.get_ident()
            self.started.append(tid)
            try:
                f()
            finally:
                self.finished.append(tid)
                while not self._can_exit:
                    _wait()

        try:
            for i in range(n):
                start_new_thread(task, ())
        except:
            self._can_exit = True
            raise

    def wait_for_started(self):
        while len(self.started) < self.n:
            _wait()

    def wait_for_finished(self):
        while len(self.finished) < self.n:
            _wait()
        self.wait_thread.__exit__(None, None, None)

    def do_finish(self):
        self._can_exit = True


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self._threads = threading_helper.threading_setup()

    def tearDown(self):
        threading_helper.threading_cleanup(*self._threads)
        support.reap_children()

    def assertTimeout(self, actual, expected):
        self.assertGreaterEqual(actual, (expected * 0.6))
        self.assertLess(actual, (expected * 10.0))


class BaseLockTests(BaseTestCase):
    "\n    Tests for both recursive and non-recursive locks.\n    "

    def test_constructor(self):
        lock = self.locktype()
        del lock

    def test_repr(self):
        lock = self.locktype()
        self.assertRegex(repr(lock), "<unlocked .* object (.*)?at .*>")
        del lock

    def test_locked_repr(self):
        lock = self.locktype()
        lock.acquire()
        self.assertRegex(repr(lock), "<locked .* object (.*)?at .*>")
        del lock

    def test_acquire_destroy(self):
        lock = self.locktype()
        lock.acquire()
        del lock

    def test_acquire_release(self):
        lock = self.locktype()
        lock.acquire()
        lock.release()
        del lock

    def test_try_acquire(self):
        lock = self.locktype()
        self.assertTrue(lock.acquire(False))
        lock.release()

    def test_try_acquire_contended(self):
        lock = self.locktype()
        lock.acquire()
        result = []

        def f():
            result.append(lock.acquire(False))

        Bunch(f, 1).wait_for_finished()
        self.assertFalse(result[0])
        lock.release()

    def test_acquire_contended(self):
        lock = self.locktype()
        lock.acquire()
        N = 5

        def f():
            lock.acquire()
            lock.release()

        b = Bunch(f, N)
        b.wait_for_started()
        _wait()
        self.assertEqual(len(b.finished), 0)
        lock.release()
        b.wait_for_finished()
        self.assertEqual(len(b.finished), N)

    def test_with(self):
        lock = self.locktype()

        def f():
            lock.acquire()
            lock.release()

        def _with(err=None):
            with lock:
                if err is not None:
                    raise err

        _with()
        Bunch(f, 1).wait_for_finished()
        self.assertRaises(TypeError, _with, TypeError)
        Bunch(f, 1).wait_for_finished()

    def test_thread_leak(self):
        lock = self.locktype()

        def f():
            lock.acquire()
            lock.release()

        n = len(threading.enumerate())
        Bunch(f, 15).wait_for_finished()
        if len(threading.enumerate()) != n:
            time.sleep(0.4)
            self.assertEqual(n, len(threading.enumerate()))

    def test_timeout(self):
        lock = self.locktype()
        self.assertRaises(ValueError, lock.acquire, False, 1)
        self.assertRaises(ValueError, lock.acquire, timeout=(-100))
        self.assertRaises(OverflowError, lock.acquire, timeout=1e100)
        self.assertRaises(OverflowError, lock.acquire, timeout=(TIMEOUT_MAX + 1))
        lock.acquire(timeout=TIMEOUT_MAX)
        lock.release()
        t1 = time.monotonic()
        self.assertTrue(lock.acquire(timeout=5))
        t2 = time.monotonic()
        self.assertLess((t2 - t1), 5)
        results = []

        def f():
            t1 = time.monotonic()
            results.append(lock.acquire(timeout=0.5))
            t2 = time.monotonic()
            results.append((t2 - t1))

        Bunch(f, 1).wait_for_finished()
        self.assertFalse(results[0])
        self.assertTimeout(results[1], 0.5)

    def test_weakref_exists(self):
        lock = self.locktype()
        ref = weakref.ref(lock)
        self.assertIsNotNone(ref())

    def test_weakref_deleted(self):
        lock = self.locktype()
        ref = weakref.ref(lock)
        del lock
        self.assertIsNone(ref())


class LockTests(BaseLockTests):
    "\n    Tests for non-recursive, weak locks\n    (which can be acquired and released from different threads).\n    "

    def test_reacquire(self):
        lock = self.locktype()
        phase = []

        def f():
            lock.acquire()
            phase.append(None)
            lock.acquire()
            phase.append(None)

        with threading_helper.wait_threads_exit():
            start_new_thread(f, ())
            while len(phase) == 0:
                _wait()
            _wait()
            self.assertEqual(len(phase), 1)
            lock.release()
            while len(phase) == 1:
                _wait()
            self.assertEqual(len(phase), 2)

    def test_different_thread(self):
        lock = self.locktype()
        lock.acquire()

        def f():
            lock.release()

        b = Bunch(f, 1)
        b.wait_for_finished()
        lock.acquire()
        lock.release()

    def test_state_after_timeout(self):
        lock = self.locktype()
        lock.acquire()
        self.assertFalse(lock.acquire(timeout=0.01))
        lock.release()
        self.assertFalse(lock.locked())
        self.assertTrue(lock.acquire(blocking=False))

    @requires_fork
    def test_at_fork_reinit(self):
        def use_lock(lock):
            lock.acquire()
            lock.release()

        lock = self.locktype()
        lock._at_fork_reinit()
        use_lock(lock)
        lock2 = self.locktype()
        lock2.acquire()
        lock2._at_fork_reinit()
        use_lock(lock2)


class RLockTests(BaseLockTests):
    "\n    Tests for recursive locks.\n    "

    def test_reacquire(self):
        lock = self.locktype()
        lock.acquire()
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()
        lock.release()

    def test_release_unacquired(self):
        lock = self.locktype()
        self.assertRaises(RuntimeError, lock.release)
        lock.acquire()
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()
        lock.release()
        self.assertRaises(RuntimeError, lock.release)

    def test_release_save_unacquired(self):
        lock = self.locktype()
        self.assertRaises(RuntimeError, lock._release_save)
        lock.acquire()
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()
        lock.release()
        self.assertRaises(RuntimeError, lock._release_save)

    def test_different_thread(self):
        lock = self.locktype()

        def f():
            lock.acquire()

        b = Bunch(f, 1, True)
        try:
            self.assertRaises(RuntimeError, lock.release)
        finally:
            b.do_finish()
        b.wait_for_finished()

    def test__is_owned(self):
        lock = self.locktype()
        self.assertFalse(lock._is_owned())
        lock.acquire()
        self.assertTrue(lock._is_owned())
        lock.acquire()
        self.assertTrue(lock._is_owned())
        result = []

        def f():
            result.append(lock._is_owned())

        Bunch(f, 1).wait_for_finished()
        self.assertFalse(result[0])
        lock.release()
        self.assertTrue(lock._is_owned())
        lock.release()
        self.assertFalse(lock._is_owned())


class EventTests(BaseTestCase):
    "\n    Tests for Event objects.\n    "

    def test_is_set(self):
        evt = self.eventtype()
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertTrue(evt.is_set())
        evt.set()
        self.assertTrue(evt.is_set())
        evt.clear()
        self.assertFalse(evt.is_set())
        evt.clear()
        self.assertFalse(evt.is_set())

    def _check_notify(self, evt):
        N = 5
        results1 = []
        results2 = []

        def f():
            results1.append(evt.wait())
            results2.append(evt.wait())

        b = Bunch(f, N)
        b.wait_for_started()
        _wait()
        self.assertEqual(len(results1), 0)
        evt.set()
        b.wait_for_finished()
        self.assertEqual(results1, ([True] * N))
        self.assertEqual(results2, ([True] * N))

    def test_notify(self):
        evt = self.eventtype()
        self._check_notify(evt)
        evt.set()
        evt.clear()
        self._check_notify(evt)

    def test_timeout(self):
        evt = self.eventtype()
        results1 = []
        results2 = []
        N = 5

        def f():
            results1.append(evt.wait(0.0))
            t1 = time.monotonic()
            r = evt.wait(0.5)
            t2 = time.monotonic()
            results2.append((r, (t2 - t1)))

        Bunch(f, N).wait_for_finished()
        self.assertEqual(results1, ([False] * N))
        for (r, dt) in results2:
            self.assertFalse(r)
            self.assertTimeout(dt, 0.5)
        results1 = []
        results2 = []
        evt.set()
        Bunch(f, N).wait_for_finished()
        self.assertEqual(results1, ([True] * N))
        for (r, dt) in results2:
            self.assertTrue(r)

    def test_set_and_clear(self):
        evt = self.eventtype()
        results = []
        timeout = 0.25
        N = 5

        def f():
            results.append(evt.wait((timeout * 4)))

        b = Bunch(f, N)
        b.wait_for_started()
        time.sleep(timeout)
        evt.set()
        evt.clear()
        b.wait_for_finished()
        self.assertEqual(results, ([True] * N))

    @requires_fork
    def test_at_fork_reinit(self):
        evt = self.eventtype()
        with evt._cond:
            self.assertFalse(evt._cond.acquire(False))
        evt._at_fork_reinit()
        with evt._cond:
            self.assertFalse(evt._cond.acquire(False))


class ConditionTests(BaseTestCase):
    "\n    Tests for condition variables.\n    "

    def test_acquire(self):
        cond = self.condtype()
        cond.acquire()
        cond.acquire()
        cond.release()
        cond.release()
        lock = threading.Lock()
        cond = self.condtype(lock)
        cond.acquire()
        self.assertFalse(lock.acquire(False))
        cond.release()
        self.assertTrue(lock.acquire(False))
        self.assertFalse(cond.acquire(False))
        lock.release()
        with cond:
            self.assertFalse(lock.acquire(False))

    def test_unacquired_wait(self):
        cond = self.condtype()
        self.assertRaises(RuntimeError, cond.wait)

    def test_unacquired_notify(self):
        cond = self.condtype()
        self.assertRaises(RuntimeError, cond.notify)

    def _check_notify(self, cond):
        N = 5
        ready = []
        results1 = []
        results2 = []
        phase_num = 0

        def f():
            cond.acquire()
            ready.append(phase_num)
            result = cond.wait()
            cond.release()
            results1.append((result, phase_num))
            cond.acquire()
            ready.append(phase_num)
            result = cond.wait()
            cond.release()
            results2.append((result, phase_num))

        b = Bunch(f, N)
        b.wait_for_started()
        while len(ready) < 5:
            _wait()
        ready.clear()
        self.assertEqual(results1, [])
        cond.acquire()
        cond.notify(3)
        _wait()
        phase_num = 1
        cond.release()
        while len(results1) < 3:
            _wait()
        self.assertEqual(results1, ([(True, 1)] * 3))
        self.assertEqual(results2, [])
        while len(ready) < 3:
            _wait()
        cond.acquire()
        cond.notify(5)
        _wait()
        phase_num = 2
        cond.release()
        while (len(results1) + len(results2)) < 8:
            _wait()
        self.assertEqual(results1, (([(True, 1)] * 3) + ([(True, 2)] * 2)))
        self.assertEqual(results2, ([(True, 2)] * 3))
        while len(ready) < 5:
            _wait()
        cond.acquire()
        cond.notify_all()
        _wait()
        phase_num = 3
        cond.release()
        while len(results2) < 5:
            _wait()
        self.assertEqual(results1, (([(True, 1)] * 3) + ([(True, 2)] * 2)))
        self.assertEqual(results2, (([(True, 2)] * 3) + ([(True, 3)] * 2)))
        b.wait_for_finished()

    def test_notify(self):
        cond = self.condtype()
        self._check_notify(cond)
        self._check_notify(cond)

    def test_timeout(self):
        cond = self.condtype()
        results = []
        N = 5

        def f():
            cond.acquire()
            t1 = time.monotonic()
            result = cond.wait(0.5)
            t2 = time.monotonic()
            cond.release()
            results.append(((t2 - t1), result))

        Bunch(f, N).wait_for_finished()
        self.assertEqual(len(results), N)
        for (dt, result) in results:
            self.assertTimeout(dt, 0.5)
            self.assertFalse(result)

    def test_waitfor(self):
        cond = self.condtype()
        state = 0

        def f():
            with cond:
                result = cond.wait_for((lambda: (state == 4)))
                self.assertTrue(result)
                self.assertEqual(state, 4)

        b = Bunch(f, 1)
        b.wait_for_started()
        for i in range(4):
            time.sleep(0.01)
            with cond:
                state += 1
                cond.notify()
        b.wait_for_finished()

    def test_waitfor_timeout(self):
        cond = self.condtype()
        state = 0
        success = []

        def f():
            with cond:
                dt = time.monotonic()
                result = cond.wait_for((lambda: (state == 4)), timeout=0.1)
                dt = time.monotonic() - dt
                self.assertFalse(result)
                self.assertTimeout(dt, 0.1)
                success.append(None)

        b = Bunch(f, 1)
        b.wait_for_started()
        for i in range(3):
            time.sleep(0.01)
            with cond:
                state += 1
                cond.notify()
        b.wait_for_finished()
        self.assertEqual(len(success), 1)


class BaseSemaphoreTests(BaseTestCase):
    "\n    Common tests for {bounded, unbounded} semaphore objects.\n    "

    def test_constructor(self):
        self.assertRaises(ValueError, self.semtype, value=(-1))
        self.assertRaises(ValueError, self.semtype, value=(-sys.maxsize))

    def test_acquire(self):
        sem = self.semtype(1)
        sem.acquire()
        sem.release()
        sem = self.semtype(2)
        sem.acquire()
        sem.acquire()
        sem.release()
        sem.release()

    def test_acquire_destroy(self):
        sem = self.semtype()
        sem.acquire()
        del sem

    def test_acquire_contended(self):
        sem = self.semtype(7)
        sem.acquire()
        N = 10
        sem_results = []
        results1 = []
        results2 = []
        phase_num = 0

        def f():
            sem_results.append(sem.acquire())
            results1.append(phase_num)
            sem_results.append(sem.acquire())
            results2.append(phase_num)

        b = Bunch(f, 10)
        b.wait_for_started()
        while (len(results1) + len(results2)) < 6:
            _wait()
        self.assertEqual((results1 + results2), ([0] * 6))
        phase_num = 1
        for i in range(7):
            sem.release()
        while (len(results1) + len(results2)) < 13:
            _wait()
        self.assertEqual(sorted((results1 + results2)), (([0] * 6) + ([1] * 7)))
        phase_num = 2
        for i in range(6):
            sem.release()
        while (len(results1) + len(results2)) < 19:
            _wait()
        self.assertEqual(
            sorted((results1 + results2)), ((([0] * 6) + ([1] * 7)) + ([2] * 6))
        )
        self.assertFalse(sem.acquire(False))
        sem.release()
        b.wait_for_finished()
        self.assertEqual(sem_results, ([True] * (((6 + 7) + 6) + 1)))

    def test_multirelease(self):
        sem = self.semtype(7)
        sem.acquire()
        results1 = []
        results2 = []
        phase_num = 0

        def f():
            sem.acquire()
            results1.append(phase_num)
            sem.acquire()
            results2.append(phase_num)

        b = Bunch(f, 10)
        b.wait_for_started()
        while (len(results1) + len(results2)) < 6:
            _wait()
        self.assertEqual((results1 + results2), ([0] * 6))
        phase_num = 1
        sem.release(7)
        while (len(results1) + len(results2)) < 13:
            _wait()
        self.assertEqual(sorted((results1 + results2)), (([0] * 6) + ([1] * 7)))
        phase_num = 2
        sem.release(6)
        while (len(results1) + len(results2)) < 19:
            _wait()
        self.assertEqual(
            sorted((results1 + results2)), ((([0] * 6) + ([1] * 7)) + ([2] * 6))
        )
        self.assertFalse(sem.acquire(False))
        sem.release()
        b.wait_for_finished()

    def test_try_acquire(self):
        sem = self.semtype(2)
        self.assertTrue(sem.acquire(False))
        self.assertTrue(sem.acquire(False))
        self.assertFalse(sem.acquire(False))
        sem.release()
        self.assertTrue(sem.acquire(False))

    def test_try_acquire_contended(self):
        sem = self.semtype(4)
        sem.acquire()
        results = []

        def f():
            results.append(sem.acquire(False))
            results.append(sem.acquire(False))

        Bunch(f, 5).wait_for_finished()
        self.assertEqual(sorted(results), (([False] * 7) + ([True] * 3)))

    def test_acquire_timeout(self):
        sem = self.semtype(2)
        self.assertRaises(ValueError, sem.acquire, False, timeout=1.0)
        self.assertTrue(sem.acquire(timeout=0.005))
        self.assertTrue(sem.acquire(timeout=0.005))
        self.assertFalse(sem.acquire(timeout=0.005))
        sem.release()
        self.assertTrue(sem.acquire(timeout=0.005))
        t = time.monotonic()
        self.assertFalse(sem.acquire(timeout=0.5))
        dt = time.monotonic() - t
        self.assertTimeout(dt, 0.5)

    def test_default_value(self):
        sem = self.semtype()
        sem.acquire()

        def f():
            sem.acquire()
            sem.release()

        b = Bunch(f, 1)
        b.wait_for_started()
        _wait()
        self.assertFalse(b.finished)
        sem.release()
        b.wait_for_finished()

    def test_with(self):
        sem = self.semtype(2)

        def _with(err=None):
            with sem:
                self.assertTrue(sem.acquire(False))
                sem.release()
                with sem:
                    self.assertFalse(sem.acquire(False))
                    if err:
                        raise err

        _with()
        self.assertTrue(sem.acquire(False))
        sem.release()
        self.assertRaises(TypeError, _with, TypeError)
        self.assertTrue(sem.acquire(False))
        sem.release()


class SemaphoreTests(BaseSemaphoreTests):
    "\n    Tests for unbounded semaphores.\n    "

    def test_release_unacquired(self):
        sem = self.semtype(1)
        sem.release()
        sem.acquire()
        sem.acquire()
        sem.release()


class BoundedSemaphoreTests(BaseSemaphoreTests):
    "\n    Tests for bounded semaphores.\n    "

    def test_release_unacquired(self):
        sem = self.semtype()
        self.assertRaises(ValueError, sem.release)
        sem.acquire()
        sem.release()
        self.assertRaises(ValueError, sem.release)


class BarrierTests(BaseTestCase):
    "\n    Tests for Barrier objects.\n    "
    N = 5
    defaultTimeout = 2.0

    def setUp(self):
        self.barrier = self.barriertype(self.N, timeout=self.defaultTimeout)

    def tearDown(self):
        self.barrier.abort()

    def run_threads(self, f):
        b = Bunch(f, (self.N - 1))
        f()
        b.wait_for_finished()

    def multipass(self, results, n):
        m = self.barrier.parties
        self.assertEqual(m, self.N)
        for i in range(n):
            results[0].append(True)
            self.assertEqual(len(results[1]), (i * m))
            self.barrier.wait()
            results[1].append(True)
            self.assertEqual(len(results[0]), ((i + 1) * m))
            self.barrier.wait()
        self.assertEqual(self.barrier.n_waiting, 0)
        self.assertFalse(self.barrier.broken)

    def test_barrier(self, passes=1):
        "\n        Test that a barrier is passed in lockstep\n        "
        results = [[], []]

        def f():
            self.multipass(results, passes)

        self.run_threads(f)

    def test_barrier_10(self):
        "\n        Test that a barrier works for 10 consecutive runs\n        "
        return self.test_barrier(10)

    def test_wait_return(self):
        "\n        test the return value from barrier.wait\n        "
        results = []

        def f():
            r = self.barrier.wait()
            results.append(r)

        self.run_threads(f)
        self.assertEqual(sum(results), sum(range(self.N)))

    def test_action(self):
        "\n        Test the 'action' callback\n        "
        results = []

        def action():
            results.append(True)

        barrier = self.barriertype(self.N, action)

        def f():
            barrier.wait()
            self.assertEqual(len(results), 1)

        self.run_threads(f)

    def test_abort(self):
        "\n        Test that an abort will put the barrier in a broken state\n        "
        results1 = []
        results2 = []

        def f():
            try:
                i = self.barrier.wait()
                if i == (self.N // 2):
                    raise RuntimeError
                self.barrier.wait()
                results1.append(True)
            except threading.BrokenBarrierError:
                results2.append(True)
            except RuntimeError:
                self.barrier.abort()
                pass

        self.run_threads(f)
        self.assertEqual(len(results1), 0)
        self.assertEqual(len(results2), (self.N - 1))
        self.assertTrue(self.barrier.broken)

    def test_reset(self):
        "\n        Test that a 'reset' on a barrier frees the waiting threads\n        "
        results1 = []
        results2 = []
        results3 = []

        def f():
            i = self.barrier.wait()
            if i == (self.N // 2):
                while self.barrier.n_waiting < (self.N - 1):
                    time.sleep(0.001)
                self.barrier.reset()
            else:
                try:
                    self.barrier.wait()
                    results1.append(True)
                except threading.BrokenBarrierError:
                    results2.append(True)
            self.barrier.wait()
            results3.append(True)

        self.run_threads(f)
        self.assertEqual(len(results1), 0)
        self.assertEqual(len(results2), (self.N - 1))
        self.assertEqual(len(results3), self.N)

    def test_abort_and_reset(self):
        "\n        Test that a barrier can be reset after being broken.\n        "
        results1 = []
        results2 = []
        results3 = []
        barrier2 = self.barriertype(self.N)

        def f():
            try:
                i = self.barrier.wait()
                if i == (self.N // 2):
                    raise RuntimeError
                self.barrier.wait()
                results1.append(True)
            except threading.BrokenBarrierError:
                results2.append(True)
            except RuntimeError:
                self.barrier.abort()
                pass
            if barrier2.wait() == (self.N // 2):
                self.barrier.reset()
            barrier2.wait()
            self.barrier.wait()
            results3.append(True)

        self.run_threads(f)
        self.assertEqual(len(results1), 0)
        self.assertEqual(len(results2), (self.N - 1))
        self.assertEqual(len(results3), self.N)

    def test_timeout(self):
        "\n        Test wait(timeout)\n        "

        def f():
            i = self.barrier.wait()
            if i == (self.N // 2):
                time.sleep(1.0)
            self.assertRaises(threading.BrokenBarrierError, self.barrier.wait, 0.5)

        self.run_threads(f)

    def test_default_timeout(self):
        "\n        Test the barrier's default timeout\n        "
        barrier = self.barriertype(self.N, timeout=0.3)

        def f():
            i = barrier.wait()
            if i == (self.N // 2):
                time.sleep(1.0)
            self.assertRaises(threading.BrokenBarrierError, barrier.wait)

        self.run_threads(f)

    def test_single_thread(self):
        b = self.barriertype(1)
        b.wait()
        b.wait()
