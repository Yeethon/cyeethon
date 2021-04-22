"When called as a script, print a comma-separated list of the open\nfile descriptors on stdout.\n\nUsage:\nfd_stats.py: check all file descriptors\nfd_status.py fd1 fd2 ...: check only specified file descriptors\n"
import errno
import os
import stat
import sys

if __name__ == "__main__":
    fds = []
    if len(sys.argv) == 1:
        try:
            _MAXFD = os.sysconf("SC_OPEN_MAX")
        except:
            _MAXFD = 256
        test_fds = range(0, _MAXFD)
    else:
        test_fds = map(int, sys.argv[1:])
    for fd in test_fds:
        try:
            st = os.fstat(fd)
        except OSError as e:
            if e.errno == errno.EBADF:
                continue
            raise
        if not stat.S_ISDOOR(st.st_mode):
            fds.append(fd)
    print(",".join(map(str, fds)))
