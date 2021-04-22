"Support for tasks, coroutines and the scheduler."
__all__ = (
    "Task",
    "create_task",
    "FIRST_COMPLETED",
    "FIRST_EXCEPTION",
    "ALL_COMPLETED",
    "wait",
    "wait_for",
    "as_completed",
    "sleep",
    "gather",
    "shield",
    "ensure_future",
    "run_coroutine_threadsafe",
    "current_task",
    "all_tasks",
    "_register_task",
    "_unregister_task",
    "_enter_task",
    "_leave_task",
)
import concurrent.futures
import contextvars
import functools
import inspect
import itertools
import types
import warnings
import weakref
from . import base_tasks
from . import coroutines
from . import events
from . import exceptions
from . import futures
from .coroutines import _is_coroutine

_task_name_counter = itertools.count(1).__next__


def current_task(loop=None):
    "Return a currently executed task."
    if loop is None:
        loop = events.get_running_loop()
    return _current_tasks.get(loop)


def all_tasks(loop=None):
    "Return a set of all tasks for the loop."
    if loop is None:
        loop = events.get_running_loop()
    i = 0
    while True:
        try:
            tasks = list(_all_tasks)
        except RuntimeError:
            i += 1
            if i >= 1000:
                raise
        else:
            break
    return {t for t in tasks if ((futures._get_loop(t) is loop) and (not t.done()))}


def _set_task_name(task, name):
    if name is not None:
        try:
            set_name = task.set_name
        except AttributeError:
            pass
        else:
            set_name(name)


class Task(futures._PyFuture):
    "A coroutine wrapped in a Future."
    _log_destroy_pending = True

    def __init__(self, coro, *, loop=None, name=None):
        super().__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[(-1)]
        if not coroutines.iscoroutine(coro):
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")
        if name is None:
            self._name = f"Task-{_task_name_counter()}"
        else:
            self._name = str(name)
        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        self._context = contextvars.copy_context()
        self._loop.call_soon(self.__step, context=self._context)
        _register_task(self)

    def __del__(self):
        if (self._state == futures._PENDING) and self._log_destroy_pending:
            context = {"task": self, "message": "Task was destroyed but it is pending!"}
            if self._source_traceback:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)
        super().__del__()

    def __class_getitem__(cls, type):
        return cls

    def _repr_info(self):
        return base_tasks._task_repr_info(self)

    def get_coro(self):
        return self._coro

    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = str(value)

    def set_result(self, result):
        raise RuntimeError("Task does not support set_result operation")

    def set_exception(self, exception):
        raise RuntimeError("Task does not support set_exception operation")

    def get_stack(self, *, limit=None):
        "Return the list of stack frames for this task's coroutine.\n\n        If the coroutine is not done, this returns the stack where it is\n        suspended.  If the coroutine has completed successfully or was\n        cancelled, this returns an empty list.  If the coroutine was\n        terminated by an exception, this returns the list of traceback\n        frames.\n\n        The frames are always ordered from oldest to newest.\n\n        The optional limit gives the maximum number of frames to\n        return; by default all available frames are returned.  Its\n        meaning differs depending on whether a stack or a traceback is\n        returned: the newest frames of a stack are returned, but the\n        oldest frames of a traceback are returned.  (This matches the\n        behavior of the traceback module.)\n\n        For reasons beyond our control, only one stack frame is\n        returned for a suspended coroutine.\n        "
        return base_tasks._task_get_stack(self, limit)

    def print_stack(self, *, limit=None, file=None):
        "Print the stack or traceback for this task's coroutine.\n\n        This produces output similar to that of the traceback module,\n        for the frames retrieved by get_stack().  The limit argument\n        is passed to get_stack().  The file argument is an I/O stream\n        to which the output is written; by default output is written\n        to sys.stderr.\n        "
        return base_tasks._task_print_stack(self, limit, file)

    def cancel(self, msg=None):
        "Request that this task cancel itself.\n\n        This arranges for a CancelledError to be thrown into the\n        wrapped coroutine on the next cycle through the event loop.\n        The coroutine then has a chance to clean up or even deny\n        the request using try/except/finally.\n\n        Unlike Future.cancel, this does not guarantee that the\n        task will be cancelled: the exception might be caught and\n        acted upon, delaying cancellation of the task or preventing\n        cancellation completely.  The task may also return a value or\n        raise a different exception.\n\n        Immediately after this method is called, Task.cancelled() will\n        not return True (unless the task was already cancelled).  A\n        task will be marked as cancelled when the wrapped coroutine\n        terminates with a CancelledError exception (even if cancel()\n        was not called).\n        "
        self._log_traceback = False
        if self.done():
            return False
        if self._fut_waiter is not None:
            if self._fut_waiter.cancel(msg=msg):
                return True
        self._must_cancel = True
        self._cancel_message = msg
        return True

    def __step(self, exc=None):
        if self.done():
            raise exceptions.InvalidStateError(
                f"_step(): already done: {self!r}, {exc!r}"
            )
        if self._must_cancel:
            if not isinstance(exc, exceptions.CancelledError):
                exc = self._make_cancelled_error()
            self._must_cancel = False
        coro = self._coro
        self._fut_waiter = None
        _enter_task(self._loop, self)
        try:
            if exc is None:
                result = coro.send(None)
            else:
                result = coro.throw(exc)
        except StopIteration as exc:
            if self._must_cancel:
                self._must_cancel = False
                super().cancel(msg=self._cancel_message)
            else:
                super().set_result(exc.value)
        except exceptions.CancelledError as exc:
            self._cancelled_exc = exc
            super().cancel()
        except (KeyboardInterrupt, SystemExit) as exc:
            super().set_exception(exc)
            raise
        except BaseException as exc:
            super().set_exception(exc)
        else:
            blocking = getattr(result, "_asyncio_future_blocking", None)
            if blocking is not None:
                if futures._get_loop(result) is not self._loop:
                    new_exc = RuntimeError(
                        f"Task {self!r} got Future {result!r} attached to a different loop"
                    )
                    self._loop.call_soon(self.__step, new_exc, context=self._context)
                elif blocking:
                    if result is self:
                        new_exc = RuntimeError(f"Task cannot await on itself: {self!r}")
                        self._loop.call_soon(
                            self.__step, new_exc, context=self._context
                        )
                    else:
                        result._asyncio_future_blocking = False
                        result.add_done_callback(self.__wakeup, context=self._context)
                        self._fut_waiter = result
                        if self._must_cancel:
                            if self._fut_waiter.cancel(msg=self._cancel_message):
                                self._must_cancel = False
                else:
                    new_exc = RuntimeError(
                        f"yield was used instead of yield from in task {self!r} with {result!r}"
                    )
                    self._loop.call_soon(self.__step, new_exc, context=self._context)
            elif result is None:
                self._loop.call_soon(self.__step, context=self._context)
            elif inspect.isgenerator(result):
                new_exc = RuntimeError(
                    f"yield was used instead of yield from for generator in task {self!r} with {result!r}"
                )
                self._loop.call_soon(self.__step, new_exc, context=self._context)
            else:
                new_exc = RuntimeError(f"Task got bad yield: {result!r}")
                self._loop.call_soon(self.__step, new_exc, context=self._context)
        finally:
            _leave_task(self._loop, self)
            self = None

    def __wakeup(self, future):
        try:
            future.result()
        except BaseException as exc:
            self.__step(exc)
        else:
            self.__step()
        self = None


