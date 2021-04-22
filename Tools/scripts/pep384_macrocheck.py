'\npep384_macrocheck.py\n\nThis programm tries to locate errors in the relevant Python header\nfiles where macros access type fields when they are reachable from\nthe limided API.\n\nThe idea is to search macros with the string "->tp_" in it.\nWhen the macro name does not begin with an underscore,\nthen we have found a dormant error.\n\nChristian Tismer\n2018-06-02\n'
import sys
import os
import re

DEBUG = False


def dprint(*args, **kw):
    if DEBUG:
        print(*args, **kw)


def parse_headerfiles(startpath):
    "\n    Scan all header files which are reachable fronm Python.h\n    "
    search = "Python.h"
    name = os.path.join(startpath, search)
    if not os.path.exists(name):
        raise ValueError(
            "file {} was not found in {}\nPlease give the path to Python's include directory.".format(
                search, startpath
            )
        )
    errors = 0
    with open(name) as python_h:
        while True:
            line = python_h.readline()
            if not line:
                break
            found = re.match('^\\s*#\\s*include\\s*"(\\w+\\.h)"', line)
            if not found:
                continue
            include = found.group(1)
            dprint("Scanning", include)
            name = os.path.join(startpath, include)
            if not os.path.exists(name):
                name = os.path.join(startpath, "../PC", include)
            errors += parse_file(name)
    return errors


def ifdef_level_gen():
    "\n    Scan lines for #ifdef and track the level.\n    "
    level = 0
    ifdef_pattern = "^\\s*#\\s*if"
    endif_pattern = "^\\s*#\\s*endif"
    while True:
        line = yield level
        if re.match(ifdef_pattern, line):
            level += 1
        elif re.match(endif_pattern, line):
            level -= 1


def limited_gen():
    "\n    Scan lines for Py_LIMITED_API yes(1) no(-1) or nothing (0)\n    "
    limited = [0]
    unlimited_pattern = "^\\s*#\\s*ifndef\\s+Py_LIMITED_API"
    limited_pattern = "|".join(
        [
            "^\\s*#\\s*ifdef\\s+Py_LIMITED_API",
            "^\\s*#\\s*(el)?if\\s+!\\s*defined\\s*\\(\\s*Py_LIMITED_API\\s*\\)\\s*\\|\\|",
            "^\\s*#\\s*(el)?if\\s+defined\\s*\\(\\s*Py_LIMITED_API",
        ]
    )
    else_pattern = "^\\s*#\\s*else"
    ifdef_level = ifdef_level_gen()
    status = next(ifdef_level)
    wait_for = -1
    while True:
        line = yield limited[(-1)]
        new_status = ifdef_level.send(line)
        dir = new_status - status
        status = new_status
        if dir == 1:
            if re.match(unlimited_pattern, line):
                limited.append((-1))
                wait_for = status - 1
            elif re.match(limited_pattern, line):
                limited.append(1)
                wait_for = status - 1
        elif dir == (-1):
            if status == wait_for:
                limited.pop()
                wait_for = -1
        elif re.match(limited_pattern, line):
            limited.append(1)
            wait_for = status - 1
        elif re.match(else_pattern, line):
            limited.append((-limited.pop()))


def parse_file(fname):
    errors = 0
    with open(fname) as f:
        lines = f.readlines()
    type_pattern = "^.*?->\\s*tp_"
    define_pattern = "^\\s*#\\s*define\\s+(\\w+)"
    limited = limited_gen()
    status = next(limited)
    for (nr, line) in enumerate(lines):
        status = limited.send(line)
        line = line.rstrip()
        dprint(fname, nr, status, line)
        if status != (-1):
            if re.match(define_pattern, line):
                name = re.match(define_pattern, line).group(1)
                if not name.startswith("_"):
                    macro = line + "\n"
                    idx = nr
                    while line.endswith("\\"):
                        idx += 1
                        line = lines[idx].rstrip()
                        macro += line + "\n"
                    if re.match(type_pattern, macro, re.DOTALL):
                        report(fname, (nr + 1), macro)
                        errors += 1
    return errors


def report(fname, nr, macro):
    f = sys.stderr
    print(((fname + ":") + str(nr)), file=f)
    print(macro, file=f)


if __name__ == "__main__":
    p = sys.argv[1] if sys.argv[1:] else "../../Include"
    errors = parse_headerfiles(p)
    if errors:
        raise TypeError("These {} locations contradict the limited API.".format(errors))
