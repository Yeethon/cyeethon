import itertools
import random
import threading
import time
import unittest
import weakref
from test.support import import_helper
from test.support import threading_helper

py_queue = import_helper.import_fresh_module("queue", blocked=["_queue"])
c_queue = import_helper.import_fresh_module("queue", fresh=["_queue"])
need_c_queue = unittest.skipUnless(c_queue, "No _queue module found")
QUEUE_SIZE = 5


def qfull(q):
    return (q.maxsize > 0) and (q.qsize() == q.maxsize)


class _TriggerThread(threading.Thread):
    def __init__(self, fn, args):
        self.fn = fn
        self.args = args
        self.startedEvent = threading.Event()
        threading.Thread.__init__(self)

    def run(self):
        time.sleep(0.1)
        self.startedEvent.set()
        self.fn(*self.args)


class BlockingTestMixin:
    def do_blocking_test(self, block_func, block_args, trigger_func, trigger_args):
        thread = _TriggerThread(trigger_func, trigger_args)
        thread.start()
        try:
            self.result = block_func(*block_args)
            if not thread.startedEvent.is_set():
                self.fail(("blocking function %r appeared not to block" % block_func))
            return self.result
        finally:
            threading_helper.join_thread(thread)

    def do_exceptional_blocking_test(
        self,
        block_func,
        block_args,
        trigger_func,
        trigger_args,
        expected_exception_class,
    ):
        thread = _TriggerThread(trigger_func, trigger_args)
        thread.start()
        try:
            try:
                block_func(*block_args)
            except expected_exception_class:
                raise
            else:
                self.fail(("expected exception of kind %r" % expected_exception_class))
        finally:
            threading_helper.join_thread(thread)
            if not thread.startedEvent.is_set():
                self.fail("trigger thread ended but event never set")