_PyTask = Task
try:
    import _asyncio
except ImportError:
    pass
else:
    Task = _CTask = _asyncio.Task


def create_task(coro, *, name=None):
    "Schedule the execution of a coroutine object in a spawn task.\n\n    Return a Task object.\n    "
    loop = events.get_running_loop()
    task = loop.create_task(coro)
    _set_task_name(task, name)
    return task


FIRST_COMPLETED = concurrent.futures.FIRST_COMPLETED
FIRST_EXCEPTION = concurrent.futures.FIRST_EXCEPTION
ALL_COMPLETED = concurrent.futures.ALL_COMPLETED


async def wait(fs, *, timeout=None, return_when=ALL_COMPLETED):
    "Wait for the Futures and coroutines given by fs to complete.\n\n    The fs iterable must not be empty.\n\n    Coroutines will be wrapped in Tasks.\n\n    Returns two sets of Future: (done, pending).\n\n    Usage:\n\n        done, pending = await asyncio.wait(fs)\n\n    Note: This does not raise TimeoutError! Futures that aren't done\n    when the timeout occurs are returned in the second set.\n    "
    if futures.isfuture(fs) or coroutines.iscoroutine(fs):
        raise TypeError(f"expect a list of futures, not {type(fs).__name__}")
    if not fs:
        raise ValueError("Set of coroutines/Futures is empty.")
    if return_when not in (FIRST_COMPLETED, FIRST_EXCEPTION, ALL_COMPLETED):
        raise ValueError(f"Invalid return_when value: {return_when}")
    loop = events.get_running_loop()
    fs = set(fs)
    if any((coroutines.iscoroutine(f) for f in fs)):
        warnings.warn(
            "The explicit passing of coroutine objects to asyncio.wait() is deprecated since Python 3.8, and scheduled for removal in Python 3.11.",
            DeprecationWarning,
            stacklevel=2,
        )
    fs = {ensure_future(f, loop=loop) for f in fs}
    return await _wait(fs, timeout, return_when, loop)


