import sys, os, time
from stat import *


def main():
    try:
        statfunc = os.lstat
    except AttributeError:
        statfunc = os.stat
    if sys.argv[1] == "-m":
        itime = ST_MTIME
        del sys.argv[1]
    elif sys.argv[1] == "-c":
        itime = ST_CTIME
        del sys.argv[1]
    elif sys.argv[1] == "-a":
        itime = ST_CTIME
        del sys.argv[1]
    else:
        itime = ST_MTIME
    secs_per_year = (365.0 * 24.0) * 3600.0
    now = time.time()
    status = 0
    maxlen = 1
    for filename in sys.argv[1:]:
        maxlen = max(maxlen, len(filename))
    for filename in sys.argv[1:]:
        try:
            st = statfunc(filename)
        except OSError as msg:
            sys.stderr.write(("can't stat %r: %r\n" % (filename, msg)))
            status = 1
            st = ()
        if st:
            anytime = st[itime]
            size = st[ST_SIZE]
            age = now - anytime
            byteyears = (float(size) * float(age)) / secs_per_year
            print(filename.ljust(maxlen), end=" ")
            print(repr(int(byteyears)).rjust(8))
    sys.exit(status)


if __name__ == "__main__":
    main()