class BaseQueueTestMixin(BlockingTestMixin):
    def setUp(self):
        self.cum = 0
        self.cumlock = threading.Lock()

    def basic_queue_test(self, q):
        if q.qsize():
            raise RuntimeError("Call this function with an empty queue")
        self.assertTrue(q.empty())
        self.assertFalse(q.full())
        q.put(111)
        q.put(333)
        q.put(222)
        target_order = dict(
            Queue=[111, 333, 222],
            LifoQueue=[222, 333, 111],
            PriorityQueue=[111, 222, 333],
        )
        actual_order = [q.get(), q.get(), q.get()]
        self.assertEqual(
            actual_order,
            target_order[q.__class__.__name__],
            "Didn't seem to queue the correct data!",
        )
        for i in range((QUEUE_SIZE - 1)):
            q.put(i)
            self.assertTrue(q.qsize(), "Queue should not be empty")
        self.assertTrue((not qfull(q)), "Queue should not be full")
        last = 2 * QUEUE_SIZE
        full = (3 * 2) * QUEUE_SIZE
        q.put(last)
        self.assertTrue(qfull(q), "Queue should be full")
        self.assertFalse(q.empty())
        self.assertTrue(q.full())
        try:
            q.put(full, block=0)
            self.fail("Didn't appear to block with a full queue")
        except self.queue.Full:
            pass
        try:
            q.put(full, timeout=0.01)
            self.fail("Didn't appear to time-out with a full queue")
        except self.queue.Full:
            pass
        self.do_blocking_test(q.put, (full,), q.get, ())
        self.do_blocking_test(q.put, (full, True, 10), q.get, ())
        for i in range(QUEUE_SIZE):
            q.get()
        self.assertTrue((not q.qsize()), "Queue should be empty")
        try:
            q.get(block=0)
            self.fail("Didn't appear to block with an empty queue")
        except self.queue.Empty:
            pass
        try:
            q.get(timeout=0.01)
            self.fail("Didn't appear to time-out with an empty queue")
        except self.queue.Empty:
            pass
        self.do_blocking_test(q.get, (), q.put, ("empty",))
        self.do_blocking_test(q.get, (True, 10), q.put, ("empty",))

    def worker(self, q):
        while True:
            x = q.get()
            if x < 0:
                q.task_done()
                return
            with self.cumlock:
                self.cum += x
            q.task_done()

    def queue_join_test(self, q):
        self.cum = 0
        threads = []
        for i in (0, 1):
            thread = threading.Thread(target=self.worker, args=(q,))
            thread.start()
            threads.append(thread)
        for i in range(100):
            q.put(i)
        q.join()
        self.assertEqual(
            self.cum,
            sum(range(100)),
            "q.join() did not block until all tasks were done",
        )
        for i in (0, 1):
            q.put((-1))
        q.join()
        for thread in threads:
            thread.join()

    def test_queue_task_done(self):
        q = self.type2test()
        try:
            q.task_done()
        except ValueError:
            pass
        else:
            self.fail("Did not detect task count going negative")

    def test_queue_join(self):
        q = self.type2test()
        self.queue_join_test(q)
        self.queue_join_test(q)
        try:
            q.task_done()
        except ValueError:
            pass
        else:
            self.fail("Did not detect task count going negative")

    def test_basic(self):
        q = self.type2test(QUEUE_SIZE)
        self.basic_queue_test(q)
        self.basic_queue_test(q)

    def test_negative_timeout_raises_exception(self):
        q = self.type2test(QUEUE_SIZE)
        with self.assertRaises(ValueError):
            q.put(1, timeout=(-1))
        with self.assertRaises(ValueError):
            q.get(1, timeout=(-1))

    def test_nowait(self):
        q = self.type2test(QUEUE_SIZE)
        for i in range(QUEUE_SIZE):
            q.put_nowait(1)
        with self.assertRaises(self.queue.Full):
            q.put_nowait(1)
        for i in range(QUEUE_SIZE):
            q.get_nowait()
        with self.assertRaises(self.queue.Empty):
            q.get_nowait()

    def test_shrinking_queue(self):
        q = self.type2test(3)
        q.put(1)
        q.put(2)
        q.put(3)
        with self.assertRaises(self.queue.Full):
            q.put_nowait(4)
        self.assertEqual(q.qsize(), 3)
        q.maxsize = 2
        with self.assertRaises(self.queue.Full):
            q.put_nowait(4)


class QueueTest(BaseQueueTestMixin):
    def setUp(self):
        self.type2test = self.queue.Queue
        super().setUp()


class PyQueueTest(QueueTest, unittest.TestCase):
    queue = py_queue


@need_c_queue
class CQueueTest(QueueTest, unittest.TestCase):
    queue = c_queue


class LifoQueueTest(BaseQueueTestMixin):
    def setUp(self):
        self.type2test = self.queue.LifoQueue
        super().setUp()


class PyLifoQueueTest(LifoQueueTest, unittest.TestCase):
    queue = py_queue


@need_c_queue
class CLifoQueueTest(LifoQueueTest, unittest.TestCase):
    queue = c_queue


class PriorityQueueTest(BaseQueueTestMixin):
    def setUp(self):
        self.type2test = self.queue.PriorityQueue
        super().setUp()


class PyPriorityQueueTest(PriorityQueueTest, unittest.TestCase):
    queue = py_queue


@need_c_queue
class CPriorityQueueTest(PriorityQueueTest, unittest.TestCase):
    queue = c_queue


class FailingQueueException(Exception):
    pass


