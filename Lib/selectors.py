"Selectors module.\n\nThis module allows high-level and efficient I/O multiplexing, built upon the\n`select` module primitives.\n"
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from collections.abc import Mapping
import math
import select
import sys

EVENT_READ = 1 << 0
EVENT_WRITE = 1 << 1


def _fileobj_to_fd(fileobj):
    "Return a file descriptor from a file object.\n\n    Parameters:\n    fileobj -- file object or file descriptor\n\n    Returns:\n    corresponding file descriptor\n\n    Raises:\n    ValueError if the object is invalid\n    "
    if isinstance(fileobj, int):
        fd = fileobj
    else:
        try:
            fd = int(fileobj.fileno())
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Invalid file object: {!r}".format(fileobj)) from None
    if fd < 0:
        raise ValueError("Invalid file descriptor: {}".format(fd))
    return fd


SelectorKey = namedtuple("SelectorKey", ["fileobj", "fd", "events", "data"])
SelectorKey.__doc__ = "SelectorKey(fileobj, fd, events, data)\n\n    Object used to associate a file object to its backing\n    file descriptor, selected event mask, and attached data.\n"
if sys.version_info >= (3, 5):
    SelectorKey.fileobj.__doc__ = "File object registered."
    SelectorKey.fd.__doc__ = "Underlying file descriptor."
    SelectorKey.events.__doc__ = "Events that must be waited for on this file object."
    SelectorKey.data.__doc__ = "Optional opaque data associated to this file object.\n    For example, this could be used to store a per-client session ID."


class _SelectorMapping(Mapping):
    "Mapping of file objects to selector keys."

    def __init__(self, selector):
        self._selector = selector

    def __len__(self):
        return len(self._selector._fd_to_key)

    def __getitem__(self, fileobj):
        try:
            fd = self._selector._fileobj_lookup(fileobj)
            return self._selector._fd_to_key[fd]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None

    def __iter__(self):
        return iter(self._selector._fd_to_key)


class BaseSelector(metaclass=ABCMeta):
    "Selector abstract base class.\n\n    A selector supports registering file objects to be monitored for specific\n    I/O events.\n\n    A file object is a file descriptor or any object with a `fileno()` method.\n    An arbitrary object can be attached to the file object, which can be used\n    for example to store context information, a callback, etc.\n\n    A selector can use various implementations (select(), poll(), epoll()...)\n    depending on the platform. The default `Selector` class uses the most\n    efficient implementation on the current platform.\n    "

    @abstractmethod
    def register(self, fileobj, events, data=None):
        "Register a file object.\n\n        Parameters:\n        fileobj -- file object or file descriptor\n        events  -- events to monitor (bitwise mask of EVENT_READ|EVENT_WRITE)\n        data    -- attached data\n\n        Returns:\n        SelectorKey instance\n\n        Raises:\n        ValueError if events is invalid\n        KeyError if fileobj is already registered\n        OSError if fileobj is closed or otherwise is unacceptable to\n                the underlying system call (if a system call is made)\n\n        Note:\n        OSError may or may not be raised\n        "
        raise NotImplementedError

    @abstractmethod
    def unregister(self, fileobj):
        "Unregister a file object.\n\n        Parameters:\n        fileobj -- file object or file descriptor\n\n        Returns:\n        SelectorKey instance\n\n        Raises:\n        KeyError if fileobj is not registered\n\n        Note:\n        If fileobj is registered but has since been closed this does\n        *not* raise OSError (even if the wrapped syscall does)\n        "
        raise NotImplementedError

    def modify(self, fileobj, events, data=None):
        "Change a registered file object monitored events or attached data.\n\n        Parameters:\n        fileobj -- file object or file descriptor\n        events  -- events to monitor (bitwise mask of EVENT_READ|EVENT_WRITE)\n        data    -- attached data\n\n        Returns:\n        SelectorKey instance\n\n        Raises:\n        Anything that unregister() or register() raises\n        "
        self.unregister(fileobj)
        return self.register(fileobj, events, data)

    @abstractmethod
    def select(self, timeout=None):
        "Perform the actual selection, until some monitored file objects are\n        ready or a timeout expires.\n\n        Parameters:\n        timeout -- if timeout > 0, this specifies the maximum wait time, in\n                   seconds\n                   if timeout <= 0, the select() call won't block, and will\n                   report the currently ready file objects\n                   if timeout is None, select() will block until a monitored\n                   file object becomes ready\n\n        Returns:\n        list of (key, events) for ready file objects\n        `events` is a bitwise mask of EVENT_READ|EVENT_WRITE\n        "
        raise NotImplementedError

    def close(self):
        "Close the selector.\n\n        This must be called to make sure that any underlying resource is freed.\n        "
        pass

    def get_key(self, fileobj):
        "Return the key associated to a registered file object.\n\n        Returns:\n        SelectorKey for this file object\n        "
        mapping = self.get_map()
        if mapping is None:
            raise RuntimeError("Selector is closed")
        try:
            return mapping[fileobj]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None

    @abstractmethod
    def get_map(self):
        "Return a mapping of file objects to selector keys."
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _BaseSelectorImpl(BaseSelector):
    "Base selector implementation."

    def __init__(self):
        self._fd_to_key = {}
        self._map = _SelectorMapping(self)

    def _fileobj_lookup(self, fileobj):
        "Return a file descriptor from a file object.\n\n        This wraps _fileobj_to_fd() to do an exhaustive search in case\n        the object is invalid but we still have it in our map.  This\n        is used by unregister() so we can unregister an object that\n        was previously registered even if it is closed.  It is also\n        used by _SelectorMapping.\n        "
        try:
            return _fileobj_to_fd(fileobj)
        except ValueError:
            for key in self._fd_to_key.values():
                if key.fileobj is fileobj:
                    return key.fd
            raise

    def register(self, fileobj, events, data=None):
        if (not events) or (events & (~(EVENT_READ | EVENT_WRITE))):
            raise ValueError("Invalid events: {!r}".format(events))
        key = SelectorKey(fileobj, self._fileobj_lookup(fileobj), events, data)
        if key.fd in self._fd_to_key:
            raise KeyError("{!r} (FD {}) is already registered".format(fileobj, key.fd))
        self._fd_to_key[key.fd] = key
        return key

    def unregister(self, fileobj):
        try:
            key = self._fd_to_key.pop(self._fileobj_lookup(fileobj))
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        return key

    def modify(self, fileobj, events, data=None):
        try:
            key = self._fd_to_key[self._fileobj_lookup(fileobj)]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        if events != key.events:
            self.unregister(fileobj)
            key = self.register(fileobj, events, data)
        elif data != key.data:
            key = key._replace(data=data)
            self._fd_to_key[key.fd] = key
        return key

    def close(self):
        self._fd_to_key.clear()
        self._map = None

    def get_map(self):
        return self._map

    def _key_from_fd(self, fd):
        "Return the key associated to a given file descriptor.\n\n        Parameters:\n        fd -- file descriptor\n\n        Returns:\n        corresponding key, or None if not found\n        "
        try:
            return self._fd_to_key[fd]
        except KeyError:
            return None


