"Synchronization primitives."
__all__ = ("Lock", "Event", "Condition", "Semaphore", "BoundedSemaphore")
import collections
from . import exceptions
from . import mixins


class _ContextManagerMixin:
    async def __aenter__(self):
        (await self.acquire())
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.release()


class Lock(_ContextManagerMixin, mixins._LoopBoundMixin):
    "Primitive lock objects.\n\n    A primitive lock is a synchronization primitive that is not owned\n    by a particular coroutine when locked.  A primitive lock is in one\n    of two states, 'locked' or 'unlocked'.\n\n    It is created in the unlocked state.  It has two basic methods,\n    acquire() and release().  When the state is unlocked, acquire()\n    changes the state to locked and returns immediately.  When the\n    state is locked, acquire() blocks until a call to release() in\n    another coroutine changes it to unlocked, then the acquire() call\n    resets it to locked and returns.  The release() method should only\n    be called in the locked state; it changes the state to unlocked\n    and returns immediately.  If an attempt is made to release an\n    unlocked lock, a RuntimeError will be raised.\n\n    When more than one coroutine is blocked in acquire() waiting for\n    the state to turn to unlocked, only one coroutine proceeds when a\n    release() call resets the state to unlocked; first coroutine which\n    is blocked in acquire() is being processed.\n\n    acquire() is a coroutine and should be called with 'await'.\n\n    Locks also support the asynchronous context management protocol.\n    'async with lock' statement should be used.\n\n    Usage:\n\n        lock = Lock()\n        ...\n        await lock.acquire()\n        try:\n            ...\n        finally:\n            lock.release()\n\n    Context manager usage:\n\n        lock = Lock()\n        ...\n        async with lock:\n             ...\n\n    Lock objects can be tested for locking state:\n\n        if not lock.locked():\n           await lock.acquire()\n        else:\n           # lock is acquired\n           ...\n\n    "

    def __init__(self, *, loop=mixins._marker):
        super().__init__(loop=loop)
        self._waiters = None
        self._locked = False

    def __repr__(self):
        res = super().__repr__()
        extra = "locked" if self._locked else "unlocked"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:(- 1)]} [{extra}]>"

    def locked(self):
        "Return True if lock is acquired."
        return self._locked

    async def acquire(self):
        "Acquire a lock.\n\n        This method blocks until the lock is unlocked, then sets it to\n        locked and returns True.\n        "
        if (not self._locked) and (
            (self._waiters is None) or all((w.cancelled() for w in self._waiters))
        ):
            self._locked = True
            return True
        if self._waiters is None:
            self._waiters = collections.deque()
        fut = self._get_loop().create_future()
        self._waiters.append(fut)
        try:
            try:
                (await fut)
            finally:
                self._waiters.remove(fut)
        except exceptions.CancelledError:
            if not self._locked:
                self._wake_up_first()
            raise
        self._locked = True
        return True

    def release(self):
        "Release a lock.\n\n        When the lock is locked, reset it to unlocked, and return.\n        If any other coroutines are blocked waiting for the lock to become\n        unlocked, allow exactly one of them to proceed.\n\n        When invoked on an unlocked lock, a RuntimeError is raised.\n\n        There is no return value.\n        "
        if self._locked:
            self._locked = False
            self._wake_up_first()
        else:
            raise RuntimeError("Lock is not acquired.")

    def _wake_up_first(self):
        "Wake up the first waiter if it isn't done."
        if not self._waiters:
            return
        try:
            fut = next(iter(self._waiters))
        except StopIteration:
            return
        if not fut.done():
            fut.set_result(True)


class Event(mixins._LoopBoundMixin):
    "Asynchronous equivalent to threading.Event.\n\n    Class implementing event objects. An event manages a flag that can be set\n    to true with the set() method and reset to false with the clear() method.\n    The wait() method blocks until the flag is true. The flag is initially\n    false.\n    "

    def __init__(self, *, loop=mixins._marker):
        super().__init__(loop=loop)
        self._waiters = collections.deque()
        self._value = False

    def __repr__(self):
        res = super().__repr__()
        extra = "set" if self._value else "unset"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:(- 1)]} [{extra}]>"

    def is_set(self):
        "Return True if and only if the internal flag is true."
        return self._value

    def set(self):
        "Set the internal flag to true. All coroutines waiting for it to\n        become true are awakened. Coroutine that call wait() once the flag is\n        true will not block at all.\n        "
        if not self._value:
            self._value = True
            for fut in self._waiters:
                if not fut.done():
                    fut.set_result(True)

    def clear(self):
        "Reset the internal flag to false. Subsequently, coroutines calling\n        wait() will block until set() is called to set the internal flag\n        to true again."
        self._value = False

    async def wait(self):
        "Block until the internal flag is true.\n\n        If the internal flag is true on entry, return True\n        immediately.  Otherwise, block until another coroutine calls\n        set() to set the flag to true, then return True.\n        "
        if self._value:
            return True
        fut = self._get_loop().create_future()
        self._waiters.append(fut)
        try:
            (await fut)
            return True
        finally:
            self._waiters.remove(fut)


