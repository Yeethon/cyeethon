"Thread-local objects.\n\n(Note that this module provides a Python version of the threading.local\n class.  Depending on the version of Python you're using, there may be a\n faster one available.  You should always import the `local` class from\n `threading`.)\n\nThread-local objects support the management of thread-local data.\nIf you have data that you want to be local to a thread, simply create\na thread-local object and use its attributes:\n\n  >>> mydata = local()\n  >>> mydata.number = 42\n  >>> mydata.number\n  42\n\nYou can also access the local-object's dictionary:\n\n  >>> mydata.__dict__\n  {'number': 42}\n  >>> mydata.__dict__.setdefault('widgets', [])\n  []\n  >>> mydata.widgets\n  []\n\nWhat's important about thread-local objects is that their data are\nlocal to a thread. If we access the data in a different thread:\n\n  >>> log = []\n  >>> def f():\n  ...     items = sorted(mydata.__dict__.items())\n  ...     log.append(items)\n  ...     mydata.number = 11\n  ...     log.append(mydata.number)\n\n  >>> import threading\n  >>> thread = threading.Thread(target=f)\n  >>> thread.start()\n  >>> thread.join()\n  >>> log\n  [[], 11]\n\nwe get different data.  Furthermore, changes made in the other thread\ndon't affect data seen in this thread:\n\n  >>> mydata.number\n  42\n\nOf course, values you get from a local object, including a __dict__\nattribute, are for whatever thread was current at the time the\nattribute was read.  For that reason, you generally don't want to save\nthese values across threads, as they apply only to the thread they\ncame from.\n\nYou can create custom local objects by subclassing the local class:\n\n  >>> class MyLocal(local):\n  ...     number = 2\n  ...     def __init__(self, /, **kw):\n  ...         self.__dict__.update(kw)\n  ...     def squared(self):\n  ...         return self.number ** 2\n\nThis can be useful to support default values, methods and\ninitialization.  Note that if you define an __init__ method, it will be\ncalled each time the local object is used in a separate thread.  This\nis necessary to initialize each thread's dictionary.\n\nNow if we create a local object:\n\n  >>> mydata = MyLocal(color='red')\n\nNow we have a default number:\n\n  >>> mydata.number\n  2\n\nan initial color:\n\n  >>> mydata.color\n  'red'\n  >>> del mydata.color\n\nAnd a method that operates on the data:\n\n  >>> mydata.squared()\n  4\n\nAs before, we can access the data in a separate thread:\n\n  >>> log = []\n  >>> thread = threading.Thread(target=f)\n  >>> thread.start()\n  >>> thread.join()\n  >>> log\n  [[('color', 'red')], 11]\n\nwithout affecting this thread's data:\n\n  >>> mydata.number\n  2\n  >>> mydata.color\n  Traceback (most recent call last):\n  ...\n  AttributeError: 'MyLocal' object has no attribute 'color'\n\nNote that subclasses can define slots, but they are not thread\nlocal. They are shared across threads:\n\n  >>> class MyLocal(local):\n  ...     __slots__ = 'number'\n\n  >>> mydata = MyLocal()\n  >>> mydata.number = 42\n  >>> mydata.color = 'red'\n\nSo, the separate thread:\n\n  >>> thread = threading.Thread(target=f)\n  >>> thread.start()\n  >>> thread.join()\n\naffects what we see:\n\n  >>> mydata.number\n  11\n\n>>> del mydata\n"
from weakref import ref
from contextlib import contextmanager

__all__ = ["local"]


class _localimpl:
    "A class managing thread-local dicts"
    __slots__ = ("key", "dicts", "localargs", "locallock", "__weakref__")

    def __init__(self):
        self.key = "_threading_local._localimpl." + str(id(self))
        self.dicts = {}

    def get_dict(self):
        "Return the dict for the current thread. Raises KeyError if none\n        defined."
        thread = current_thread()
        return self.dicts[id(thread)][1]

    def create_dict(self):
        "Create a new dict for the current thread, and return it."
        localdict = {}
        key = self.key
        thread = current_thread()
        idt = id(thread)

        def local_deleted(_, key=key):
            thread = wrthread()
            if thread is not None:
                del thread.__dict__[key]

        def thread_deleted(_, idt=idt):
            local = wrlocal()
            if local is not None:
                dct = local.dicts.pop(idt)

        wrlocal = ref(self, local_deleted)
        wrthread = ref(thread, thread_deleted)
        thread.__dict__[key] = wrlocal
        self.dicts[idt] = (wrthread, localdict)
        return localdict


@contextmanager
def _patch(self):
    impl = object.__getattribute__(self, "_local__impl")
    try:
        dct = impl.get_dict()
    except KeyError:
        dct = impl.create_dict()
        (args, kw) = impl.localargs
        self.__init__(*args, **kw)
    with impl.locallock:
        object.__setattr__(self, "__dict__", dct)
        (yield)


class local:
    __slots__ = ("_local__impl", "__dict__")

    def __new__(cls, /, *args, **kw):
        if (args or kw) and (cls.__init__ is object.__init__):
            raise TypeError("Initialization arguments are not supported")
        self = object.__new__(cls)
        impl = _localimpl()
        impl.localargs = (args, kw)
        impl.locallock = RLock()
        object.__setattr__(self, "_local__impl", impl)
        impl.create_dict()
        return self

    def __getattribute__(self, name):
        with _patch(self):
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name == "__dict__":
            raise AttributeError(
                (
                    "%r object attribute '__dict__' is read-only"
                    % self.__class__.__name__
                )
            )
        with _patch(self):
            return object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name == "__dict__":
            raise AttributeError(
                (
                    "%r object attribute '__dict__' is read-only"
                    % self.__class__.__name__
                )
            )
        with _patch(self):
            return object.__delattr__(self, name)


from threading import current_thread, RLock
