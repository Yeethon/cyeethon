import enum
import errno
import os
import random
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import unittest
from test import support
from test.support import os_helper
from test.support.script_helper import assert_python_ok, spawn_python

try:
    import _testcapi
except ImportError:
    _testcapi = None


class GenericTests(unittest.TestCase):
    def test_enums(self):
        for name in dir(signal):
            sig = getattr(signal, name)
            if name in {"SIG_DFL", "SIG_IGN"}:
                self.assertIsInstance(sig, signal.Handlers)
            elif name in {"SIG_BLOCK", "SIG_UNBLOCK", "SIG_SETMASK"}:
                self.assertIsInstance(sig, signal.Sigmasks)
            elif name.startswith("SIG") and (not name.startswith("SIG_")):
                self.assertIsInstance(sig, signal.Signals)
            elif name.startswith("CTRL_"):
                self.assertIsInstance(sig, signal.Signals)
                self.assertEqual(sys.platform, "win32")
        CheckedSignals = enum._old_convert_(
            enum.IntEnum,
            "Signals",
            "signal",
            (
                lambda name: (
                    (
                        name.isupper()
                        and (name.startswith("SIG") and (not name.startswith("SIG_")))
                    )
                    or name.startswith("CTRL_")
                )
            ),
            source=signal,
        )
        enum._test_simple_enum(CheckedSignals, signal.Signals)
        CheckedHandlers = enum._old_convert_(
            enum.IntEnum,
            "Handlers",
            "signal",
            (lambda name: (name in ("SIG_DFL", "SIG_IGN"))),
            source=signal,
        )
        enum._test_simple_enum(CheckedHandlers, signal.Handlers)
        Sigmasks = getattr(signal, "Sigmasks", None)
        if Sigmasks is not None:
            CheckedSigmasks = enum._old_convert_(
                enum.IntEnum,
                "Sigmasks",
                "signal",
                (lambda name: (name in ("SIG_BLOCK", "SIG_UNBLOCK", "SIG_SETMASK"))),
                source=signal,
            )
            enum._test_simple_enum(CheckedSigmasks, Sigmasks)


@unittest.skipIf((sys.platform == "win32"), "Not valid on Windows")
class PosixTests(unittest.TestCase):
    def trivial_signal_handler(self, *args):
        pass

    def test_out_of_range_signal_number_raises_error(self):
        self.assertRaises(ValueError, signal.getsignal, 4242)
        self.assertRaises(ValueError, signal.signal, 4242, self.trivial_signal_handler)
        self.assertRaises(ValueError, signal.strsignal, 4242)

    def test_setting_signal_handler_to_none_raises_error(self):
        self.assertRaises(TypeError, signal.signal, signal.SIGUSR1, None)

    def test_getsignal(self):
        hup = signal.signal(signal.SIGHUP, self.trivial_signal_handler)
        self.assertIsInstance(hup, signal.Handlers)
        self.assertEqual(signal.getsignal(signal.SIGHUP), self.trivial_signal_handler)
        signal.signal(signal.SIGHUP, hup)
        self.assertEqual(signal.getsignal(signal.SIGHUP), hup)

    def test_strsignal(self):
        self.assertIn("Interrupt", signal.strsignal(signal.SIGINT))
        self.assertIn("Terminated", signal.strsignal(signal.SIGTERM))
        self.assertIn("Hangup", signal.strsignal(signal.SIGHUP))

    def test_interprocess_signal(self):
        dirname = os.path.dirname(__file__)
        script = os.path.join(dirname, "signalinterproctester.py")
        assert_python_ok(script)

    def test_valid_signals(self):
        s = signal.valid_signals()
        self.assertIsInstance(s, set)
        self.assertIn(signal.Signals.SIGINT, s)
        self.assertIn(signal.Signals.SIGALRM, s)
        self.assertNotIn(0, s)
        self.assertNotIn(signal.NSIG, s)
        self.assertLess(len(s), signal.NSIG)

    @unittest.skipUnless(sys.executable, "sys.executable required.")
    def test_keyboard_interrupt_exit_code(self):
        "KeyboardInterrupt triggers exit via SIGINT."
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os, signal, time\nos.kill(os.getpid(), signal.SIGINT)\nfor _ in range(999): time.sleep(0.01)",
            ],
            stderr=subprocess.PIPE,
        )
        self.assertIn(b"KeyboardInterrupt", process.stderr)
        self.assertEqual(process.returncode, (-signal.SIGINT))


@unittest.skipUnless((sys.platform == "win32"), "Windows specific")
class WindowsSignalTests(unittest.TestCase):
    def test_valid_signals(self):
        s = signal.valid_signals()
        self.assertIsInstance(s, set)
        self.assertGreaterEqual(len(s), 6)
        self.assertIn(signal.Signals.SIGINT, s)
        self.assertNotIn(0, s)
        self.assertNotIn(signal.NSIG, s)
        self.assertLess(len(s), signal.NSIG)

    def test_issue9324(self):
        handler = lambda x, y: None
        checked = set()
        for sig in (
            signal.SIGABRT,
            signal.SIGBREAK,
            signal.SIGFPE,
            signal.SIGILL,
            signal.SIGINT,
            signal.SIGSEGV,
            signal.SIGTERM,
        ):
            if signal.getsignal(sig) is not None:
                signal.signal(sig, signal.signal(sig, handler))
                checked.add(sig)
        self.assertTrue(checked)
        with self.assertRaises(ValueError):
            signal.signal((-1), handler)
        with self.assertRaises(ValueError):
            signal.signal(7, handler)

    @unittest.skipUnless(sys.executable, "sys.executable required.")
    def test_keyboard_interrupt_exit_code(self):
        "KeyboardInterrupt triggers an exit using STATUS_CONTROL_C_EXIT."
        process = subprocess.run(
            [sys.executable, "-c", "raise KeyboardInterrupt"], stderr=subprocess.PIPE
        )
        self.assertIn(b"KeyboardInterrupt", process.stderr)
        STATUS_CONTROL_C_EXIT = 3221225786
        self.assertEqual(process.returncode, STATUS_CONTROL_C_EXIT)


