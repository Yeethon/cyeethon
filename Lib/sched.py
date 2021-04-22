'A generally useful event scheduler class.\n\nEach instance of this class manages its own queue.\nNo multi-threading is implied; you are supposed to hack that\nyourself, or use a single instance per application.\n\nEach instance is parametrized with two functions, one that is\nsupposed to return the current time, one that is supposed to\nimplement a delay.  You can implement real-time scheduling by\nsubstituting time and sleep from built-in module time, or you can\nimplement simulated time by writing your own functions.  This can\nalso be used to integrate scheduling with STDWIN events; the delay\nfunction is allowed to modify the queue.  Time can be expressed as\nintegers or floating point numbers, as long as it is consistent.\n\nEvents are specified by tuples (time, priority, action, argument, kwargs).\nAs in UNIX, lower priority numbers mean higher priority; in this\nway the queue can be maintained as a priority queue.  Execution of the\nevent means calling the action function, passing it the argument\nsequence in "argument" (remember that in Python, multiple function\narguments are be packed in a sequence) and keyword parameters in "kwargs".\nThe action function may be an instance method so it\nhas another way to reference private data (besides global variables).\n'
import time
import heapq
from collections import namedtuple
from itertools import count
import threading
from time import monotonic as _time

__all__ = ["scheduler"]
Event = namedtuple("Event", "time, priority, sequence, action, argument, kwargs")
Event.time.__doc__ = "Numeric type compatible with the return value of the\ntimefunc function passed to the constructor."
Event.priority.__doc__ = "Events scheduled for the same time will be executed\nin the order of their priority."
Event.sequence.__doc__ = "A continually increasing sequence number that\n    separates events if time and priority are equal."
Event.action.__doc__ = (
    "Executing the event means executing\naction(*argument, **kwargs)"
)
Event.argument.__doc__ = (
    "argument is a sequence holding the positional\narguments for the action."
)
Event.kwargs.__doc__ = (
    "kwargs is a dictionary holding the keyword\narguments for the action."
)
_sentinel = object()


class scheduler:
    def __init__(self, timefunc=_time, delayfunc=time.sleep):
        "Initialize a new instance, passing the time and delay\n        functions"
        self._queue = []
        self._lock = threading.RLock()
        self.timefunc = timefunc
        self.delayfunc = delayfunc
        self._sequence_generator = count()

    def enterabs(self, time, priority, action, argument=(), kwargs=_sentinel):
        "Enter a new event in the queue at an absolute time.\n\n        Returns an ID for the event which can be used to remove it,\n        if necessary.\n\n        "
        if kwargs is _sentinel:
            kwargs = {}
        with self._lock:
            event = Event(
                time, priority, next(self._sequence_generator), action, argument, kwargs
            )
            heapq.heappush(self._queue, event)
        return event

    def enter(self, delay, priority, action, argument=(), kwargs=_sentinel):
        "A variant that specifies the time as a relative time.\n\n        This is actually the more commonly used interface.\n\n        "
        time = self.timefunc() + delay
        return self.enterabs(time, priority, action, argument, kwargs)

    def cancel(self, event):
        "Remove an event from the queue.\n\n        This must be presented the ID as returned by enter().\n        If the event is not in the queue, this raises ValueError.\n\n        "
        with self._lock:
            self._queue.remove(event)
            heapq.heapify(self._queue)

    def empty(self):
        "Check whether the queue is empty."
        with self._lock:
            return not self._queue

    def run(self, blocking=True):
        "Execute events until the queue is empty.\n        If blocking is False executes the scheduled events due to\n        expire soonest (if any) and then return the deadline of the\n        next scheduled call in the scheduler.\n\n        When there is a positive delay until the first event, the\n        delay function is called and the event is left in the queue;\n        otherwise, the event is removed from the queue and executed\n        (its action function is called, passing it the argument).  If\n        the delay function returns prematurely, it is simply\n        restarted.\n\n        It is legal for both the delay function and the action\n        function to modify the queue or to raise an exception;\n        exceptions are not caught but the scheduler's state remains\n        well-defined so run() may be called again.\n\n        A questionable hack is added to allow other threads to run:\n        just after an event is executed, a delay of 0 is executed, to\n        avoid monopolizing the CPU when other threads are also\n        runnable.\n\n        "
        lock = self._lock
        q = self._queue
        delayfunc = self.delayfunc
        timefunc = self.timefunc
        pop = heapq.heappop
        while True:
            with lock:
                if not q:
                    break
                (time, priority, sequence, action, argument, kwargs) = q[0]
                now = timefunc()
                if time > now:
                    delay = True
                else:
                    delay = False
                    pop(q)
            if delay:
                if not blocking:
                    return time - now
                delayfunc((time - now))
            else:
                action(*argument, **kwargs)
                delayfunc(0)

    @property
    def queue(self):
        "An ordered list of upcoming events.\n\n        Events are named tuples with fields for:\n            time, priority, action, arguments, kwargs\n\n        "
        with self._lock:
            events = self._queue[:]
        return list(map(heapq.heappop, ([events] * len(events))))