class FailingQueueTest(BlockingTestMixin):
    def setUp(self):
        Queue = self.queue.Queue

        class FailingQueue(Queue):
            def __init__(self, *args):
                self.fail_next_put = False
                self.fail_next_get = False
                Queue.__init__(self, *args)

            def _put(self, item):
                if self.fail_next_put:
                    self.fail_next_put = False
                    raise FailingQueueException("You Lose")
                return Queue._put(self, item)

            def _get(self):
                if self.fail_next_get:
                    self.fail_next_get = False
                    raise FailingQueueException("You Lose")
                return Queue._get(self)

        self.FailingQueue = FailingQueue
        super().setUp()

    def failing_queue_test(self, q):
        if q.qsize():
            raise RuntimeError("Call this function with an empty queue")
        for i in range((QUEUE_SIZE - 1)):
            q.put(i)
        q.fail_next_put = True
        try:
            q.put("oops", block=0)
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        q.fail_next_put = True
        try:
            q.put("oops", timeout=0.1)
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        q.put("last")
        self.assertTrue(qfull(q), "Queue should be full")
        q.fail_next_put = True
        try:
            self.do_blocking_test(q.put, ("full",), q.get, ())
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        q.put("last")
        q.fail_next_put = True
        try:
            self.do_exceptional_blocking_test(
                q.put, ("full", True, 10), q.get, (), FailingQueueException
            )
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        q.put("last")
        self.assertTrue(qfull(q), "Queue should be full")
        q.get()
        self.assertTrue((not qfull(q)), "Queue should not be full")
        q.put("last")
        self.assertTrue(qfull(q), "Queue should be full")
        self.do_blocking_test(q.put, ("full",), q.get, ())
        for i in range(QUEUE_SIZE):
            q.get()
        self.assertTrue((not q.qsize()), "Queue should be empty")
        q.put("first")
        q.fail_next_get = True
        try:
            q.get()
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        self.assertTrue(q.qsize(), "Queue should not be empty")
        q.fail_next_get = True
        try:
            q.get(timeout=0.1)
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        self.assertTrue(q.qsize(), "Queue should not be empty")
        q.get()
        self.assertTrue((not q.qsize()), "Queue should be empty")
        q.fail_next_get = True
        try:
            self.do_exceptional_blocking_test(
                q.get, (), q.put, ("empty",), FailingQueueException
            )
            self.fail("The queue didn't fail when it should have")
        except FailingQueueException:
            pass
        self.assertTrue(q.qsize(), "Queue should not be empty")
        q.get()
        self.assertTrue((not q.qsize()), "Queue should be empty")

    def test_failing_queue(self):
        q = self.FailingQueue(QUEUE_SIZE)
        self.failing_queue_test(q)
        self.failing_queue_test(q)


class PyFailingQueueTest(FailingQueueTest, unittest.TestCase):
    queue = py_queue


@need_c_queue
class CFailingQueueTest(FailingQueueTest, unittest.TestCase):
    queue = c_queue


