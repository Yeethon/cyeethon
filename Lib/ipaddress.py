"A fast, lightweight IPv4/IPv6 manipulation library in Python.\n\nThis library is used to create/poke/manipulate IPv4 and IPv6 addresses\nand networks.\n\n"
__version__ = "1.0"
import functools

IPV4LENGTH = 32
IPV6LENGTH = 128


class AddressValueError(ValueError):
    "A Value Error related to the address."


class NetmaskValueError(ValueError):
    "A Value Error related to the netmask."


def ip_address(address):
    "Take an IP string/int and return an object of the correct type.\n\n    Args:\n        address: A string or integer, the IP address.  Either IPv4 or\n          IPv6 addresses may be supplied; integers less than 2**32 will\n          be considered to be IPv4 by default.\n\n    Returns:\n        An IPv4Address or IPv6Address object.\n\n    Raises:\n        ValueError: if the *address* passed isn't either a v4 or a v6\n          address\n\n    "
    try:
        return IPv4Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Address(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError(("%r does not appear to be an IPv4 or IPv6 address" % address))


def ip_network(address, strict=True):
    "Take an IP string/int and return an object of the correct type.\n\n    Args:\n        address: A string or integer, the IP network.  Either IPv4 or\n          IPv6 networks may be supplied; integers less than 2**32 will\n          be considered to be IPv4 by default.\n\n    Returns:\n        An IPv4Network or IPv6Network object.\n\n    Raises:\n        ValueError: if the string passed isn't either a v4 or a v6\n          address. Or if the network has host bits set.\n\n    "
    try:
        return IPv4Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Network(address, strict)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError(("%r does not appear to be an IPv4 or IPv6 network" % address))


def ip_interface(address):
    "Take an IP string/int and return an object of the correct type.\n\n    Args:\n        address: A string or integer, the IP address.  Either IPv4 or\n          IPv6 addresses may be supplied; integers less than 2**32 will\n          be considered to be IPv4 by default.\n\n    Returns:\n        An IPv4Interface or IPv6Interface object.\n\n    Raises:\n        ValueError: if the string passed isn't either a v4 or a v6\n          address.\n\n    Notes:\n        The IPv?Interface classes describe an Address on a particular\n        Network, so they're basically a combination of both the Address\n        and Network classes.\n\n    "
    try:
        return IPv4Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    try:
        return IPv6Interface(address)
    except (AddressValueError, NetmaskValueError):
        pass
    raise ValueError(("%r does not appear to be an IPv4 or IPv6 interface" % address))


def v4_int_to_packed(address):
    "Represent an address as 4 packed bytes in network (big-endian) order.\n\n    Args:\n        address: An integer representation of an IPv4 IP address.\n\n    Returns:\n        The integer address packed as 4 bytes in network (big-endian) order.\n\n    Raises:\n        ValueError: If the integer is negative or too large to be an\n          IPv4 IP address.\n\n    "
    try:
        return address.to_bytes(4, "big")
    except OverflowError:
        raise ValueError("Address negative or too large for IPv4")


def v6_int_to_packed(address):
    "Represent an address as 16 packed bytes in network (big-endian) order.\n\n    Args:\n        address: An integer representation of an IPv6 IP address.\n\n    Returns:\n        The integer address packed as 16 bytes in network (big-endian) order.\n\n    "
    try:
        return address.to_bytes(16, "big")
    except OverflowError:
        raise ValueError("Address negative or too large for IPv6")


def _split_optional_netmask(address):
    "Helper to split the netmask and raise AddressValueError if needed"
    addr = str(address).split("/")
    if len(addr) > 2:
        raise AddressValueError(("Only one '/' permitted in %r" % address))
    return addr


def _find_address_range(addresses):
    "Find a sequence of sorted deduplicated IPv#Address.\n\n    Args:\n        addresses: a list of IPv#Address objects.\n\n    Yields:\n        A tuple containing the first and last IP addresses in the sequence.\n\n    "
    it = iter(addresses)
    first = last = next(it)
    for ip in it:
        if ip._ip != (last._ip + 1):
            (yield (first, last))
            first = ip
        last = ip
    (yield (first, last))


def _count_righthand_zero_bits(number, bits):
    "Count the number of zero bits on the right hand side.\n\n    Args:\n        number: an integer.\n        bits: maximum number of bits to count.\n\n    Returns:\n        The number of zero bits on the right hand side of the number.\n\n    "
    if number == 0:
        return bits
    return min(bits, ((~number) & (number - 1)).bit_length())


def summarize_address_range(first, last):
    "Summarize a network range given the first and last IP addresses.\n\n    Example:\n        >>> list(summarize_address_range(IPv4Address('192.0.2.0'),\n        ...                              IPv4Address('192.0.2.130')))\n        ...                                #doctest: +NORMALIZE_WHITESPACE\n        [IPv4Network('192.0.2.0/25'), IPv4Network('192.0.2.128/31'),\n         IPv4Network('192.0.2.130/32')]\n\n    Args:\n        first: the first IPv4Address or IPv6Address in the range.\n        last: the last IPv4Address or IPv6Address in the range.\n\n    Returns:\n        An iterator of the summarized IPv(4|6) network objects.\n\n    Raise:\n        TypeError:\n            If the first and last objects are not IP addresses.\n            If the first and last objects are not the same version.\n        ValueError:\n            If the last object is not greater than the first.\n            If the version of the first address is not 4 or 6.\n\n    "
    if not (isinstance(first, _BaseAddress) and isinstance(last, _BaseAddress)):
        raise TypeError("first and last must be IP addresses, not networks")
    if first.version != last.version:
        raise TypeError(("%s and %s are not of the same version" % (first, last)))
    if first > last:
        raise ValueError("last IP address must be greater than first")
    if first.version == 4:
        ip = IPv4Network
    elif first.version == 6:
        ip = IPv6Network
    else:
        raise ValueError("unknown IP version")
    ip_bits = first._max_prefixlen
    first_int = first._ip
    last_int = last._ip
    while first_int <= last_int:
        nbits = min(
            _count_righthand_zero_bits(first_int, ip_bits),
            (((last_int - first_int) + 1).bit_length() - 1),
        )
        net = ip((first_int, (ip_bits - nbits)))
        (yield net)
        first_int += 1 << nbits
        if (first_int - 1) == ip._ALL_ONES:
            break


def _collapse_addresses_internal(addresses):
    "Loops through the addresses, collapsing concurrent netblocks.\n\n    Example:\n\n        ip1 = IPv4Network('192.0.2.0/26')\n        ip2 = IPv4Network('192.0.2.64/26')\n        ip3 = IPv4Network('192.0.2.128/26')\n        ip4 = IPv4Network('192.0.2.192/26')\n\n        _collapse_addresses_internal([ip1, ip2, ip3, ip4]) ->\n          [IPv4Network('192.0.2.0/24')]\n\n        This shouldn't be called directly; it is called via\n          collapse_addresses([]).\n\n    Args:\n        addresses: A list of IPv4Network's or IPv6Network's\n\n    Returns:\n        A list of IPv4Network's or IPv6Network's depending on what we were\n        passed.\n\n    "
    to_merge = list(addresses)
    subnets = {}
    while to_merge:
        net = to_merge.pop()
        supernet = net.supernet()
        existing = subnets.get(supernet)
        if existing is None:
            subnets[supernet] = net
        elif existing != net:
            del subnets[supernet]
            to_merge.append(supernet)
    last = None
    for net in sorted(subnets.values()):
        if last is not None:
            if last.broadcast_address >= net.broadcast_address:
                continue
        (yield net)
        last = net


def collapse_addresses(addresses):
    "Collapse a list of IP objects.\n\n    Example:\n        collapse_addresses([IPv4Network('192.0.2.0/25'),\n                            IPv4Network('192.0.2.128/25')]) ->\n                           [IPv4Network('192.0.2.0/24')]\n\n    Args:\n        addresses: An iterator of IPv4Network or IPv6Network objects.\n\n    Returns:\n        An iterator of the collapsed IPv(4|6)Network objects.\n\n    Raises:\n        TypeError: If passed a list of mixed version objects.\n\n    "
    addrs = []
    ips = []
    nets = []
    for ip in addresses:
        if isinstance(ip, _BaseAddress):
            if ips and (ips[(-1)]._version != ip._version):
                raise TypeError(
                    ("%s and %s are not of the same version" % (ip, ips[(-1)]))
                )
            ips.append(ip)
        elif ip._prefixlen == ip._max_prefixlen:
            if ips and (ips[(-1)]._version != ip._version):
                raise TypeError(
                    ("%s and %s are not of the same version" % (ip, ips[(-1)]))
                )
            try:
                ips.append(ip.ip)
            except AttributeError:
                ips.append(ip.network_address)
        else:
            if nets and (nets[(-1)]._version != ip._version):
                raise TypeError(
                    ("%s and %s are not of the same version" % (ip, nets[(-1)]))
                )
            nets.append(ip)
    ips = sorted(set(ips))
    if ips:
        for (first, last) in _find_address_range(ips):
            addrs.extend(summarize_address_range(first, last))
    return _collapse_addresses_internal((addrs + nets))


def get_mixed_type_key(obj):
    "Return a key suitable for sorting between networks and addresses.\n\n    Address and Network objects are not sortable by default; they're\n    fundamentally different so the expression\n\n        IPv4Address('192.0.2.0') <= IPv4Network('192.0.2.0/24')\n\n    doesn't make any sense.  There are some times however, where you may wish\n    to have ipaddress sort these for you anyway. If you need to do this, you\n    can use this function as the key= argument to sorted().\n\n    Args:\n      obj: either a Network or Address object.\n    Returns:\n      appropriate key.\n\n    "
    if isinstance(obj, _BaseNetwork):
        return obj._get_networks_key()
    elif isinstance(obj, _BaseAddress):
        return obj._get_address_key()
    return NotImplemented


class _IPAddressBase:
    "The mother class."
    __slots__ = ()

    @property
    def exploded(self):
        "Return the longhand version of the IP address as a string."
        return self._explode_shorthand_ip_string()

    @property
    def compressed(self):
        "Return the shorthand version of the IP address as a string."
        return str(self)

    @property
    def reverse_pointer(self):
        "The name of the reverse DNS pointer for the IP address, e.g.:\n            >>> ipaddress.ip_address(\"127.0.0.1\").reverse_pointer\n            '1.0.0.127.in-addr.arpa'\n            >>> ipaddress.ip_address(\"2001:db8::1\").reverse_pointer\n            '1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa'\n\n        "
        return self._reverse_pointer()

    @property
    def version(self):
        msg = "%200s has no version specified" % (type(self),)
        raise NotImplementedError(msg)

    def _check_int_address(self, address):
        if address < 0:
            msg = "%d (< 0) is not permitted as an IPv%d address"
            raise AddressValueError((msg % (address, self._version)))
        if address > self._ALL_ONES:
            msg = "%d (>= 2**%d) is not permitted as an IPv%d address"
            raise AddressValueError(
                (msg % (address, self._max_prefixlen, self._version))
            )

    def _check_packed_address(self, address, expected_len):
        address_len = len(address)
        if address_len != expected_len:
            msg = "%r (len %d != %d) is not permitted as an IPv%d address"
            raise AddressValueError(
                (msg % (address, address_len, expected_len, self._version))
            )

    @classmethod
    def _ip_int_from_prefix(cls, prefixlen):
        "Turn the prefix length into a bitwise netmask\n\n        Args:\n            prefixlen: An integer, the prefix length.\n\n        Returns:\n            An integer.\n\n        "
        return cls._ALL_ONES ^ (cls._ALL_ONES >> prefixlen)

    @classmethod
    def _prefix_from_ip_int(cls, ip_int):
        "Return prefix length from the bitwise netmask.\n\n        Args:\n            ip_int: An integer, the netmask in expanded bitwise format\n\n        Returns:\n            An integer, the prefix length.\n\n        Raises:\n            ValueError: If the input intermingles zeroes & ones\n        "
        trailing_zeroes = _count_righthand_zero_bits(ip_int, cls._max_prefixlen)
        prefixlen = cls._max_prefixlen - trailing_zeroes
        leading_ones = ip_int >> trailing_zeroes
        all_ones = (1 << prefixlen) - 1
        if leading_ones != all_ones:
            byteslen = cls._max_prefixlen // 8
            details = ip_int.to_bytes(byteslen, "big")
            msg = "Netmask pattern %r mixes zeroes & ones"
            raise ValueError((msg % details))
        return prefixlen

    @classmethod
    def _report_invalid_netmask(cls, netmask_str):
        msg = "%r is not a valid netmask" % netmask_str
        raise NetmaskValueError(msg) from None

    @classmethod
    def _prefix_from_prefix_string(cls, prefixlen_str):
        "Return prefix length from a numeric string\n\n        Args:\n            prefixlen_str: The string to be converted\n\n        Returns:\n            An integer, the prefix length.\n\n        Raises:\n            NetmaskValueError: If the input is not a valid netmask\n        "
        if not (prefixlen_str.isascii() and prefixlen_str.isdigit()):
            cls._report_invalid_netmask(prefixlen_str)
        try:
            prefixlen = int(prefixlen_str)
        except ValueError:
            cls._report_invalid_netmask(prefixlen_str)
        if not (0 <= prefixlen <= cls._max_prefixlen):
            cls._report_invalid_netmask(prefixlen_str)
        return prefixlen

    @classmethod
    def _prefix_from_ip_string(cls, ip_str):
        "Turn a netmask/hostmask string into a prefix length\n\n        Args:\n            ip_str: The netmask/hostmask to be converted\n\n        Returns:\n            An integer, the prefix length.\n\n        Raises:\n            NetmaskValueError: If the input is not a valid netmask/hostmask\n        "
        try:
            ip_int = cls._ip_int_from_string(ip_str)
        except AddressValueError:
            cls._report_invalid_netmask(ip_str)
        try:
            return cls._prefix_from_ip_int(ip_int)
        except ValueError:
            pass
        ip_int ^= cls._ALL_ONES
        try:
            return cls._prefix_from_ip_int(ip_int)
        except ValueError:
            cls._report_invalid_netmask(ip_str)

    @classmethod
    def _split_addr_prefix(cls, address):
        "Helper function to parse address of Network/Interface.\n\n        Arg:\n            address: Argument of Network/Interface.\n\n        Returns:\n            (addr, prefix) tuple.\n        "
        if isinstance(address, (bytes, int)):
            return (address, cls._max_prefixlen)
        if not isinstance(address, tuple):
            address = _split_optional_netmask(address)
        if len(address) > 1:
            return address
        return (address[0], cls._max_prefixlen)

    def __reduce__(self):
        return (self.__class__, (str(self),))


_address_fmt_re = None


@functools.total_ordering
class _BaseAddress(_IPAddressBase):
    "A generic IP object.\n\n    This IP class contains the version independent methods which are\n    used by single IP addresses.\n    "
    __slots__ = ()

    def __int__(self):
        return self._ip

    def __eq__(self, other):
        try:
            return (self._ip == other._ip) and (self._version == other._version)
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        if not isinstance(other, _BaseAddress):
            return NotImplemented
        if self._version != other._version:
            raise TypeError(("%s and %s are not of the same version" % (self, other)))
        if self._ip != other._ip:
            return self._ip < other._ip
        return False

    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__((int(self) + other))

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return self.__class__((int(self) - other))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, str(self))

    def __str__(self):
        return str(self._string_from_ip_int(self._ip))

    def __hash__(self):
        return hash(hex(int(self._ip)))

    def _get_address_key(self):
        return (self._version, self)

    def __reduce__(self):
        return (self.__class__, (self._ip,))

    def __format__(self, fmt):
        "Returns an IP address as a formatted string.\n\n        Supported presentation types are:\n        's': returns the IP address as a string (default)\n        'b': converts to binary and returns a zero-padded string\n        'X' or 'x': converts to upper- or lower-case hex and returns a zero-padded string\n        'n': the same as 'b' for IPv4 and 'x' for IPv6\n\n        For binary and hex presentation types, the alternate form specifier\n        '#' and the grouping option '_' are supported.\n        "
        if (not fmt) or (fmt[(-1)] == "s"):
            return format(str(self), fmt)
        global _address_fmt_re
        if _address_fmt_re is None:
            import re

            _address_fmt_re = re.compile("(#?)(_?)([xbnX])")
        m = _address_fmt_re.fullmatch(fmt)
        if not m:
            return super().__format__(fmt)
        (alternate, grouping, fmt_base) = m.groups()
        if fmt_base == "n":
            if self._version == 4:
                fmt_base = "b"
            else:
                fmt_base = "x"
        if fmt_base == "b":
            padlen = self._max_prefixlen
        else:
            padlen = self._max_prefixlen // 4
        if grouping:
            padlen += (padlen // 4) - 1
        if alternate:
            padlen += 2
        return format(int(self), f"{alternate}0{padlen}{grouping}{fmt_base}")


@functools.total_ordering
class _BaseNetwork(_IPAddressBase):
    "A generic IP network object.\n\n    This IP class contains the version independent methods which are\n    used by networks.\n    "

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, str(self))

    def __str__(self):
        return "%s/%d" % (self.network_address, self.prefixlen)

    def hosts(self):
        "Generate Iterator over usable hosts in a network.\n\n        This is like __iter__ except it doesn't return the network\n        or broadcast addresses.\n\n        "
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range((network + 1), broadcast):
            (yield self._address_class(x))

    def __iter__(self):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range(network, (broadcast + 1)):
            (yield self._address_class(x))

    def __getitem__(self, n):
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        if n >= 0:
            if (network + n) > broadcast:
                raise IndexError("address out of range")
            return self._address_class((network + n))
        else:
            n += 1
            if (broadcast + n) < network:
                raise IndexError("address out of range")
            return self._address_class((broadcast + n))

    def __lt__(self, other):
        if not isinstance(other, _BaseNetwork):
            return NotImplemented
        if self._version != other._version:
            raise TypeError(("%s and %s are not of the same version" % (self, other)))
        if self.network_address != other.network_address:
            return self.network_address < other.network_address
        if self.netmask != other.netmask:
            return self.netmask < other.netmask
        return False

    def __eq__(self, other):
        try:
            return (
                (self._version == other._version)
                and (self.network_address == other.network_address)
                and (int(self.netmask) == int(other.netmask))
            )
        except AttributeError:
            return NotImplemented

    def __hash__(self):
        return hash((int(self.network_address) ^ int(self.netmask)))

    def __contains__(self, other):
        if self._version != other._version:
            return False
        if isinstance(other, _BaseNetwork):
            return False
        else:
            return (other._ip & self.netmask._ip) == self.network_address._ip

    def overlaps(self, other):
        "Tell if self is partly contained in other."
        return (self.network_address in other) or (
            (self.broadcast_address in other)
            or ((other.network_address in self) or (other.broadcast_address in self))
        )

    @functools.cached_property
    def broadcast_address(self):
        return self._address_class((int(self.network_address) | int(self.hostmask)))

    @functools.cached_property
    def hostmask(self):
        return self._address_class((int(self.netmask) ^ self._ALL_ONES))

    @property
    def with_prefixlen(self):
        return "%s/%d" % (self.network_address, self._prefixlen)

    @property
    def with_netmask(self):
        return "%s/%s" % (self.network_address, self.netmask)

    @property
    def with_hostmask(self):
        return "%s/%s" % (self.network_address, self.hostmask)

    @property
    def num_addresses(self):
        "Number of hosts in the current subnet."
        return (int(self.broadcast_address) - int(self.network_address)) + 1

    @property
    def _address_class(self):
        msg = "%200s has no associated address class" % (type(self),)
        raise NotImplementedError(msg)

    @property
    def prefixlen(self):
        return self._prefixlen

    def address_exclude(self, other):
        "Remove an address from a larger block.\n\n        For example:\n\n            addr1 = ip_network('192.0.2.0/28')\n            addr2 = ip_network('192.0.2.1/32')\n            list(addr1.address_exclude(addr2)) =\n                [IPv4Network('192.0.2.0/32'), IPv4Network('192.0.2.2/31'),\n                 IPv4Network('192.0.2.4/30'), IPv4Network('192.0.2.8/29')]\n\n        or IPv6:\n\n            addr1 = ip_network('2001:db8::1/32')\n            addr2 = ip_network('2001:db8::1/128')\n            list(addr1.address_exclude(addr2)) =\n                [ip_network('2001:db8::1/128'),\n                 ip_network('2001:db8::2/127'),\n                 ip_network('2001:db8::4/126'),\n                 ip_network('2001:db8::8/125'),\n                 ...\n                 ip_network('2001:db8:8000::/33')]\n\n        Args:\n            other: An IPv4Network or IPv6Network object of the same type.\n\n        Returns:\n            An iterator of the IPv(4|6)Network objects which is self\n            minus other.\n\n        Raises:\n            TypeError: If self and other are of differing address\n              versions, or if other is not a network object.\n            ValueError: If other is not completely contained by self.\n\n        "
        if not (self._version == other._version):
            raise TypeError(("%s and %s are not of the same version" % (self, other)))
        if not isinstance(other, _BaseNetwork):
            raise TypeError(("%s is not a network object" % other))
        if not other.subnet_of(self):
            raise ValueError(("%s not contained in %s" % (other, self)))
        if other == self:
            return
        other = other.__class__(("%s/%s" % (other.network_address, other.prefixlen)))
        (s1, s2) = self.subnets()
        while (s1 != other) and (s2 != other):
            if other.subnet_of(s1):
                (yield s2)
                (s1, s2) = s1.subnets()
            elif other.subnet_of(s2):
                (yield s1)
                (s1, s2) = s2.subnets()
            else:
                raise AssertionError(
                    (
                        "Error performing exclusion: s1: %s s2: %s other: %s"
                        % (s1, s2, other)
                    )
                )
        if s1 == other:
            (yield s2)
        elif s2 == other:
            (yield s1)
        else:
            raise AssertionError(
                (
                    "Error performing exclusion: s1: %s s2: %s other: %s"
                    % (s1, s2, other)
                )
            )

    def compare_networks(self, other):
        "Compare two IP objects.\n\n        This is only concerned about the comparison of the integer\n        representation of the network addresses.  This means that the\n        host bits aren't considered at all in this method.  If you want\n        to compare host bits, you can easily enough do a\n        'HostA._ip < HostB._ip'\n\n        Args:\n            other: An IP object.\n\n        Returns:\n            If the IP versions of self and other are the same, returns:\n\n            -1 if self < other:\n              eg: IPv4Network('192.0.2.0/25') < IPv4Network('192.0.2.128/25')\n              IPv6Network('2001:db8::1000/124') <\n                  IPv6Network('2001:db8::2000/124')\n            0 if self == other\n              eg: IPv4Network('192.0.2.0/24') == IPv4Network('192.0.2.0/24')\n              IPv6Network('2001:db8::1000/124') ==\n                  IPv6Network('2001:db8::1000/124')\n            1 if self > other\n              eg: IPv4Network('192.0.2.128/25') > IPv4Network('192.0.2.0/25')\n                  IPv6Network('2001:db8::2000/124') >\n                      IPv6Network('2001:db8::1000/124')\n\n          Raises:\n              TypeError if the IP versions are different.\n\n        "
        if self._version != other._version:
            raise TypeError(("%s and %s are not of the same type" % (self, other)))
        if self.network_address < other.network_address:
            return -1
        if self.network_address > other.network_address:
            return 1
        if self.netmask < other.netmask:
            return -1
        if self.netmask > other.netmask:
            return 1
        return 0

    def _get_networks_key(self):
        'Network-only key function.\n\n        Returns an object that identifies this address\' network and\n        netmask. This function is a suitable "key" argument for sorted()\n        and list.sort().\n\n        '
        return (self._version, self.network_address, self.netmask)

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        "The subnets which join to make the current subnet.\n\n        In the case that self contains only one IP\n        (self._prefixlen == 32 for IPv4 or self._prefixlen == 128\n        for IPv6), yield an iterator with just ourself.\n\n        Args:\n            prefixlen_diff: An integer, the amount the prefix length\n              should be increased by. This should not be set if\n              new_prefix is also set.\n            new_prefix: The desired new prefix length. This must be a\n              larger number (smaller prefix) than the existing prefix.\n              This should not be set if prefixlen_diff is also set.\n\n        Returns:\n            An iterator of IPv(4|6) objects.\n\n        Raises:\n            ValueError: The prefixlen_diff is too small or too large.\n                OR\n            prefixlen_diff and new_prefix are both set or new_prefix\n              is a smaller number than the current prefix (smaller\n              number means a larger network)\n\n        "
        if self._prefixlen == self._max_prefixlen:
            (yield self)
            return
        if new_prefix is not None:
            if new_prefix < self._prefixlen:
                raise ValueError("new prefix must be longer")
            if prefixlen_diff != 1:
                raise ValueError("cannot set prefixlen_diff and new_prefix")
            prefixlen_diff = new_prefix - self._prefixlen
        if prefixlen_diff < 0:
            raise ValueError("prefix length diff must be > 0")
        new_prefixlen = self._prefixlen + prefixlen_diff
        if new_prefixlen > self._max_prefixlen:
            raise ValueError(
                (
                    "prefix length diff %d is invalid for netblock %s"
                    % (new_prefixlen, self)
                )
            )
        start = int(self.network_address)
        end = int(self.broadcast_address) + 1
        step = (int(self.hostmask) + 1) >> prefixlen_diff
        for new_addr in range(start, end, step):
            current = self.__class__((new_addr, new_prefixlen))
            (yield current)

    def supernet(self, prefixlen_diff=1, new_prefix=None):
        "The supernet containing the current network.\n\n        Args:\n            prefixlen_diff: An integer, the amount the prefix length of\n              the network should be decreased by.  For example, given a\n              /24 network and a prefixlen_diff of 3, a supernet with a\n              /21 netmask is returned.\n\n        Returns:\n            An IPv4 network object.\n\n        Raises:\n            ValueError: If self.prefixlen - prefixlen_diff < 0. I.e., you have\n              a negative prefix length.\n                OR\n            If prefixlen_diff and new_prefix are both set or new_prefix is a\n              larger number than the current prefix (larger number means a\n              smaller network)\n\n        "
        if self._prefixlen == 0:
            return self
        if new_prefix is not None:
            if new_prefix > self._prefixlen:
                raise ValueError("new prefix must be shorter")
            if prefixlen_diff != 1:
                raise ValueError("cannot set prefixlen_diff and new_prefix")
            prefixlen_diff = self._prefixlen - new_prefix
        new_prefixlen = self.prefixlen - prefixlen_diff
        if new_prefixlen < 0:
            raise ValueError(
                (
                    "current prefixlen is %d, cannot have a prefixlen_diff of %d"
                    % (self.prefixlen, prefixlen_diff)
                )
            )
        return self.__class__(
            (
                (int(self.network_address) & (int(self.netmask) << prefixlen_diff)),
                new_prefixlen,
            )
        )

    @property
    def is_multicast(self):
        "Test if the address is reserved for multicast use.\n\n        Returns:\n            A boolean, True if the address is a multicast address.\n            See RFC 2373 2.7 for details.\n\n        "
        return self.network_address.is_multicast and self.broadcast_address.is_multicast

    @staticmethod
    def _is_subnet_of(a, b):
        try:
            if a._version != b._version:
                raise TypeError(f"{a} and {b} are not of the same version")
            return (b.network_address <= a.network_address) and (
                b.broadcast_address >= a.broadcast_address
            )
        except AttributeError:
            raise TypeError(f"Unable to test subnet containment between {a} and {b}")

    def subnet_of(self, other):
        "Return True if this network is a subnet of other."
        return self._is_subnet_of(self, other)

    def supernet_of(self, other):
        "Return True if this network is a supernet of other."
        return self._is_subnet_of(other, self)

    @property
    def is_reserved(self):
        "Test if the address is otherwise IETF reserved.\n\n        Returns:\n            A boolean, True if the address is within one of the\n            reserved IPv6 Network ranges.\n\n        "
        return self.network_address.is_reserved and self.broadcast_address.is_reserved

    @property
    def is_link_local(self):
        "Test if the address is reserved for link-local.\n\n        Returns:\n            A boolean, True if the address is reserved per RFC 4291.\n\n        "
        return (
            self.network_address.is_link_local and self.broadcast_address.is_link_local
        )

    @property
    def is_private(self):
        "Test if this address is allocated for private networks.\n\n        Returns:\n            A boolean, True if the address is reserved per\n            iana-ipv4-special-registry or iana-ipv6-special-registry.\n\n        "
        return self.network_address.is_private and self.broadcast_address.is_private

    @property
    def is_global(self):
        "Test if this address is allocated for public networks.\n\n        Returns:\n            A boolean, True if the address is not reserved per\n            iana-ipv4-special-registry or iana-ipv6-special-registry.\n\n        "
        return not self.is_private

    @property
    def is_unspecified(self):
        "Test if the address is unspecified.\n\n        Returns:\n            A boolean, True if this is the unspecified address as defined in\n            RFC 2373 2.5.2.\n\n        "
        return (
            self.network_address.is_unspecified
            and self.broadcast_address.is_unspecified
        )

    @property
    def is_loopback(self):
        "Test if the address is a loopback address.\n\n        Returns:\n            A boolean, True if the address is a loopback address as defined in\n            RFC 2373 2.5.3.\n\n        "
        return self.network_address.is_loopback and self.broadcast_address.is_loopback


