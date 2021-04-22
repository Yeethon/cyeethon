"UUID objects (universally unique identifiers) according to RFC 4122.\n\nThis module provides immutable UUID objects (class UUID) and the functions\nuuid1(), uuid3(), uuid4(), uuid5() for generating version 1, 3, 4, and 5\nUUIDs as specified in RFC 4122.\n\nIf all you want is a unique ID, you should probably call uuid1() or uuid4().\nNote that uuid1() may compromise privacy since it creates a UUID containing\nthe computer's network address.  uuid4() creates a random UUID.\n\nTypical usage:\n\n    >>> import uuid\n\n    # make a UUID based on the host ID and current time\n    >>> uuid.uuid1()    # doctest: +SKIP\n    UUID('a8098c1a-f86e-11da-bd1a-00112444be1e')\n\n    # make a UUID using an MD5 hash of a namespace UUID and a name\n    >>> uuid.uuid3(uuid.NAMESPACE_DNS, 'python.org')\n    UUID('6fa459ea-ee8a-3ca4-894e-db77e160355e')\n\n    # make a random UUID\n    >>> uuid.uuid4()    # doctest: +SKIP\n    UUID('16fd2706-8baf-433b-82eb-8c7fada847da')\n\n    # make a UUID using a SHA-1 hash of a namespace UUID and a name\n    >>> uuid.uuid5(uuid.NAMESPACE_DNS, 'python.org')\n    UUID('886313e1-3b8a-5372-9b90-0c9aee199e5d')\n\n    # make a UUID from a string of hex digits (braces and hyphens ignored)\n    >>> x = uuid.UUID('{00010203-0405-0607-0809-0a0b0c0d0e0f}')\n\n    # convert a UUID to a string of hex digits in standard form\n    >>> str(x)\n    '00010203-0405-0607-0809-0a0b0c0d0e0f'\n\n    # get the raw 16 bytes of the UUID\n    >>> x.bytes\n    b'\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f'\n\n    # make a UUID from a 16-byte string\n    >>> uuid.UUID(bytes=x.bytes)\n    UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')\n"
import os
import sys
from enum import Enum, _simple_enum

__author__ = "Ka-Ping Yee <ping@zesty.ca>"
if sys.platform in ("win32", "darwin"):
    _AIX = _LINUX = False
else:
    import platform

    _platform_system = platform.system()
    _AIX = _platform_system == "AIX"
    _LINUX = _platform_system == "Linux"
_MAC_DELIM = b":"
_MAC_OMITS_LEADING_ZEROES = False
if _AIX:
    _MAC_DELIM = b"."
    _MAC_OMITS_LEADING_ZEROES = True
(RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE) = [
    "reserved for NCS compatibility",
    "specified in RFC 4122",
    "reserved for Microsoft compatibility",
    "reserved for future definition",
]
int_ = int
bytes_ = bytes


@_simple_enum(Enum)
class SafeUUID:
    safe = 0
    unsafe = -1
    unknown = None


