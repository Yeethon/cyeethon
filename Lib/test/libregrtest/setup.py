import atexit
import faulthandler
import os
import signal
import sys
import unittest
from test import support

try:
    import gc
except ImportError:
    gc = None
from test.libregrtest.utils import setup_unraisable_hook, setup_threading_excepthook


def setup_tests(ns):
    try:
        stderr_fd = sys.__stderr__.fileno()
    except (ValueError, AttributeError):
        stderr_fd = None
    else:
        faulthandler.enable(all_threads=True, file=stderr_fd)
        signals = []
        if hasattr(signal, "SIGALRM"):
            signals.append(signal.SIGALRM)
        if hasattr(signal, "SIGUSR1"):
            signals.append(signal.SIGUSR1)
        for signum in signals:
            faulthandler.register(signum, chain=True, file=stderr_fd)
    replace_stdout()
    support.record_original_stdout(sys.stdout)
    if ns.testdir:
        sys.path.insert(0, os.path.abspath(ns.testdir))
    for module in sys.modules.values():
        if hasattr(module, "__path__"):
            for (index, path) in enumerate(module.__path__):
                module.__path__[index] = os.path.abspath(path)
        if getattr(module, "__file__", None):
            module.__file__ = os.path.abspath(module.__file__)
    if ns.huntrleaks:
        unittest.BaseTestSuite._cleanup = False
        sys._deactivate_opcache()
    if ns.memlimit is not None:
        support.set_memlimit(ns.memlimit)
    if ns.threshold is not None:
        gc.set_threshold(ns.threshold)
    support.suppress_msvcrt_asserts((ns.verbose and (ns.verbose >= 2)))
    support.use_resources = ns.use_resources
    if hasattr(sys, "addaudithook"):

        def _test_audit_hook(name, args):
            pass

        sys.addaudithook(_test_audit_hook)
    setup_unraisable_hook()
    setup_threading_excepthook()
    if ns.timeout is not None:
        support.SHORT_TIMEOUT = max(support.SHORT_TIMEOUT, (ns.timeout / 40))
        support.LONG_TIMEOUT = max(support.LONG_TIMEOUT, (ns.timeout / 4))
        support.LOOPBACK_TIMEOUT = min(support.LOOPBACK_TIMEOUT, ns.timeout)
        support.INTERNET_TIMEOUT = min(support.INTERNET_TIMEOUT, ns.timeout)
        support.SHORT_TIMEOUT = min(support.SHORT_TIMEOUT, ns.timeout)
        support.LONG_TIMEOUT = min(support.LONG_TIMEOUT, ns.timeout)
    if ns.xmlpath:
        from test.support.testresult import RegressionTestResult

        RegressionTestResult.USE_XML = True


def replace_stdout():
    "Set stdout encoder error handler to backslashreplace (as stderr error\n    handler) to avoid UnicodeEncodeError when printing a traceback"
    stdout = sys.stdout
    try:
        fd = stdout.fileno()
    except ValueError:
        return
    sys.stdout = open(
        fd,
        "w",
        encoding=stdout.encoding,
        errors="backslashreplace",
        closefd=False,
        newline="\n",
    )

    def restore_stdout():
        sys.stdout.close()
        sys.stdout = stdout

    atexit.register(restore_stdout)