class _BaseV4:
    "Base IPv4 object.\n\n    The following methods are used by IPv4 objects in both single IP\n    addresses and networks.\n\n    "
    __slots__ = ()
    _version = 4
    _ALL_ONES = (2 ** IPV4LENGTH) - 1
    _max_prefixlen = IPV4LENGTH
    _netmask_cache = {}

    def _explode_shorthand_ip_string(self):
        return str(self)

    @classmethod
    def _make_netmask(cls, arg):
        'Make a (netmask, prefix_len) tuple from the given argument.\n\n        Argument can be:\n        - an integer (the prefix length)\n        - a string representing the prefix length (e.g. "24")\n        - a string representing the prefix netmask (e.g. "255.255.255.0")\n        '
        if arg not in cls._netmask_cache:
            if isinstance(arg, int):
                prefixlen = arg
                if not (0 <= prefixlen <= cls._max_prefixlen):
                    cls._report_invalid_netmask(prefixlen)
            else:
                try:
                    prefixlen = cls._prefix_from_prefix_string(arg)
                except NetmaskValueError:
                    prefixlen = cls._prefix_from_ip_string(arg)
            netmask = IPv4Address(cls._ip_int_from_prefix(prefixlen))
            cls._netmask_cache[arg] = (netmask, prefixlen)
        return cls._netmask_cache[arg]

    @classmethod
    def _ip_int_from_string(cls, ip_str):
        "Turn the given IP string into an integer for comparison.\n\n        Args:\n            ip_str: A string, the IP ip_str.\n\n        Returns:\n            The IP ip_str as an integer.\n\n        Raises:\n            AddressValueError: if ip_str isn't a valid IPv4 Address.\n\n        "
        if not ip_str:
            raise AddressValueError("Address cannot be empty")
        octets = ip_str.split(".")
        if len(octets) != 4:
            raise AddressValueError(("Expected 4 octets in %r" % ip_str))
        try:
            return int.from_bytes(map(cls._parse_octet, octets), "big")
        except ValueError as exc:
            raise AddressValueError(("%s in %r" % (exc, ip_str))) from None

    @classmethod
    def _parse_octet(cls, octet_str):
        "Convert a decimal octet into an integer.\n\n        Args:\n            octet_str: A string, the number to parse.\n\n        Returns:\n            The octet as an integer.\n\n        Raises:\n            ValueError: if the octet isn't strictly a decimal from [0..255].\n\n        "
        if not octet_str:
            raise ValueError("Empty octet not permitted")
        if not (octet_str.isascii() and octet_str.isdigit()):
            msg = "Only decimal digits permitted in %r"
            raise ValueError((msg % octet_str))
        if len(octet_str) > 3:
            msg = "At most 3 characters permitted in %r"
            raise ValueError((msg % octet_str))
        octet_int = int(octet_str, 10)
        if octet_int > 255:
            raise ValueError(("Octet %d (> 255) not permitted" % octet_int))
        return octet_int

    @classmethod
    def _string_from_ip_int(cls, ip_int):
        "Turns a 32-bit integer into dotted decimal notation.\n\n        Args:\n            ip_int: An integer, the IP address.\n\n        Returns:\n            The IP address as a string in dotted decimal notation.\n\n        "
        return ".".join(map(str, ip_int.to_bytes(4, "big")))

    def _reverse_pointer(self):
        "Return the reverse DNS pointer name for the IPv4 address.\n\n        This implements the method described in RFC1035 3.5.\n\n        "
        reverse_octets = str(self).split(".")[::(-1)]
        return ".".join(reverse_octets) + ".in-addr.arpa"

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version


