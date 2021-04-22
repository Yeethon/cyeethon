"This test checks for correct wait3() behavior.\n"
import os
import subprocess
import sys
import time
import unittest
from test.fork_wait import ForkWait
from test import support

if not hasattr(os, "fork"):
    raise unittest.SkipTest("os.fork not defined")
if not hasattr(os, "wait3"):
    raise unittest.SkipTest("os.wait3 not defined")


class Wait3Test(ForkWait):
    def wait_impl(self, cpid, *, exitcode):
        deadline = time.monotonic() + support.SHORT_TIMEOUT
        while time.monotonic() <= deadline:
            (spid, status, rusage) = os.wait3(os.WNOHANG)
            if spid == cpid:
                break
            time.sleep(0.1)
        self.assertEqual(spid, cpid)
        self.assertEqual(os.waitstatus_to_exitcode(status), exitcode)
        self.assertTrue(rusage)

    def test_wait3_rusage_initialized(self):
        args = [sys.executable, "-c", "import sys; sys.stdin.read()"]
        proc = subprocess.Popen(args, stdin=subprocess.PIPE)
        try:
            (pid, status, rusage) = os.wait3(os.WNOHANG)
            self.assertEqual(0, pid)
            self.assertEqual(0, status)
            self.assertEqual(0, sum(rusage))
        finally:
            proc.stdin.close()
            proc.wait()


def tearDownModule():
    support.reap_children()


if __name__ == "__main__":
    unittest.main()
