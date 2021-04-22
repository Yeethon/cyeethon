__all__ = ["BaseProcess", "current_process", "active_children", "parent_process"]
import os
import sys
import signal
import itertools
import threading
from _weakrefset import WeakSet

try:
    ORIGINAL_DIR = os.path.abspath(os.getcwd())
except OSError:
    ORIGINAL_DIR = None


def current_process():
    "\n    Return process object representing the current process\n    "
    return _current_process


def active_children():
    "\n    Return list of process objects corresponding to live child processes\n    "
    _cleanup()
    return list(_children)


def parent_process():
    "\n    Return process object representing the parent process\n    "
    return _parent_process


def _cleanup():
    for p in list(_children):
        if p._popen.poll() is not None:
            _children.discard(p)


class BaseProcess(object):
    "\n    Process objects represent activity that is run in a separate process\n\n    The class is analogous to `threading.Thread`\n    "

    def _Popen(self):
        raise NotImplementedError

    def __init__(
        self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None
    ):
        assert group is None, "group argument must be None for now"
        count = next(_process_counter)
        self._identity = _current_process._identity + (count,)
        self._config = _current_process._config.copy()
        self._parent_pid = os.getpid()
        self._parent_name = _current_process.name
        self._popen = None
        self._closed = False
        self._target = target
        self._args = tuple(args)
        self._kwargs = dict(kwargs)
        self._name = name or (
            (type(self).__name__ + "-") + ":".join((str(i) for i in self._identity))
        )
        if daemon is not None:
            self.daemon = daemon
        _dangling.add(self)

    def _check_closed(self):
        if self._closed:
            raise ValueError("process object is closed")

    def run(self):
        "\n        Method to be run in sub-process; can be overridden in sub-class\n        "
        if self._target:
            self._target(*self._args, **self._kwargs)

    def start(self):
        "\n        Start child process\n        "
        self._check_closed()
        assert self._popen is None, "cannot start a process twice"
        assert (
            self._parent_pid == os.getpid()
        ), "can only start a process object created by current process"
        assert not _current_process._config.get(
            "daemon"
        ), "daemonic processes are not allowed to have children"
        _cleanup()
        self._popen = self._Popen(self)
        self._sentinel = self._popen.sentinel
        del self._target, self._args, self._kwargs
        _children.add(self)

    def terminate(self):
        "\n        Terminate process; sends SIGTERM signal or uses TerminateProcess()\n        "
        self._check_closed()
        self._popen.terminate()

    def kill(self):
        "\n        Terminate process; sends SIGKILL signal or uses TerminateProcess()\n        "
        self._check_closed()
        self._popen.kill()

    def join(self, timeout=None):
        "\n        Wait until child process terminates\n        "
        self._check_closed()
        assert self._parent_pid == os.getpid(), "can only join a child process"
        assert self._popen is not None, "can only join a started process"
        res = self._popen.wait(timeout)
        if res is not None:
            _children.discard(self)

    def is_alive(self):
        "\n        Return whether process is alive\n        "
        self._check_closed()
        if self is _current_process:
            return True
        assert self._parent_pid == os.getpid(), "can only test a child process"
        if self._popen is None:
            return False
        returncode = self._popen.poll()
        if returncode is None:
            return True
        else:
            _children.discard(self)
            return False

    def close(self):
        "\n        Close the Process object.\n\n        This method releases resources held by the Process object.  It is\n        an error to call this method if the child process is still running.\n        "
        if self._popen is not None:
            if self._popen.poll() is None:
                raise ValueError(
                    "Cannot close a process while it is still running. You should first call join() or terminate()."
                )
            self._popen.close()
            self._popen = None
            del self._sentinel
            _children.discard(self)
        self._closed = True

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        assert isinstance(name, str), "name must be a string"
        self._name = name

    @property
    def daemon(self):
        "\n        Return whether process is a daemon\n        "
        return self._config.get("daemon", False)

    @daemon.setter
    def daemon(self, daemonic):
        "\n        Set whether process is a daemon\n        "
        assert self._popen is None, "process has already started"
        self._config["daemon"] = daemonic

    @property
    def authkey(self):
        return self._config["authkey"]

    @authkey.setter
    def authkey(self, authkey):
        "\n        Set authorization key of process\n        "
        self._config["authkey"] = AuthenticationString(authkey)

    @property
    def exitcode(self):
        "\n        Return exit code of process or `None` if it has yet to stop\n        "
        self._check_closed()
        if self._popen is None:
            return self._popen
        return self._popen.poll()

    @property
    def ident(self):
        "\n        Return identifier (PID) of process or `None` if it has yet to start\n        "
        self._check_closed()
        if self is _current_process:
            return os.getpid()
        else:
            return self._popen and self._popen.pid

    pid = ident

    @property
    def sentinel(self):
        "\n        Return a file descriptor (Unix) or handle (Windows) suitable for\n        waiting for process termination.\n        "
        self._check_closed()
        try:
            return self._sentinel
        except AttributeError:
            raise ValueError("process not started") from None

    def __repr__(self):
        exitcode = None
        if self is _current_process:
            status = "started"
        elif self._closed:
            status = "closed"
        elif self._parent_pid != os.getpid():
            status = "unknown"
        elif self._popen is None:
            status = "initial"
        else:
            exitcode = self._popen.poll()
            if exitcode is not None:
                status = "stopped"
            else:
                status = "started"
        info = [type(self).__name__, ("name=%r" % self._name)]
        if self._popen is not None:
            info.append(("pid=%s" % self._popen.pid))
        info.append(("parent=%s" % self._parent_pid))
        info.append(status)
        if exitcode is not None:
            exitcode = _exitcode_to_name.get(exitcode, exitcode)
            info.append(("exitcode=%s" % exitcode))
        if self.daemon:
            info.append("daemon")
        return "<%s>" % " ".join(info)

    def _bootstrap(self, parent_sentinel=None):
        from . import util, context

        global _current_process, _parent_process, _process_counter, _children
        try:
            if self._start_method is not None:
                context._force_start_method(self._start_method)
            _process_counter = itertools.count(1)
            _children = set()
            util._close_stdin()
            old_process = _current_process
            _current_process = self
            _parent_process = _ParentProcess(
                self._parent_name, self._parent_pid, parent_sentinel
            )
            if threading._HAVE_THREAD_NATIVE_ID:
                threading.main_thread()._set_native_id()
            try:
                util._finalizer_registry.clear()
                util._run_after_forkers()
            finally:
                del old_process
            util.info("child process calling self.run()")
            try:
                self.run()
                exitcode = 0
            finally:
                util._exit_function()
        except SystemExit as e:
            if e.code is None:
                exitcode = 0
            elif isinstance(e.code, int):
                exitcode = e.code
            else:
                sys.stderr.write((str(e.code) + "\n"))
                exitcode = 1
        except:
            exitcode = 1
            import traceback

            sys.stderr.write(("Process %s:\n" % self.name))
            traceback.print_exc()
        finally:
            threading._shutdown()
            util.info(("process exiting with exitcode %d" % exitcode))
            util._flush_std_streams()
        return exitcode


class AuthenticationString(bytes):
    def __reduce__(self):
        from .context import get_spawning_popen

        if get_spawning_popen() is None:
            raise TypeError(
                "Pickling an AuthenticationString object is disallowed for security reasons"
            )
        return (AuthenticationString, (bytes(self),))


class _ParentProcess(BaseProcess):
    def __init__(self, name, pid, sentinel):
        self._identity = ()
        self._name = name
        self._pid = pid
        self._parent_pid = None
        self._popen = None
        self._closed = False
        self._sentinel = sentinel
        self._config = {}

    def is_alive(self):
        from multiprocessing.connection import wait

        return not wait([self._sentinel], timeout=0)

    @property
    def ident(self):
        return self._pid

    def join(self, timeout=None):
        "\n        Wait until parent process terminates\n        "
        from multiprocessing.connection import wait

        wait([self._sentinel], timeout=timeout)

    pid = ident


class _MainProcess(BaseProcess):
    def __init__(self):
        self._identity = ()
        self._name = "MainProcess"
        self._parent_pid = None
        self._popen = None
        self._closed = False
        self._config = {
            "authkey": AuthenticationString(os.urandom(32)),
            "semprefix": "/mp",
        }

    def close(self):
        pass


_parent_process = None
_current_process = _MainProcess()
_process_counter = itertools.count(1)
_children = set()
del _MainProcess
_exitcode_to_name = {}
for (name, signum) in list(signal.__dict__.items()):
    if (name[:3] == "SIG") and ("_" not in name):
        _exitcode_to_name[(-signum)] = f"-{name}"
_dangling = WeakSet()