class IPv4Address(_BaseV4, _BaseAddress):
    "Represent and manipulate single IPv4 Addresses."
    __slots__ = ("_ip", "__weakref__")

    def __init__(self, address):
        "\n        Args:\n            address: A string or integer representing the IP\n\n              Additionally, an integer can be passed, so\n              IPv4Address('192.0.2.1') == IPv4Address(3221225985).\n              or, more generally\n              IPv4Address(int(IPv4Address('192.0.2.1'))) ==\n                IPv4Address('192.0.2.1')\n\n        Raises:\n            AddressValueError: If ipaddress isn't a valid IPv4 address.\n\n        "
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            return
        if isinstance(address, bytes):
            self._check_packed_address(address, 4)
            self._ip = int.from_bytes(address, "big")
            return
        addr_str = str(address)
        if "/" in addr_str:
            raise AddressValueError(("Unexpected '/' in %r" % address))
        self._ip = self._ip_int_from_string(addr_str)

    @property
    def packed(self):
        "The binary representation of this address."
        return v4_int_to_packed(self._ip)

    @property
    def is_reserved(self):
        "Test if the address is otherwise IETF reserved.\n\n         Returns:\n             A boolean, True if the address is within the\n             reserved IPv4 Network range.\n\n        "
        return self in self._constants._reserved_network

    @property
    @functools.lru_cache()
    def is_private(self):
        "Test if this address is allocated for private networks.\n\n        Returns:\n            A boolean, True if the address is reserved per\n            iana-ipv4-special-registry.\n\n        "
        return any(((self in net) for net in self._constants._private_networks))

    @property
    @functools.lru_cache()
    def is_global(self):
        return (self not in self._constants._public_network) and (not self.is_private)

    @property
    def is_multicast(self):
        "Test if the address is reserved for multicast use.\n\n        Returns:\n            A boolean, True if the address is multicast.\n            See RFC 3171 for details.\n\n        "
        return self in self._constants._multicast_network

    @property
    def is_unspecified(self):
        "Test if the address is unspecified.\n\n        Returns:\n            A boolean, True if this is the unspecified address as defined in\n            RFC 5735 3.\n\n        "
        return self == self._constants._unspecified_address

    @property
    def is_loopback(self):
        "Test if the address is a loopback address.\n\n        Returns:\n            A boolean, True if the address is a loopback per RFC 3330.\n\n        "
        return self in self._constants._loopback_network

    @property
    def is_link_local(self):
        "Test if the address is reserved for link-local.\n\n        Returns:\n            A boolean, True if the address is link-local per RFC 3927.\n\n        "
        return self in self._constants._linklocal_network