def _release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)


async def wait_for(fut, timeout):
    "Wait for the single Future or coroutine to complete, with timeout.\n\n    Coroutine will be wrapped in Task.\n\n    Returns result of the Future or coroutine.  When a timeout occurs,\n    it cancels the task and raises TimeoutError.  To avoid the task\n    cancellation, wrap it in shield().\n\n    If the wait is cancelled, the task is also cancelled.\n\n    This function is a coroutine.\n    "
    loop = events.get_running_loop()
    if timeout is None:
        return await fut
    if timeout <= 0:
        fut = ensure_future(fut, loop=loop)
        if fut.done():
            return fut.result()
        (await _cancel_and_wait(fut, loop=loop))
        try:
            fut.result()
        except exceptions.CancelledError as exc:
            raise exceptions.TimeoutError() from exc
        else:
            raise exceptions.TimeoutError()
    waiter = loop.create_future()
    timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    cb = functools.partial(_release_waiter, waiter)
    fut = ensure_future(fut, loop=loop)
    fut.add_done_callback(cb)
    try:
        try:
            (await waiter)
        except exceptions.CancelledError:
            if fut.done():
                return fut.result()
            else:
                fut.remove_done_callback(cb)
                (await _cancel_and_wait(fut, loop=loop))
                raise
        if fut.done():
            return fut.result()
        else:
            fut.remove_done_callback(cb)
            (await _cancel_and_wait(fut, loop=loop))
            try:
                fut.result()
            except exceptions.CancelledError as exc:
                raise exceptions.TimeoutError() from exc
            else:
                raise exceptions.TimeoutError()
    finally:
        timeout_handle.cancel()


async def _wait(fs, timeout, return_when, loop):
    "Internal helper for wait().\n\n    The fs argument must be a collection of Futures.\n    "
    assert fs, "Set of Futures is empty."
    waiter = loop.create_future()
    timeout_handle = None
    if timeout is not None:
        timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    counter = len(fs)

    def _on_completion(f):
        nonlocal counter
        counter -= 1
        if (
            (counter <= 0)
            or (return_when == FIRST_COMPLETED)
            or (
                (return_when == FIRST_EXCEPTION)
                and ((not f.cancelled()) and (f.exception() is not None))
            )
        ):
            if timeout_handle is not None:
                timeout_handle.cancel()
            if not waiter.done():
                waiter.set_result(None)

    for f in fs:
        f.add_done_callback(_on_completion)
    try:
        (await waiter)
    finally:
        if timeout_handle is not None:
            timeout_handle.cancel()
        for f in fs:
            f.remove_done_callback(_on_completion)
    (done, pending) = (set(), set())
    for f in fs:
        if f.done():
            done.add(f)
        else:
            pending.add(f)
    return (done, pending)


async def _cancel_and_wait(fut, loop):
    "Cancel the *fut* future or task and wait until it completes."
    waiter = loop.create_future()
    cb = functools.partial(_release_waiter, waiter)
    fut.add_done_callback(cb)
    try:
        fut.cancel()
        (await waiter)
    finally:
        fut.remove_done_callback(cb)


def as_completed(fs, *, timeout=None):
    "Return an iterator whose values are coroutines.\n\n    When waiting for the yielded coroutines you'll get the results (or\n    exceptions!) of the original Futures (or coroutines), in the order\n    in which and as soon as they complete.\n\n    This differs from PEP 3148; the proper way to use this is:\n\n        for f in as_completed(fs):\n            result = await f  # The 'await' may raise.\n            # Use result.\n\n    If a timeout is specified, the 'await' will raise\n    TimeoutError when the timeout occurs before all Futures are done.\n\n    Note: The futures 'f' are not necessarily members of fs.\n    "
    if futures.isfuture(fs) or coroutines.iscoroutine(fs):
        raise TypeError(f"expect an iterable of futures, not {type(fs).__name__}")
    from .queues import Queue

    done = Queue()
    loop = events.get_event_loop()
    todo = {ensure_future(f, loop=loop) for f in set(fs)}
    timeout_handle = None

    def _on_timeout():
        for f in todo:
            f.remove_done_callback(_on_completion)
            done.put_nowait(None)
        todo.clear()

    def _on_completion(f):
        if not todo:
            return
        todo.remove(f)
        done.put_nowait(f)
        if (not todo) and (timeout_handle is not None):
            timeout_handle.cancel()

    async def _wait_for_one():
        f = await done.get()
        if f is None:
            raise exceptions.TimeoutError
        return f.result()

    for f in todo:
        f.add_done_callback(_on_completion)
    if todo and (timeout is not None):
        timeout_handle = loop.call_later(timeout, _on_timeout)
    for _ in range(len(todo)):
        (yield _wait_for_one())


