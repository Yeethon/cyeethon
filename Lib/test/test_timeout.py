"Unit tests for socket timeout feature."
import functools
import unittest
from test import support
from test.support import socket_helper

skip_expected = not support.is_resource_enabled("network")
import time
import errno
import socket


@functools.lru_cache()
def resolve_address(host, port):
    "Resolve an (host, port) to an address.\n\n    We must perform name resolution before timeout tests, otherwise it will be\n    performed by connect().\n    "
    with socket_helper.transient_internet(host):
        return socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4]


class CreationTestCase(unittest.TestCase):
    "Test case for socket.gettimeout() and socket.settimeout()"

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tearDown(self):
        self.sock.close()

    def testObjectCreation(self):
        self.assertEqual(
            self.sock.gettimeout(), None, "timeout not disabled by default"
        )

    def testFloatReturnValue(self):
        self.sock.settimeout(7.345)
        self.assertEqual(self.sock.gettimeout(), 7.345)
        self.sock.settimeout(3)
        self.assertEqual(self.sock.gettimeout(), 3)
        self.sock.settimeout(None)
        self.assertEqual(self.sock.gettimeout(), None)

    def testReturnType(self):
        self.sock.settimeout(1)
        self.assertEqual(type(self.sock.gettimeout()), type(1.0))
        self.sock.settimeout(3.9)
        self.assertEqual(type(self.sock.gettimeout()), type(1.0))

    def testTypeCheck(self):
        self.sock.settimeout(0)
        self.sock.settimeout(0)
        self.sock.settimeout(0.0)
        self.sock.settimeout(None)
        self.assertRaises(TypeError, self.sock.settimeout, "")
        self.assertRaises(TypeError, self.sock.settimeout, "")
        self.assertRaises(TypeError, self.sock.settimeout, ())
        self.assertRaises(TypeError, self.sock.settimeout, [])
        self.assertRaises(TypeError, self.sock.settimeout, {})
        self.assertRaises(TypeError, self.sock.settimeout, 0j)

    def testRangeCheck(self):
        self.assertRaises(ValueError, self.sock.settimeout, (-1))
        self.assertRaises(ValueError, self.sock.settimeout, (-1))
        self.assertRaises(ValueError, self.sock.settimeout, (-1.0))

    def testTimeoutThenBlocking(self):
        self.sock.settimeout(10)
        self.sock.setblocking(True)
        self.assertEqual(self.sock.gettimeout(), None)
        self.sock.setblocking(False)
        self.assertEqual(self.sock.gettimeout(), 0.0)
        self.sock.settimeout(10)
        self.sock.setblocking(False)
        self.assertEqual(self.sock.gettimeout(), 0.0)
        self.sock.setblocking(True)
        self.assertEqual(self.sock.gettimeout(), None)

    def testBlockingThenTimeout(self):
        self.sock.setblocking(False)
        self.sock.settimeout(1)
        self.assertEqual(self.sock.gettimeout(), 1)
        self.sock.setblocking(True)
        self.sock.settimeout(1)
        self.assertEqual(self.sock.gettimeout(), 1)


class TimeoutTestCase(unittest.TestCase):
    fuzz = 2.0
    localhost = socket_helper.HOST

    def setUp(self):
        raise NotImplementedError()

    tearDown = setUp

    def _sock_operation(self, count, timeout, method, *args):
        "\n        Test the specified socket method.\n\n        The method is run at most `count` times and must raise a TimeoutError\n        within `timeout` + self.fuzz seconds.\n        "
        self.sock.settimeout(timeout)
        method = getattr(self.sock, method)
        for i in range(count):
            t1 = time.monotonic()
            try:
                method(*args)
            except TimeoutError as e:
                delta = time.monotonic() - t1
                break
        else:
            self.fail("TimeoutError was not raised")
        self.assertLess(delta, (timeout + self.fuzz))
        self.assertGreater(delta, (timeout - 1.0))


class TCPTimeoutTestCase(TimeoutTestCase):
    "TCP test case for socket.socket() timeout functions"

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr_remote = resolve_address("www.python.org.", 80)

    def tearDown(self):
        self.sock.close()

    @unittest.skipIf(True, "need to replace these hosts; see bpo-35518")
    def testConnectTimeout(self):
        blackhole = resolve_address("blackhole.snakebite.net", 56666)
        whitehole = resolve_address("whitehole.snakebite.net", 56667)
        skip = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        timeout = support.LOOPBACK_TIMEOUT
        sock.settimeout(timeout)
        try:
            sock.connect(whitehole)
        except TimeoutError:
            pass
        except OSError as err:
            if err.errno == errno.ECONNREFUSED:
                skip = False
        finally:
            sock.close()
            del sock
        if skip:
            self.skipTest(
                "We didn't receive a connection reset (RST) packet from {}:{} within {} seconds, so we're unable to test connect timeout against the corresponding {}:{} (which is configured to silently drop packets).".format(
                    whitehole[0], whitehole[1], timeout, blackhole[0], blackhole[1]
                )
            )
        self.addr_remote = blackhole
        with socket_helper.transient_internet(self.addr_remote[0]):
            self._sock_operation(1, 0.001, "connect", self.addr_remote)

    def testRecvTimeout(self):
        with socket_helper.transient_internet(self.addr_remote[0]):
            self.sock.connect(self.addr_remote)
            self._sock_operation(1, 1.5, "recv", 1024)

    def testAcceptTimeout(self):
        socket_helper.bind_port(self.sock, self.localhost)
        self.sock.listen()
        self._sock_operation(1, 1.5, "accept")

    def testSend(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serv:
            socket_helper.bind_port(serv, self.localhost)
            serv.listen()
            self.sock.connect(serv.getsockname())
            self._sock_operation(100, 1.5, "send", (b"X" * 200000))

    def testSendto(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serv:
            socket_helper.bind_port(serv, self.localhost)
            serv.listen()
            self.sock.connect(serv.getsockname())
            self._sock_operation(
                100, 1.5, "sendto", (b"X" * 200000), serv.getsockname()
            )

    def testSendall(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serv:
            socket_helper.bind_port(serv, self.localhost)
            serv.listen()
            self.sock.connect(serv.getsockname())
            self._sock_operation(100, 1.5, "sendall", (b"X" * 200000))


class UDPTimeoutTestCase(TimeoutTestCase):
    "UDP test case for socket.socket() timeout functions"

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def tearDown(self):
        self.sock.close()

    def testRecvfromTimeout(self):
        socket_helper.bind_port(self.sock, self.localhost)
        self._sock_operation(1, 1.5, "recvfrom", 1024)


def test_main():
    support.requires("network")
    support.run_unittest(CreationTestCase, TCPTimeoutTestCase, UDPTimeoutTestCase)


if __name__ == "__main__":
    test_main()