class IPv4Interface(IPv4Address):
    def __init__(self, address):
        (addr, mask) = self._split_addr_prefix(address)
        IPv4Address.__init__(self, addr)
        self.network = IPv4Network((addr, mask), strict=False)
        self.netmask = self.network.netmask
        self._prefixlen = self.network._prefixlen

    @functools.cached_property
    def hostmask(self):
        return self.network.hostmask

    def __str__(self):
        return "%s/%d" % (self._string_from_ip_int(self._ip), self._prefixlen)

    def __eq__(self, other):
        address_equal = IPv4Address.__eq__(self, other)
        if (address_equal is NotImplemented) or (not address_equal):
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            return False

    def __lt__(self, other):
        address_less = IPv4Address.__lt__(self, other)
        if address_less is NotImplemented:
            return NotImplemented
        try:
            return (self.network < other.network) or (
                (self.network == other.network) and address_less
            )
        except AttributeError:
            return False

    def __hash__(self):
        return hash((self._ip, self._prefixlen, int(self.network.network_address)))

    __reduce__ = _IPAddressBase.__reduce__

    @property
    def ip(self):
        return IPv4Address(self._ip)

    @property
    def with_prefixlen(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self._prefixlen)

    @property
    def with_netmask(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self.netmask)

    @property
    def with_hostmask(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self.hostmask)


class IPv4Network(_BaseV4, _BaseNetwork):
    "This class represents and manipulates 32-bit IPv4 network + addresses..\n\n    Attributes: [examples for IPv4Network('192.0.2.0/27')]\n        .network_address: IPv4Address('192.0.2.0')\n        .hostmask: IPv4Address('0.0.0.31')\n        .broadcast_address: IPv4Address('192.0.2.32')\n        .netmask: IPv4Address('255.255.255.224')\n        .prefixlen: 27\n\n    "
    _address_class = IPv4Address

    def __init__(self, address, strict=True):
        "Instantiate a new IPv4 network object.\n\n        Args:\n            address: A string or integer representing the IP [& network].\n              '192.0.2.0/24'\n              '192.0.2.0/255.255.255.0'\n              '192.0.2.0/0.0.0.255'\n              are all functionally the same in IPv4. Similarly,\n              '192.0.2.1'\n              '192.0.2.1/255.255.255.255'\n              '192.0.2.1/32'\n              are also functionally equivalent. That is to say, failing to\n              provide a subnetmask will create an object with a mask of /32.\n\n              If the mask (portion after the / in the argument) is given in\n              dotted quad form, it is treated as a netmask if it starts with a\n              non-zero field (e.g. /255.0.0.0 == /8) and as a hostmask if it\n              starts with a zero field (e.g. 0.255.255.255 == /8), with the\n              single exception of an all-zero mask which is treated as a\n              netmask == /0. If no mask is given, a default of /32 is used.\n\n              Additionally, an integer can be passed, so\n              IPv4Network('192.0.2.1') == IPv4Network(3221225985)\n              or, more generally\n              IPv4Interface(int(IPv4Interface('192.0.2.1'))) ==\n                IPv4Interface('192.0.2.1')\n\n        Raises:\n            AddressValueError: If ipaddress isn't a valid IPv4 address.\n            NetmaskValueError: If the netmask isn't valid for\n              an IPv4 address.\n            ValueError: If strict is True and a network address is not\n              supplied.\n        "
        (addr, mask) = self._split_addr_prefix(address)
        self.network_address = IPv4Address(addr)
        (self.netmask, self._prefixlen) = self._make_netmask(mask)
        packed = int(self.network_address)
        if (packed & int(self.netmask)) != packed:
            if strict:
                raise ValueError(("%s has host bits set" % self))
            else:
                self.network_address = IPv4Address((packed & int(self.netmask)))
        if self._prefixlen == (self._max_prefixlen - 1):
            self.hosts = self.__iter__
        elif self._prefixlen == self._max_prefixlen:
            self.hosts = lambda: [IPv4Address(addr)]

    @property
    @functools.lru_cache()
    def is_global(self):
        "Test if this address is allocated for public networks.\n\n        Returns:\n            A boolean, True if the address is not reserved per\n            iana-ipv4-special-registry.\n\n        "
        return (
            not (
                (self.network_address in IPv4Network("100.64.0.0/10"))
                and (self.broadcast_address in IPv4Network("100.64.0.0/10"))
            )
        ) and (not self.is_private)


