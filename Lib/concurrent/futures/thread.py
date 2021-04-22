"Implements ThreadPoolExecutor."
__author__ = "Brian Quinlan (brian@sweetapp.com)"
from concurrent.futures import _base
import itertools
import queue
import threading
import types
import weakref
import os

_threads_queues = weakref.WeakKeyDictionary()
_shutdown = False
_global_shutdown_lock = threading.Lock()


def _python_exit():
    global _shutdown
    with _global_shutdown_lock:
        _shutdown = True
    items = list(_threads_queues.items())
    for (t, q) in items:
        q.put(None)
    for (t, q) in items:
        t.join()


threading._register_atexit(_python_exit)


class _WorkItem(object):
    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return
        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as exc:
            self.future.set_exception(exc)
            self = None
        else:
            self.future.set_result(result)

    __class_getitem__ = classmethod(types.GenericAlias)


def _worker(executor_reference, work_queue, initializer, initargs):
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical("Exception in initializer:", exc_info=True)
            executor = executor_reference()
            if executor is not None:
                executor._initializer_failed()
            return
    try:
        while True:
            work_item = work_queue.get(block=True)
            if work_item is not None:
                work_item.run()
                del work_item
                executor = executor_reference()
                if executor is not None:
                    executor._idle_semaphore.release()
                del executor
                continue
            executor = executor_reference()
            if _shutdown or (executor is None) or executor._shutdown:
                if executor is not None:
                    executor._shutdown = True
                work_queue.put(None)
                return
            del executor
    except BaseException:
        _base.LOGGER.critical("Exception in worker", exc_info=True)


class BrokenThreadPool(_base.BrokenExecutor):
    "\n    Raised when a worker thread in a ThreadPoolExecutor failed initializing.\n    "


class ThreadPoolExecutor(_base.Executor):
    _counter = itertools.count().__next__

    def __init__(
        self, max_workers=None, thread_name_prefix="", initializer=None, initargs=()
    ):
        "Initializes a new ThreadPoolExecutor instance.\n\n        Args:\n            max_workers: The maximum number of threads that can be used to\n                execute the given calls.\n            thread_name_prefix: An optional name prefix to give our threads.\n            initializer: A callable used to initialize worker threads.\n            initargs: A tuple of arguments to pass to the initializer.\n        "
        if max_workers is None:
            max_workers = min(32, ((os.cpu_count() or 1) + 4))
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        if (initializer is not None) and (not callable(initializer)):
            raise TypeError("initializer must be a callable")
        self._max_workers = max_workers
        self._work_queue = queue.SimpleQueue()
        self._idle_semaphore = threading.Semaphore(0)
        self._threads = set()
        self._broken = False
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._thread_name_prefix = thread_name_prefix or (
            "ThreadPoolExecutor-%d" % self._counter()
        )
        self._initializer = initializer
        self._initargs = initargs

    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock, _global_shutdown_lock:
            if self._broken:
                raise BrokenThreadPool(self._broken)
            if self._shutdown:
                raise RuntimeError("cannot schedule new futures after shutdown")
            if _shutdown:
                raise RuntimeError(
                    "cannot schedule new futures after interpreter shutdown"
                )
            f = _base.Future()
            w = _WorkItem(f, fn, args, kwargs)
            self._work_queue.put(w)
            self._adjust_thread_count()
            return f

    submit.__doc__ = _base.Executor.submit.__doc__

    def _adjust_thread_count(self):
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % ((self._thread_name_prefix or self), num_threads)
            t = threading.Thread(
                name=thread_name,
                target=_worker,
                args=(
                    weakref.ref(self, weakref_cb),
                    self._work_queue,
                    self._initializer,
                    self._initargs,
                ),
            )
            t.start()
            self._threads.add(t)
            _threads_queues[t] = self._work_queue

    def _initializer_failed(self):
        with self._shutdown_lock:
            self._broken = (
                "A thread initializer failed, the thread pool is not usable anymore"
            )
            while True:
                try:
                    work_item = self._work_queue.get_nowait()
                except queue.Empty:
                    break
                if work_item is not None:
                    work_item.future.set_exception(BrokenThreadPool(self._broken))

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_lock:
            self._shutdown = True
            if cancel_futures:
                while True:
                    try:
                        work_item = self._work_queue.get_nowait()
                    except queue.Empty:
                        break
                    if work_item is not None:
                        work_item.future.cancel()
            self._work_queue.put(None)
        if wait:
            for t in self._threads:
                t.join()

    shutdown.__doc__ = _base.Executor.shutdown.__doc__