@types.coroutine
def __sleep0():
    "Skip one event loop run cycle.\n\n    This is a private helper for 'asyncio.sleep()', used\n    when the 'delay' is set to 0.  It uses a bare 'yield'\n    expression (which Task.__step knows how to handle)\n    instead of creating a Future object.\n    "
    (yield)


async def sleep(delay, result=None):
    "Coroutine that completes after a given time (in seconds)."
    if delay <= 0:
        (await __sleep0())
        return result
    loop = events.get_running_loop()
    future = loop.create_future()
    h = loop.call_later(delay, futures._set_result_unless_cancelled, future, result)
    try:
        return await future
    finally:
        h.cancel()


def ensure_future(coro_or_future, *, loop=None):
    "Wrap a coroutine or an awaitable in a future.\n\n    If the argument is a Future, it is returned directly.\n    "
    if coroutines.iscoroutine(coro_or_future):
        if loop is None:
            loop = events.get_event_loop()
        task = loop.create_task(coro_or_future)
        if task._source_traceback:
            del task._source_traceback[(-1)]
        return task
    elif futures.isfuture(coro_or_future):
        if (loop is not None) and (loop is not futures._get_loop(coro_or_future)):
            raise ValueError(
                "The future belongs to a different loop than the one specified as the loop argument"
            )
        return coro_or_future
    elif inspect.isawaitable(coro_or_future):
        return ensure_future(_wrap_awaitable(coro_or_future), loop=loop)
    else:
        raise TypeError("An asyncio.Future, a coroutine or an awaitable is required")


@types.coroutine
def _wrap_awaitable(awaitable):
    "Helper for asyncio.ensure_future().\n\n    Wraps awaitable (an object with __await__) into a coroutine\n    that will later be wrapped in a Task by ensure_future().\n    "
    return (yield from awaitable.__await__())


_wrap_awaitable._is_coroutine = _is_coroutine


class _GatheringFuture(futures.Future):
    "Helper for gather().\n\n    This overrides cancel() to cancel all the children and act more\n    like Task.cancel(), which doesn't immediately mark itself as\n    cancelled.\n    "

    def __init__(self, children, *, loop=None):
        super().__init__(loop=loop)
        self._children = children
        self._cancel_requested = False

    def cancel(self, msg=None):
        if self.done():
            return False
        ret = False
        for child in self._children:
            if child.cancel(msg=msg):
                ret = True
        if ret:
            self._cancel_requested = True
        return ret


