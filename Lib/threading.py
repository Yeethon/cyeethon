"Thread module emulating a subset of Java's threading model."
import os as _os
import sys as _sys
import _thread
import functools
from time import monotonic as _time
from _weakrefset import WeakSet
from itertools import islice as _islice, count as _count

try:
    from _collections import deque as _deque
except ImportError:
    from collections import deque as _deque
__all__ = [
    "get_ident",
    "active_count",
    "Condition",
    "current_thread",
    "enumerate",
    "main_thread",
    "TIMEOUT_MAX",
    "Event",
    "Lock",
    "RLock",
    "Semaphore",
    "BoundedSemaphore",
    "Thread",
    "Barrier",
    "BrokenBarrierError",
    "Timer",
    "ThreadError",
    "setprofile",
    "settrace",
    "local",
    "stack_size",
    "excepthook",
    "ExceptHookArgs",
    "gettrace",
    "getprofile",
]
_start_new_thread = _thread.start_new_thread
_allocate_lock = _thread.allocate_lock
_set_sentinel = _thread._set_sentinel
get_ident = _thread.get_ident
try:
    get_native_id = _thread.get_native_id
    _HAVE_THREAD_NATIVE_ID = True
    __all__.append("get_native_id")
except AttributeError:
    _HAVE_THREAD_NATIVE_ID = False
ThreadError = _thread.error
try:
    _CRLock = _thread.RLock
except AttributeError:
    _CRLock = None
TIMEOUT_MAX = _thread.TIMEOUT_MAX
del _thread
_profile_hook = None
_trace_hook = None


def setprofile(func):
    "Set a profile function for all threads started from the threading module.\n\n    The func will be passed to sys.setprofile() for each thread, before its\n    run() method is called.\n\n    "
    global _profile_hook
    _profile_hook = func


def getprofile():
    "Get the profiler function as set by threading.setprofile()."
    return _profile_hook


def settrace(func):
    "Set a trace function for all threads started from the threading module.\n\n    The func will be passed to sys.settrace() for each thread, before its run()\n    method is called.\n\n    "
    global _trace_hook
    _trace_hook = func


def gettrace():
    "Get the trace function as set by threading.settrace()."
    return _trace_hook


Lock = _allocate_lock


def RLock(*args, **kwargs):
    "Factory function that returns a new reentrant lock.\n\n    A reentrant lock must be released by the thread that acquired it. Once a\n    thread has acquired a reentrant lock, the same thread may acquire it again\n    without blocking; the thread must release it once for each time it has\n    acquired it.\n\n    "
    if _CRLock is None:
        return _PyRLock(*args, **kwargs)
    return _CRLock(*args, **kwargs)


class _RLock:
    "This class implements reentrant lock objects.\n\n    A reentrant lock must be released by the thread that acquired it. Once a\n    thread has acquired a reentrant lock, the same thread may acquire it\n    again without blocking; the thread must release it once for each time it\n    has acquired it.\n\n    "

    def __init__(self):
        self._block = _allocate_lock()
        self._owner = None
        self._count = 0

    def __repr__(self):
        owner = self._owner
        try:
            owner = _active[owner].name
        except KeyError:
            pass
        return "<%s %s.%s object owner=%r count=%d at %s>" % (
            ("locked" if self._block.locked() else "unlocked"),
            self.__class__.__module__,
            self.__class__.__qualname__,
            owner,
            self._count,
            hex(id(self)),
        )

    def _at_fork_reinit(self):
        self._block._at_fork_reinit()
        self._owner = None
        self._count = 0

    def acquire(self, blocking=True, timeout=(-1)):
        "Acquire a lock, blocking or non-blocking.\n\n        When invoked without arguments: if this thread already owns the lock,\n        increment the recursion level by one, and return immediately. Otherwise,\n        if another thread owns the lock, block until the lock is unlocked. Once\n        the lock is unlocked (not owned by any thread), then grab ownership, set\n        the recursion level to one, and return. If more than one thread is\n        blocked waiting until the lock is unlocked, only one at a time will be\n        able to grab ownership of the lock. There is no return value in this\n        case.\n\n        When invoked with the blocking argument set to true, do the same thing\n        as when called without arguments, and return true.\n\n        When invoked with the blocking argument set to false, do not block. If a\n        call without an argument would block, return false immediately;\n        otherwise, do the same thing as when called without arguments, and\n        return true.\n\n        When invoked with the floating-point timeout argument set to a positive\n        value, block for at most the number of seconds specified by timeout\n        and as long as the lock cannot be acquired.  Return true if the lock has\n        been acquired, false if the timeout has elapsed.\n\n        "
        me = get_ident()
        if self._owner == me:
            self._count += 1
            return 1
        rc = self._block.acquire(blocking, timeout)
        if rc:
            self._owner = me
            self._count = 1
        return rc

    __enter__ = acquire

    def release(self):
        "Release a lock, decrementing the recursion level.\n\n        If after the decrement it is zero, reset the lock to unlocked (not owned\n        by any thread), and if any other threads are blocked waiting for the\n        lock to become unlocked, allow exactly one of them to proceed. If after\n        the decrement the recursion level is still nonzero, the lock remains\n        locked and owned by the calling thread.\n\n        Only call this method when the calling thread owns the lock. A\n        RuntimeError is raised if this method is called when the lock is\n        unlocked.\n\n        There is no return value.\n\n        "
        if self._owner != get_ident():
            raise RuntimeError("cannot release un-acquired lock")
        self._count = count = self._count - 1
        if not count:
            self._owner = None
            self._block.release()

    def __exit__(self, t, v, tb):
        self.release()

    def _acquire_restore(self, state):
        self._block.acquire()
        (self._count, self._owner) = state

    def _release_save(self):
        if self._count == 0:
            raise RuntimeError("cannot release un-acquired lock")
        count = self._count
        self._count = 0
        owner = self._owner
        self._owner = None
        self._block.release()
        return (count, owner)

    def _is_owned(self):
        return self._owner == get_ident()