class SelectSelector(_BaseSelectorImpl):
    "Select-based selector."

    def __init__(self):
        super().__init__()
        self._readers = set()
        self._writers = set()

    def register(self, fileobj, events, data=None):
        key = super().register(fileobj, events, data)
        if events & EVENT_READ:
            self._readers.add(key.fd)
        if events & EVENT_WRITE:
            self._writers.add(key.fd)
        return key

    def unregister(self, fileobj):
        key = super().unregister(fileobj)
        self._readers.discard(key.fd)
        self._writers.discard(key.fd)
        return key

    if sys.platform == "win32":

        def _select(self, r, w, _, timeout=None):
            (r, w, x) = select.select(r, w, w, timeout)
            return (r, (w + x), [])

    else:
        _select = select.select

    def select(self, timeout=None):
        timeout = None if (timeout is None) else max(timeout, 0)
        ready = []
        try:
            (r, w, _) = self._select(self._readers, self._writers, [], timeout)
        except InterruptedError:
            return ready
        r = set(r)
        w = set(w)
        for fd in r | w:
            events = 0
            if fd in r:
                events |= EVENT_READ
            if fd in w:
                events |= EVENT_WRITE
            key = self._key_from_fd(fd)
            if key:
                ready.append((key, (events & key.events)))
        return ready


class _PollLikeSelector(_BaseSelectorImpl):
    "Base class shared between poll, epoll and devpoll selectors."
    _selector_cls = None
    _EVENT_READ = None
    _EVENT_WRITE = None

    def __init__(self):
        super().__init__()
        self._selector = self._selector_cls()

    def register(self, fileobj, events, data=None):
        key = super().register(fileobj, events, data)
        poller_events = 0
        if events & EVENT_READ:
            poller_events |= self._EVENT_READ
        if events & EVENT_WRITE:
            poller_events |= self._EVENT_WRITE
        try:
            self._selector.register(key.fd, poller_events)
        except:
            super().unregister(fileobj)
            raise
        return key

    def unregister(self, fileobj):
        key = super().unregister(fileobj)
        try:
            self._selector.unregister(key.fd)
        except OSError:
            pass
        return key

    def modify(self, fileobj, events, data=None):
        try:
            key = self._fd_to_key[self._fileobj_lookup(fileobj)]
        except KeyError:
            raise KeyError(f"{fileobj!r} is not registered") from None
        changed = False
        if events != key.events:
            selector_events = 0
            if events & EVENT_READ:
                selector_events |= self._EVENT_READ
            if events & EVENT_WRITE:
                selector_events |= self._EVENT_WRITE
            try:
                self._selector.modify(key.fd, selector_events)
            except:
                super().unregister(fileobj)
                raise
            changed = True
        if data != key.data:
            changed = True
        if changed:
            key = key._replace(events=events, data=data)
            self._fd_to_key[key.fd] = key
        return key

    def select(self, timeout=None):
        if timeout is None:
            timeout = None
        elif timeout <= 0:
            timeout = 0
        else:
            timeout = math.ceil((timeout * 1000.0))
        ready = []
        try:
            fd_event_list = self._selector.poll(timeout)
        except InterruptedError:
            return ready
        for (fd, event) in fd_event_list:
            events = 0
            if event & (~self._EVENT_READ):
                events |= EVENT_WRITE
            if event & (~self._EVENT_WRITE):
                events |= EVENT_READ
            key = self._key_from_fd(fd)
            if key:
                ready.append((key, (events & key.events)))
        return ready


