"Utilities for with-statement contexts.  See PEP 343."
import abc
import sys
import _collections_abc
from collections import deque
from functools import wraps
from types import MethodType, GenericAlias

__all__ = [
    "asynccontextmanager",
    "contextmanager",
    "closing",
    "nullcontext",
    "AbstractContextManager",
    "AbstractAsyncContextManager",
    "AsyncExitStack",
    "ContextDecorator",
    "ExitStack",
    "redirect_stdout",
    "redirect_stderr",
    "suppress",
    "aclosing",
]


class AbstractContextManager(abc.ABC):
    "An abstract base class for context managers."
    __class_getitem__ = classmethod(GenericAlias)

    def __enter__(self):
        "Return `self` upon entering the runtime context."
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        "Raise any exception triggered within the runtime context."
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractContextManager:
            return _collections_abc._check_methods(C, "__enter__", "__exit__")
        return NotImplemented


class AbstractAsyncContextManager(abc.ABC):
    "An abstract base class for asynchronous context managers."
    __class_getitem__ = classmethod(GenericAlias)

    async def __aenter__(self):
        "Return `self` upon entering the runtime context."
        return self

    @abc.abstractmethod
    async def __aexit__(self, exc_type, exc_value, traceback):
        "Raise any exception triggered within the runtime context."
        return None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is AbstractAsyncContextManager:
            return _collections_abc._check_methods(C, "__aenter__", "__aexit__")
        return NotImplemented


class ContextDecorator(object):
    "A base class or mixin that enables context managers to work as decorators."

    def _recreate_cm(self):
        "Return a recreated instance of self.\n\n        Allows an otherwise one-shot context manager like\n        _GeneratorContextManager to support use as\n        a decorator via implicit recreation.\n\n        This is a private interface just for _GeneratorContextManager.\n        See issue #11647 for details.\n        "
        return self

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            with self._recreate_cm():
                return func(*args, **kwds)

        return inner


class AsyncContextDecorator(object):
    "A base class or mixin that enables async context managers to work as decorators."

    def _recreate_cm(self):
        "Return a recreated instance of self.\n        "
        return self

    def __call__(self, func):
        @wraps(func)
        async def inner(*args, **kwds):
            async with self._recreate_cm():
                return await func(*args, **kwds)

        return inner


class _GeneratorContextManagerBase:
    "Shared functionality for @contextmanager and @asynccontextmanager."

    def __init__(self, func, args, kwds):
        self.gen = func(*args, **kwds)
        (self.func, self.args, self.kwds) = (func, args, kwds)
        doc = getattr(func, "__doc__", None)
        if doc is None:
            doc = type(self).__doc__
        self.__doc__ = doc


