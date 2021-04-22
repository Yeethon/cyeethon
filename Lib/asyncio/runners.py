__all__ = ("run",)
from . import coroutines
from . import events
from . import tasks


def run(main, *, debug=None):
    "Execute the coroutine and return the result.\n\n    This function runs the passed coroutine, taking care of\n    managing the asyncio event loop and finalizing asynchronous\n    generators.\n\n    This function cannot be called when another asyncio event loop is\n    running in the same thread.\n\n    If debug is True, the event loop will be run in debug mode.\n\n    This function always creates a new event loop and closes it at the end.\n    It should be used as a main entry point for asyncio programs, and should\n    ideally only be called once.\n\n    Example:\n\n        async def main():\n            await asyncio.sleep(1)\n            print('hello')\n\n        asyncio.run(main())\n    "
    if events._get_running_loop() is not None:
        raise RuntimeError("asyncio.run() cannot be called from a running event loop")
    if not coroutines.iscoroutine(main):
        raise ValueError("a coroutine was expected, got {!r}".format(main))
    loop = events.new_event_loop()
    try:
        events.set_event_loop(loop)
        if debug is not None:
            loop.set_debug(debug)
        return loop.run_until_complete(main)
    finally:
        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            events.set_event_loop(None)
            loop.close()


def _cancel_all_tasks(loop):
    to_cancel = tasks.all_tasks(loop)
    if not to_cancel:
        return
    for task in to_cancel:
        task.cancel()
    loop.run_until_complete(tasks.gather(*to_cancel, return_exceptions=True))
    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )
