import os
import signal
import sys
import threading
import warnings
from . import spawn
from . import util

__all__ = ["ensure_running", "register", "unregister"]
_HAVE_SIGMASK = hasattr(signal, "pthread_sigmask")
_IGNORED_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_CLEANUP_FUNCS = {"noop": (lambda: None)}
if os.name == "posix":
    import _multiprocessing
    import _posixshmem

    if hasattr(_multiprocessing, "sem_unlink"):
        _CLEANUP_FUNCS.update({"semaphore": _multiprocessing.sem_unlink})
    _CLEANUP_FUNCS.update({"shared_memory": _posixshmem.shm_unlink})


class ResourceTracker(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._fd = None
        self._pid = None

    def _stop(self):
        with self._lock:
            if self._fd is None:
                return
            os.close(self._fd)
            self._fd = None
            os.waitpid(self._pid, 0)
            self._pid = None

    def getfd(self):
        self.ensure_running()
        return self._fd

    def ensure_running(self):
        "Make sure that resource tracker process is running.\n\n        This can be run from any process.  Usually a child process will use\n        the resource created by its parent."
        with self._lock:
            if self._fd is not None:
                if self._check_alive():
                    return
                os.close(self._fd)
                try:
                    if self._pid is not None:
                        os.waitpid(self._pid, 0)
                except ChildProcessError:
                    pass
                self._fd = None
                self._pid = None
                warnings.warn(
                    "resource_tracker: process died unexpectedly, relaunching.  Some resources might leak."
                )
            fds_to_pass = []
            try:
                fds_to_pass.append(sys.stderr.fileno())
            except Exception:
                pass
            cmd = "from multiprocessing.resource_tracker import main;main(%d)"
            (r, w) = os.pipe()
            try:
                fds_to_pass.append(r)
                exe = spawn.get_executable()
                args = [exe] + util._args_from_interpreter_flags()
                args += ["-c", (cmd % r)]
                try:
                    if _HAVE_SIGMASK:
                        signal.pthread_sigmask(signal.SIG_BLOCK, _IGNORED_SIGNALS)
                    pid = util.spawnv_passfds(exe, args, fds_to_pass)
                finally:
                    if _HAVE_SIGMASK:
                        signal.pthread_sigmask(signal.SIG_UNBLOCK, _IGNORED_SIGNALS)
            except:
                os.close(w)
                raise
            else:
                self._fd = w
                self._pid = pid
            finally:
                os.close(r)

    def _check_alive(self):
        "Check that the pipe has not been closed by sending a probe."
        try:
            os.write(self._fd, b"PROBE:0:noop\n")
        except OSError:
            return False
        else:
            return True

    def register(self, name, rtype):
        "Register name of resource with resource tracker."
        self._send("REGISTER", name, rtype)

    def unregister(self, name, rtype):
        "Unregister name of resource with resource tracker."
        self._send("UNREGISTER", name, rtype)

    def _send(self, cmd, name, rtype):
        self.ensure_running()
        msg = "{0}:{1}:{2}\n".format(cmd, name, rtype).encode("ascii")
        if len(name) > 512:
            raise ValueError("name too long")
        nbytes = os.write(self._fd, msg)
        assert nbytes == len(msg), "nbytes {0:n} but len(msg) {1:n}".format(
            nbytes, len(msg)
        )


_resource_tracker = ResourceTracker()
ensure_running = _resource_tracker.ensure_running
register = _resource_tracker.register
unregister = _resource_tracker.unregister
getfd = _resource_tracker.getfd


def main(fd):
    "Run resource tracker."
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if _HAVE_SIGMASK:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _IGNORED_SIGNALS)
    for f in (sys.stdin, sys.stdout):
        try:
            f.close()
        except Exception:
            pass
    cache = {rtype: set() for rtype in _CLEANUP_FUNCS.keys()}
    try:
        with open(fd, "rb") as f:
            for line in f:
                try:
                    (cmd, name, rtype) = line.strip().decode("ascii").split(":")
                    cleanup_func = _CLEANUP_FUNCS.get(rtype, None)
                    if cleanup_func is None:
                        raise ValueError(
                            f"Cannot register {name} for automatic cleanup: unknown resource type {rtype}"
                        )
                    if cmd == "REGISTER":
                        cache[rtype].add(name)
                    elif cmd == "UNREGISTER":
                        cache[rtype].remove(name)
                    elif cmd == "PROBE":
                        pass
                    else:
                        raise RuntimeError(("unrecognized command %r" % cmd))
                except Exception:
                    try:
                        sys.excepthook(*sys.exc_info())
                    except:
                        pass
    finally:
        for (rtype, rtype_cache) in cache.items():
            if rtype_cache:
                try:
                    warnings.warn(
                        (
                            "resource_tracker: There appear to be %d leaked %s objects to clean up at shutdown"
                            % (len(rtype_cache), rtype)
                        )
                    )
                except Exception:
                    pass
            for name in rtype_cache:
                try:
                    try:
                        _CLEANUP_FUNCS[rtype](name)
                    except Exception as e:
                        warnings.warn(("resource_tracker: %r: %s" % (name, e)))
                finally:
                    pass