class BaseSimpleQueueTest:
    def setUp(self):
        self.q = self.type2test()

    def feed(self, q, seq, rnd):
        while True:
            try:
                val = seq.pop()
            except IndexError:
                return
            q.put(val)
            if rnd.random() > 0.5:
                time.sleep((rnd.random() * 0.001))

    def consume(self, q, results, sentinel):
        while True:
            val = q.get()
            if val == sentinel:
                return
            results.append(val)

    def consume_nonblock(self, q, results, sentinel):
        while True:
            while True:
                try:
                    val = q.get(block=False)
                except self.queue.Empty:
                    time.sleep(1e-05)
                else:
                    break
            if val == sentinel:
                return
            results.append(val)

    def consume_timeout(self, q, results, sentinel):
        while True:
            while True:
                try:
                    val = q.get(timeout=1e-05)
                except self.queue.Empty:
                    pass
                else:
                    break
            if val == sentinel:
                return
            results.append(val)

    def run_threads(self, n_feeders, n_consumers, q, inputs, feed_func, consume_func):
        results = []
        sentinel = None
        seq = inputs + ([sentinel] * n_consumers)
        seq.reverse()
        rnd = random.Random(42)
        exceptions = []

        def log_exceptions(f):
            def wrapper(*args, **kwargs):
                try:
                    f(*args, **kwargs)
                except BaseException as e:
                    exceptions.append(e)

            return wrapper

        feeders = [
            threading.Thread(target=log_exceptions(feed_func), args=(q, seq, rnd))
            for i in range(n_feeders)
        ]
        consumers = [
            threading.Thread(
                target=log_exceptions(consume_func), args=(q, results, sentinel)
            )
            for i in range(n_consumers)
        ]
        with threading_helper.start_threads((feeders + consumers)):
            pass
        self.assertFalse(exceptions)
        self.assertTrue(q.empty())
        self.assertEqual(q.qsize(), 0)
        return results

    def test_basic(self):
        q = self.q
        self.assertTrue(q.empty())
        self.assertEqual(q.qsize(), 0)
        q.put(1)
        self.assertFalse(q.empty())
        self.assertEqual(q.qsize(), 1)
        q.put(2)
        q.put_nowait(3)
        q.put(4)
        self.assertFalse(q.empty())
        self.assertEqual(q.qsize(), 4)
        self.assertEqual(q.get(), 1)
        self.assertEqual(q.qsize(), 3)
        self.assertEqual(q.get_nowait(), 2)
        self.assertEqual(q.qsize(), 2)
        self.assertEqual(q.get(block=False), 3)
        self.assertFalse(q.empty())
        self.assertEqual(q.qsize(), 1)
        self.assertEqual(q.get(timeout=0.1), 4)
        self.assertTrue(q.empty())
        self.assertEqual(q.qsize(), 0)
        with self.assertRaises(self.queue.Empty):
            q.get(block=False)
        with self.assertRaises(self.queue.Empty):
            q.get(timeout=0.001)
        with self.assertRaises(self.queue.Empty):
            q.get_nowait()
        self.assertTrue(q.empty())
        self.assertEqual(q.qsize(), 0)

    def test_negative_timeout_raises_exception(self):
        q = self.q
        q.put(1)
        with self.assertRaises(ValueError):
            q.get(timeout=(-1))

    def test_order(self):
        q = self.q
        inputs = list(range(100))
        results = self.run_threads(1, 1, q, inputs, self.feed, self.consume)
        self.assertEqual(results, inputs)

    def test_many_threads(self):
        N = 50
        q = self.q
        inputs = list(range(10000))
        results = self.run_threads(N, N, q, inputs, self.feed, self.consume)
        self.assertEqual(sorted(results), inputs)

    def test_many_threads_nonblock(self):
        N = 50
        q = self.q
        inputs = list(range(10000))
        results = self.run_threads(N, N, q, inputs, self.feed, self.consume_nonblock)
        self.assertEqual(sorted(results), inputs)

    def test_many_threads_timeout(self):
        N = 50
        q = self.q
        inputs = list(range(1000))
        results = self.run_threads(N, N, q, inputs, self.feed, self.consume_timeout)
        self.assertEqual(sorted(results), inputs)

    def test_references(self):
        class C:
            pass

        N = 20
        q = self.q
        for i in range(N):
            q.put(C())
        for i in range(N):
            wr = weakref.ref(q.get())
            self.assertIsNone(wr())


class PySimpleQueueTest(BaseSimpleQueueTest, unittest.TestCase):
    queue = py_queue

    def setUp(self):
        self.type2test = self.queue._PySimpleQueue
        super().setUp()


@need_c_queue
class CSimpleQueueTest(BaseSimpleQueueTest, unittest.TestCase):
    queue = c_queue

    def setUp(self):
        self.type2test = self.queue.SimpleQueue
        super().setUp()

    def test_is_default(self):
        self.assertIs(self.type2test, self.queue.SimpleQueue)
        self.assertIs(self.type2test, self.queue.SimpleQueue)

    def test_reentrancy(self):
        q = self.q
        gen = itertools.count()
        N = 10000
        results = []

        class Circular(object):
            def __init__(self):
                self.circular = self

            def __del__(self):
                q.put(next(gen))

        while True:
            o = Circular()
            q.put(next(gen))
            del o
            results.append(q.get())
            if results[(-1)] >= N:
                break
        self.assertEqual(results, list(range((N + 1))))


if __name__ == "__main__":
    unittest.main()
