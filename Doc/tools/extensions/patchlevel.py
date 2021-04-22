"\n    patchlevel.py\n    ~~~~~~~~~~~~~\n\n    Extract version info from Include/patchlevel.h.\n    Adapted from Doc/tools/getversioninfo.\n\n    :copyright: 2007-2008 by Georg Brandl.\n    :license: Python license.\n"
from __future__ import print_function
import os
import re
import sys


def get_header_version_info(srcdir):
    patchlevel_h = os.path.join(srcdir, "..", "Include", "patchlevel.h")
    rx = re.compile("\\s*#define\\s+([a-zA-Z][a-zA-Z_0-9]*)\\s+([a-zA-Z_0-9]+)")
    d = {}
    with open(patchlevel_h) as f:
        for line in f:
            m = rx.match(line)
            if m is not None:
                (name, value) = m.group(1, 2)
                d[name] = value
    release = version = "%s.%s" % (d["PY_MAJOR_VERSION"], d["PY_MINOR_VERSION"])
    micro = int(d["PY_MICRO_VERSION"])
    release += "." + str(micro)
    level = d["PY_RELEASE_LEVEL"]
    suffixes = {
        "PY_RELEASE_LEVEL_ALPHA": "a",
        "PY_RELEASE_LEVEL_BETA": "b",
        "PY_RELEASE_LEVEL_GAMMA": "rc",
    }
    if level != "PY_RELEASE_LEVEL_FINAL":
        release += suffixes[level] + str(int(d["PY_RELEASE_SERIAL"]))
    return (version, release)


def get_sys_version_info():
    (major, minor, micro, level, serial) = sys.version_info
    release = version = "%s.%s" % (major, minor)
    release += ".%s" % micro
    if level != "final":
        release += "%s%s" % (level[0], serial)
    return (version, release)


def get_version_info():
    try:
        return get_header_version_info(".")
    except (IOError, OSError):
        (version, release) = get_sys_version_info()
        print(
            (
                "Can't get version info from Include/patchlevel.h, using version of this interpreter (%s)."
                % release
            ),
            file=sys.stderr,
        )
        return (version, release)


if __name__ == "__main__":
    print(get_header_version_info(".")[1])