def gather(*coros_or_futures, return_exceptions=False):
    "Return a future aggregating results from the given coroutines/futures.\n\n    Coroutines will be wrapped in a future and scheduled in the event\n    loop. They will not necessarily be scheduled in the same order as\n    passed in.\n\n    All futures must share the same event loop.  If all the tasks are\n    done successfully, the returned future's result is the list of\n    results (in the order of the original sequence, not necessarily\n    the order of results arrival).  If *return_exceptions* is True,\n    exceptions in the tasks are treated the same as successful\n    results, and gathered in the result list; otherwise, the first\n    raised exception will be immediately propagated to the returned\n    future.\n\n    Cancellation: if the outer Future is cancelled, all children (that\n    have not completed yet) are also cancelled.  If any child is\n    cancelled, this is treated as if it raised CancelledError --\n    the outer Future is *not* cancelled in this case.  (This is to\n    prevent the cancellation of one child to cause other children to\n    be cancelled.)\n\n    If *return_exceptions* is False, cancelling gather() after it\n    has been marked done won't cancel any submitted awaitables.\n    For instance, gather can be marked done after propagating an\n    exception to the caller, therefore, calling ``gather.cancel()``\n    after catching an exception (raised by one of the awaitables) from\n    gather won't cancel any other awaitables.\n    "
    if not coros_or_futures:
        loop = events.get_event_loop()
        outer = loop.create_future()
        outer.set_result([])
        return outer

    def _done_callback(fut):
        nonlocal nfinished
        nfinished += 1
        if outer.done():
            if not fut.cancelled():
                fut.exception()
            return
        if not return_exceptions:
            if fut.cancelled():
                exc = fut._make_cancelled_error()
                outer.set_exception(exc)
                return
            else:
                exc = fut.exception()
                if exc is not None:
                    outer.set_exception(exc)
                    return
        if nfinished == nfuts:
            results = []
            for fut in children:
                if fut.cancelled():
                    res = exceptions.CancelledError(
                        ("" if (fut._cancel_message is None) else fut._cancel_message)
                    )
                else:
                    res = fut.exception()
                    if res is None:
                        res = fut.result()
                results.append(res)
            if outer._cancel_requested:
                exc = fut._make_cancelled_error()
                outer.set_exception(exc)
            else:
                outer.set_result(results)

    arg_to_fut = {}
    children = []
    nfuts = 0
    nfinished = 0
    loop = None
    for arg in coros_or_futures:
        if arg not in arg_to_fut:
            fut = ensure_future(arg, loop=loop)
            if loop is None:
                loop = futures._get_loop(fut)
            if fut is not arg:
                fut._log_destroy_pending = False
            nfuts += 1
            arg_to_fut[arg] = fut
            fut.add_done_callback(_done_callback)
        else:
            fut = arg_to_fut[arg]
        children.append(fut)
    outer = _GatheringFuture(children, loop=loop)
    return outer


def shield(arg):
    "Wait for a future, shielding it from cancellation.\n\n    The statement\n\n        res = await shield(something())\n\n    is exactly equivalent to the statement\n\n        res = await something()\n\n    *except* that if the coroutine containing it is cancelled, the\n    task running in something() is not cancelled.  From the POV of\n    something(), the cancellation did not happen.  But its caller is\n    still cancelled, so the yield-from expression still raises\n    CancelledError.  Note: If something() is cancelled by other means\n    this will still cancel shield().\n\n    If you want to completely ignore cancellation (not recommended)\n    you can combine shield() with a try/except clause, as follows:\n\n        try:\n            res = await shield(something())\n        except CancelledError:\n            res = None\n    "
    inner = ensure_future(arg)
    if inner.done():
        return inner
    loop = futures._get_loop(inner)
    outer = loop.create_future()

    def _inner_done_callback(inner):
        if outer.cancelled():
            if not inner.cancelled():
                inner.exception()
            return
        if inner.cancelled():
            outer.cancel()
        else:
            exc = inner.exception()
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(inner.result())

    def _outer_done_callback(outer):
        if not inner.done():
            inner.remove_done_callback(_inner_done_callback)

    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer


def run_coroutine_threadsafe(coro, loop):
    "Submit a coroutine object to a given event loop.\n\n    Return a concurrent.futures.Future to access the result.\n    "
    if not coroutines.iscoroutine(coro):
        raise TypeError("A coroutine object is required")
    future = concurrent.futures.Future()

    def callback():
        try:
            futures._chain_future(ensure_future(coro, loop=loop), future)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            if future.set_running_or_notify_cancel():
                future.set_exception(exc)
            raise

    loop.call_soon_threadsafe(callback)
    return future


_all_tasks = weakref.WeakSet()
_current_tasks = {}


def _register_task(task):
    "Register a new task in asyncio as executed by loop."
    _all_tasks.add(task)


def _enter_task(loop, task):
    current_task = _current_tasks.get(loop)
    if current_task is not None:
        raise RuntimeError(
            f"Cannot enter into task {task!r} while another task {current_task!r} is being executed."
        )
    _current_tasks[loop] = task


def _leave_task(loop, task):
    current_task = _current_tasks.get(loop)
    if current_task is not task:
        raise RuntimeError(
            f"Leaving task {task!r} does not match the current task {current_task!r}."
        )
    del _current_tasks[loop]


def _unregister_task(task):
    "Unregister a task."
    _all_tasks.discard(task)


_py_register_task = _register_task
_py_unregister_task = _unregister_task
_py_enter_task = _enter_task
_py_leave_task = _leave_task
try:
    from _asyncio import (
        _register_task,
        _unregister_task,
        _enter_task,
        _leave_task,
        _all_tasks,
        _current_tasks,
    )
except ImportError:
    pass
else:
    _c_register_task = _register_task
    _c_unregister_task = _unregister_task
    _c_enter_task = _enter_task
    _c_leave_task = _leave_task