class _IPv4Constants:
    _linklocal_network = IPv4Network("169.254.0.0/16")
    _loopback_network = IPv4Network("127.0.0.0/8")
    _multicast_network = IPv4Network("224.0.0.0/4")
    _public_network = IPv4Network("100.64.0.0/10")
    _private_networks = [
        IPv4Network("0.0.0.0/8"),
        IPv4Network("10.0.0.0/8"),
        IPv4Network("127.0.0.0/8"),
        IPv4Network("169.254.0.0/16"),
        IPv4Network("172.16.0.0/12"),
        IPv4Network("192.0.0.0/29"),
        IPv4Network("192.0.0.170/31"),
        IPv4Network("192.0.2.0/24"),
        IPv4Network("192.168.0.0/16"),
        IPv4Network("198.18.0.0/15"),
        IPv4Network("198.51.100.0/24"),
        IPv4Network("203.0.113.0/24"),
        IPv4Network("240.0.0.0/4"),
        IPv4Network("255.255.255.255/32"),
    ]
    _reserved_network = IPv4Network("240.0.0.0/4")
    _unspecified_address = IPv4Address("0.0.0.0")


IPv4Address._constants = _IPv4Constants


class _BaseV6:
    "Base IPv6 object.\n\n    The following methods are used by IPv6 objects in both single IP\n    addresses and networks.\n\n    "
    __slots__ = ()
    _version = 6
    _ALL_ONES = (2 ** IPV6LENGTH) - 1
    _HEXTET_COUNT = 8
    _HEX_DIGITS = frozenset("0123456789ABCDEFabcdef")
    _max_prefixlen = IPV6LENGTH
    _netmask_cache = {}

    @classmethod
    def _make_netmask(cls, arg):
        'Make a (netmask, prefix_len) tuple from the given argument.\n\n        Argument can be:\n        - an integer (the prefix length)\n        - a string representing the prefix length (e.g. "24")\n        - a string representing the prefix netmask (e.g. "255.255.255.0")\n        '
        if arg not in cls._netmask_cache:
            if isinstance(arg, int):
                prefixlen = arg
                if not (0 <= prefixlen <= cls._max_prefixlen):
                    cls._report_invalid_netmask(prefixlen)
            else:
                prefixlen = cls._prefix_from_prefix_string(arg)
            netmask = IPv6Address(cls._ip_int_from_prefix(prefixlen))
            cls._netmask_cache[arg] = (netmask, prefixlen)
        return cls._netmask_cache[arg]

    @classmethod
    def _ip_int_from_string(cls, ip_str):
        "Turn an IPv6 ip_str into an integer.\n\n        Args:\n            ip_str: A string, the IPv6 ip_str.\n\n        Returns:\n            An int, the IPv6 address\n\n        Raises:\n            AddressValueError: if ip_str isn't a valid IPv6 Address.\n\n        "
        if not ip_str:
            raise AddressValueError("Address cannot be empty")
        parts = ip_str.split(":")
        _min_parts = 3
        if len(parts) < _min_parts:
            msg = "At least %d parts expected in %r" % (_min_parts, ip_str)
            raise AddressValueError(msg)
        if "." in parts[(-1)]:
            try:
                ipv4_int = IPv4Address(parts.pop())._ip
            except AddressValueError as exc:
                raise AddressValueError(("%s in %r" % (exc, ip_str))) from None
            parts.append(("%x" % ((ipv4_int >> 16) & 65535)))
            parts.append(("%x" % (ipv4_int & 65535)))
        _max_parts = cls._HEXTET_COUNT + 1
        if len(parts) > _max_parts:
            msg = "At most %d colons permitted in %r" % ((_max_parts - 1), ip_str)
            raise AddressValueError(msg)
        skip_index = None
        for i in range(1, (len(parts) - 1)):
            if not parts[i]:
                if skip_index is not None:
                    msg = "At most one '::' permitted in %r" % ip_str
                    raise AddressValueError(msg)
                skip_index = i
        if skip_index is not None:
            parts_hi = skip_index
            parts_lo = (len(parts) - skip_index) - 1
            if not parts[0]:
                parts_hi -= 1
                if parts_hi:
                    msg = "Leading ':' only permitted as part of '::' in %r"
                    raise AddressValueError((msg % ip_str))
            if not parts[(-1)]:
                parts_lo -= 1
                if parts_lo:
                    msg = "Trailing ':' only permitted as part of '::' in %r"
                    raise AddressValueError((msg % ip_str))
            parts_skipped = cls._HEXTET_COUNT - (parts_hi + parts_lo)
            if parts_skipped < 1:
                msg = "Expected at most %d other parts with '::' in %r"
                raise AddressValueError((msg % ((cls._HEXTET_COUNT - 1), ip_str)))
        else:
            if len(parts) != cls._HEXTET_COUNT:
                msg = "Exactly %d parts expected without '::' in %r"
                raise AddressValueError((msg % (cls._HEXTET_COUNT, ip_str)))
            if not parts[0]:
                msg = "Leading ':' only permitted as part of '::' in %r"
                raise AddressValueError((msg % ip_str))
            if not parts[(-1)]:
                msg = "Trailing ':' only permitted as part of '::' in %r"
                raise AddressValueError((msg % ip_str))
            parts_hi = len(parts)
            parts_lo = 0
            parts_skipped = 0
        try:
            ip_int = 0
            for i in range(parts_hi):
                ip_int <<= 16
                ip_int |= cls._parse_hextet(parts[i])
            ip_int <<= 16 * parts_skipped
            for i in range((-parts_lo), 0):
                ip_int <<= 16
                ip_int |= cls._parse_hextet(parts[i])
            return ip_int
        except ValueError as exc:
            raise AddressValueError(("%s in %r" % (exc, ip_str))) from None

    @classmethod
    def _parse_hextet(cls, hextet_str):
        "Convert an IPv6 hextet string into an integer.\n\n        Args:\n            hextet_str: A string, the number to parse.\n\n        Returns:\n            The hextet as an integer.\n\n        Raises:\n            ValueError: if the input isn't strictly a hex number from\n              [0..FFFF].\n\n        "
        if not cls._HEX_DIGITS.issuperset(hextet_str):
            raise ValueError(("Only hex digits permitted in %r" % hextet_str))
        if len(hextet_str) > 4:
            msg = "At most 4 characters permitted in %r"
            raise ValueError((msg % hextet_str))
        return int(hextet_str, 16)

    @classmethod
    def _compress_hextets(cls, hextets):
        'Compresses a list of hextets.\n\n        Compresses a list of strings, replacing the longest continuous\n        sequence of "0" in the list with "" and adding empty strings at\n        the beginning or at the end of the string such that subsequently\n        calling ":".join(hextets) will produce the compressed version of\n        the IPv6 address.\n\n        Args:\n            hextets: A list of strings, the hextets to compress.\n\n        Returns:\n            A list of strings.\n\n        '
        best_doublecolon_start = -1
        best_doublecolon_len = 0
        doublecolon_start = -1
        doublecolon_len = 0
        for (index, hextet) in enumerate(hextets):
            if hextet == "0":
                doublecolon_len += 1
                if doublecolon_start == (-1):
                    doublecolon_start = index
                if doublecolon_len > best_doublecolon_len:
                    best_doublecolon_len = doublecolon_len
                    best_doublecolon_start = doublecolon_start
            else:
                doublecolon_len = 0
                doublecolon_start = -1
        if best_doublecolon_len > 1:
            best_doublecolon_end = best_doublecolon_start + best_doublecolon_len
            if best_doublecolon_end == len(hextets):
                hextets += [""]
            hextets[best_doublecolon_start:best_doublecolon_end] = [""]
            if best_doublecolon_start == 0:
                hextets = [""] + hextets
        return hextets

    @classmethod
    def _string_from_ip_int(cls, ip_int=None):
        "Turns a 128-bit integer into hexadecimal notation.\n\n        Args:\n            ip_int: An integer, the IP address.\n\n        Returns:\n            A string, the hexadecimal representation of the address.\n\n        Raises:\n            ValueError: The address is bigger than 128 bits of all ones.\n\n        "
        if ip_int is None:
            ip_int = int(cls._ip)
        if ip_int > cls._ALL_ONES:
            raise ValueError("IPv6 address is too large")
        hex_str = "%032x" % ip_int
        hextets = [("%x" % int(hex_str[x : (x + 4)], 16)) for x in range(0, 32, 4)]
        hextets = cls._compress_hextets(hextets)
        return ":".join(hextets)

    def _explode_shorthand_ip_string(self):
        "Expand a shortened IPv6 address.\n\n        Args:\n            ip_str: A string, the IPv6 address.\n\n        Returns:\n            A string, the expanded IPv6 address.\n\n        "
        if isinstance(self, IPv6Network):
            ip_str = str(self.network_address)
        elif isinstance(self, IPv6Interface):
            ip_str = str(self.ip)
        else:
            ip_str = str(self)
        ip_int = self._ip_int_from_string(ip_str)
        hex_str = "%032x" % ip_int
        parts = [hex_str[x : (x + 4)] for x in range(0, 32, 4)]
        if isinstance(self, (_BaseNetwork, IPv6Interface)):
            return "%s/%d" % (":".join(parts), self._prefixlen)
        return ":".join(parts)

    def _reverse_pointer(self):
        "Return the reverse DNS pointer name for the IPv6 address.\n\n        This implements the method described in RFC3596 2.5.\n\n        "
        reverse_chars = self.exploded[::(-1)].replace(":", "")
        return ".".join(reverse_chars) + ".ip6.arpa"

    @staticmethod
    def _split_scope_id(ip_str):
        "Helper function to parse IPv6 string address with scope id.\n\n        See RFC 4007 for details.\n\n        Args:\n            ip_str: A string, the IPv6 address.\n\n        Returns:\n            (addr, scope_id) tuple.\n\n        "
        (addr, sep, scope_id) = ip_str.partition("%")
        if not sep:
            scope_id = None
        elif (not scope_id) or ("%" in scope_id):
            raise AddressValueError(('Invalid IPv6 address: "%r"' % ip_str))
        return (addr, scope_id)

    @property
    def max_prefixlen(self):
        return self._max_prefixlen

    @property
    def version(self):
        return self._version


