__all__ = ("Queue", "PriorityQueue", "LifoQueue", "QueueFull", "QueueEmpty")
import collections
import heapq
from . import locks
from . import mixins


class QueueEmpty(Exception):
    "Raised when Queue.get_nowait() is called on an empty Queue."
    pass


class QueueFull(Exception):
    "Raised when the Queue.put_nowait() method is called on a full Queue."
    pass


class Queue(mixins._LoopBoundMixin):
    "A queue, useful for coordinating producer and consumer coroutines.\n\n    If maxsize is less than or equal to zero, the queue size is infinite. If it\n    is an integer greater than 0, then \"await put()\" will block when the\n    queue reaches maxsize, until an item is removed by get().\n\n    Unlike the standard library Queue, you can reliably know this Queue's size\n    with qsize(), since your single-threaded asyncio application won't be\n    interrupted between calling qsize() and doing an operation on the Queue.\n    "

    def __init__(self, maxsize=0, *, loop=mixins._marker):
        super().__init__(loop=loop)
        self._maxsize = maxsize
        self._getters = collections.deque()
        self._putters = collections.deque()
        self._unfinished_tasks = 0
        self._finished = locks.Event()
        self._finished.set()
        self._init(maxsize)

    def _init(self, maxsize):
        self._queue = collections.deque()

    def _get(self):
        return self._queue.popleft()

    def _put(self, item):
        self._queue.append(item)

    def _wakeup_next(self, waiters):
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self):
        return f"<{type(self).__name__} at {id(self):#x} {self._format()}>"

    def __str__(self):
        return f"<{type(self).__name__} {self._format()}>"

    def __class_getitem__(cls, type):
        return cls

    def _format(self):
        result = f"maxsize={self._maxsize!r}"
        if getattr(self, "_queue", None):
            result += f" _queue={list(self._queue)!r}"
        if self._getters:
            result += f" _getters[{len(self._getters)}]"
        if self._putters:
            result += f" _putters[{len(self._putters)}]"
        if self._unfinished_tasks:
            result += f" tasks={self._unfinished_tasks}"
        return result

    def qsize(self):
        "Number of items in the queue."
        return len(self._queue)

    @property
    def maxsize(self):
        "Number of items allowed in the queue."
        return self._maxsize

    def empty(self):
        "Return True if the queue is empty, False otherwise."
        return not self._queue

    def full(self):
        "Return True if there are maxsize items in the queue.\n\n        Note: if the Queue was initialized with maxsize=0 (the default),\n        then full() is never True.\n        "
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

    async def put(self, item):
        "Put an item into the queue.\n\n        Put an item into the queue. If the queue is full, wait until a free\n        slot is available before adding item.\n        "
        while self.full():
            putter = self._get_loop().create_future()
            self._putters.append(putter)
            try:
                (await putter)
            except:
                putter.cancel()
                try:
                    self._putters.remove(putter)
                except ValueError:
                    pass
                if (not self.full()) and (not putter.cancelled()):
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(item)

    def put_nowait(self, item):
        "Put an item into the queue without blocking.\n\n        If no free slot is immediately available, raise QueueFull.\n        "
        if self.full():
            raise QueueFull
        self._put(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    async def get(self):
        "Remove and return an item from the queue.\n\n        If queue is empty, wait until an item is available.\n        "
        while self.empty():
            getter = self._get_loop().create_future()
            self._getters.append(getter)
            try:
                (await getter)
            except:
                getter.cancel()
                try:
                    self._getters.remove(getter)
                except ValueError:
                    pass
                if (not self.empty()) and (not getter.cancelled()):
                    self._wakeup_next(self._getters)
                raise
        return self.get_nowait()

    def get_nowait(self):
        "Remove and return an item from the queue.\n\n        Return an item if one is immediately available, else raise QueueEmpty.\n        "
        if self.empty():
            raise QueueEmpty
        item = self._get()
        self._wakeup_next(self._putters)
        return item

    def task_done(self):
        "Indicate that a formerly enqueued task is complete.\n\n        Used by queue consumers. For each get() used to fetch a task,\n        a subsequent call to task_done() tells the queue that the processing\n        on the task is complete.\n\n        If a join() is currently blocking, it will resume when all items have\n        been processed (meaning that a task_done() call was received for every\n        item that had been put() into the queue).\n\n        Raises ValueError if called more times than there were items placed in\n        the queue.\n        "
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self):
        "Block until all items in the queue have been gotten and processed.\n\n        The count of unfinished tasks goes up whenever an item is added to the\n        queue. The count goes down whenever a consumer calls task_done() to\n        indicate that the item was retrieved and all work on it is complete.\n        When the count of unfinished tasks drops to zero, join() unblocks.\n        "
        if self._unfinished_tasks > 0:
            (await self._finished.wait())


class PriorityQueue(Queue):
    "A subclass of Queue; retrieves entries in priority order (lowest first).\n\n    Entries are typically tuples of the form: (priority number, data).\n    "

    def _init(self, maxsize):
        self._queue = []

    def _put(self, item, heappush=heapq.heappush):
        heappush(self._queue, item)

    def _get(self, heappop=heapq.heappop):
        return heappop(self._queue)


class LifoQueue(Queue):
    "A subclass of Queue that retrieves most recently added entries first."

    def _init(self, maxsize):
        self._queue = []

    def _put(self, item):
        self._queue.append(item)

    def _get(self):
        return self._queue.pop()
