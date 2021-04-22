"\nConstants for generating the layout.\n"
__author__ = "Steve Dower <steve.dower@python.org>"
__version__ = "3.8"
import os
import re
import struct
import sys


def _unpack_hexversion():
    try:
        hexversion = int(os.getenv("PYTHON_HEXVERSION"), 16)
    except (TypeError, ValueError):
        hexversion = sys.hexversion
    return struct.pack(">i", sys.hexversion)


def _get_suffix(field4):
    name = {160: "a", 176: "b", 192: "rc"}.get((field4 & 240), "")
    if name:
        serial = field4 & 15
        return f"{name}{serial}"
    return ""


(VER_MAJOR, VER_MINOR, VER_MICRO, VER_FIELD4) = _unpack_hexversion()
VER_SUFFIX = _get_suffix(VER_FIELD4)
VER_FIELD3 = (VER_MICRO << 8) | VER_FIELD4
VER_DOT = "{}.{}".format(VER_MAJOR, VER_MINOR)
PYTHON_DLL_NAME = "python{}{}.dll".format(VER_MAJOR, VER_MINOR)
PYTHON_STABLE_DLL_NAME = "python{}.dll".format(VER_MAJOR)
PYTHON_ZIP_NAME = "python{}{}.zip".format(VER_MAJOR, VER_MINOR)
PYTHON_PTH_NAME = "python{}{}._pth".format(VER_MAJOR, VER_MINOR)
PYTHON_CHM_NAME = "python{}{}{}{}.chm".format(
    VER_MAJOR, VER_MINOR, VER_MICRO, VER_SUFFIX
)