if hasattr(select, "poll"):

    class PollSelector(_PollLikeSelector):
        "Poll-based selector."
        _selector_cls = select.poll
        _EVENT_READ = select.POLLIN
        _EVENT_WRITE = select.POLLOUT


if hasattr(select, "epoll"):

    class EpollSelector(_PollLikeSelector):
        "Epoll-based selector."
        _selector_cls = select.epoll
        _EVENT_READ = select.EPOLLIN
        _EVENT_WRITE = select.EPOLLOUT

        def fileno(self):
            return self._selector.fileno()

        def select(self, timeout=None):
            if timeout is None:
                timeout = -1
            elif timeout <= 0:
                timeout = 0
            else:
                timeout = math.ceil((timeout * 1000.0)) * 0.001
            max_ev = max(len(self._fd_to_key), 1)
            ready = []
            try:
                fd_event_list = self._selector.poll(timeout, max_ev)
            except InterruptedError:
                return ready
            for (fd, event) in fd_event_list:
                events = 0
                if event & (~select.EPOLLIN):
                    events |= EVENT_WRITE
                if event & (~select.EPOLLOUT):
                    events |= EVENT_READ
                key = self._key_from_fd(fd)
                if key:
                    ready.append((key, (events & key.events)))
            return ready

        def close(self):
            self._selector.close()
            super().close()


if hasattr(select, "devpoll"):

    class DevpollSelector(_PollLikeSelector):
        "Solaris /dev/poll selector."
        _selector_cls = select.devpoll
        _EVENT_READ = select.POLLIN
        _EVENT_WRITE = select.POLLOUT

        def fileno(self):
            return self._selector.fileno()

        def close(self):
            self._selector.close()
            super().close()


if hasattr(select, "kqueue"):

    class KqueueSelector(_BaseSelectorImpl):
        "Kqueue-based selector."

        def __init__(self):
            super().__init__()
            self._selector = select.kqueue()

        def fileno(self):
            return self._selector.fileno()

        def register(self, fileobj, events, data=None):
            key = super().register(fileobj, events, data)
            try:
                if events & EVENT_READ:
                    kev = select.kevent(key.fd, select.KQ_FILTER_READ, select.KQ_EV_ADD)
                    self._selector.control([kev], 0, 0)
                if events & EVENT_WRITE:
                    kev = select.kevent(
                        key.fd, select.KQ_FILTER_WRITE, select.KQ_EV_ADD
                    )
                    self._selector.control([kev], 0, 0)
            except:
                super().unregister(fileobj)
                raise
            return key

        def unregister(self, fileobj):
            key = super().unregister(fileobj)
            if key.events & EVENT_READ:
                kev = select.kevent(key.fd, select.KQ_FILTER_READ, select.KQ_EV_DELETE)
                try:
                    self._selector.control([kev], 0, 0)
                except OSError:
                    pass
            if key.events & EVENT_WRITE:
                kev = select.kevent(key.fd, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE)
                try:
                    self._selector.control([kev], 0, 0)
                except OSError:
                    pass
            return key

        def select(self, timeout=None):
            timeout = None if (timeout is None) else max(timeout, 0)
            max_ev = max(len(self._fd_to_key), 1)
            ready = []
            try:
                kev_list = self._selector.control(None, max_ev, timeout)
            except InterruptedError:
                return ready
            for kev in kev_list:
                fd = kev.ident
                flag = kev.filter
                events = 0
                if flag == select.KQ_FILTER_READ:
                    events |= EVENT_READ
                if flag == select.KQ_FILTER_WRITE:
                    events |= EVENT_WRITE
                key = self._key_from_fd(fd)
                if key:
                    ready.append((key, (events & key.events)))
            return ready

        def close(self):
            self._selector.close()
            super().close()


def _can_use(method):
    "Check if we can use the selector depending upon the\n    operating system. "
    selector = getattr(select, method, None)
    if selector is None:
        return False
    try:
        selector_obj = selector()
        if method == "poll":
            selector_obj.poll(0)
        else:
            selector_obj.close()
        return True
    except OSError:
        return False


if _can_use("kqueue"):
    DefaultSelector = KqueueSelector
elif _can_use("epoll"):
    DefaultSelector = EpollSelector
elif _can_use("devpoll"):
    DefaultSelector = DevpollSelector
elif _can_use("poll"):
    DefaultSelector = PollSelector
else:
    DefaultSelector = SelectSelector
