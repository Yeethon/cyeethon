from contextlib import contextmanager
import datetime
import faulthandler
import os
import re
import signal
import subprocess
import sys
import sysconfig
from test import support
from test.support import os_helper
from test.support import script_helper, is_android
import tempfile
import unittest
from textwrap import dedent

try:
    import _testcapi
except ImportError:
    _testcapi = None
TIMEOUT = 0.5
MS_WINDOWS = os.name == "nt"
_cflags = sysconfig.get_config_var("CFLAGS") or ""
_config_args = sysconfig.get_config_var("CONFIG_ARGS") or ""
UB_SANITIZER = ("-fsanitize=undefined" in _cflags) or (
    "--with-undefined-behavior-sanitizer" in _config_args
)
MEMORY_SANITIZER = ("-fsanitize=memory" in _cflags) or (
    "--with-memory-sanitizer" in _config_args
)


def expected_traceback(lineno1, lineno2, header, min_count=1):
    regex = header
    regex += '  File "<string>", line %s in func\n' % lineno1
    regex += '  File "<string>", line %s in <module>' % lineno2
    if 1 < min_count:
        return ("^" + ((regex + "\n") * (min_count - 1))) + regex
    else:
        return ("^" + regex) + "$"


def skip_segfault_on_android(test):
    return unittest.skipIf(is_android, "raising SIGSEGV on Android is unreliable")(test)


@contextmanager
def temporary_filename():
    filename = tempfile.mktemp()
    try:
        (yield filename)
    finally:
        os_helper.unlink(filename)