class UUID:
    "Instances of the UUID class represent UUIDs as specified in RFC 4122.\n    UUID objects are immutable, hashable, and usable as dictionary keys.\n    Converting a UUID to a string with str() yields something in the form\n    '12345678-1234-1234-1234-123456789abc'.  The UUID constructor accepts\n    five possible forms: a similar string of hexadecimal digits, or a tuple\n    of six integer fields (with 32-bit, 16-bit, 16-bit, 8-bit, 8-bit, and\n    48-bit values respectively) as an argument named 'fields', or a string\n    of 16 bytes (with all the integer fields in big-endian order) as an\n    argument named 'bytes', or a string of 16 bytes (with the first three\n    fields in little-endian order) as an argument named 'bytes_le', or a\n    single 128-bit integer as an argument named 'int'.\n\n    UUIDs have these read-only attributes:\n\n        bytes       the UUID as a 16-byte string (containing the six\n                    integer fields in big-endian byte order)\n\n        bytes_le    the UUID as a 16-byte string (with time_low, time_mid,\n                    and time_hi_version in little-endian byte order)\n\n        fields      a tuple of the six integer fields of the UUID,\n                    which are also available as six individual attributes\n                    and two derived attributes:\n\n            time_low                the first 32 bits of the UUID\n            time_mid                the next 16 bits of the UUID\n            time_hi_version         the next 16 bits of the UUID\n            clock_seq_hi_variant    the next 8 bits of the UUID\n            clock_seq_low           the next 8 bits of the UUID\n            node                    the last 48 bits of the UUID\n\n            time                    the 60-bit timestamp\n            clock_seq               the 14-bit sequence number\n\n        hex         the UUID as a 32-character hexadecimal string\n\n        int         the UUID as a 128-bit integer\n\n        urn         the UUID as a URN as specified in RFC 4122\n\n        variant     the UUID variant (one of the constants RESERVED_NCS,\n                    RFC_4122, RESERVED_MICROSOFT, or RESERVED_FUTURE)\n\n        version     the UUID version number (1 through 5, meaningful only\n                    when the variant is RFC_4122)\n\n        is_safe     An enum indicating whether the UUID has been generated in\n                    a way that is safe for multiprocessing applications, via\n                    uuid_generate_time_safe(3).\n    "
    __slots__ = ("int", "is_safe", "__weakref__")

    def __init__(
        self,
        hex=None,
        bytes=None,
        bytes_le=None,
        fields=None,
        int=None,
        version=None,
        *,
        is_safe=SafeUUID.unknown
    ):
        "Create a UUID from either a string of 32 hexadecimal digits,\n        a string of 16 bytes as the 'bytes' argument, a string of 16 bytes\n        in little-endian order as the 'bytes_le' argument, a tuple of six\n        integers (32-bit time_low, 16-bit time_mid, 16-bit time_hi_version,\n        8-bit clock_seq_hi_variant, 8-bit clock_seq_low, 48-bit node) as\n        the 'fields' argument, or a single 128-bit integer as the 'int'\n        argument.  When a string of hex digits is given, curly braces,\n        hyphens, and a URN prefix are all optional.  For example, these\n        expressions all yield the same UUID:\n\n        UUID('{12345678-1234-5678-1234-567812345678}')\n        UUID('12345678123456781234567812345678')\n        UUID('urn:uuid:12345678-1234-5678-1234-567812345678')\n        UUID(bytes='\\x12\\x34\\x56\\x78'*4)\n        UUID(bytes_le='\\x78\\x56\\x34\\x12\\x34\\x12\\x78\\x56' +\n                      '\\x12\\x34\\x56\\x78\\x12\\x34\\x56\\x78')\n        UUID(fields=(0x12345678, 0x1234, 0x5678, 0x12, 0x34, 0x567812345678))\n        UUID(int=0x12345678123456781234567812345678)\n\n        Exactly one of 'hex', 'bytes', 'bytes_le', 'fields', or 'int' must\n        be given.  The 'version' argument is optional; if given, the resulting\n        UUID will have its variant and version set according to RFC 4122,\n        overriding the given 'hex', 'bytes', 'bytes_le', 'fields', or 'int'.\n\n        is_safe is an enum exposed as an attribute on the instance.  It\n        indicates whether the UUID has been generated in a way that is safe\n        for multiprocessing applications, via uuid_generate_time_safe(3).\n        "
        if [hex, bytes, bytes_le, fields, int].count(None) != 4:
            raise TypeError(
                "one of the hex, bytes, bytes_le, fields, or int arguments must be given"
            )
        if hex is not None:
            hex = hex.replace("urn:", "").replace("uuid:", "")
            hex = hex.strip("{}").replace("-", "")
            if len(hex) != 32:
                raise ValueError("badly formed hexadecimal UUID string")
            int = int_(hex, 16)
        if bytes_le is not None:
            if len(bytes_le) != 16:
                raise ValueError("bytes_le is not a 16-char string")
            bytes = (
                (bytes_le[(4 - 1) :: (-1)] + bytes_le[(6 - 1) : (4 - 1) : (-1)])
                + bytes_le[(8 - 1) : (6 - 1) : (-1)]
            ) + bytes_le[8:]
        if bytes is not None:
            if len(bytes) != 16:
                raise ValueError("bytes is not a 16-char string")
            assert isinstance(bytes, bytes_), repr(bytes)
            int = int_.from_bytes(bytes, byteorder="big")
        if fields is not None:
            if len(fields) != 6:
                raise ValueError("fields is not a 6-tuple")
            (
                time_low,
                time_mid,
                time_hi_version,
                clock_seq_hi_variant,
                clock_seq_low,
                node,
            ) = fields
            if not (0 <= time_low < (1 << 32)):
                raise ValueError("field 1 out of range (need a 32-bit value)")
            if not (0 <= time_mid < (1 << 16)):
                raise ValueError("field 2 out of range (need a 16-bit value)")
            if not (0 <= time_hi_version < (1 << 16)):
                raise ValueError("field 3 out of range (need a 16-bit value)")
            if not (0 <= clock_seq_hi_variant < (1 << 8)):
                raise ValueError("field 4 out of range (need an 8-bit value)")
            if not (0 <= clock_seq_low < (1 << 8)):
                raise ValueError("field 5 out of range (need an 8-bit value)")
            if not (0 <= node < (1 << 48)):
                raise ValueError("field 6 out of range (need a 48-bit value)")
            clock_seq = (clock_seq_hi_variant << 8) | clock_seq_low
            int = (
                (((time_low << 96) | (time_mid << 80)) | (time_hi_version << 64))
                | (clock_seq << 48)
            ) | node
        if int is not None:
            if not (0 <= int < (1 << 128)):
                raise ValueError("int is out of range (need a 128-bit value)")
        if version is not None:
            if not (1 <= version <= 5):
                raise ValueError("illegal version number")
            int &= ~(49152 << 48)
            int |= 32768 << 48
            int &= ~(61440 << 64)
            int |= version << 76
        object.__setattr__(self, "int", int)
        object.__setattr__(self, "is_safe", is_safe)

    def __getstate__(self):
        d = {"int": self.int}
        if self.is_safe != SafeUUID.unknown:
            d["is_safe"] = self.is_safe.value
        return d

    def __setstate__(self, state):
        object.__setattr__(self, "int", state["int"])
        object.__setattr__(
            self,
            "is_safe",
            (SafeUUID(state["is_safe"]) if ("is_safe" in state) else SafeUUID.unknown),
        )

    def __eq__(self, other):
        if isinstance(other, UUID):
            return self.int == other.int
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, UUID):
            return self.int < other.int
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, UUID):
            return self.int > other.int
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, UUID):
            return self.int <= other.int
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, UUID):
            return self.int >= other.int
        return NotImplemented

    def __hash__(self):
        return hash(self.int)

    def __int__(self):
        return self.int

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, str(self))

    def __setattr__(self, name, value):
        raise TypeError("UUID objects are immutable")

    def __str__(self):
        hex = "%032x" % self.int
        return "%s-%s-%s-%s-%s" % (hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:])

    @property
    def bytes(self):
        return self.int.to_bytes(16, "big")

    @property
    def bytes_le(self):
        bytes = self.bytes
        return (
            (bytes[(4 - 1) :: (-1)] + bytes[(6 - 1) : (4 - 1) : (-1)])
            + bytes[(8 - 1) : (6 - 1) : (-1)]
        ) + bytes[8:]

    @property
    def fields(self):
        return (
            self.time_low,
            self.time_mid,
            self.time_hi_version,
            self.clock_seq_hi_variant,
            self.clock_seq_low,
            self.node,
        )

    @property
    def time_low(self):
        return self.int >> 96

    @property
    def time_mid(self):
        return (self.int >> 80) & 65535

    @property
    def time_hi_version(self):
        return (self.int >> 64) & 65535

    @property
    def clock_seq_hi_variant(self):
        return (self.int >> 56) & 255

    @property
    def clock_seq_low(self):
        return (self.int >> 48) & 255

    @property
    def time(self):
        return (
            ((self.time_hi_version & 4095) << 48) | (self.time_mid << 32)
        ) | self.time_low

    @property
    def clock_seq(self):
        return ((self.clock_seq_hi_variant & 63) << 8) | self.clock_seq_low

    @property
    def node(self):
        return self.int & 281474976710655

    @property
    def hex(self):
        return "%032x" % self.int

    @property
    def urn(self):
        return "urn:uuid:" + str(self)

    @property
    def variant(self):
        if not (self.int & (32768 << 48)):
            return RESERVED_NCS
        elif not (self.int & (16384 << 48)):
            return RFC_4122
        elif not (self.int & (8192 << 48)):
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE

    @property
    def version(self):
        if self.variant == RFC_4122:
            return int(((self.int >> 76) & 15))


