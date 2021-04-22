"\nSend/receive UDP multicast packets.\nRequires that your OS kernel supports IP multicast.\n\nUsage:\n  mcast -s (sender, IPv4)\n  mcast -s -6 (sender, IPv6)\n  mcast    (receivers, IPv4)\n  mcast  -6  (receivers, IPv6)\n"
MYPORT = 8123
MYGROUP_4 = "225.0.0.250"
MYGROUP_6 = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"
MYTTL = 1
import time
import struct
import socket
import sys


def main():
    group = MYGROUP_6 if ("-6" in sys.argv[1:]) else MYGROUP_4
    if "-s" in sys.argv[1:]:
        sender(group)
    else:
        receiver(group)


def sender(group):
    addrinfo = socket.getaddrinfo(group, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
    ttl_bin = struct.pack("@i", MYTTL)
    if addrinfo[0] == socket.AF_INET:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
    else:
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
    while True:
        data = repr(time.time()).encode("utf-8") + b"\x00"
        s.sendto(data, (addrinfo[4][0], MYPORT))
        time.sleep(1)


def receiver(group):
    addrinfo = socket.getaddrinfo(group, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", MYPORT))
    group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
    if addrinfo[0] == socket.AF_INET:
        mreq = group_bin + struct.pack("=I", socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    else:
        mreq = group_bin + struct.pack("@I", 0)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
    while True:
        (data, sender) = s.recvfrom(1500)
        while data[(-1):] == "\x00":
            data = data[:(-1)]
        print(((str(sender) + "  ") + repr(data)))


if __name__ == "__main__":
    main()