class IPv6Address(_BaseV6, _BaseAddress):
    "Represent and manipulate single IPv6 Addresses."
    __slots__ = ("_ip", "_scope_id", "__weakref__")

    def __init__(self, address):
        "Instantiate a new IPv6 address object.\n\n        Args:\n            address: A string or integer representing the IP\n\n              Additionally, an integer can be passed, so\n              IPv6Address('2001:db8::') ==\n                IPv6Address(42540766411282592856903984951653826560)\n              or, more generally\n              IPv6Address(int(IPv6Address('2001:db8::'))) ==\n                IPv6Address('2001:db8::')\n\n        Raises:\n            AddressValueError: If address isn't a valid IPv6 address.\n\n        "
        if isinstance(address, int):
            self._check_int_address(address)
            self._ip = address
            self._scope_id = None
            return
        if isinstance(address, bytes):
            self._check_packed_address(address, 16)
            self._ip = int.from_bytes(address, "big")
            self._scope_id = None
            return
        addr_str = str(address)
        if "/" in addr_str:
            raise AddressValueError(("Unexpected '/' in %r" % address))
        (addr_str, self._scope_id) = self._split_scope_id(addr_str)
        self._ip = self._ip_int_from_string(addr_str)

    def __str__(self):
        ip_str = super().__str__()
        return ((ip_str + "%") + self._scope_id) if self._scope_id else ip_str

    def __hash__(self):
        return hash((self._ip, self._scope_id))

    def __eq__(self, other):
        address_equal = super().__eq__(other)
        if address_equal is NotImplemented:
            return NotImplemented
        if not address_equal:
            return False
        return self._scope_id == getattr(other, "_scope_id", None)

    @property
    def scope_id(self):
        "Identifier of a particular zone of the address's scope.\n\n        See RFC 4007 for details.\n\n        Returns:\n            A string identifying the zone of the address if specified, else None.\n\n        "
        return self._scope_id

    @property
    def packed(self):
        "The binary representation of this address."
        return v6_int_to_packed(self._ip)

    @property
    def is_multicast(self):
        "Test if the address is reserved for multicast use.\n\n        Returns:\n            A boolean, True if the address is a multicast address.\n            See RFC 2373 2.7 for details.\n\n        "
        return self in self._constants._multicast_network

    @property
    def is_reserved(self):
        "Test if the address is otherwise IETF reserved.\n\n        Returns:\n            A boolean, True if the address is within one of the\n            reserved IPv6 Network ranges.\n\n        "
        return any(((self in x) for x in self._constants._reserved_networks))

    @property
    def is_link_local(self):
        "Test if the address is reserved for link-local.\n\n        Returns:\n            A boolean, True if the address is reserved per RFC 4291.\n\n        "
        return self in self._constants._linklocal_network

    @property
    def is_site_local(self):
        "Test if the address is reserved for site-local.\n\n        Note that the site-local address space has been deprecated by RFC 3879.\n        Use is_private to test if this address is in the space of unique local\n        addresses as defined by RFC 4193.\n\n        Returns:\n            A boolean, True if the address is reserved per RFC 3513 2.5.6.\n\n        "
        return self in self._constants._sitelocal_network

    @property
    @functools.lru_cache()
    def is_private(self):
        "Test if this address is allocated for private networks.\n\n        Returns:\n            A boolean, True if the address is reserved per\n            iana-ipv6-special-registry.\n\n        "
        return any(((self in net) for net in self._constants._private_networks))

    @property
    def is_global(self):
        "Test if this address is allocated for public networks.\n\n        Returns:\n            A boolean, true if the address is not reserved per\n            iana-ipv6-special-registry.\n\n        "
        return not self.is_private

    @property
    def is_unspecified(self):
        "Test if the address is unspecified.\n\n        Returns:\n            A boolean, True if this is the unspecified address as defined in\n            RFC 2373 2.5.2.\n\n        "
        return self._ip == 0

    @property
    def is_loopback(self):
        "Test if the address is a loopback address.\n\n        Returns:\n            A boolean, True if the address is a loopback address as defined in\n            RFC 2373 2.5.3.\n\n        "
        return self._ip == 1

    @property
    def ipv4_mapped(self):
        "Return the IPv4 mapped address.\n\n        Returns:\n            If the IPv6 address is a v4 mapped address, return the\n            IPv4 mapped address. Return None otherwise.\n\n        "
        if (self._ip >> 32) != 65535:
            return None
        return IPv4Address((self._ip & 4294967295))

    @property
    def teredo(self):
        "Tuple of embedded teredo IPs.\n\n        Returns:\n            Tuple of the (server, client) IPs or None if the address\n            doesn't appear to be a teredo address (doesn't start with\n            2001::/32)\n\n        "
        if (self._ip >> 96) != 536936448:
            return None
        return (
            IPv4Address(((self._ip >> 64) & 4294967295)),
            IPv4Address(((~self._ip) & 4294967295)),
        )

    @property
    def sixtofour(self):
        "Return the IPv4 6to4 embedded address.\n\n        Returns:\n            The IPv4 6to4-embedded address if present or None if the\n            address doesn't appear to contain a 6to4 embedded address.\n\n        "
        if (self._ip >> 112) != 8194:
            return None
        return IPv4Address(((self._ip >> 80) & 4294967295))


