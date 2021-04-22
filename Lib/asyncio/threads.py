"High-level support for working with threads in asyncio"
import functools
import contextvars
from . import events

__all__ = ("to_thread",)


async def to_thread(func, /, *args, **kwargs):
    "Asynchronously run function *func* in a separate thread.\n\n    Any *args and **kwargs supplied for this function are directly passed\n    to *func*. Also, the current :class:`contextvars.Context` is propogated,\n    allowing context variables from the main thread to be accessed in the\n    separate thread.\n\n    Return a coroutine that can be awaited to get the eventual result of *func*.\n    "
    loop = events.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)