_PyRLock = _RLock


class Condition:
    "Class that implements a condition variable.\n\n    A condition variable allows one or more threads to wait until they are\n    notified by another thread.\n\n    If the lock argument is given and not None, it must be a Lock or RLock\n    object, and it is used as the underlying lock. Otherwise, a new RLock object\n    is created and used as the underlying lock.\n\n    "

    def __init__(self, lock=None):
        if lock is None:
            lock = RLock()
        self._lock = lock
        self.acquire = lock.acquire
        self.release = lock.release
        try:
            self._release_save = lock._release_save
        except AttributeError:
            pass
        try:
            self._acquire_restore = lock._acquire_restore
        except AttributeError:
            pass
        try:
            self._is_owned = lock._is_owned
        except AttributeError:
            pass
        self._waiters = _deque()

    def _at_fork_reinit(self):
        self._lock._at_fork_reinit()
        self._waiters.clear()

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, *args):
        return self._lock.__exit__(*args)

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self._lock, len(self._waiters))

    def _release_save(self):
        self._lock.release()

    def _acquire_restore(self, x):
        self._lock.acquire()

    def _is_owned(self):
        if self._lock.acquire(False):
            self._lock.release()
            return False
        else:
            return True

    def wait(self, timeout=None):
        "Wait until notified or until a timeout occurs.\n\n        If the calling thread has not acquired the lock when this method is\n        called, a RuntimeError is raised.\n\n        This method releases the underlying lock, and then blocks until it is\n        awakened by a notify() or notify_all() call for the same condition\n        variable in another thread, or until the optional timeout occurs. Once\n        awakened or timed out, it re-acquires the lock and returns.\n\n        When the timeout argument is present and not None, it should be a\n        floating point number specifying a timeout for the operation in seconds\n        (or fractions thereof).\n\n        When the underlying lock is an RLock, it is not released using its\n        release() method, since this may not actually unlock the lock when it\n        was acquired multiple times recursively. Instead, an internal interface\n        of the RLock class is used, which really unlocks it even when it has\n        been recursively acquired several times. Another internal interface is\n        then used to restore the recursion level when the lock is reacquired.\n\n        "
        if not self._is_owned():
            raise RuntimeError("cannot wait on un-acquired lock")
        waiter = _allocate_lock()
        waiter.acquire()
        self._waiters.append(waiter)
        saved_state = self._release_save()
        gotit = False
        try:
            if timeout is None:
                waiter.acquire()
                gotit = True
            elif timeout > 0:
                gotit = waiter.acquire(True, timeout)
            else:
                gotit = waiter.acquire(False)
            return gotit
        finally:
            self._acquire_restore(saved_state)
            if not gotit:
                try:
                    self._waiters.remove(waiter)
                except ValueError:
                    pass

    def wait_for(self, predicate, timeout=None):
        "Wait until a condition evaluates to True.\n\n        predicate should be a callable which result will be interpreted as a\n        boolean value.  A timeout may be provided giving the maximum time to\n        wait.\n\n        "
        endtime = None
        waittime = timeout
        result = predicate()
        while not result:
            if waittime is not None:
                if endtime is None:
                    endtime = _time() + waittime
                else:
                    waittime = endtime - _time()
                    if waittime <= 0:
                        break
            self.wait(waittime)
            result = predicate()
        return result

    def notify(self, n=1):
        "Wake up one or more threads waiting on this condition, if any.\n\n        If the calling thread has not acquired the lock when this method is\n        called, a RuntimeError is raised.\n\n        This method wakes up at most n of the threads waiting for the condition\n        variable; it is a no-op if no threads are waiting.\n\n        "
        if not self._is_owned():
            raise RuntimeError("cannot notify on un-acquired lock")
        all_waiters = self._waiters
        waiters_to_notify = _deque(_islice(all_waiters, n))
        if not waiters_to_notify:
            return
        for waiter in waiters_to_notify:
            waiter.release()
            try:
                all_waiters.remove(waiter)
            except ValueError:
                pass

    def notify_all(self):
        "Wake up all threads waiting on this condition.\n\n        If the calling thread has not acquired the lock when this method\n        is called, a RuntimeError is raised.\n\n        "
        self.notify(len(self._waiters))

    def notifyAll(self):
        "Wake up all threads waiting on this condition.\n\n        This method is deprecated, use notify_all() instead.\n\n        "
        import warnings

        warnings.warn(
            "notifyAll() is deprecated, use notify_all() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.notify_all()


class Semaphore:
    "This class implements semaphore objects.\n\n    Semaphores manage a counter representing the number of release() calls minus\n    the number of acquire() calls, plus an initial value. The acquire() method\n    blocks if necessary until it can return without making the counter\n    negative. If not given, value defaults to 1.\n\n    "

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self._cond = Condition(Lock())
        self._value = value

    def acquire(self, blocking=True, timeout=None):
        "Acquire a semaphore, decrementing the internal counter by one.\n\n        When invoked without arguments: if the internal counter is larger than\n        zero on entry, decrement it by one and return immediately. If it is zero\n        on entry, block, waiting until some other thread has called release() to\n        make it larger than zero. This is done with proper interlocking so that\n        if multiple acquire() calls are blocked, release() will wake exactly one\n        of them up. The implementation may pick one at random, so the order in\n        which blocked threads are awakened should not be relied on. There is no\n        return value in this case.\n\n        When invoked with blocking set to true, do the same thing as when called\n        without arguments, and return true.\n\n        When invoked with blocking set to false, do not block. If a call without\n        an argument would block, return false immediately; otherwise, do the\n        same thing as when called without arguments, and return true.\n\n        When invoked with a timeout other than None, it will block for at\n        most timeout seconds.  If acquire does not complete successfully in\n        that interval, return false.  Return true otherwise.\n\n        "
        if (not blocking) and (timeout is not None):
            raise ValueError("can't specify timeout for non-blocking acquire")
        rc = False
        endtime = None
        with self._cond:
            while self._value == 0:
                if not blocking:
                    break
                if timeout is not None:
                    if endtime is None:
                        endtime = _time() + timeout
                    else:
                        timeout = endtime - _time()
                        if timeout <= 0:
                            break
                self._cond.wait(timeout)
            else:
                self._value -= 1
                rc = True
        return rc

    __enter__ = acquire

    def release(self, n=1):
        "Release a semaphore, incrementing the internal counter by one or more.\n\n        When the counter is zero on entry and another thread is waiting for it\n        to become larger than zero again, wake up that thread.\n\n        "
        if n < 1:
            raise ValueError("n must be one or more")
        with self._cond:
            self._value += n
            for i in range(n):
                self._cond.notify()

    def __exit__(self, t, v, tb):
        self.release()


class BoundedSemaphore(Semaphore):
    "Implements a bounded semaphore.\n\n    A bounded semaphore checks to make sure its current value doesn't exceed its\n    initial value. If it does, ValueError is raised. In most situations\n    semaphores are used to guard resources with limited capacity.\n\n    If the semaphore is released too many times it's a sign of a bug. If not\n    given, value defaults to 1.\n\n    Like regular semaphores, bounded semaphores manage a counter representing\n    the number of release() calls minus the number of acquire() calls, plus an\n    initial value. The acquire() method blocks if necessary until it can return\n    without making the counter negative. If not given, value defaults to 1.\n\n    "

    def __init__(self, value=1):
        Semaphore.__init__(self, value)
        self._initial_value = value

    def release(self, n=1):
        "Release a semaphore, incrementing the internal counter by one or more.\n\n        When the counter is zero on entry and another thread is waiting for it\n        to become larger than zero again, wake up that thread.\n\n        If the number of releases exceeds the number of acquires,\n        raise a ValueError.\n\n        "
        if n < 1:
            raise ValueError("n must be one or more")
        with self._cond:
            if (self._value + n) > self._initial_value:
                raise ValueError("Semaphore released too many times")
            self._value += n
            for i in range(n):
                self._cond.notify()


class Event:
    "Class implementing event objects.\n\n    Events manage a flag that can be set to true with the set() method and reset\n    to false with the clear() method. The wait() method blocks until the flag is\n    true.  The flag is initially false.\n\n    "

    def __init__(self):
        self._cond = Condition(Lock())
        self._flag = False

    def _at_fork_reinit(self):
        self._cond._at_fork_reinit()

    def is_set(self):
        "Return true if and only if the internal flag is true."
        return self._flag

    def isSet(self):
        "Return true if and only if the internal flag is true.\n\n        This method is deprecated, use notify_all() instead.\n\n        "
        import warnings

        warnings.warn(
            "isSet() is deprecated, use is_set() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.is_set()

    def set(self):
        "Set the internal flag to true.\n\n        All threads waiting for it to become true are awakened. Threads\n        that call wait() once the flag is true will not block at all.\n\n        "
        with self._cond:
            self._flag = True
            self._cond.notify_all()

    def clear(self):
        "Reset the internal flag to false.\n\n        Subsequently, threads calling wait() will block until set() is called to\n        set the internal flag to true again.\n\n        "
        with self._cond:
            self._flag = False

    def wait(self, timeout=None):
        "Block until the internal flag is true.\n\n        If the internal flag is true on entry, return immediately. Otherwise,\n        block until another thread calls set() to set the flag to true, or until\n        the optional timeout occurs.\n\n        When the timeout argument is present and not None, it should be a\n        floating point number specifying a timeout for the operation in seconds\n        (or fractions thereof).\n\n        This method returns the internal flag on exit, so it will always return\n        True except if a timeout is given and the operation times out.\n\n        "
        with self._cond:
            signaled = self._flag
            if not signaled:
                signaled = self._cond.wait(timeout)
            return signaled


class Barrier:
    "Implements a Barrier.\n\n    Useful for synchronizing a fixed number of threads at known synchronization\n    points.  Threads block on 'wait()' and are simultaneously awoken once they\n    have all made that call.\n\n    "

    def __init__(self, parties, action=None, timeout=None):
        "Create a barrier, initialised to 'parties' threads.\n\n        'action' is a callable which, when supplied, will be called by one of\n        the threads after they have all entered the barrier and just prior to\n        releasing them all. If a 'timeout' is provided, it is used as the\n        default for all subsequent 'wait()' calls.\n\n        "
        self._cond = Condition(Lock())
        self._action = action
        self._timeout = timeout
        self._parties = parties
        self._state = 0
        self._count = 0

    def wait(self, timeout=None):
        "Wait for the barrier.\n\n        When the specified number of threads have started waiting, they are all\n        simultaneously awoken. If an 'action' was provided for the barrier, one\n        of the threads will have executed that callback prior to returning.\n        Returns an individual index number from 0 to 'parties-1'.\n\n        "
        if timeout is None:
            timeout = self._timeout
        with self._cond:
            self._enter()
            index = self._count
            self._count += 1
            try:
                if (index + 1) == self._parties:
                    self._release()
                else:
                    self._wait(timeout)
                return index
            finally:
                self._count -= 1
                self._exit()

    def _enter(self):
        while self._state in ((-1), 1):
            self._cond.wait()
        if self._state < 0:
            raise BrokenBarrierError
        assert self._state == 0

    def _release(self):
        try:
            if self._action:
                self._action()
            self._state = 1
            self._cond.notify_all()
        except:
            self._break()
            raise

    def _wait(self, timeout):
        if not self._cond.wait_for((lambda: (self._state != 0)), timeout):
            self._break()
            raise BrokenBarrierError
        if self._state < 0:
            raise BrokenBarrierError
        assert self._state == 1

    def _exit(self):
        if self._count == 0:
            if self._state in ((-1), 1):
                self._state = 0
                self._cond.notify_all()

    def reset(self):
        "Reset the barrier to the initial state.\n\n        Any threads currently waiting will get the BrokenBarrier exception\n        raised.\n\n        "
        with self._cond:
            if self._count > 0:
                if self._state == 0:
                    self._state = -1
                elif self._state == (-2):
                    self._state = -1
            else:
                self._state = 0
            self._cond.notify_all()

    def abort(self):
        "Place the barrier into a 'broken' state.\n\n        Useful in case of error.  Any currently waiting threads and threads\n        attempting to 'wait()' will have BrokenBarrierError raised.\n\n        "
        with self._cond:
            self._break()

    def _break(self):
        self._state = -2
        self._cond.notify_all()

    @property
    def parties(self):
        "Return the number of threads required to trip the barrier."
        return self._parties

    @property
    def n_waiting(self):
        "Return the number of threads currently waiting at the barrier."
        if self._state == 0:
            return self._count
        return 0

    @property
    def broken(self):
        "Return True if the barrier is in a broken state."
        return self._state == (-2)


class BrokenBarrierError(RuntimeError):
    pass


_counter = _count(1).__next__


def _newname(name_template):
    return name_template % _counter()


_active_limbo_lock = _allocate_lock()
_active = {}
_limbo = {}
_dangling = WeakSet()
_shutdown_locks_lock = _allocate_lock()
_shutdown_locks = set()


class Thread:
    "A class that represents a thread of control.\n\n    This class can be safely subclassed in a limited fashion. There are two ways\n    to specify the activity: by passing a callable object to the constructor, or\n    by overriding the run() method in a subclass.\n\n    "
    _initialized = False

    def __init__(
        self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None
    ):
        'This constructor should always be called with keyword arguments. Arguments are:\n\n        *group* should be None; reserved for future extension when a ThreadGroup\n        class is implemented.\n\n        *target* is the callable object to be invoked by the run()\n        method. Defaults to None, meaning nothing is called.\n\n        *name* is the thread name. By default, a unique name is constructed of\n        the form "Thread-N" where N is a small decimal number.\n\n        *args* is the argument tuple for the target invocation. Defaults to ().\n\n        *kwargs* is a dictionary of keyword arguments for the target\n        invocation. Defaults to {}.\n\n        If a subclass overrides the constructor, it must make sure to invoke\n        the base class constructor (Thread.__init__()) before doing anything\n        else to the thread.\n\n        '
        assert group is None, "group argument must be None for now"
        if kwargs is None:
            kwargs = {}
        if name:
            name = str(name)
        else:
            name = _newname("Thread-%d")
            if target is not None:
                try:
                    target_name = target.__name__
                    name += f" ({target_name})"
                except AttributeError:
                    pass
        self._target = target
        self._name = name
        self._args = args
        self._kwargs = kwargs
        if daemon is not None:
            self._daemonic = daemon
        else:
            self._daemonic = current_thread().daemon
        self._ident = None
        if _HAVE_THREAD_NATIVE_ID:
            self._native_id = None
        self._tstate_lock = None
        self._started = Event()
        self._is_stopped = False
        self._initialized = True
        self._stderr = _sys.stderr
        self._invoke_excepthook = _make_invoke_excepthook()
        _dangling.add(self)

    def _reset_internal_locks(self, is_alive):
        self._started._at_fork_reinit()
        if is_alive:
            if self._tstate_lock is not None:
                self._tstate_lock._at_fork_reinit()
                self._tstate_lock.acquire()
        else:
            self._is_stopped = True
            self._tstate_lock = None

    def __repr__(self):
        assert self._initialized, "Thread.__init__() was not called"
        status = "initial"
        if self._started.is_set():
            status = "started"
        self.is_alive()
        if self._is_stopped:
            status = "stopped"
        if self._daemonic:
            status += " daemon"
        if self._ident is not None:
            status += " %s" % self._ident
        return "<%s(%s, %s)>" % (self.__class__.__name__, self._name, status)

    def start(self):
        "Start the thread's activity.\n\n        It must be called at most once per thread object. It arranges for the\n        object's run() method to be invoked in a separate thread of control.\n\n        This method will raise a RuntimeError if called more than once on the\n        same thread object.\n\n        "
        if not self._initialized:
            raise RuntimeError("thread.__init__() not called")
        if self._started.is_set():
            raise RuntimeError("threads can only be started once")
        with _active_limbo_lock:
            _limbo[self] = self
        try:
            _start_new_thread(self._bootstrap, ())
        except Exception:
            with _active_limbo_lock:
                del _limbo[self]
            raise
        self._started.wait()

    def run(self):
        "Method representing the thread's activity.\n\n        You may override this method in a subclass. The standard run() method\n        invokes the callable object passed to the object's constructor as the\n        target argument, if any, with sequential and keyword arguments taken\n        from the args and kwargs arguments, respectively.\n\n        "
        try:
            if self._target is not None:
                self._target(*self._args, **self._kwargs)
        finally:
            del self._target, self._args, self._kwargs

    def _bootstrap(self):
        try:
            self._bootstrap_inner()
        except:
            if self._daemonic and (_sys is None):
                return
            raise

    def _set_ident(self):
        self._ident = get_ident()

    if _HAVE_THREAD_NATIVE_ID:

        def _set_native_id(self):
            self._native_id = get_native_id()

    def _set_tstate_lock(self):
        "\n        Set a lock object which will be released by the interpreter when\n        the underlying thread state (see pystate.h) gets deleted.\n        "
        self._tstate_lock = _set_sentinel()
        self._tstate_lock.acquire()
        if not self.daemon:
            with _shutdown_locks_lock:
                _shutdown_locks.add(self._tstate_lock)

    def _bootstrap_inner(self):
        try:
            self._set_ident()
            self._set_tstate_lock()
            if _HAVE_THREAD_NATIVE_ID:
                self._set_native_id()
            self._started.set()
            with _active_limbo_lock:
                _active[self._ident] = self
                del _limbo[self]
            if _trace_hook:
                _sys.settrace(_trace_hook)
            if _profile_hook:
                _sys.setprofile(_profile_hook)
            try:
                self.run()
            except:
                self._invoke_excepthook(self)
        finally:
            with _active_limbo_lock:
                try:
                    del _active[get_ident()]
                except:
                    pass

    def _stop(self):
        lock = self._tstate_lock
        if lock is not None:
            assert not lock.locked()
        self._is_stopped = True
        self._tstate_lock = None
        if not self.daemon:
            with _shutdown_locks_lock:
                _shutdown_locks.discard(lock)

    def _delete(self):
        "Remove current thread from the dict of currently running threads."
        with _active_limbo_lock:
            del _active[get_ident()]

    def join(self, timeout=None):
        "Wait until the thread terminates.\n\n        This blocks the calling thread until the thread whose join() method is\n        called terminates -- either normally or through an unhandled exception\n        or until the optional timeout occurs.\n\n        When the timeout argument is present and not None, it should be a\n        floating point number specifying a timeout for the operation in seconds\n        (or fractions thereof). As join() always returns None, you must call\n        is_alive() after join() to decide whether a timeout happened -- if the\n        thread is still alive, the join() call timed out.\n\n        When the timeout argument is not present or None, the operation will\n        block until the thread terminates.\n\n        A thread can be join()ed many times.\n\n        join() raises a RuntimeError if an attempt is made to join the current\n        thread as that would cause a deadlock. It is also an error to join() a\n        thread before it has been started and attempts to do so raises the same\n        exception.\n\n        "
        if not self._initialized:
            raise RuntimeError("Thread.__init__() not called")
        if not self._started.is_set():
            raise RuntimeError("cannot join thread before it is started")
        if self is current_thread():
            raise RuntimeError("cannot join current thread")
        if timeout is None:
            self._wait_for_tstate_lock()
        else:
            self._wait_for_tstate_lock(timeout=max(timeout, 0))

    def _wait_for_tstate_lock(self, block=True, timeout=(-1)):
        lock = self._tstate_lock
        if lock is None:
            assert self._is_stopped
        elif lock.acquire(block, timeout):
            lock.release()
            self._stop()

    @property
    def name(self):
        "A string used for identification purposes only.\n\n        It has no semantics. Multiple threads may be given the same name. The\n        initial name is set by the constructor.\n\n        "
        assert self._initialized, "Thread.__init__() not called"
        return self._name

    @name.setter
    def name(self, name):
        assert self._initialized, "Thread.__init__() not called"
        self._name = str(name)

    @property
    def ident(self):
        "Thread identifier of this thread or None if it has not been started.\n\n        This is a nonzero integer. See the get_ident() function. Thread\n        identifiers may be recycled when a thread exits and another thread is\n        created. The identifier is available even after the thread has exited.\n\n        "
        assert self._initialized, "Thread.__init__() not called"
        return self._ident

    if _HAVE_THREAD_NATIVE_ID:

        @property
        def native_id(self):
            "Native integral thread ID of this thread, or None if it has not been started.\n\n            This is a non-negative integer. See the get_native_id() function.\n            This represents the Thread ID as reported by the kernel.\n\n            "
            assert self._initialized, "Thread.__init__() not called"
            return self._native_id

    def is_alive(self):
        "Return whether the thread is alive.\n\n        This method returns True just before the run() method starts until just\n        after the run() method terminates. The module function enumerate()\n        returns a list of all alive threads.\n\n        "
        assert self._initialized, "Thread.__init__() not called"
        if self._is_stopped or (not self._started.is_set()):
            return False
        self._wait_for_tstate_lock(False)
        return not self._is_stopped

    @property
    def daemon(self):
        "A boolean value indicating whether this thread is a daemon thread.\n\n        This must be set before start() is called, otherwise RuntimeError is\n        raised. Its initial value is inherited from the creating thread; the\n        main thread is not a daemon thread and therefore all threads created in\n        the main thread default to daemon = False.\n\n        The entire Python program exits when only daemon threads are left.\n\n        "
        assert self._initialized, "Thread.__init__() not called"
        return self._daemonic

    @daemon.setter
    def daemon(self, daemonic):
        if not self._initialized:
            raise RuntimeError("Thread.__init__() not called")
        if self._started.is_set():
            raise RuntimeError("cannot set daemon status of active thread")
        self._daemonic = daemonic

    def isDaemon(self):
        "Return whether this thread is a daemon.\n\n        This method is deprecated, use the daemon attribute instead.\n\n        "
        import warnings

        warnings.warn(
            "isDaemon() is deprecated, get the daemon attribute instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.daemon

    def setDaemon(self, daemonic):
        "Set whether this thread is a daemon.\n\n        This method is deprecated, use the .daemon property instead.\n\n        "
        import warnings

        warnings.warn(
            "setDaemon() is deprecated, set the daemon attribute instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.daemon = daemonic

    def getName(self):
        "Return a string used for identification purposes only.\n\n        This method is deprecated, use the name attribute instead.\n\n        "
        import warnings

        warnings.warn(
            "getName() is deprecated, get the name attribute instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.name

    def setName(self, name):
        "Set the name string for this thread.\n\n        This method is deprecated, use the name attribute instead.\n\n        "
        import warnings

        warnings.warn(
            "setName() is deprecated, set the name attribute instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.name = name


try:
    from _thread import _excepthook as excepthook, _ExceptHookArgs as ExceptHookArgs
except ImportError:
    from traceback import print_exception as _print_exception
    from collections import namedtuple

    _ExceptHookArgs = namedtuple(
        "ExceptHookArgs", "exc_type exc_value exc_traceback thread"
    )

    def ExceptHookArgs(args):
        return _ExceptHookArgs(*args)

    def excepthook(args, /):
        "\n        Handle uncaught Thread.run() exception.\n        "
        if args.exc_type == SystemExit:
            return
        if (_sys is not None) and (_sys.stderr is not None):
            stderr = _sys.stderr
        elif args.thread is not None:
            stderr = args.thread._stderr
            if stderr is None:
                return
        else:
            return
        if args.thread is not None:
            name = args.thread.name
        else:
            name = get_ident()
        print(f"Exception in thread {name}:", file=stderr, flush=True)
        _print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=stderr)
        stderr.flush()


__excepthook__ = excepthook


def _make_invoke_excepthook():
    old_excepthook = excepthook
    old_sys_excepthook = _sys.excepthook
    if old_excepthook is None:
        raise RuntimeError("threading.excepthook is None")
    if old_sys_excepthook is None:
        raise RuntimeError("sys.excepthook is None")
    sys_exc_info = _sys.exc_info
    local_print = print
    local_sys = _sys

    def invoke_excepthook(thread):
        global excepthook
        try:
            hook = excepthook
            if hook is None:
                hook = old_excepthook
            args = ExceptHookArgs([*sys_exc_info(), thread])
            hook(args)
        except Exception as exc:
            exc.__suppress_context__ = True
            del exc
            if (local_sys is not None) and (local_sys.stderr is not None):
                stderr = local_sys.stderr
            else:
                stderr = thread._stderr
            local_print("Exception in threading.excepthook:", file=stderr, flush=True)
            if (local_sys is not None) and (local_sys.excepthook is not None):
                sys_excepthook = local_sys.excepthook
            else:
                sys_excepthook = old_sys_excepthook
            sys_excepthook(*sys_exc_info())
        finally:
            args = None

    return invoke_excepthook


class Timer(Thread):
    "Call a function after a specified number of seconds:\n\n            t = Timer(30.0, f, args=None, kwargs=None)\n            t.start()\n            t.cancel()     # stop the timer's action if it's still waiting\n\n    "

    def __init__(self, interval, function, args=None, kwargs=None):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args if (args is not None) else []
        self.kwargs = kwargs if (kwargs is not None) else {}
        self.finished = Event()

    def cancel(self):
        "Stop the timer if it hasn't finished yet."
        self.finished.set()

    def run(self):
        self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()


class _MainThread(Thread):
    def __init__(self):
        Thread.__init__(self, name="MainThread", daemon=False)
        self._set_tstate_lock()
        self._started.set()
        self._set_ident()
        if _HAVE_THREAD_NATIVE_ID:
            self._set_native_id()
        with _active_limbo_lock:
            _active[self._ident] = self


class _DummyThread(Thread):
    def __init__(self):
        Thread.__init__(self, name=_newname("Dummy-%d"), daemon=True)
        self._started.set()
        self._set_ident()
        if _HAVE_THREAD_NATIVE_ID:
            self._set_native_id()
        with _active_limbo_lock:
            _active[self._ident] = self

    def _stop(self):
        pass

    def is_alive(self):
        assert (not self._is_stopped) and self._started.is_set()
        return True

    def join(self, timeout=None):
        assert False, "cannot join a dummy thread"


def current_thread():
    "Return the current Thread object, corresponding to the caller's thread of control.\n\n    If the caller's thread of control was not created through the threading\n    module, a dummy thread object with limited functionality is returned.\n\n    "
    try:
        return _active[get_ident()]
    except KeyError:
        return _DummyThread()


def currentThread():
    "Return the current Thread object, corresponding to the caller's thread of control.\n\n    This function is deprecated, use current_thread() instead.\n\n    "
    import warnings

    warnings.warn(
        "currentThread() is deprecated, use current_thread() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return current_thread()


def active_count():
    "Return the number of Thread objects currently alive.\n\n    The returned count is equal to the length of the list returned by\n    enumerate().\n\n    "
    with _active_limbo_lock:
        return len(_active) + len(_limbo)


def activeCount():
    "Return the number of Thread objects currently alive.\n\n    This function is deprecated, use active_count() instead.\n\n    "
    import warnings

    warnings.warn(
        "activeCount() is deprecated, use active_count() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return active_count()


def _enumerate():
    return list(_active.values()) + list(_limbo.values())


def enumerate():
    "Return a list of all Thread objects currently alive.\n\n    The list includes daemonic threads, dummy thread objects created by\n    current_thread(), and the main thread. It excludes terminated threads and\n    threads that have not yet been started.\n\n    "
    with _active_limbo_lock:
        return list(_active.values()) + list(_limbo.values())


_threading_atexits = []
_SHUTTING_DOWN = False


def _register_atexit(func, *arg, **kwargs):
    "CPython internal: register *func* to be called before joining threads.\n\n    The registered *func* is called with its arguments just before all\n    non-daemon threads are joined in `_shutdown()`. It provides a similar\n    purpose to `atexit.register()`, but its functions are called prior to\n    threading shutdown instead of interpreter shutdown.\n\n    For similarity to atexit, the registered functions are called in reverse.\n    "
    if _SHUTTING_DOWN:
        raise RuntimeError("can't register atexit after shutdown")
    call = functools.partial(func, *arg, **kwargs)
    _threading_atexits.append(call)


from _thread import stack_size

_main_thread = _MainThread()


def _shutdown():
    "\n    Wait until the Python thread state of all non-daemon threads get deleted.\n    "
    if _main_thread._is_stopped:
        return
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = True
    tlock = _main_thread._tstate_lock
    assert tlock is not None
    assert tlock.locked()
    tlock.release()
    _main_thread._stop()
    for atexit_call in reversed(_threading_atexits):
        atexit_call()
    while True:
        with _shutdown_locks_lock:
            locks = list(_shutdown_locks)
            _shutdown_locks.clear()
        if not locks:
            break
        for lock in locks:
            lock.acquire()
            lock.release()


def main_thread():
    "Return the main thread object.\n\n    In normal conditions, the main thread is the thread from which the\n    Python interpreter was started.\n    "
    return _main_thread


try:
    from _thread import _local as local
except ImportError:
    from _threading_local import local


def _after_fork():
    "\n    Cleanup threading module state that should not exist after a fork.\n    "
    global _active_limbo_lock, _main_thread
    global _shutdown_locks_lock, _shutdown_locks
    _active_limbo_lock = _allocate_lock()
    new_active = {}
    try:
        current = _active[get_ident()]
    except KeyError:
        current = _MainThread()
    _main_thread = current
    _shutdown_locks_lock = _allocate_lock()
    _shutdown_locks = set()
    with _active_limbo_lock:
        threads = set(_enumerate())
        threads.update(_dangling)
        for thread in threads:
            if thread is current:
                thread._reset_internal_locks(True)
                ident = get_ident()
                thread._ident = ident
                new_active[ident] = thread
            else:
                thread._reset_internal_locks(False)
                thread._stop()
        _limbo.clear()
        _active.clear()
        _active.update(new_active)
        assert len(_active) == 1


if hasattr(_os, "register_at_fork"):
    _os.register_at_fork(after_in_child=_after_fork)