class IPv6Interface(IPv6Address):
    def __init__(self, address):
        (addr, mask) = self._split_addr_prefix(address)
        IPv6Address.__init__(self, addr)
        self.network = IPv6Network((addr, mask), strict=False)
        self.netmask = self.network.netmask
        self._prefixlen = self.network._prefixlen

    @functools.cached_property
    def hostmask(self):
        return self.network.hostmask

    def __str__(self):
        return "%s/%d" % (super().__str__(), self._prefixlen)

    def __eq__(self, other):
        address_equal = IPv6Address.__eq__(self, other)
        if (address_equal is NotImplemented) or (not address_equal):
            return address_equal
        try:
            return self.network == other.network
        except AttributeError:
            return False

    def __lt__(self, other):
        address_less = IPv6Address.__lt__(self, other)
        if address_less is NotImplemented:
            return address_less
        try:
            return (self.network < other.network) or (
                (self.network == other.network) and address_less
            )
        except AttributeError:
            return False

    def __hash__(self):
        return hash((self._ip, self._prefixlen, int(self.network.network_address)))

    __reduce__ = _IPAddressBase.__reduce__

    @property
    def ip(self):
        return IPv6Address(self._ip)

    @property
    def with_prefixlen(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self._prefixlen)

    @property
    def with_netmask(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self.netmask)

    @property
    def with_hostmask(self):
        return "%s/%s" % (self._string_from_ip_int(self._ip), self.hostmask)

    @property
    def is_unspecified(self):
        return (self._ip == 0) and self.network.is_unspecified

    @property
    def is_loopback(self):
        return (self._ip == 1) and self.network.is_loopback


class IPv6Network(_BaseV6, _BaseNetwork):
    "This class represents and manipulates 128-bit IPv6 networks.\n\n    Attributes: [examples for IPv6('2001:db8::1000/124')]\n        .network_address: IPv6Address('2001:db8::1000')\n        .hostmask: IPv6Address('::f')\n        .broadcast_address: IPv6Address('2001:db8::100f')\n        .netmask: IPv6Address('ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff0')\n        .prefixlen: 124\n\n    "
    _address_class = IPv6Address

    def __init__(self, address, strict=True):
        "Instantiate a new IPv6 Network object.\n\n        Args:\n            address: A string or integer representing the IPv6 network or the\n              IP and prefix/netmask.\n              '2001:db8::/128'\n              '2001:db8:0000:0000:0000:0000:0000:0000/128'\n              '2001:db8::'\n              are all functionally the same in IPv6.  That is to say,\n              failing to provide a subnetmask will create an object with\n              a mask of /128.\n\n              Additionally, an integer can be passed, so\n              IPv6Network('2001:db8::') ==\n                IPv6Network(42540766411282592856903984951653826560)\n              or, more generally\n              IPv6Network(int(IPv6Network('2001:db8::'))) ==\n                IPv6Network('2001:db8::')\n\n            strict: A boolean. If true, ensure that we have been passed\n              A true network address, eg, 2001:db8::1000/124 and not an\n              IP address on a network, eg, 2001:db8::1/124.\n\n        Raises:\n            AddressValueError: If address isn't a valid IPv6 address.\n            NetmaskValueError: If the netmask isn't valid for\n              an IPv6 address.\n            ValueError: If strict was True and a network address was not\n              supplied.\n        "
        (addr, mask) = self._split_addr_prefix(address)
        self.network_address = IPv6Address(addr)
        (self.netmask, self._prefixlen) = self._make_netmask(mask)
        packed = int(self.network_address)
        if (packed & int(self.netmask)) != packed:
            if strict:
                raise ValueError(("%s has host bits set" % self))
            else:
                self.network_address = IPv6Address((packed & int(self.netmask)))
        if self._prefixlen == (self._max_prefixlen - 1):
            self.hosts = self.__iter__
        elif self._prefixlen == self._max_prefixlen:
            self.hosts = lambda: [IPv6Address(addr)]

    def hosts(self):
        "Generate Iterator over usable hosts in a network.\n\n          This is like __iter__ except it doesn't return the\n          Subnet-Router anycast address.\n\n        "
        network = int(self.network_address)
        broadcast = int(self.broadcast_address)
        for x in range((network + 1), (broadcast + 1)):
            (yield self._address_class(x))

    @property
    def is_site_local(self):
        "Test if the address is reserved for site-local.\n\n        Note that the site-local address space has been deprecated by RFC 3879.\n        Use is_private to test if this address is in the space of unique local\n        addresses as defined by RFC 4193.\n\n        Returns:\n            A boolean, True if the address is reserved per RFC 3513 2.5.6.\n\n        "
        return (
            self.network_address.is_site_local and self.broadcast_address.is_site_local
        )


class _IPv6Constants:
    _linklocal_network = IPv6Network("fe80::/10")
    _multicast_network = IPv6Network("ff00::/8")
    _private_networks = [
        IPv6Network("::1/128"),
        IPv6Network("::/128"),
        IPv6Network("::ffff:0:0/96"),
        IPv6Network("100::/64"),
        IPv6Network("2001::/23"),
        IPv6Network("2001:2::/48"),
        IPv6Network("2001:db8::/32"),
        IPv6Network("2001:10::/28"),
        IPv6Network("fc00::/7"),
        IPv6Network("fe80::/10"),
    ]
    _reserved_networks = [
        IPv6Network("::/8"),
        IPv6Network("100::/8"),
        IPv6Network("200::/7"),
        IPv6Network("400::/6"),
        IPv6Network("800::/5"),
        IPv6Network("1000::/4"),
        IPv6Network("4000::/3"),
        IPv6Network("6000::/3"),
        IPv6Network("8000::/3"),
        IPv6Network("A000::/3"),
        IPv6Network("C000::/3"),
        IPv6Network("E000::/4"),
        IPv6Network("F000::/5"),
        IPv6Network("F800::/6"),
        IPv6Network("FE00::/9"),
    ]
    _sitelocal_network = IPv6Network("fec0::/10")


IPv6Address._constants = _IPv6Constants