class WakeupFDTests(unittest.TestCase):
    def test_invalid_call(self):
        with self.assertRaises(TypeError):
            signal.set_wakeup_fd(signum=signal.SIGINT)
        with self.assertRaises(TypeError):
            signal.set_wakeup_fd(signal.SIGINT, False)

    def test_invalid_fd(self):
        fd = os_helper.make_bad_fd()
        self.assertRaises((ValueError, OSError), signal.set_wakeup_fd, fd)

    def test_invalid_socket(self):
        sock = socket.socket()
        fd = sock.fileno()
        sock.close()
        self.assertRaises((ValueError, OSError), signal.set_wakeup_fd, fd)

    def test_set_wakeup_fd_result(self):
        (r1, w1) = os.pipe()
        self.addCleanup(os.close, r1)
        self.addCleanup(os.close, w1)
        (r2, w2) = os.pipe()
        self.addCleanup(os.close, r2)
        self.addCleanup(os.close, w2)
        if hasattr(os, "set_blocking"):
            os.set_blocking(w1, False)
            os.set_blocking(w2, False)
        signal.set_wakeup_fd(w1)
        self.assertEqual(signal.set_wakeup_fd(w2), w1)
        self.assertEqual(signal.set_wakeup_fd((-1)), w2)
        self.assertEqual(signal.set_wakeup_fd((-1)), (-1))

    def test_set_wakeup_fd_socket_result(self):
        sock1 = socket.socket()
        self.addCleanup(sock1.close)
        sock1.setblocking(False)
        fd1 = sock1.fileno()
        sock2 = socket.socket()
        self.addCleanup(sock2.close)
        sock2.setblocking(False)
        fd2 = sock2.fileno()
        signal.set_wakeup_fd(fd1)
        self.assertEqual(signal.set_wakeup_fd(fd2), fd1)
        self.assertEqual(signal.set_wakeup_fd((-1)), fd2)
        self.assertEqual(signal.set_wakeup_fd((-1)), (-1))

    @unittest.skipIf((sys.platform == "win32"), "tests specific to POSIX")
    def test_set_wakeup_fd_blocking(self):
        (rfd, wfd) = os.pipe()
        self.addCleanup(os.close, rfd)
        self.addCleanup(os.close, wfd)
        os.set_blocking(wfd, True)
        with self.assertRaises(ValueError) as cm:
            signal.set_wakeup_fd(wfd)
        self.assertEqual(
            str(cm.exception), ("the fd %s must be in non-blocking mode" % wfd)
        )
        os.set_blocking(wfd, False)
        signal.set_wakeup_fd(wfd)
        signal.set_wakeup_fd((-1))