class _GeneratorContextManager(
    _GeneratorContextManagerBase, AbstractContextManager, ContextDecorator
):
    "Helper for @contextmanager decorator."

    def _recreate_cm(self):
        return self.__class__(self.func, self.args, self.kwds)

    def __enter__(self):
        del self.args, self.kwds, self.func
        try:
            return next(self.gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                next(self.gen)
            except StopIteration:
                return False
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = type()
            try:
                self.gen.throw(type, value, traceback)
            except StopIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if (type is StopIteration) and (exc.__cause__ is value):
                    return False
                raise
            except:
                if sys.exc_info()[1] is value:
                    return False
                raise
            raise RuntimeError("generator didn't stop after throw()")


class _AsyncGeneratorContextManager(
    _GeneratorContextManagerBase, AbstractAsyncContextManager, AsyncContextDecorator
):
    "Helper for @asynccontextmanager."

    def _recreate_cm(self):
        return self.__class__(self.func, self.args, self.kwds)

    async def __aenter__(self):
        try:
            return await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("generator didn't yield") from None

    async def __aexit__(self, typ, value, traceback):
        if typ is None:
            try:
                (await self.gen.__anext__())
            except StopAsyncIteration:
                return
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = typ()
            try:
                (await self.gen.athrow(typ, value, traceback))
                raise RuntimeError("generator didn't stop after athrow()")
            except StopAsyncIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if isinstance(value, (StopIteration, StopAsyncIteration)):
                    if exc.__cause__ is value:
                        return False
                raise
            except BaseException as exc:
                if exc is not value:
                    raise


def contextmanager(func):
    "@contextmanager decorator.\n\n    Typical usage:\n\n        @contextmanager\n        def some_generator(<arguments>):\n            <setup>\n            try:\n                yield <value>\n            finally:\n                <cleanup>\n\n    This makes this:\n\n        with some_generator(<arguments>) as <variable>:\n            <body>\n\n    equivalent to this:\n\n        <setup>\n        try:\n            <variable> = <value>\n            <body>\n        finally:\n            <cleanup>\n    "

    @wraps(func)
    def helper(*args, **kwds):
        return _GeneratorContextManager(func, args, kwds)

    return helper


def asynccontextmanager(func):
    "@asynccontextmanager decorator.\n\n    Typical usage:\n\n        @asynccontextmanager\n        async def some_async_generator(<arguments>):\n            <setup>\n            try:\n                yield <value>\n            finally:\n                <cleanup>\n\n    This makes this:\n\n        async with some_async_generator(<arguments>) as <variable>:\n            <body>\n\n    equivalent to this:\n\n        <setup>\n        try:\n            <variable> = <value>\n            <body>\n        finally:\n            <cleanup>\n    "

    @wraps(func)
    def helper(*args, **kwds):
        return _AsyncGeneratorContextManager(func, args, kwds)

    return helper


class closing(AbstractContextManager):
    "Context to automatically close something at the end of a block.\n\n    Code like this:\n\n        with closing(<module>.open(<arguments>)) as f:\n            <block>\n\n    is equivalent to this:\n\n        f = <module>.open(<arguments>)\n        try:\n            <block>\n        finally:\n            f.close()\n\n    "

    def __init__(self, thing):
        self.thing = thing

    def __enter__(self):
        return self.thing

    def __exit__(self, *exc_info):
        self.thing.close()


class aclosing(AbstractAsyncContextManager):
    "Async context manager for safely finalizing an asynchronously cleaned-up\n    resource such as an async generator, calling its ``aclose()`` method.\n\n    Code like this:\n\n        async with aclosing(<module>.fetch(<arguments>)) as agen:\n            <block>\n\n    is equivalent to this:\n\n        agen = <module>.fetch(<arguments>)\n        try:\n            <block>\n        finally:\n            await agen.aclose()\n\n    "

    def __init__(self, thing):
        self.thing = thing

    async def __aenter__(self):
        return self.thing

    async def __aexit__(self, *exc_info):
        (await self.thing.aclose())


class _RedirectStream(AbstractContextManager):
    _stream = None

    def __init__(self, new_target):
        self._new_target = new_target
        self._old_targets = []

    def __enter__(self):
        self._old_targets.append(getattr(sys, self._stream))
        setattr(sys, self._stream, self._new_target)
        return self._new_target

    def __exit__(self, exctype, excinst, exctb):
        setattr(sys, self._stream, self._old_targets.pop())


class redirect_stdout(_RedirectStream):
    "Context manager for temporarily redirecting stdout to another file.\n\n        # How to send help() to stderr\n        with redirect_stdout(sys.stderr):\n            help(dir)\n\n        # How to write help() to a file\n        with open('help.txt', 'w') as f:\n            with redirect_stdout(f):\n                help(pow)\n    "
    _stream = "stdout"


class redirect_stderr(_RedirectStream):
    "Context manager for temporarily redirecting stderr to another file."
    _stream = "stderr"


class suppress(AbstractContextManager):
    "Context manager to suppress specified exceptions\n\n    After the exception is suppressed, execution proceeds with the next\n    statement following the with statement.\n\n         with suppress(FileNotFoundError):\n             os.remove(somefile)\n         # Execution still resumes here if the file was already removed\n    "

    def __init__(self, *exceptions):
        self._exceptions = exceptions

    def __enter__(self):
        pass

    def __exit__(self, exctype, excinst, exctb):
        return (exctype is not None) and issubclass(exctype, self._exceptions)


class _BaseExitStack:
    "A base class for ExitStack and AsyncExitStack."

    @staticmethod
    def _create_exit_wrapper(cm, cm_exit):
        return MethodType(cm_exit, cm)

    @staticmethod
    def _create_cb_wrapper(callback, /, *args, **kwds):
        def _exit_wrapper(exc_type, exc, tb):
            callback(*args, **kwds)

        return _exit_wrapper

    def __init__(self):
        self._exit_callbacks = deque()

    def pop_all(self):
        "Preserve the context stack by transferring it to a new instance."
        new_stack = type(self)()
        new_stack._exit_callbacks = self._exit_callbacks
        self._exit_callbacks = deque()
        return new_stack

    def push(self, exit):
        "Registers a callback with the standard __exit__ method signature.\n\n        Can suppress exceptions the same way __exit__ method can.\n        Also accepts any object with an __exit__ method (registering a call\n        to the method instead of the object itself).\n        "
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__exit__
        except AttributeError:
            self._push_exit_callback(exit)
        else:
            self._push_cm_exit(exit, exit_method)
        return exit

    def enter_context(self, cm):
        "Enters the supplied context manager.\n\n        If successful, also pushes its __exit__ method as a callback and\n        returns the result of the __enter__ method.\n        "
        _cm_type = type(cm)
        _exit = _cm_type.__exit__
        result = _cm_type.__enter__(cm)
        self._push_cm_exit(cm, _exit)
        return result

    def callback(self, callback, /, *args, **kwds):
        "Registers an arbitrary callback and arguments.\n\n        Cannot suppress exceptions.\n        "
        _exit_wrapper = self._create_cb_wrapper(callback, *args, **kwds)
        _exit_wrapper.__wrapped__ = callback
        self._push_exit_callback(_exit_wrapper)
        return callback

    def _push_cm_exit(self, cm, cm_exit):
        "Helper to correctly register callbacks to __exit__ methods."
        _exit_wrapper = self._create_exit_wrapper(cm, cm_exit)
        self._push_exit_callback(_exit_wrapper, True)

    def _push_exit_callback(self, callback, is_sync=True):
        self._exit_callbacks.append((is_sync, callback))


class ExitStack(_BaseExitStack, AbstractContextManager):
    "Context manager for dynamic management of a stack of exit callbacks.\n\n    For example:\n        with ExitStack() as stack:\n            files = [stack.enter_context(open(fname)) for fname in filenames]\n            # All opened files will automatically be closed at the end of\n            # the with statement, even if attempts to open files later\n            # in the list raise an exception.\n    "

    def __enter__(self):
        return self

    def __exit__(self, *exc_details):
        received_exc = exc_details[0] is not None
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            while 1:
                exc_context = new_exc.__context__
                if exc_context is old_exc:
                    return
                if (exc_context is None) or (exc_context is frame_exc):
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        suppressed_exc = False
        pending_raise = False
        while self._exit_callbacks:
            (is_sync, cb) = self._exit_callbacks.pop()
            assert is_sync
            try:
                if cb(*exc_details):
                    suppressed_exc = True
                    pending_raise = False
                    exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                _fix_exception_context(new_exc_details[1], exc_details[1])
                pending_raise = True
                exc_details = new_exc_details
        if pending_raise:
            try:
                fixed_ctx = exc_details[1].__context__
                raise exc_details[1]
            except BaseException:
                exc_details[1].__context__ = fixed_ctx
                raise
        return received_exc and suppressed_exc

    def close(self):
        "Immediately unwind the context stack."
        self.__exit__(None, None, None)


class AsyncExitStack(_BaseExitStack, AbstractAsyncContextManager):
    "Async context manager for dynamic management of a stack of exit\n    callbacks.\n\n    For example:\n        async with AsyncExitStack() as stack:\n            connections = [await stack.enter_async_context(get_connection())\n                for i in range(5)]\n            # All opened connections will automatically be released at the\n            # end of the async with statement, even if attempts to open a\n            # connection later in the list raise an exception.\n    "

    @staticmethod
    def _create_async_exit_wrapper(cm, cm_exit):
        return MethodType(cm_exit, cm)

    @staticmethod
    def _create_async_cb_wrapper(callback, /, *args, **kwds):
        async def _exit_wrapper(exc_type, exc, tb):
            (await callback(*args, **kwds))

        return _exit_wrapper

    async def enter_async_context(self, cm):
        "Enters the supplied async context manager.\n\n        If successful, also pushes its __aexit__ method as a callback and\n        returns the result of the __aenter__ method.\n        "
        _cm_type = type(cm)
        _exit = _cm_type.__aexit__
        result = await _cm_type.__aenter__(cm)
        self._push_async_cm_exit(cm, _exit)
        return result

    def push_async_exit(self, exit):
        "Registers a coroutine function with the standard __aexit__ method\n        signature.\n\n        Can suppress exceptions the same way __aexit__ method can.\n        Also accepts any object with an __aexit__ method (registering a call\n        to the method instead of the object itself).\n        "
        _cb_type = type(exit)
        try:
            exit_method = _cb_type.__aexit__
        except AttributeError:
            self._push_exit_callback(exit, False)
        else:
            self._push_async_cm_exit(exit, exit_method)
        return exit

    def push_async_callback(self, callback, /, *args, **kwds):
        "Registers an arbitrary coroutine function and arguments.\n\n        Cannot suppress exceptions.\n        "
        _exit_wrapper = self._create_async_cb_wrapper(callback, *args, **kwds)
        _exit_wrapper.__wrapped__ = callback
        self._push_exit_callback(_exit_wrapper, False)
        return callback

    async def aclose(self):
        "Immediately unwind the context stack."
        (await self.__aexit__(None, None, None))

    def _push_async_cm_exit(self, cm, cm_exit):
        "Helper to correctly register coroutine function to __aexit__\n        method."
        _exit_wrapper = self._create_async_exit_wrapper(cm, cm_exit)
        self._push_exit_callback(_exit_wrapper, False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_details):
        received_exc = exc_details[0] is not None
        frame_exc = sys.exc_info()[1]

        def _fix_exception_context(new_exc, old_exc):
            while 1:
                exc_context = new_exc.__context__
                if exc_context is old_exc:
                    return
                if (exc_context is None) or (exc_context is frame_exc):
                    break
                new_exc = exc_context
            new_exc.__context__ = old_exc

        suppressed_exc = False
        pending_raise = False
        while self._exit_callbacks:
            (is_sync, cb) = self._exit_callbacks.pop()
            try:
                if is_sync:
                    cb_suppress = cb(*exc_details)
                else:
                    cb_suppress = await cb(*exc_details)
                if cb_suppress:
                    suppressed_exc = True
                    pending_raise = False
                    exc_details = (None, None, None)
            except:
                new_exc_details = sys.exc_info()
                _fix_exception_context(new_exc_details[1], exc_details[1])
                pending_raise = True
                exc_details = new_exc_details
        if pending_raise:
            try:
                fixed_ctx = exc_details[1].__context__
                raise exc_details[1]
            except BaseException:
                exc_details[1].__context__ = fixed_ctx
                raise
        return received_exc and suppressed_exc


class nullcontext(AbstractContextManager, AbstractAsyncContextManager):
    "Context manager that does no additional processing.\n\n    Used as a stand-in for a normal context manager, when a particular\n    block of code is only sometimes used with a normal context manager:\n\n    cm = optional_cm if condition else nullcontext()\n    with cm:\n        # Perform operation, using optional_cm if condition is True\n    "

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass

    async def __aenter__(self):
        return self.enter_result

    async def __aexit__(self, *excinfo):
        pass
