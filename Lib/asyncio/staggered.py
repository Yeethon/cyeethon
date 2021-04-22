"Support for running coroutines in parallel with staggered start times."
__all__ = ("staggered_race",)
import contextlib
import typing
from . import events
from . import exceptions as exceptions_mod
from . import locks
from . import tasks


async def staggered_race(
    coro_fns: typing.Iterable[typing.Callable[([], typing.Awaitable)]],
    delay: typing.Optional[float],
    *,
    loop: events.AbstractEventLoop = None
) -> typing.Tuple[
    (typing.Any, typing.Optional[int], typing.List[typing.Optional[Exception]])
]:
    "Run coroutines with staggered start times and take the first to finish.\n\n    This method takes an iterable of coroutine functions. The first one is\n    started immediately. From then on, whenever the immediately preceding one\n    fails (raises an exception), or when *delay* seconds has passed, the next\n    coroutine is started. This continues until one of the coroutines complete\n    successfully, in which case all others are cancelled, or until all\n    coroutines fail.\n\n    The coroutines provided should be well-behaved in the following way:\n\n    * They should only ``return`` if completed successfully.\n\n    * They should always raise an exception if they did not complete\n      successfully. In particular, if they handle cancellation, they should\n      probably reraise, like this::\n\n        try:\n            # do work\n        except asyncio.CancelledError:\n            # undo partially completed work\n            raise\n\n    Args:\n        coro_fns: an iterable of coroutine functions, i.e. callables that\n            return a coroutine object when called. Use ``functools.partial`` or\n            lambdas to pass arguments.\n\n        delay: amount of time, in seconds, between starting coroutines. If\n            ``None``, the coroutines will run sequentially.\n\n        loop: the event loop to use.\n\n    Returns:\n        tuple *(winner_result, winner_index, exceptions)* where\n\n        - *winner_result*: the result of the winning coroutine, or ``None``\n          if no coroutines won.\n\n        - *winner_index*: the index of the winning coroutine in\n          ``coro_fns``, or ``None`` if no coroutines won. If the winning\n          coroutine may return None on success, *winner_index* can be used\n          to definitively determine whether any coroutine won.\n\n        - *exceptions*: list of exceptions returned by the coroutines.\n          ``len(exceptions)`` is equal to the number of coroutines actually\n          started, and the order is the same as in ``coro_fns``. The winning\n          coroutine's entry is ``None``.\n\n    "
    loop = loop or events.get_running_loop()
    enum_coro_fns = enumerate(coro_fns)
    winner_result = None
    winner_index = None
    exceptions = []
    running_tasks = []

    async def run_one_coro(previous_failed: typing.Optional[locks.Event]) -> None:
        if previous_failed is not None:
            with contextlib.suppress(exceptions_mod.TimeoutError):
                (await tasks.wait_for(previous_failed.wait(), delay))
        try:
            (this_index, coro_fn) = next(enum_coro_fns)
        except StopIteration:
            return
        this_failed = locks.Event()
        next_task = loop.create_task(run_one_coro(this_failed))
        running_tasks.append(next_task)
        assert len(running_tasks) == (this_index + 2)
        exceptions.append(None)
        assert len(exceptions) == (this_index + 1)
        try:
            result = await coro_fn()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            exceptions[this_index] = e
            this_failed.set()
        else:
            nonlocal winner_index, winner_result
            assert winner_index is None
            winner_index = this_index
            winner_result = result
            for (i, t) in enumerate(running_tasks):
                if i != this_index:
                    t.cancel()

    first_task = loop.create_task(run_one_coro(None))
    running_tasks.append(first_task)
    try:
        done_count = 0
        while done_count != len(running_tasks):
            (done, _) = await tasks.wait(running_tasks)
            done_count = len(done)
            if __debug__:
                for d in done:
                    if d.done() and (not d.cancelled()) and d.exception():
                        raise d.exception()
        return (winner_result, winner_index, exceptions)
    finally:
        for t in running_tasks:
            t.cancel()
