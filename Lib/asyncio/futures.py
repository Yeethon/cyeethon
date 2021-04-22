"A Future class similar to the one in PEP 3148."
__all__ = ("Future", "wrap_future", "isfuture")
import concurrent.futures
import contextvars
import logging
import sys
from . import base_futures
from . import events
from . import exceptions
from . import format_helpers

isfuture = base_futures.isfuture
_PENDING = base_futures._PENDING
_CANCELLED = base_futures._CANCELLED
_FINISHED = base_futures._FINISHED
STACK_DEBUG = logging.DEBUG - 1


class Future:
    "This class is *almost* compatible with concurrent.futures.Future.\n\n    Differences:\n\n    - This class is not thread-safe.\n\n    - result() and exception() do not take a timeout argument and\n      raise an exception when the future isn't done yet.\n\n    - Callbacks registered with add_done_callback() are always called\n      via the event loop's call_soon().\n\n    - This class is not compatible with the wait() and as_completed()\n      methods in the concurrent.futures package.\n\n    (In Python 3.4 or later we may be able to unify the implementations.)\n    "
    _state = _PENDING
    _result = None
    _exception = None
    _loop = None
    _source_traceback = None
    _cancel_message = None
    _cancelled_exc = None
    _asyncio_future_blocking = False
    __log_traceback = False

    def __init__(self, *, loop=None):
        "Initialize the future.\n\n        The optional event_loop argument allows explicitly setting the event\n        loop object used by the future. If it's not provided, the future uses\n        the default event loop.\n        "
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
        self._callbacks = []
        if self._loop.get_debug():
            self._source_traceback = format_helpers.extract_stack(sys._getframe(1))

    _repr_info = base_futures._future_repr_info

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, " ".join(self._repr_info()))

    def __del__(self):
        if not self.__log_traceback:
            return
        exc = self._exception
        context = {
            "message": f"{self.__class__.__name__} exception was never retrieved",
            "exception": exc,
            "future": self,
        }
        if self._source_traceback:
            context["source_traceback"] = self._source_traceback
        self._loop.call_exception_handler(context)

    def __class_getitem__(cls, type):
        return cls

    @property
    def _log_traceback(self):
        return self.__log_traceback

    @_log_traceback.setter
    def _log_traceback(self, val):
        if val:
            raise ValueError("_log_traceback can only be set to False")
        self.__log_traceback = False

    def get_loop(self):
        "Return the event loop the Future is bound to."
        loop = self._loop
        if loop is None:
            raise RuntimeError("Future object is not initialized.")
        return loop

    def _make_cancelled_error(self):
        "Create the CancelledError to raise if the Future is cancelled.\n\n        This should only be called once when handling a cancellation since\n        it erases the saved context exception value.\n        "
        if self._cancel_message is None:
            exc = exceptions.CancelledError()
        else:
            exc = exceptions.CancelledError(self._cancel_message)
        exc.__context__ = self._cancelled_exc
        self._cancelled_exc = None
        return exc

    def cancel(self, msg=None):
        "Cancel the future and schedule callbacks.\n\n        If the future is already done or cancelled, return False.  Otherwise,\n        change the future's state to cancelled, schedule the callbacks and\n        return True.\n        "
        self.__log_traceback = False
        if self._state != _PENDING:
            return False
        self._state = _CANCELLED
        self._cancel_message = msg
        self.__schedule_callbacks()
        return True

    def __schedule_callbacks(self):
        "Internal: Ask the event loop to call all callbacks.\n\n        The callbacks are scheduled to be called as soon as possible. Also\n        clears the callback list.\n        "
        callbacks = self._callbacks[:]
        if not callbacks:
            return
        self._callbacks[:] = []
        for (callback, ctx) in callbacks:
            self._loop.call_soon(callback, self, context=ctx)

    def cancelled(self):
        "Return True if the future was cancelled."
        return self._state == _CANCELLED

    def done(self):
        "Return True if the future is done.\n\n        Done means either that a result / exception are available, or that the\n        future was cancelled.\n        "
        return self._state != _PENDING

    def result(self):
        "Return the result this future represents.\n\n        If the future has been cancelled, raises CancelledError.  If the\n        future's result isn't yet available, raises InvalidStateError.  If\n        the future is done and has an exception set, this exception is raised.\n        "
        if self._state == _CANCELLED:
            exc = self._make_cancelled_error()
            raise exc
        if self._state != _FINISHED:
            raise exceptions.InvalidStateError("Result is not ready.")
        self.__log_traceback = False
        if self._exception is not None:
            raise self._exception
        return self._result

    def exception(self):
        "Return the exception that was set on this future.\n\n        The exception (or None if no exception was set) is returned only if\n        the future is done.  If the future has been cancelled, raises\n        CancelledError.  If the future isn't done yet, raises\n        InvalidStateError.\n        "
        if self._state == _CANCELLED:
            exc = self._make_cancelled_error()
            raise exc
        if self._state != _FINISHED:
            raise exceptions.InvalidStateError("Exception is not set.")
        self.__log_traceback = False
        return self._exception

    def add_done_callback(self, fn, *, context=None):
        "Add a callback to be run when the future becomes done.\n\n        The callback is called with a single argument - the future object. If\n        the future is already done when this is called, the callback is\n        scheduled with call_soon.\n        "
        if self._state != _PENDING:
            self._loop.call_soon(fn, self, context=context)
        else:
            if context is None:
                context = contextvars.copy_context()
            self._callbacks.append((fn, context))

    def remove_done_callback(self, fn):
        'Remove all instances of a callback from the "call when done" list.\n\n        Returns the number of callbacks removed.\n        '
        filtered_callbacks = [(f, ctx) for (f, ctx) in self._callbacks if (f != fn)]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    def set_result(self, result):
        "Mark the future done and set its result.\n\n        If the future is already done when this method is called, raises\n        InvalidStateError.\n        "
        if self._state != _PENDING:
            raise exceptions.InvalidStateError(f"{self._state}: {self!r}")
        self._result = result
        self._state = _FINISHED
        self.__schedule_callbacks()

    def set_exception(self, exception):
        "Mark the future done and set an exception.\n\n        If the future is already done when this method is called, raises\n        InvalidStateError.\n        "
        if self._state != _PENDING:
            raise exceptions.InvalidStateError(f"{self._state}: {self!r}")
        if isinstance(exception, type):
            exception = exception()
        if type(exception) is StopIteration:
            raise TypeError(
                "StopIteration interacts badly with generators and cannot be raised into a Future"
            )
        self._exception = exception
        self._state = _FINISHED
        self.__schedule_callbacks()
        self.__log_traceback = True

    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True
            (yield self)
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()

    __iter__ = __await__