@unittest.skipIf((sys.platform == "win32"), "Not valid on Windows")
class WakeupSignalTests(unittest.TestCase):
    @unittest.skipIf((_testcapi is None), "need _testcapi")
    def check_wakeup(self, test_body, *signals, ordered=True):
        code = "if 1:\n        import _testcapi\n        import os\n        import signal\n        import struct\n\n        signals = {!r}\n\n        def handler(signum, frame):\n            pass\n\n        def check_signum(signals):\n            data = os.read(read, len(signals)+1)\n            raised = struct.unpack('%uB' % len(data), data)\n            if not {!r}:\n                raised = set(raised)\n                signals = set(signals)\n            if raised != signals:\n                raise Exception(\"%r != %r\" % (raised, signals))\n\n        {}\n\n        signal.signal(signal.SIGALRM, handler)\n        read, write = os.pipe()\n        os.set_blocking(write, False)\n        signal.set_wakeup_fd(write)\n\n        test()\n        check_signum(signals)\n\n        os.close(read)\n        os.close(write)\n        ".format(
            tuple(map(int, signals)), ordered, test_body
        )
        assert_python_ok("-c", code)

    @unittest.skipIf((_testcapi is None), "need _testcapi")
    def test_wakeup_write_error(self):
        code = "if 1:\n        import _testcapi\n        import errno\n        import os\n        import signal\n        import sys\n        from test.support import captured_stderr\n\n        def handler(signum, frame):\n            1/0\n\n        signal.signal(signal.SIGALRM, handler)\n        r, w = os.pipe()\n        os.set_blocking(r, False)\n\n        # Set wakeup_fd a read-only file descriptor to trigger the error\n        signal.set_wakeup_fd(r)\n        try:\n            with captured_stderr() as err:\n                signal.raise_signal(signal.SIGALRM)\n        except ZeroDivisionError:\n            # An ignored exception should have been printed out on stderr\n            err = err.getvalue()\n            if ('Exception ignored when trying to write to the signal wakeup fd'\n                not in err):\n                raise AssertionError(err)\n            if ('OSError: [Errno %d]' % errno.EBADF) not in err:\n                raise AssertionError(err)\n        else:\n            raise AssertionError(\"ZeroDivisionError not raised\")\n\n        os.close(r)\n        os.close(w)\n        "
        (r, w) = os.pipe()
        try:
            os.write(r, b"x")
        except OSError:
            pass
        else:
            self.skipTest("OS doesn't report write() error on the read end of a pipe")
        finally:
            os.close(r)
            os.close(w)
        assert_python_ok("-c", code)

    def test_wakeup_fd_early(self):
        self.check_wakeup(
            'def test():\n            import select\n            import time\n\n            TIMEOUT_FULL = 10\n            TIMEOUT_HALF = 5\n\n            class InterruptSelect(Exception):\n                pass\n\n            def handler(signum, frame):\n                raise InterruptSelect\n            signal.signal(signal.SIGALRM, handler)\n\n            signal.alarm(1)\n\n            # We attempt to get a signal during the sleep,\n            # before select is called\n            try:\n                select.select([], [], [], TIMEOUT_FULL)\n            except InterruptSelect:\n                pass\n            else:\n                raise Exception("select() was not interrupted")\n\n            before_time = time.monotonic()\n            select.select([read], [], [], TIMEOUT_FULL)\n            after_time = time.monotonic()\n            dt = after_time - before_time\n            if dt >= TIMEOUT_HALF:\n                raise Exception("%s >= %s" % (dt, TIMEOUT_HALF))\n        ',
            signal.SIGALRM,
        )

    def test_wakeup_fd_during(self):
        self.check_wakeup(
            'def test():\n            import select\n            import time\n\n            TIMEOUT_FULL = 10\n            TIMEOUT_HALF = 5\n\n            class InterruptSelect(Exception):\n                pass\n\n            def handler(signum, frame):\n                raise InterruptSelect\n            signal.signal(signal.SIGALRM, handler)\n\n            signal.alarm(1)\n            before_time = time.monotonic()\n            # We attempt to get a signal during the select call\n            try:\n                select.select([read], [], [], TIMEOUT_FULL)\n            except InterruptSelect:\n                pass\n            else:\n                raise Exception("select() was not interrupted")\n            after_time = time.monotonic()\n            dt = after_time - before_time\n            if dt >= TIMEOUT_HALF:\n                raise Exception("%s >= %s" % (dt, TIMEOUT_HALF))\n        ',
            signal.SIGALRM,
        )

    def test_signum(self):
        self.check_wakeup(
            "def test():\n            signal.signal(signal.SIGUSR1, handler)\n            signal.raise_signal(signal.SIGUSR1)\n            signal.raise_signal(signal.SIGALRM)\n        ",
            signal.SIGUSR1,
            signal.SIGALRM,
        )

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def test_pending(self):
        self.check_wakeup(
            "def test():\n            signum1 = signal.SIGUSR1\n            signum2 = signal.SIGUSR2\n\n            signal.signal(signum1, handler)\n            signal.signal(signum2, handler)\n\n            signal.pthread_sigmask(signal.SIG_BLOCK, (signum1, signum2))\n            signal.raise_signal(signum1)\n            signal.raise_signal(signum2)\n            # Unblocking the 2 signals calls the C signal handler twice\n            signal.pthread_sigmask(signal.SIG_UNBLOCK, (signum1, signum2))\n        ",
            signal.SIGUSR1,
            signal.SIGUSR2,
            ordered=False,
        )


