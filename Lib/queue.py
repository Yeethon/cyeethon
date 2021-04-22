"A multi-producer, multi-consumer queue."
import threading
import types
from collections import deque
from heapq import heappush, heappop
from time import monotonic as time

try:
    from _queue import SimpleQueue
except ImportError:
    SimpleQueue = None
__all__ = ["Empty", "Full", "Queue", "PriorityQueue", "LifoQueue", "SimpleQueue"]
try:
    from _queue import Empty
except ImportError:

    class Empty(Exception):
        "Exception raised by Queue.get(block=0)/get_nowait()."
        pass


class Full(Exception):
    "Exception raised by Queue.put(block=0)/put_nowait()."
    pass


class Queue:
    "Create a queue object with a given maximum size.\n\n    If maxsize is <= 0, the queue size is infinite.\n    "

    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self._init(maxsize)
        self.mutex = threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    def task_done(self):
        "Indicate that a formerly enqueued task is complete.\n\n        Used by Queue consumer threads.  For each get() used to fetch a task,\n        a subsequent call to task_done() tells the queue that the processing\n        on the task is complete.\n\n        If a join() is currently blocking, it will resume when all items\n        have been processed (meaning that a task_done() call was received\n        for every item that had been put() into the queue).\n\n        Raises a ValueError if called more times than there were items\n        placed in the queue.\n        "
        with self.all_tasks_done:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError("task_done() called too many times")
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished

    def join(self):
        "Blocks until all items in the Queue have been gotten and processed.\n\n        The count of unfinished tasks goes up whenever an item is added to the\n        queue. The count goes down whenever a consumer thread calls task_done()\n        to indicate the item was retrieved and all work on it is complete.\n\n        When the count of unfinished tasks drops to zero, join() unblocks.\n        "
        with self.all_tasks_done:
            while self.unfinished_tasks:
                self.all_tasks_done.wait()

    def qsize(self):
        "Return the approximate size of the queue (not reliable!)."
        with self.mutex:
            return self._qsize()

    def empty(self):
        "Return True if the queue is empty, False otherwise (not reliable!).\n\n        This method is likely to be removed at some point.  Use qsize() == 0\n        as a direct substitute, but be aware that either approach risks a race\n        condition where a queue can grow before the result of empty() or\n        qsize() can be used.\n\n        To create code that needs to wait for all queued tasks to be\n        completed, the preferred technique is to use the join() method.\n        "
        with self.mutex:
            return not self._qsize()

    def full(self):
        "Return True if the queue is full, False otherwise (not reliable!).\n\n        This method is likely to be removed at some point.  Use qsize() >= n\n        as a direct substitute, but be aware that either approach risks a race\n        condition where a queue can shrink before the result of full() or\n        qsize() can be used.\n        "
        with self.mutex:
            return 0 < self.maxsize <= self._qsize()

    def put(self, item, block=True, timeout=None):
        "Put an item into the queue.\n\n        If optional args 'block' is true and 'timeout' is None (the default),\n        block if necessary until a free slot is available. If 'timeout' is\n        a non-negative number, it blocks at most 'timeout' seconds and raises\n        the Full exception if no free slot was available within that time.\n        Otherwise ('block' is false), put an item on the queue if a free slot\n        is immediately available, else raise the Full exception ('timeout'\n        is ignored in that case).\n        "
        with self.not_full:
            if self.maxsize > 0:
                if not block:
                    if self._qsize() >= self.maxsize:
                        raise Full
                elif timeout is None:
                    while self._qsize() >= self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    endtime = time() + timeout
                    while self._qsize() >= self.maxsize:
                        remaining = endtime - time()
                        if remaining <= 0.0:
                            raise Full
                        self.not_full.wait(remaining)
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()

    def get(self, block=True, timeout=None):
        "Remove and return an item from the queue.\n\n        If optional args 'block' is true and 'timeout' is None (the default),\n        block if necessary until an item is available. If 'timeout' is\n        a non-negative number, it blocks at most 'timeout' seconds and raises\n        the Empty exception if no item was available within that time.\n        Otherwise ('block' is false), return an item if one is immediately\n        available, else raise the Empty exception ('timeout' is ignored\n        in that case).\n        "
        with self.not_empty:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while not self._qsize():
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._get()
            self.not_full.notify()
            return item

    def put_nowait(self, item):
        "Put an item into the queue without blocking.\n\n        Only enqueue the item if a free slot is immediately available.\n        Otherwise raise the Full exception.\n        "
        return self.put(item, block=False)

    def get_nowait(self):
        "Remove and return an item from the queue without blocking.\n\n        Only get an item if one is immediately available. Otherwise\n        raise the Empty exception.\n        "
        return self.get(block=False)

    def _init(self, maxsize):
        self.queue = deque()

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.popleft()

    __class_getitem__ = classmethod(types.GenericAlias)


class PriorityQueue(Queue):
    "Variant of Queue that retrieves open entries in priority order (lowest first).\n\n    Entries are typically tuples of the form:  (priority number, data).\n    "

    def _init(self, maxsize):
        self.queue = []

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        heappush(self.queue, item)

    def _get(self):
        return heappop(self.queue)


class LifoQueue(Queue):
    "Variant of Queue that retrieves most recently added entries first."

    def _init(self, maxsize):
        self.queue = []

    def _qsize(self):
        return len(self.queue)

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()


class _PySimpleQueue:
    "Simple, unbounded FIFO queue.\n\n    This pure Python implementation is not reentrant.\n    "

    def __init__(self):
        self._queue = deque()
        self._count = threading.Semaphore(0)

    def put(self, item, block=True, timeout=None):
        "Put the item on the queue.\n\n        The optional 'block' and 'timeout' arguments are ignored, as this method\n        never blocks.  They are provided for compatibility with the Queue class.\n        "
        self._queue.append(item)
        self._count.release()

    def get(self, block=True, timeout=None):
        "Remove and return an item from the queue.\n\n        If optional args 'block' is true and 'timeout' is None (the default),\n        block if necessary until an item is available. If 'timeout' is\n        a non-negative number, it blocks at most 'timeout' seconds and raises\n        the Empty exception if no item was available within that time.\n        Otherwise ('block' is false), return an item if one is immediately\n        available, else raise the Empty exception ('timeout' is ignored\n        in that case).\n        "
        if (timeout is not None) and (timeout < 0):
            raise ValueError("'timeout' must be a non-negative number")
        if not self._count.acquire(block, timeout):
            raise Empty
        return self._queue.popleft()

    def put_nowait(self, item):
        "Put an item into the queue without blocking.\n\n        This is exactly equivalent to `put(item)` and is only provided\n        for compatibility with the Queue class.\n        "
        return self.put(item, block=False)

    def get_nowait(self):
        "Remove and return an item from the queue without blocking.\n\n        Only get an item if one is immediately available. Otherwise\n        raise the Empty exception.\n        "
        return self.get(block=False)

    def empty(self):
        "Return True if the queue is empty, False otherwise (not reliable!)."
        return len(self._queue) == 0

    def qsize(self):
        "Return the approximate size of the queue (not reliable!)."
        return len(self._queue)

    __class_getitem__ = classmethod(types.GenericAlias)


if SimpleQueue is None:
    SimpleQueue = _PySimpleQueue