class FaultHandlerTests(unittest.TestCase):
    def get_output(self, code, filename=None, fd=None):
        '\n        Run the specified code in Python (in a new child process) and read the\n        output from the standard error or from a file (if filename is set).\n        Return the output lines as a list.\n\n        Strip the reference count from the standard error for Python debug\n        build, and replace "Current thread 0x00007f8d8fbd9700" by "Current\n        thread XXX".\n        '
        code = dedent(code).strip()
        pass_fds = []
        if fd is not None:
            pass_fds.append(fd)
        with support.SuppressCrashReport():
            process = script_helper.spawn_python("-c", code, pass_fds=pass_fds)
            with process:
                (output, stderr) = process.communicate()
                exitcode = process.wait()
        output = output.decode("ascii", "backslashreplace")
        if filename:
            self.assertEqual(output, "")
            with open(filename, "rb") as fp:
                output = fp.read()
            output = output.decode("ascii", "backslashreplace")
        elif fd is not None:
            self.assertEqual(output, "")
            os.lseek(fd, os.SEEK_SET, 0)
            with open(fd, "rb", closefd=False) as fp:
                output = fp.read()
            output = output.decode("ascii", "backslashreplace")
        return (output.splitlines(), exitcode)

    def check_error(
        self,
        code,
        line_number,
        fatal_error,
        *,
        filename=None,
        all_threads=True,
        other_regex=None,
        fd=None,
        know_current_thread=True,
        py_fatal_error=False,
    ):
        "\n        Check that the fault handler for fatal errors is enabled and check the\n        traceback from the child process output.\n\n        Raise an error if the output doesn't match the expected format.\n        "
        if all_threads:
            if know_current_thread:
                header = "Current thread 0x[0-9a-f]+"
            else:
                header = "Thread 0x[0-9a-f]+"
        else:
            header = "Stack"
        regex = '\n            (?m)^{fatal_error}\n\n            {header} \\(most recent call first\\):\n              File "<string>", line {lineno} in <module>\n            '
        if py_fatal_error:
            fatal_error += "\nPython runtime state: initialized"
        regex = (
            dedent(regex)
            .format(lineno=line_number, fatal_error=fatal_error, header=header)
            .strip()
        )
        if other_regex:
            regex += "|" + other_regex
        (output, exitcode) = self.get_output(code, filename=filename, fd=fd)
        output = "\n".join(output)
        self.assertRegex(output, regex)
        self.assertNotEqual(exitcode, 0)

    def check_fatal_error(self, code, line_number, name_regex, func=None, **kw):
        if func:
            name_regex = "%s: %s" % (func, name_regex)
        fatal_error = "Fatal Python error: %s" % name_regex
        self.check_error(code, line_number, fatal_error, **kw)

    def check_windows_exception(self, code, line_number, name_regex, **kw):
        fatal_error = "Windows fatal exception: %s" % name_regex
        self.check_error(code, line_number, fatal_error, **kw)

    @unittest.skipIf(
        sys.platform.startswith("aix"),
        "the first page of memory is a mapped read-only on AIX",
    )
    def test_read_null(self):
        if not MS_WINDOWS:
            self.check_fatal_error(
                "\n                import faulthandler\n                faulthandler.enable()\n                faulthandler._read_null()\n                ",
                3,
                "(?:Segmentation fault|Bus error|Illegal instruction)",
            )
        else:
            self.check_windows_exception(
                "\n                import faulthandler\n                faulthandler.enable()\n                faulthandler._read_null()\n                ",
                3,
                "access violation",
            )

    @skip_segfault_on_android
    def test_sigsegv(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._sigsegv()\n            ",
            3,
            "Segmentation fault",
        )

    def test_fatal_error_c_thread(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._fatal_error_c_thread()\n            ",
            3,
            "in new thread",
            know_current_thread=False,
            func="faulthandler_fatal_error_thread",
            py_fatal_error=True,
        )

    def test_sigabrt(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._sigabrt()\n            ",
            3,
            "Aborted",
        )

    @unittest.skipIf((sys.platform == "win32"), "SIGFPE cannot be caught on Windows")
    def test_sigfpe(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._sigfpe()\n            ",
            3,
            "Floating point exception",
        )

    @unittest.skipIf((_testcapi is None), "need _testcapi")
    @unittest.skipUnless(hasattr(signal, "SIGBUS"), "need signal.SIGBUS")
    @skip_segfault_on_android
    def test_sigbus(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            import signal\n\n            faulthandler.enable()\n            signal.raise_signal(signal.SIGBUS)\n            ",
            5,
            "Bus error",
        )

    @unittest.skipIf((_testcapi is None), "need _testcapi")
    @unittest.skipUnless(hasattr(signal, "SIGILL"), "need signal.SIGILL")
    @skip_segfault_on_android
    def test_sigill(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            import signal\n\n            faulthandler.enable()\n            signal.raise_signal(signal.SIGILL)\n            ",
            5,
            "Illegal instruction",
        )

    def check_fatal_error_func(self, release_gil):
        with support.SuppressCrashReport():
            self.check_fatal_error(
                f"""
                import _testcapi
                _testcapi.fatal_error(b'xyz', {release_gil})
                """,
                2,
                "xyz",
                func="test_fatal_error",
                py_fatal_error=True,
            )

    def test_fatal_error(self):
        self.check_fatal_error_func(False)

    def test_fatal_error_without_gil(self):
        self.check_fatal_error_func(True)

    @unittest.skipIf(
        sys.platform.startswith("openbsd"),
        "Issue #12868: sigaltstack() doesn't work on OpenBSD if Python is compiled with pthread",
    )
    @unittest.skipIf(
        (not hasattr(faulthandler, "_stack_overflow")),
        "need faulthandler._stack_overflow()",
    )
    def test_stack_overflow(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._stack_overflow()\n            ",
            3,
            "(?:Segmentation fault|Bus error)",
            other_regex="unable to raise a stack overflow",
        )

    @skip_segfault_on_android
    def test_gil_released(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler._sigsegv(True)\n            ",
            3,
            "Segmentation fault",
        )

    @unittest.skipIf(
        (UB_SANITIZER or MEMORY_SANITIZER),
        "sanitizer builds change crashing process output.",
    )
    @skip_segfault_on_android
    def test_enable_file(self):
        with temporary_filename() as filename:
            self.check_fatal_error(
                "\n                import faulthandler\n                output = open({filename}, 'wb')\n                faulthandler.enable(output)\n                faulthandler._sigsegv()\n                ".format(
                    filename=repr(filename)
                ),
                4,
                "Segmentation fault",
                filename=filename,
            )

    @unittest.skipIf(
        (sys.platform == "win32"), "subprocess doesn't support pass_fds on Windows"
    )
    @unittest.skipIf(
        (UB_SANITIZER or MEMORY_SANITIZER),
        "sanitizer builds change crashing process output.",
    )
    @skip_segfault_on_android
    def test_enable_fd(self):
        with tempfile.TemporaryFile("wb+") as fp:
            fd = fp.fileno()
            self.check_fatal_error(
                (
                    "\n                import faulthandler\n                import sys\n                faulthandler.enable(%s)\n                faulthandler._sigsegv()\n                "
                    % fd
                ),
                4,
                "Segmentation fault",
                fd=fd,
            )

    @skip_segfault_on_android
    def test_enable_single_thread(self):
        self.check_fatal_error(
            "\n            import faulthandler\n            faulthandler.enable(all_threads=False)\n            faulthandler._sigsegv()\n            ",
            3,
            "Segmentation fault",
            all_threads=False,
        )

    @skip_segfault_on_android
    def test_disable(self):
        code = "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler.disable()\n            faulthandler._sigsegv()\n            "
        not_expected = "Fatal Python error"
        (stderr, exitcode) = self.get_output(code)
        stderr = "\n".join(stderr)
        self.assertTrue(
            (not_expected not in stderr),
            ("%r is present in %r" % (not_expected, stderr)),
        )
        self.assertNotEqual(exitcode, 0)

    @skip_segfault_on_android
    def test_dump_ext_modules(self):
        code = "\n            import faulthandler\n            import sys\n            # Don't filter stdlib module names\n            sys.stdlib_module_names = frozenset()\n            faulthandler.enable()\n            faulthandler._sigsegv()\n            "
        (stderr, exitcode) = self.get_output(code)
        stderr = "\n".join(stderr)
        match = re.search(
            "^Extension modules:(.*) \\(total: [0-9]+\\)$", stderr, re.MULTILINE
        )
        if not match:
            self.fail(f"Cannot find 'Extension modules:' in {stderr!r}")
        modules = set(match.group(1).strip().split(", "))
        for name in ("sys", "faulthandler"):
            self.assertIn(name, modules)

    def test_is_enabled(self):
        orig_stderr = sys.stderr
        try:
            sys.stderr = sys.__stderr__
            was_enabled = faulthandler.is_enabled()
            try:
                faulthandler.enable()
                self.assertTrue(faulthandler.is_enabled())
                faulthandler.disable()
                self.assertFalse(faulthandler.is_enabled())
            finally:
                if was_enabled:
                    faulthandler.enable()
                else:
                    faulthandler.disable()
        finally:
            sys.stderr = orig_stderr

    def test_disabled_by_default(self):
        code = "import faulthandler; print(faulthandler.is_enabled())"
        args = (sys.executable, "-E", "-c", code)
        output = subprocess.check_output(args)
        self.assertEqual(output.rstrip(), b"False")

    def test_sys_xoptions(self):
        code = "import faulthandler; print(faulthandler.is_enabled())"
        args = filter(
            None,
            (
                sys.executable,
                ("-E" if sys.flags.ignore_environment else ""),
                "-X",
                "faulthandler",
                "-c",
                code,
            ),
        )
        env = os.environ.copy()
        env.pop("PYTHONFAULTHANDLER", None)
        output = subprocess.check_output(args, env=env)
        self.assertEqual(output.rstrip(), b"True")

    def test_env_var(self):
        code = "import faulthandler; print(faulthandler.is_enabled())"
        args = (sys.executable, "-c", code)
        env = dict(os.environ)
        env["PYTHONFAULTHANDLER"] = ""
        env["PYTHONDEVMODE"] = ""
        output = subprocess.check_output(args, env=env)
        self.assertEqual(output.rstrip(), b"False")
        env = dict(os.environ)
        env["PYTHONFAULTHANDLER"] = "1"
        env["PYTHONDEVMODE"] = ""
        output = subprocess.check_output(args, env=env)
        self.assertEqual(output.rstrip(), b"True")

    def check_dump_traceback(self, *, filename=None, fd=None):
        "\n        Explicitly call dump_traceback() function and check its output.\n        Raise an error if the output doesn't match the expected format.\n        "
        code = '\n            import faulthandler\n\n            filename = {filename!r}\n            fd = {fd}\n\n            def funcB():\n                if filename:\n                    with open(filename, "wb") as fp:\n                        faulthandler.dump_traceback(fp, all_threads=False)\n                elif fd is not None:\n                    faulthandler.dump_traceback(fd,\n                                                all_threads=False)\n                else:\n                    faulthandler.dump_traceback(all_threads=False)\n\n            def funcA():\n                funcB()\n\n            funcA()\n            '
        code = code.format(filename=filename, fd=fd)
        if filename:
            lineno = 9
        elif fd is not None:
            lineno = 11
        else:
            lineno = 14
        expected = [
            "Stack (most recent call first):",
            ('  File "<string>", line %s in funcB' % lineno),
            '  File "<string>", line 17 in funcA',
            '  File "<string>", line 19 in <module>',
        ]
        (trace, exitcode) = self.get_output(code, filename, fd)
        self.assertEqual(trace, expected)
        self.assertEqual(exitcode, 0)

    def test_dump_traceback(self):
        self.check_dump_traceback()

    def test_dump_traceback_file(self):
        with temporary_filename() as filename:
            self.check_dump_traceback(filename=filename)

    @unittest.skipIf(
        (sys.platform == "win32"), "subprocess doesn't support pass_fds on Windows"
    )
    def test_dump_traceback_fd(self):
        with tempfile.TemporaryFile("wb+") as fp:
            self.check_dump_traceback(fd=fp.fileno())

    def test_truncate(self):
        maxlen = 500
        func_name = "x" * (maxlen + 50)
        truncated = ("x" * maxlen) + "..."
        code = "\n            import faulthandler\n\n            def {func_name}():\n                faulthandler.dump_traceback(all_threads=False)\n\n            {func_name}()\n            "
        code = code.format(func_name=func_name)
        expected = [
            "Stack (most recent call first):",
            ('  File "<string>", line 4 in %s' % truncated),
            '  File "<string>", line 6 in <module>',
        ]
        (trace, exitcode) = self.get_output(code)
        self.assertEqual(trace, expected)
        self.assertEqual(exitcode, 0)

    def check_dump_traceback_threads(self, filename):
        "\n        Call explicitly dump_traceback(all_threads=True) and check the output.\n        Raise an error if the output doesn't match the expected format.\n        "
        code = '\n            import faulthandler\n            from threading import Thread, Event\n            import time\n\n            def dump():\n                if {filename}:\n                    with open({filename}, "wb") as fp:\n                        faulthandler.dump_traceback(fp, all_threads=True)\n                else:\n                    faulthandler.dump_traceback(all_threads=True)\n\n            class Waiter(Thread):\n                # avoid blocking if the main thread raises an exception.\n                daemon = True\n\n                def __init__(self):\n                    Thread.__init__(self)\n                    self.running = Event()\n                    self.stop = Event()\n\n                def run(self):\n                    self.running.set()\n                    self.stop.wait()\n\n            waiter = Waiter()\n            waiter.start()\n            waiter.running.wait()\n            dump()\n            waiter.stop.set()\n            waiter.join()\n            '
        code = code.format(filename=repr(filename))
        (output, exitcode) = self.get_output(code, filename)
        output = "\n".join(output)
        if filename:
            lineno = 8
        else:
            lineno = 10
        regex = '\n            ^Thread 0x[0-9a-f]+ \\(most recent call first\\):\n            (?:  File ".*threading.py", line [0-9]+ in [_a-z]+\n            ){{1,3}}  File "<string>", line 23 in run\n              File ".*threading.py", line [0-9]+ in _bootstrap_inner\n              File ".*threading.py", line [0-9]+ in _bootstrap\n\n            Current thread 0x[0-9a-f]+ \\(most recent call first\\):\n              File "<string>", line {lineno} in dump\n              File "<string>", line 28 in <module>$\n            '
        regex = dedent(regex.format(lineno=lineno)).strip()
        self.assertRegex(output, regex)
        self.assertEqual(exitcode, 0)

    def test_dump_traceback_threads(self):
        self.check_dump_traceback_threads(None)

    def test_dump_traceback_threads_file(self):
        with temporary_filename() as filename:
            self.check_dump_traceback_threads(filename)

    def check_dump_traceback_later(
        self, repeat=False, cancel=False, loops=1, *, filename=None, fd=None
    ):
        "\n        Check how many times the traceback is written in timeout x 2.5 seconds,\n        or timeout x 3.5 seconds if cancel is True: 1, 2 or 3 times depending\n        on repeat and cancel options.\n\n        Raise an error if the output doesn't match the expect format.\n        "
        timeout_str = str(datetime.timedelta(seconds=TIMEOUT))
        code = '\n            import faulthandler\n            import time\n            import sys\n\n            timeout = {timeout}\n            repeat = {repeat}\n            cancel = {cancel}\n            loops = {loops}\n            filename = {filename!r}\n            fd = {fd}\n\n            def func(timeout, repeat, cancel, file, loops):\n                for loop in range(loops):\n                    faulthandler.dump_traceback_later(timeout, repeat=repeat, file=file)\n                    if cancel:\n                        faulthandler.cancel_dump_traceback_later()\n                    time.sleep(timeout * 5)\n                    faulthandler.cancel_dump_traceback_later()\n\n            if filename:\n                file = open(filename, "wb")\n            elif fd is not None:\n                file = sys.stderr.fileno()\n            else:\n                file = None\n            func(timeout, repeat, cancel, file, loops)\n            if filename:\n                file.close()\n            '
        code = code.format(
            timeout=TIMEOUT,
            repeat=repeat,
            cancel=cancel,
            loops=loops,
            filename=filename,
            fd=fd,
        )
        (trace, exitcode) = self.get_output(code, filename)
        trace = "\n".join(trace)
        if not cancel:
            count = loops
            if repeat:
                count *= 2
            header = (
                "Timeout \\(%s\\)!\\nThread 0x[0-9a-f]+ \\(most recent call first\\):\\n"
                % timeout_str
            )
            regex = expected_traceback(17, 26, header, min_count=count)
            self.assertRegex(trace, regex)
        else:
            self.assertEqual(trace, "")
        self.assertEqual(exitcode, 0)

    def test_dump_traceback_later(self):
        self.check_dump_traceback_later()

    def test_dump_traceback_later_repeat(self):
        self.check_dump_traceback_later(repeat=True)

    def test_dump_traceback_later_cancel(self):
        self.check_dump_traceback_later(cancel=True)

    def test_dump_traceback_later_file(self):
        with temporary_filename() as filename:
            self.check_dump_traceback_later(filename=filename)

    @unittest.skipIf(
        (sys.platform == "win32"), "subprocess doesn't support pass_fds on Windows"
    )
    def test_dump_traceback_later_fd(self):
        with tempfile.TemporaryFile("wb+") as fp:
            self.check_dump_traceback_later(fd=fp.fileno())

    def test_dump_traceback_later_twice(self):
        self.check_dump_traceback_later(loops=2)

    @unittest.skipIf(
        (not hasattr(faulthandler, "register")), "need faulthandler.register"
    )
    def check_register(
        self, filename=False, all_threads=False, unregister=False, chain=False, fd=None
    ):
        "\n        Register a handler displaying the traceback on a user signal. Raise the\n        signal and check the written traceback.\n\n        If chain is True, check that the previous signal handler is called.\n\n        Raise an error if the output doesn't match the expected format.\n        "
        signum = signal.SIGUSR1
        code = '\n            import faulthandler\n            import os\n            import signal\n            import sys\n\n            all_threads = {all_threads}\n            signum = {signum}\n            unregister = {unregister}\n            chain = {chain}\n            filename = {filename!r}\n            fd = {fd}\n\n            def func(signum):\n                os.kill(os.getpid(), signum)\n\n            def handler(signum, frame):\n                handler.called = True\n            handler.called = False\n\n            if filename:\n                file = open(filename, "wb")\n            elif fd is not None:\n                file = sys.stderr.fileno()\n            else:\n                file = None\n            if chain:\n                signal.signal(signum, handler)\n            faulthandler.register(signum, file=file,\n                                  all_threads=all_threads, chain={chain})\n            if unregister:\n                faulthandler.unregister(signum)\n            func(signum)\n            if chain and not handler.called:\n                if file is not None:\n                    output = file\n                else:\n                    output = sys.stderr\n                print("Error: signal handler not called!", file=output)\n                exitcode = 1\n            else:\n                exitcode = 0\n            if filename:\n                file.close()\n            sys.exit(exitcode)\n            '
        code = code.format(
            all_threads=all_threads,
            signum=signum,
            unregister=unregister,
            chain=chain,
            filename=filename,
            fd=fd,
        )
        (trace, exitcode) = self.get_output(code, filename)
        trace = "\n".join(trace)
        if not unregister:
            if all_threads:
                regex = "Current thread 0x[0-9a-f]+ \\(most recent call first\\):\\n"
            else:
                regex = "Stack \\(most recent call first\\):\\n"
            regex = expected_traceback(14, 32, regex)
            self.assertRegex(trace, regex)
        else:
            self.assertEqual(trace, "")
        if unregister:
            self.assertNotEqual(exitcode, 0)
        else:
            self.assertEqual(exitcode, 0)

    def test_register(self):
        self.check_register()

    def test_unregister(self):
        self.check_register(unregister=True)

    def test_register_file(self):
        with temporary_filename() as filename:
            self.check_register(filename=filename)

    @unittest.skipIf(
        (sys.platform == "win32"), "subprocess doesn't support pass_fds on Windows"
    )
    def test_register_fd(self):
        with tempfile.TemporaryFile("wb+") as fp:
            self.check_register(fd=fp.fileno())

    def test_register_threads(self):
        self.check_register(all_threads=True)

    def test_register_chain(self):
        self.check_register(chain=True)

    @contextmanager
    def check_stderr_none(self):
        stderr = sys.stderr
        try:
            sys.stderr = None
            with self.assertRaises(RuntimeError) as cm:
                (yield)
            self.assertEqual(str(cm.exception), "sys.stderr is None")
        finally:
            sys.stderr = stderr

    def test_stderr_None(self):
        with self.check_stderr_none():
            faulthandler.enable()
        with self.check_stderr_none():
            faulthandler.dump_traceback()
        with self.check_stderr_none():
            faulthandler.dump_traceback_later(0.001)
        if hasattr(faulthandler, "register"):
            with self.check_stderr_none():
                faulthandler.register(signal.SIGUSR1)

    @unittest.skipUnless(MS_WINDOWS, "specific to Windows")
    def test_raise_exception(self):
        for (exc, name) in (
            ("EXCEPTION_ACCESS_VIOLATION", "access violation"),
            ("EXCEPTION_INT_DIVIDE_BY_ZERO", "int divide by zero"),
            ("EXCEPTION_STACK_OVERFLOW", "stack overflow"),
        ):
            self.check_windows_exception(
                f"""
                import faulthandler
                faulthandler.enable()
                faulthandler._raise_exception(faulthandler._{exc})
                """,
                3,
                name,
            )

    @unittest.skipUnless(MS_WINDOWS, "specific to Windows")
    def test_ignore_exception(self):
        for exc_code in (3765269347, 3762504530):
            code = f"""
                    import faulthandler
                    faulthandler.enable()
                    faulthandler._raise_exception({exc_code})
                    """
            code = dedent(code)
            (output, exitcode) = self.get_output(code)
            self.assertEqual(output, [])
            self.assertEqual(exitcode, exc_code)

    @unittest.skipUnless(MS_WINDOWS, "specific to Windows")
    def test_raise_nonfatal_exception(self):
        for exc in (0, 878082192, 1073741824, 1073745920, 1879048192, 2147483647):
            (output, exitcode) = self.get_output(
                f"""
                import faulthandler
                faulthandler.enable()
                faulthandler._raise_exception(0x{exc:x})
                """
            )
            self.assertEqual(output, [])
            self.assertIn(exitcode, (exc, (exc & (~268435456))))

    @unittest.skipUnless(MS_WINDOWS, "specific to Windows")
    def test_disable_windows_exc_handler(self):
        code = dedent(
            "\n            import faulthandler\n            faulthandler.enable()\n            faulthandler.disable()\n            code = faulthandler._EXCEPTION_ACCESS_VIOLATION\n            faulthandler._raise_exception(code)\n        "
        )
        (output, exitcode) = self.get_output(code)
        self.assertEqual(output, [])
        self.assertEqual(exitcode, 3221225477)

    def test_cancel_later_without_dump_traceback_later(self):
        code = dedent(
            "\n            import faulthandler\n            faulthandler.cancel_dump_traceback_later()\n        "
        )
        (output, exitcode) = self.get_output(code)
        self.assertEqual(output, [])
        self.assertEqual(exitcode, 0)


if __name__ == "__main__":
    unittest.main()