@unittest.skipUnless(hasattr(socket, "socketpair"), "need socket.socketpair")
class WakeupSocketSignalTests(unittest.TestCase):
    @unittest.skipIf((_testcapi is None), "need _testcapi")
    def test_socket(self):
        code = 'if 1:\n        import signal\n        import socket\n        import struct\n        import _testcapi\n\n        signum = signal.SIGINT\n        signals = (signum,)\n\n        def handler(signum, frame):\n            pass\n\n        signal.signal(signum, handler)\n\n        read, write = socket.socketpair()\n        write.setblocking(False)\n        signal.set_wakeup_fd(write.fileno())\n\n        signal.raise_signal(signum)\n\n        data = read.recv(1)\n        if not data:\n            raise Exception("no signum written")\n        raised = struct.unpack(\'B\', data)\n        if raised != signals:\n            raise Exception("%r != %r" % (raised, signals))\n\n        read.close()\n        write.close()\n        '
        assert_python_ok("-c", code)

    @unittest.skipIf((_testcapi is None), "need _testcapi")
    def test_send_error(self):
        if os.name == "nt":
            action = "send"
        else:
            action = "write"
        code = "if 1:\n        import errno\n        import signal\n        import socket\n        import sys\n        import time\n        import _testcapi\n        from test.support import captured_stderr\n\n        signum = signal.SIGINT\n\n        def handler(signum, frame):\n            pass\n\n        signal.signal(signum, handler)\n\n        read, write = socket.socketpair()\n        read.setblocking(False)\n        write.setblocking(False)\n\n        signal.set_wakeup_fd(write.fileno())\n\n        # Close sockets: send() will fail\n        read.close()\n        write.close()\n\n        with captured_stderr() as err:\n            signal.raise_signal(signum)\n\n        err = err.getvalue()\n        if ('Exception ignored when trying to {action} to the signal wakeup fd'\n            not in err):\n            raise AssertionError(err)\n        ".format(
            action=action
        )
        assert_python_ok("-c", code)

    @unittest.skipIf((_testcapi is None), "need _testcapi")
    def test_warn_on_full_buffer(self):
        if os.name == "nt":
            action = "send"
        else:
            action = "write"
        code = 'if 1:\n        import errno\n        import signal\n        import socket\n        import sys\n        import time\n        import _testcapi\n        from test.support import captured_stderr\n\n        signum = signal.SIGINT\n\n        # This handler will be called, but we intentionally won\'t read from\n        # the wakeup fd.\n        def handler(signum, frame):\n            pass\n\n        signal.signal(signum, handler)\n\n        read, write = socket.socketpair()\n\n        # Fill the socketpair buffer\n        if sys.platform == \'win32\':\n            # bpo-34130: On Windows, sometimes non-blocking send fails to fill\n            # the full socketpair buffer, so use a timeout of 50 ms instead.\n            write.settimeout(0.050)\n        else:\n            write.setblocking(False)\n\n        written = 0\n        if sys.platform == "vxworks":\n            CHUNK_SIZES = (1,)\n        else:\n            # Start with large chunk size to reduce the\n            # number of send needed to fill the buffer.\n            CHUNK_SIZES = (2 ** 16, 2 ** 8, 1)\n        for chunk_size in CHUNK_SIZES:\n            chunk = b"x" * chunk_size\n            try:\n                while True:\n                    write.send(chunk)\n                    written += chunk_size\n            except (BlockingIOError, TimeoutError):\n                pass\n\n        print(f"%s bytes written into the socketpair" % written, flush=True)\n\n        write.setblocking(False)\n        try:\n            write.send(b"x")\n        except BlockingIOError:\n            # The socketpair buffer seems full\n            pass\n        else:\n            raise AssertionError("%s bytes failed to fill the socketpair "\n                                 "buffer" % written)\n\n        # By default, we get a warning when a signal arrives\n        msg = (\'Exception ignored when trying to {action} \'\n               \'to the signal wakeup fd\')\n        signal.set_wakeup_fd(write.fileno())\n\n        with captured_stderr() as err:\n            signal.raise_signal(signum)\n\n        err = err.getvalue()\n        if msg not in err:\n            raise AssertionError("first set_wakeup_fd() test failed, "\n                                 "stderr: %r" % err)\n\n        # And also if warn_on_full_buffer=True\n        signal.set_wakeup_fd(write.fileno(), warn_on_full_buffer=True)\n\n        with captured_stderr() as err:\n            signal.raise_signal(signum)\n\n        err = err.getvalue()\n        if msg not in err:\n            raise AssertionError("set_wakeup_fd(warn_on_full_buffer=True) "\n                                 "test failed, stderr: %r" % err)\n\n        # But not if warn_on_full_buffer=False\n        signal.set_wakeup_fd(write.fileno(), warn_on_full_buffer=False)\n\n        with captured_stderr() as err:\n            signal.raise_signal(signum)\n\n        err = err.getvalue()\n        if err != "":\n            raise AssertionError("set_wakeup_fd(warn_on_full_buffer=False) "\n                                 "test failed, stderr: %r" % err)\n\n        # And then check the default again, to make sure warn_on_full_buffer\n        # settings don\'t leak across calls.\n        signal.set_wakeup_fd(write.fileno())\n\n        with captured_stderr() as err:\n            signal.raise_signal(signum)\n\n        err = err.getvalue()\n        if msg not in err:\n            raise AssertionError("second set_wakeup_fd() test failed, "\n                                 "stderr: %r" % err)\n\n        '.format(
            action=action
        )
        assert_python_ok("-c", code)