_PyFuture = Future


def _get_loop(fut):
    try:
        get_loop = fut.get_loop
    except AttributeError:
        pass
    else:
        return get_loop()
    return fut._loop


def _set_result_unless_cancelled(fut, result):
    "Helper setting the result only if the future was not cancelled."
    if fut.cancelled():
        return
    fut.set_result(result)


def _convert_future_exc(exc):
    exc_class = type(exc)
    if exc_class is concurrent.futures.CancelledError:
        return exceptions.CancelledError(*exc.args)
    elif exc_class is concurrent.futures.TimeoutError:
        return exceptions.TimeoutError(*exc.args)
    elif exc_class is concurrent.futures.InvalidStateError:
        return exceptions.InvalidStateError(*exc.args)
    else:
        return exc


def _set_concurrent_future_state(concurrent, source):
    "Copy state from a future to a concurrent.futures.Future."
    assert source.done()
    if source.cancelled():
        concurrent.cancel()
    if not concurrent.set_running_or_notify_cancel():
        return
    exception = source.exception()
    if exception is not None:
        concurrent.set_exception(_convert_future_exc(exception))
    else:
        result = source.result()
        concurrent.set_result(result)


def _copy_future_state(source, dest):
    "Internal helper to copy state from another Future.\n\n    The other Future may be a concurrent.futures.Future.\n    "
    assert source.done()
    if dest.cancelled():
        return
    assert not dest.done()
    if source.cancelled():
        dest.cancel()
    else:
        exception = source.exception()
        if exception is not None:
            dest.set_exception(_convert_future_exc(exception))
        else:
            result = source.result()
            dest.set_result(result)


def _chain_future(source, destination):
    "Chain two futures so that when one completes, so does the other.\n\n    The result (or exception) of source will be copied to destination.\n    If destination is cancelled, source gets cancelled too.\n    Compatible with both asyncio.Future and concurrent.futures.Future.\n    "
    if (not isfuture(source)) and (not isinstance(source, concurrent.futures.Future)):
        raise TypeError("A future is required for source argument")
    if (not isfuture(destination)) and (
        not isinstance(destination, concurrent.futures.Future)
    ):
        raise TypeError("A future is required for destination argument")
    source_loop = _get_loop(source) if isfuture(source) else None
    dest_loop = _get_loop(destination) if isfuture(destination) else None

    def _set_state(future, other):
        if isfuture(future):
            _copy_future_state(other, future)
        else:
            _set_concurrent_future_state(future, other)

    def _call_check_cancel(destination):
        if destination.cancelled():
            if (source_loop is None) or (source_loop is dest_loop):
                source.cancel()
            else:
                source_loop.call_soon_threadsafe(source.cancel)

    def _call_set_state(source):
        if (
            destination.cancelled()
            and (dest_loop is not None)
            and dest_loop.is_closed()
        ):
            return
        if (dest_loop is None) or (dest_loop is source_loop):
            _set_state(destination, source)
        else:
            dest_loop.call_soon_threadsafe(_set_state, destination, source)

    destination.add_done_callback(_call_check_cancel)
    source.add_done_callback(_call_set_state)


def wrap_future(future, *, loop=None):
    "Wrap concurrent.futures.Future object."
    if isfuture(future):
        return future
    assert isinstance(
        future, concurrent.futures.Future
    ), f"concurrent.futures.Future is expected, got {future!r}"
    if loop is None:
        loop = events.get_event_loop()
    new_future = loop.create_future()
    _chain_future(future, new_future)
    return new_future


try:
    import _asyncio
except ImportError:
    pass
else:
    Future = _CFuture = _asyncio.Future