def _get_command_stdout(command, *args):
    import io, os, shutil, subprocess

    try:
        path_dirs = os.environ.get("PATH", os.defpath).split(os.pathsep)
        path_dirs.extend(["/sbin", "/usr/sbin"])
        executable = shutil.which(command, path=os.pathsep.join(path_dirs))
        if executable is None:
            return None
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        proc = subprocess.Popen(
            ((executable,) + args),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        if not proc:
            return None
        (stdout, stderr) = proc.communicate()
        return io.BytesIO(stdout)
    except (OSError, subprocess.SubprocessError):
        return None


def _is_universal(mac):
    return not (mac & (1 << 41))


def _find_mac_near_keyword(command, args, keywords, get_word_index):
    "Searches a command's output for a MAC address near a keyword.\n\n    Each line of words in the output is case-insensitively searched for\n    any of the given keywords.  Upon a match, get_word_index is invoked\n    to pick a word from the line, given the index of the match.  For\n    example, lambda i: 0 would get the first word on the line, while\n    lambda i: i - 1 would get the word preceding the keyword.\n    "
    stdout = _get_command_stdout(command, args)
    if stdout is None:
        return None
    first_local_mac = None
    for line in stdout:
        words = line.lower().rstrip().split()
        for i in range(len(words)):
            if words[i] in keywords:
                try:
                    word = words[get_word_index(i)]
                    mac = int(word.replace(_MAC_DELIM, b""), 16)
                except (ValueError, IndexError):
                    pass
                else:
                    if _is_universal(mac):
                        return mac
                    first_local_mac = first_local_mac or mac
    return first_local_mac or None


def _parse_mac(word):
    parts = word.split(_MAC_DELIM)
    if len(parts) != 6:
        return
    if _MAC_OMITS_LEADING_ZEROES:
        if not all(((1 <= len(part) <= 2) for part in parts)):
            return
        hexstr = b"".join((part.rjust(2, b"0") for part in parts))
    else:
        if not all(((len(part) == 2) for part in parts)):
            return
        hexstr = b"".join(parts)
    try:
        return int(hexstr, 16)
    except ValueError:
        return


def _find_mac_under_heading(command, args, heading):
    "Looks for a MAC address under a heading in a command's output.\n\n    The first line of words in the output is searched for the given\n    heading. Words at the same word index as the heading in subsequent\n    lines are then examined to see if they look like MAC addresses.\n    "
    stdout = _get_command_stdout(command, args)
    if stdout is None:
        return None
    keywords = stdout.readline().rstrip().split()
    try:
        column_index = keywords.index(heading)
    except ValueError:
        return None
    first_local_mac = None
    for line in stdout:
        words = line.rstrip().split()
        try:
            word = words[column_index]
        except IndexError:
            continue
        mac = _parse_mac(word)
        if mac is None:
            continue
        if _is_universal(mac):
            return mac
        if first_local_mac is None:
            first_local_mac = mac
    return first_local_mac


def _ifconfig_getnode():
    "Get the hardware address on Unix by running ifconfig."
    keywords = (b"hwaddr", b"ether", b"address:", b"lladdr")
    for args in ("", "-a", "-av"):
        mac = _find_mac_near_keyword("ifconfig", args, keywords, (lambda i: (i + 1)))
        if mac:
            return mac
        return None


def _ip_getnode():
    "Get the hardware address on Unix by running ip."
    mac = _find_mac_near_keyword("ip", "link", [b"link/ether"], (lambda i: (i + 1)))
    if mac:
        return mac
    return None


def _arp_getnode():
    "Get the hardware address on Unix by running arp."
    import os, socket

    try:
        ip_addr = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None
    mac = _find_mac_near_keyword("arp", "-an", [os.fsencode(ip_addr)], (lambda i: (-1)))
    if mac:
        return mac
    mac = _find_mac_near_keyword(
        "arp", "-an", [os.fsencode(ip_addr)], (lambda i: (i + 1))
    )
    if mac:
        return mac
    mac = _find_mac_near_keyword(
        "arp", "-an", [os.fsencode(("(%s)" % ip_addr))], (lambda i: (i + 2))
    )
    if mac:
        return mac
    return None


def _lanscan_getnode():
    "Get the hardware address on Unix by running lanscan."
    return _find_mac_near_keyword("lanscan", "-ai", [b"lan0"], (lambda i: 0))


def _netstat_getnode():
    "Get the hardware address on Unix by running netstat."
    return _find_mac_under_heading("netstat", "-ian", b"Address")


def _ipconfig_getnode():
    "[DEPRECATED] Get the hardware address on Windows."
    return _windll_getnode()


def _netbios_getnode():
    "[DEPRECATED] Get the hardware address on Windows."
    return _windll_getnode()


try:
    import _uuid

    _generate_time_safe = getattr(_uuid, "generate_time_safe", None)
    _UuidCreate = getattr(_uuid, "UuidCreate", None)
    _has_uuid_generate_time_safe = _uuid.has_uuid_generate_time_safe
except ImportError:
    _uuid = None
    _generate_time_safe = None
    _UuidCreate = None
    _has_uuid_generate_time_safe = None


def _load_system_functions():
    "[DEPRECATED] Platform-specific functions loaded at import time"


def _unix_getnode():
    "Get the hardware address on Unix using the _uuid extension module."
    if _generate_time_safe:
        (uuid_time, _) = _generate_time_safe()
        return UUID(bytes=uuid_time).node


def _windll_getnode():
    "Get the hardware address on Windows using the _uuid extension module."
    if _UuidCreate:
        uuid_bytes = _UuidCreate()
        return UUID(bytes_le=uuid_bytes).node


def _random_getnode():
    "Get a random node ID."
    import random

    return random.getrandbits(48) | (1 << 40)


if _LINUX:
    _OS_GETTERS = [_ip_getnode, _ifconfig_getnode]
elif sys.platform == "darwin":
    _OS_GETTERS = [_ifconfig_getnode, _arp_getnode, _netstat_getnode]
elif sys.platform == "win32":
    _OS_GETTERS = []
elif _AIX:
    _OS_GETTERS = [_netstat_getnode]
else:
    _OS_GETTERS = [
        _ifconfig_getnode,
        _ip_getnode,
        _arp_getnode,
        _netstat_getnode,
        _lanscan_getnode,
    ]
if os.name == "posix":
    _GETTERS = [_unix_getnode] + _OS_GETTERS
elif os.name == "nt":
    _GETTERS = [_windll_getnode] + _OS_GETTERS
else:
    _GETTERS = _OS_GETTERS
_node = None


def getnode():
    "Get the hardware address as a 48-bit positive integer.\n\n    The first time this runs, it may launch a separate program, which could\n    be quite slow.  If all attempts to obtain the hardware address fail, we\n    choose a random 48-bit number with its eighth bit set to 1 as recommended\n    in RFC 4122.\n    "
    global _node
    if _node is not None:
        return _node
    for getter in _GETTERS + [_random_getnode]:
        try:
            _node = getter()
        except:
            continue
        if (_node is not None) and (0 <= _node < (1 << 48)):
            return _node
    assert False, "_random_getnode() returned invalid value: {}".format(_node)


_last_timestamp = None


def uuid1(node=None, clock_seq=None):
    "Generate a UUID from a host ID, sequence number, and the current time.\n    If 'node' is not given, getnode() is used to obtain the hardware\n    address.  If 'clock_seq' is given, it is used as the sequence number;\n    otherwise a random 14-bit sequence number is chosen."
    if (_generate_time_safe is not None) and (node is clock_seq is None):
        (uuid_time, safely_generated) = _generate_time_safe()
        try:
            is_safe = SafeUUID(safely_generated)
        except ValueError:
            is_safe = SafeUUID.unknown
        return UUID(bytes=uuid_time, is_safe=is_safe)
    global _last_timestamp
    import time

    nanoseconds = time.time_ns()
    timestamp = (nanoseconds // 100) + 122192928000000000
    if (_last_timestamp is not None) and (timestamp <= _last_timestamp):
        timestamp = _last_timestamp + 1
    _last_timestamp = timestamp
    if clock_seq is None:
        import random

        clock_seq = random.getrandbits(14)
    time_low = timestamp & 4294967295
    time_mid = (timestamp >> 32) & 65535
    time_hi_version = (timestamp >> 48) & 4095
    clock_seq_low = clock_seq & 255
    clock_seq_hi_variant = (clock_seq >> 8) & 63
    if node is None:
        node = getnode()
    return UUID(
        fields=(
            time_low,
            time_mid,
            time_hi_version,
            clock_seq_hi_variant,
            clock_seq_low,
            node,
        ),
        version=1,
    )


def uuid3(namespace, name):
    "Generate a UUID from the MD5 hash of a namespace UUID and a name."
    from hashlib import md5

    digest = md5(
        (namespace.bytes + bytes(name, "utf-8")), usedforsecurity=False
    ).digest()
    return UUID(bytes=digest[:16], version=3)


def uuid4():
    "Generate a random UUID."
    return UUID(bytes=os.urandom(16), version=4)


def uuid5(namespace, name):
    "Generate a UUID from the SHA-1 hash of a namespace UUID and a name."
    from hashlib import sha1

    hash = sha1((namespace.bytes + bytes(name, "utf-8"))).digest()
    return UUID(bytes=hash[:16], version=5)


NAMESPACE_DNS = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_URL = UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_OID = UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")
NAMESPACE_X500 = UUID("6ba7b814-9dad-11d1-80b4-00c04fd430c8")