class Condition(_ContextManagerMixin, mixins._LoopBoundMixin):
    "Asynchronous equivalent to threading.Condition.\n\n    This class implements condition variable objects. A condition variable\n    allows one or more coroutines to wait until they are notified by another\n    coroutine.\n\n    A new Lock object is created and used as the underlying lock.\n    "

    def __init__(self, lock=None, *, loop=mixins._marker):
        super().__init__(loop=loop)
        if lock is None:
            lock = Lock()
        elif lock._loop is not self._get_loop():
            raise ValueError("loop argument must agree with lock")
        self._lock = lock
        self.locked = lock.locked
        self.acquire = lock.acquire
        self.release = lock.release
        self._waiters = collections.deque()

    def __repr__(self):
        res = super().__repr__()
        extra = "locked" if self.locked() else "unlocked"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:(- 1)]} [{extra}]>"

    async def wait(self):
        "Wait until notified.\n\n        If the calling coroutine has not acquired the lock when this\n        method is called, a RuntimeError is raised.\n\n        This method releases the underlying lock, and then blocks\n        until it is awakened by a notify() or notify_all() call for\n        the same condition variable in another coroutine.  Once\n        awakened, it re-acquires the lock and returns True.\n        "
        if not self.locked():
            raise RuntimeError("cannot wait on un-acquired lock")
        self.release()
        try:
            fut = self._get_loop().create_future()
            self._waiters.append(fut)
            try:
                (await fut)
                return True
            finally:
                self._waiters.remove(fut)
        finally:
            cancelled = False
            while True:
                try:
                    (await self.acquire())
                    break
                except exceptions.CancelledError:
                    cancelled = True
            if cancelled:
                raise exceptions.CancelledError

    async def wait_for(self, predicate):
        "Wait until a predicate becomes true.\n\n        The predicate should be a callable which result will be\n        interpreted as a boolean value.  The final predicate value is\n        the return value.\n        "
        result = predicate()
        while not result:
            (await self.wait())
            result = predicate()
        return result

    def notify(self, n=1):
        "By default, wake up one coroutine waiting on this condition, if any.\n        If the calling coroutine has not acquired the lock when this method\n        is called, a RuntimeError is raised.\n\n        This method wakes up at most n of the coroutines waiting for the\n        condition variable; it is a no-op if no coroutines are waiting.\n\n        Note: an awakened coroutine does not actually return from its\n        wait() call until it can reacquire the lock. Since notify() does\n        not release the lock, its caller should.\n        "
        if not self.locked():
            raise RuntimeError("cannot notify on un-acquired lock")
        idx = 0
        for fut in self._waiters:
            if idx >= n:
                break
            if not fut.done():
                idx += 1
                fut.set_result(False)

    def notify_all(self):
        "Wake up all threads waiting on this condition. This method acts\n        like notify(), but wakes up all waiting threads instead of one. If the\n        calling thread has not acquired the lock when this method is called,\n        a RuntimeError is raised.\n        "
        self.notify(len(self._waiters))


class Semaphore(_ContextManagerMixin, mixins._LoopBoundMixin):
    "A Semaphore implementation.\n\n    A semaphore manages an internal counter which is decremented by each\n    acquire() call and incremented by each release() call. The counter\n    can never go below zero; when acquire() finds that it is zero, it blocks,\n    waiting until some other thread calls release().\n\n    Semaphores also support the context management protocol.\n\n    The optional argument gives the initial value for the internal\n    counter; it defaults to 1. If the value given is less than 0,\n    ValueError is raised.\n    "

    def __init__(self, value=1, *, loop=mixins._marker):
        super().__init__(loop=loop)
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._value = value
        self._waiters = collections.deque()

    def __repr__(self):
        res = super().__repr__()
        extra = "locked" if self.locked() else f"unlocked, value:{self._value}"
        if self._waiters:
            extra = f"{extra}, waiters:{len(self._waiters)}"
        return f"<{res[1:(- 1)]} [{extra}]>"

    def _wake_up_next(self):
        while self._waiters:
            waiter = self._waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                return

    def locked(self):
        "Returns True if semaphore can not be acquired immediately."
        return self._value == 0

    async def acquire(self):
        "Acquire a semaphore.\n\n        If the internal counter is larger than zero on entry,\n        decrement it by one and return True immediately.  If it is\n        zero on entry, block, waiting until some other coroutine has\n        called release() to make it larger than 0, and then return\n        True.\n        "
        while self._value <= 0:
            fut = self._get_loop().create_future()
            self._waiters.append(fut)
            try:
                (await fut)
            except:
                fut.cancel()
                if (self._value > 0) and (not fut.cancelled()):
                    self._wake_up_next()
                raise
        self._value -= 1
        return True

    def release(self):
        "Release a semaphore, incrementing the internal counter by one.\n        When it was zero on entry and another coroutine is waiting for it to\n        become larger than zero again, wake up that coroutine.\n        "
        self._value += 1
        self._wake_up_next()


class BoundedSemaphore(Semaphore):
    "A bounded semaphore implementation.\n\n    This raises ValueError in release() if it would increase the value\n    above the initial value.\n    "

    def __init__(self, value=1, *, loop=mixins._marker):
        self._bound_value = value
        super().__init__(value, loop=loop)

    def release(self):
        if self._value >= self._bound_value:
            raise ValueError("BoundedSemaphore released too many times")
        super().release()