@unittest.skipIf((sys.platform == "win32"), "Not valid on Windows")
@unittest.skipUnless(hasattr(signal, "siginterrupt"), "needs signal.siginterrupt()")
class SiginterruptTest(unittest.TestCase):
    def readpipe_interrupted(self, interrupt):
        "Perform a read during which a signal will arrive.  Return True if the\n        read is interrupted by the signal and raises an exception.  Return False\n        if it returns normally.\n        "
        code = (
            'if 1:\n            import errno\n            import os\n            import signal\n            import sys\n\n            interrupt = %r\n            r, w = os.pipe()\n\n            def handler(signum, frame):\n                1 / 0\n\n            signal.signal(signal.SIGALRM, handler)\n            if interrupt is not None:\n                signal.siginterrupt(signal.SIGALRM, interrupt)\n\n            print("ready")\n            sys.stdout.flush()\n\n            # run the test twice\n            try:\n                for loop in range(2):\n                    # send a SIGALRM in a second (during the read)\n                    signal.alarm(1)\n                    try:\n                        # blocking call: read from a pipe without data\n                        os.read(r, 1)\n                    except ZeroDivisionError:\n                        pass\n                    else:\n                        sys.exit(2)\n                sys.exit(3)\n            finally:\n                os.close(r)\n                os.close(w)\n        '
            % (interrupt,)
        )
        with spawn_python("-c", code) as process:
            try:
                first_line = process.stdout.readline()
                (stdout, stderr) = process.communicate(timeout=support.SHORT_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                return False
            else:
                stdout = first_line + stdout
                exitcode = process.wait()
                if exitcode not in (2, 3):
                    raise Exception(
                        ("Child error (exit code %s): %r" % (exitcode, stdout))
                    )
                return exitcode == 3

    def test_without_siginterrupt(self):
        interrupted = self.readpipe_interrupted(None)
        self.assertTrue(interrupted)

    def test_siginterrupt_on(self):
        interrupted = self.readpipe_interrupted(True)
        self.assertTrue(interrupted)

    def test_siginterrupt_off(self):
        interrupted = self.readpipe_interrupted(False)
        self.assertFalse(interrupted)


@unittest.skipIf((sys.platform == "win32"), "Not valid on Windows")
@unittest.skipUnless(
    (hasattr(signal, "getitimer") and hasattr(signal, "setitimer")),
    "needs signal.getitimer() and signal.setitimer()",
)
class ItimerTest(unittest.TestCase):
    def setUp(self):
        self.hndl_called = False
        self.hndl_count = 0
        self.itimer = None
        self.old_alarm = signal.signal(signal.SIGALRM, self.sig_alrm)

    def tearDown(self):
        signal.signal(signal.SIGALRM, self.old_alarm)
        if self.itimer is not None:
            signal.setitimer(self.itimer, 0)

    def sig_alrm(self, *args):
        self.hndl_called = True

    def sig_vtalrm(self, *args):
        self.hndl_called = True
        if self.hndl_count > 3:
            raise signal.ItimerError("setitimer didn't disable ITIMER_VIRTUAL timer.")
        elif self.hndl_count == 3:
            signal.setitimer(signal.ITIMER_VIRTUAL, 0)
        self.hndl_count += 1

    def sig_prof(self, *args):
        self.hndl_called = True
        signal.setitimer(signal.ITIMER_PROF, 0)

    def test_itimer_exc(self):
        self.assertRaises(signal.ItimerError, signal.setitimer, (-1), 0)
        if 0:
            self.assertRaises(
                signal.ItimerError, signal.setitimer, signal.ITIMER_REAL, (-1)
            )

    def test_itimer_real(self):
        self.itimer = signal.ITIMER_REAL
        signal.setitimer(self.itimer, 1.0)
        signal.pause()
        self.assertEqual(self.hndl_called, True)

    @unittest.skipIf(
        (sys.platform in ("netbsd5",)),
        "itimer not reliable (does not mix well with threading) on some BSDs.",
    )
    def test_itimer_virtual(self):
        self.itimer = signal.ITIMER_VIRTUAL
        signal.signal(signal.SIGVTALRM, self.sig_vtalrm)
        signal.setitimer(self.itimer, 0.3, 0.2)
        start_time = time.monotonic()
        while (time.monotonic() - start_time) < 60.0:
            _ = pow(12345, 67890, 10000019)
            if signal.getitimer(self.itimer) == (0.0, 0.0):
                break
        else:
            self.skipTest("timeout: likely cause: machine too slow or load too high")
        self.assertEqual(signal.getitimer(self.itimer), (0.0, 0.0))
        self.assertEqual(self.hndl_called, True)

    def test_itimer_prof(self):
        self.itimer = signal.ITIMER_PROF
        signal.signal(signal.SIGPROF, self.sig_prof)
        signal.setitimer(self.itimer, 0.2, 0.2)
        start_time = time.monotonic()
        while (time.monotonic() - start_time) < 60.0:
            _ = pow(12345, 67890, 10000019)
            if signal.getitimer(self.itimer) == (0.0, 0.0):
                break
        else:
            self.skipTest("timeout: likely cause: machine too slow or load too high")
        self.assertEqual(signal.getitimer(self.itimer), (0.0, 0.0))
        self.assertEqual(self.hndl_called, True)

    def test_setitimer_tiny(self):
        self.itimer = signal.ITIMER_REAL
        signal.setitimer(self.itimer, 1e-06)
        time.sleep(1)
        self.assertEqual(self.hndl_called, True)


class PendingSignalsTests(unittest.TestCase):
    "\n    Test pthread_sigmask(), pthread_kill(), sigpending() and sigwait()\n    functions.\n    "

    @unittest.skipUnless(hasattr(signal, "sigpending"), "need signal.sigpending()")
    def test_sigpending_empty(self):
        self.assertEqual(signal.sigpending(), set())

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    @unittest.skipUnless(hasattr(signal, "sigpending"), "need signal.sigpending()")
    def test_sigpending(self):
        code = "if 1:\n            import os\n            import signal\n\n            def handler(signum, frame):\n                1/0\n\n            signum = signal.SIGUSR1\n            signal.signal(signum, handler)\n\n            signal.pthread_sigmask(signal.SIG_BLOCK, [signum])\n            os.kill(os.getpid(), signum)\n            pending = signal.sigpending()\n            for sig in pending:\n                assert isinstance(sig, signal.Signals), repr(pending)\n            if pending != {signum}:\n                raise Exception('%s != {%s}' % (pending, signum))\n            try:\n                signal.pthread_sigmask(signal.SIG_UNBLOCK, [signum])\n            except ZeroDivisionError:\n                pass\n            else:\n                raise Exception(\"ZeroDivisionError not raised\")\n        "
        assert_python_ok("-c", code)

    @unittest.skipUnless(hasattr(signal, "pthread_kill"), "need signal.pthread_kill()")
    def test_pthread_kill(self):
        code = 'if 1:\n            import signal\n            import threading\n            import sys\n\n            signum = signal.SIGUSR1\n\n            def handler(signum, frame):\n                1/0\n\n            signal.signal(signum, handler)\n\n            tid = threading.get_ident()\n            try:\n                signal.pthread_kill(tid, signum)\n            except ZeroDivisionError:\n                pass\n            else:\n                raise Exception("ZeroDivisionError not raised")\n        '
        assert_python_ok("-c", code)

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def wait_helper(self, blocked, test):
        '\n        test: body of the "def test(signum):" function.\n        blocked: number of the blocked signal\n        '
        code = (
            'if 1:\n        import signal\n        import sys\n        from signal import Signals\n\n        def handler(signum, frame):\n            1/0\n\n        %s\n\n        blocked = %r\n        signum = signal.SIGALRM\n\n        # child: block and wait the signal\n        try:\n            signal.signal(signum, handler)\n            signal.pthread_sigmask(signal.SIG_BLOCK, [blocked])\n\n            # Do the tests\n            test(signum)\n\n            # The handler must not be called on unblock\n            try:\n                signal.pthread_sigmask(signal.SIG_UNBLOCK, [blocked])\n            except ZeroDivisionError:\n                print("the signal handler has been called",\n                      file=sys.stderr)\n                sys.exit(1)\n        except BaseException as err:\n            print("error: {}".format(err), file=sys.stderr)\n            sys.stderr.flush()\n            sys.exit(1)\n        '
            % (test.strip(), blocked)
        )
        assert_python_ok("-c", code)

    @unittest.skipUnless(hasattr(signal, "sigwait"), "need signal.sigwait()")
    def test_sigwait(self):
        self.wait_helper(
            signal.SIGALRM,
            "\n        def test(signum):\n            signal.alarm(1)\n            received = signal.sigwait([signum])\n            assert isinstance(received, signal.Signals), received\n            if received != signum:\n                raise Exception('received %s, not %s' % (received, signum))\n        ",
        )

    @unittest.skipUnless(hasattr(signal, "sigwaitinfo"), "need signal.sigwaitinfo()")
    def test_sigwaitinfo(self):
        self.wait_helper(
            signal.SIGALRM,
            '\n        def test(signum):\n            signal.alarm(1)\n            info = signal.sigwaitinfo([signum])\n            if info.si_signo != signum:\n                raise Exception("info.si_signo != %s" % signum)\n        ',
        )

    @unittest.skipUnless(hasattr(signal, "sigtimedwait"), "need signal.sigtimedwait()")
    def test_sigtimedwait(self):
        self.wait_helper(
            signal.SIGALRM,
            "\n        def test(signum):\n            signal.alarm(1)\n            info = signal.sigtimedwait([signum], 10.1000)\n            if info.si_signo != signum:\n                raise Exception('info.si_signo != %s' % signum)\n        ",
        )

    @unittest.skipUnless(hasattr(signal, "sigtimedwait"), "need signal.sigtimedwait()")
    def test_sigtimedwait_poll(self):
        self.wait_helper(
            signal.SIGALRM,
            "\n        def test(signum):\n            import os\n            os.kill(os.getpid(), signum)\n            info = signal.sigtimedwait([signum], 0)\n            if info.si_signo != signum:\n                raise Exception('info.si_signo != %s' % signum)\n        ",
        )

    @unittest.skipUnless(hasattr(signal, "sigtimedwait"), "need signal.sigtimedwait()")
    def test_sigtimedwait_timeout(self):
        self.wait_helper(
            signal.SIGALRM,
            '\n        def test(signum):\n            received = signal.sigtimedwait([signum], 1.0)\n            if received is not None:\n                raise Exception("received=%r" % (received,))\n        ',
        )

    @unittest.skipUnless(hasattr(signal, "sigtimedwait"), "need signal.sigtimedwait()")
    def test_sigtimedwait_negative_timeout(self):
        signum = signal.SIGALRM
        self.assertRaises(ValueError, signal.sigtimedwait, [signum], (-1.0))

    @unittest.skipUnless(hasattr(signal, "sigwait"), "need signal.sigwait()")
    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def test_sigwait_thread(self):
        assert_python_ok(
            "-c",
            'if True:\n            import os, threading, sys, time, signal\n\n            # the default handler terminates the process\n            signum = signal.SIGUSR1\n\n            def kill_later():\n                # wait until the main thread is waiting in sigwait()\n                time.sleep(1)\n                os.kill(os.getpid(), signum)\n\n            # the signal must be blocked by all the threads\n            signal.pthread_sigmask(signal.SIG_BLOCK, [signum])\n            killer = threading.Thread(target=kill_later)\n            killer.start()\n            received = signal.sigwait([signum])\n            if received != signum:\n                print("sigwait() received %s, not %s" % (received, signum),\n                      file=sys.stderr)\n                sys.exit(1)\n            killer.join()\n            # unblock the signal, which should have been cleared by sigwait()\n            signal.pthread_sigmask(signal.SIG_UNBLOCK, [signum])\n        ',
        )

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def test_pthread_sigmask_arguments(self):
        self.assertRaises(TypeError, signal.pthread_sigmask)
        self.assertRaises(TypeError, signal.pthread_sigmask, 1)
        self.assertRaises(TypeError, signal.pthread_sigmask, 1, 2, 3)
        self.assertRaises(OSError, signal.pthread_sigmask, 1700, [])
        with self.assertRaises(ValueError):
            signal.pthread_sigmask(signal.SIG_BLOCK, [signal.NSIG])
        with self.assertRaises(ValueError):
            signal.pthread_sigmask(signal.SIG_BLOCK, [0])
        with self.assertRaises(ValueError):
            signal.pthread_sigmask(signal.SIG_BLOCK, [(1 << 1000)])

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def test_pthread_sigmask_valid_signals(self):
        s = signal.pthread_sigmask(signal.SIG_BLOCK, signal.valid_signals())
        self.addCleanup(signal.pthread_sigmask, signal.SIG_SETMASK, s)
        s = signal.pthread_sigmask(signal.SIG_UNBLOCK, signal.valid_signals())
        self.assertLessEqual(s, signal.valid_signals())

    @unittest.skipUnless(
        hasattr(signal, "pthread_sigmask"), "need signal.pthread_sigmask()"
    )
    def test_pthread_sigmask(self):
        code = 'if 1:\n        import signal\n        import os; import threading\n\n        def handler(signum, frame):\n            1/0\n\n        def kill(signum):\n            os.kill(os.getpid(), signum)\n\n        def check_mask(mask):\n            for sig in mask:\n                assert isinstance(sig, signal.Signals), repr(sig)\n\n        def read_sigmask():\n            sigmask = signal.pthread_sigmask(signal.SIG_BLOCK, [])\n            check_mask(sigmask)\n            return sigmask\n\n        signum = signal.SIGUSR1\n\n        # Install our signal handler\n        old_handler = signal.signal(signum, handler)\n\n        # Unblock SIGUSR1 (and copy the old mask) to test our signal handler\n        old_mask = signal.pthread_sigmask(signal.SIG_UNBLOCK, [signum])\n        check_mask(old_mask)\n        try:\n            kill(signum)\n        except ZeroDivisionError:\n            pass\n        else:\n            raise Exception("ZeroDivisionError not raised")\n\n        # Block and then raise SIGUSR1. The signal is blocked: the signal\n        # handler is not called, and the signal is now pending\n        mask = signal.pthread_sigmask(signal.SIG_BLOCK, [signum])\n        check_mask(mask)\n        kill(signum)\n\n        # Check the new mask\n        blocked = read_sigmask()\n        check_mask(blocked)\n        if signum not in blocked:\n            raise Exception("%s not in %s" % (signum, blocked))\n        if old_mask ^ blocked != {signum}:\n            raise Exception("%s ^ %s != {%s}" % (old_mask, blocked, signum))\n\n        # Unblock SIGUSR1\n        try:\n            # unblock the pending signal calls immediately the signal handler\n            signal.pthread_sigmask(signal.SIG_UNBLOCK, [signum])\n        except ZeroDivisionError:\n            pass\n        else:\n            raise Exception("ZeroDivisionError not raised")\n        try:\n            kill(signum)\n        except ZeroDivisionError:\n            pass\n        else:\n            raise Exception("ZeroDivisionError not raised")\n\n        # Check the new mask\n        unblocked = read_sigmask()\n        if signum in unblocked:\n            raise Exception("%s in %s" % (signum, unblocked))\n        if blocked ^ unblocked != {signum}:\n            raise Exception("%s ^ %s != {%s}" % (blocked, unblocked, signum))\n        if old_mask != unblocked:\n            raise Exception("%s != %s" % (old_mask, unblocked))\n        '
        assert_python_ok("-c", code)

    @unittest.skipUnless(hasattr(signal, "pthread_kill"), "need signal.pthread_kill()")
    def test_pthread_kill_main_thread(self):
        code = "if True:\n            import threading\n            import signal\n            import sys\n\n            def handler(signum, frame):\n                sys.exit(3)\n\n            signal.signal(signal.SIGUSR1, handler)\n            signal.pthread_kill(threading.get_ident(), signal.SIGUSR1)\n            sys.exit(2)\n        "
        with spawn_python("-c", code) as process:
            (stdout, stderr) = process.communicate()
            exitcode = process.wait()
            if exitcode != 3:
                raise Exception(("Child error (exit code %s): %s" % (exitcode, stdout)))


class StressTest(unittest.TestCase):
    "\n    Stress signal delivery, especially when a signal arrives in\n    the middle of recomputing the signal state or executing\n    previously tripped signal handlers.\n    "

    def setsig(self, signum, handler):
        old_handler = signal.signal(signum, handler)
        self.addCleanup(signal.signal, signum, old_handler)

    def measure_itimer_resolution(self):
        N = 20
        times = []

        def handler(signum=None, frame=None):
            if len(times) < N:
                times.append(time.perf_counter())
                signal.setitimer(signal.ITIMER_REAL, 1e-06)

        self.addCleanup(signal.setitimer, signal.ITIMER_REAL, 0)
        self.setsig(signal.SIGALRM, handler)
        handler()
        while len(times) < N:
            time.sleep(0.001)
        durations = [(times[(i + 1)] - times[i]) for i in range((len(times) - 1))]
        med = statistics.median(durations)
        if support.verbose:
            print(("detected median itimer() resolution: %.6f s." % (med,)))
        return med

    def decide_itimer_count(self):
        reso = self.measure_itimer_resolution()
        if reso <= 0.0001:
            return 10000
        elif reso <= 0.01:
            return 100
        else:
            self.skipTest(
                (
                    "detected itimer resolution (%.3f s.) too high (> 10 ms.) on this platform (or system too busy)"
                    % (reso,)
                )
            )

    @unittest.skipUnless(hasattr(signal, "setitimer"), "test needs setitimer()")
    def test_stress_delivery_dependent(self):
        "\n        This test uses dependent signal handlers.\n        "
        N = self.decide_itimer_count()
        sigs = []

        def first_handler(signum, frame):
            signal.setitimer(signal.ITIMER_REAL, (1e-06 + (random.random() * 1e-05)))

        def second_handler(signum=None, frame=None):
            sigs.append(signum)

        self.setsig(signal.SIGPROF, first_handler)
        self.setsig(signal.SIGUSR1, first_handler)
        self.setsig(signal.SIGALRM, second_handler)
        expected_sigs = 0
        deadline = time.monotonic() + support.SHORT_TIMEOUT
        while expected_sigs < N:
            os.kill(os.getpid(), signal.SIGPROF)
            expected_sigs += 1
            while (len(sigs) < expected_sigs) and (time.monotonic() < deadline):
                time.sleep(1e-05)
            os.kill(os.getpid(), signal.SIGUSR1)
            expected_sigs += 1
            while (len(sigs) < expected_sigs) and (time.monotonic() < deadline):
                time.sleep(1e-05)
        self.assertEqual(len(sigs), N, "Some signals were lost")

    @unittest.skipUnless(hasattr(signal, "setitimer"), "test needs setitimer()")
    def test_stress_delivery_simultaneous(self):
        "\n        This test uses simultaneous signal handlers.\n        "
        N = self.decide_itimer_count()
        sigs = []

        def handler(signum, frame):
            sigs.append(signum)

        self.setsig(signal.SIGUSR1, handler)
        self.setsig(signal.SIGALRM, handler)
        expected_sigs = 0
        deadline = time.monotonic() + support.SHORT_TIMEOUT
        while expected_sigs < N:
            signal.setitimer(signal.ITIMER_REAL, (1e-06 + (random.random() * 1e-05)))
            os.kill(os.getpid(), signal.SIGUSR1)
            expected_sigs += 2
            while (len(sigs) < expected_sigs) and (time.monotonic() < deadline):
                time.sleep(1e-05)
        self.assertEqual(len(sigs), N, "Some signals were lost")

    @unittest.skipUnless(hasattr(signal, "SIGUSR1"), "test needs SIGUSR1")
    def test_stress_modifying_handlers(self):
        signum = signal.SIGUSR1
        num_sent_signals = 0
        num_received_signals = 0
        do_stop = False

        def custom_handler(signum, frame):
            nonlocal num_received_signals
            num_received_signals += 1

        def set_interrupts():
            nonlocal num_sent_signals
            while not do_stop:
                signal.raise_signal(signum)
                num_sent_signals += 1

        def cycle_handlers():
            while num_sent_signals < 100:
                for i in range(20000):
                    for handler in [custom_handler, signal.SIG_IGN]:
                        signal.signal(signum, handler)

        old_handler = signal.signal(signum, custom_handler)
        self.addCleanup(signal.signal, signum, old_handler)
        t = threading.Thread(target=set_interrupts)
        try:
            ignored = False
            with support.catch_unraisable_exception() as cm:
                t.start()
                cycle_handlers()
                do_stop = True
                t.join()
                if cm.unraisable is not None:
                    self.assertIsInstance(cm.unraisable.exc_value, OSError)
                    self.assertIn(
                        f"Signal {signum} ignored due to race condition",
                        str(cm.unraisable.exc_value),
                    )
                    ignored = True
            if not ignored:
                self.assertGreater(num_received_signals, 0)
            self.assertLess(num_received_signals, num_sent_signals)
        finally:
            do_stop = True
            t.join()


class RaiseSignalTest(unittest.TestCase):
    def test_sigint(self):
        with self.assertRaises(KeyboardInterrupt):
            signal.raise_signal(signal.SIGINT)

    @unittest.skipIf((sys.platform != "win32"), "Windows specific test")
    def test_invalid_argument(self):
        try:
            SIGHUP = 1
            signal.raise_signal(SIGHUP)
            self.fail("OSError (Invalid argument) expected")
        except OSError as e:
            if e.errno == errno.EINVAL:
                pass
            else:
                raise

    def test_handler(self):
        is_ok = False

        def handler(a, b):
            nonlocal is_ok
            is_ok = True

        old_signal = signal.signal(signal.SIGINT, handler)
        self.addCleanup(signal.signal, signal.SIGINT, old_signal)
        signal.raise_signal(signal.SIGINT)
        self.assertTrue(is_ok)


class PidfdSignalTest(unittest.TestCase):
    @unittest.skipUnless(
        hasattr(signal, "pidfd_send_signal"), "pidfd support not built in"
    )
    def test_pidfd_send_signal(self):
        with self.assertRaises(OSError) as cm:
            signal.pidfd_send_signal(0, signal.SIGINT)
        if cm.exception.errno == errno.ENOSYS:
            self.skipTest("kernel does not support pidfds")
        elif cm.exception.errno == errno.EPERM:
            self.skipTest("Not enough privileges to use pidfs")
        self.assertEqual(cm.exception.errno, errno.EBADF)
        my_pidfd = os.open(f"/proc/{os.getpid()}", os.O_DIRECTORY)
        self.addCleanup(os.close, my_pidfd)
        with self.assertRaisesRegex(TypeError, "^siginfo must be None$"):
            signal.pidfd_send_signal(my_pidfd, signal.SIGINT, object(), 0)
        with self.assertRaises(KeyboardInterrupt):
            signal.pidfd_send_signal(my_pidfd, signal.SIGINT)


def tearDownModule():
    support.reap_children()


if __name__ == "__main__":
    unittest.main()
