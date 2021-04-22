"Generic interface to all dbm clones.\n\nUse\n\n        import dbm\n        d = dbm.open(file, 'w', 0o666)\n\nThe returned object is a dbm.gnu, dbm.ndbm or dbm.dumb object, dependent on the\ntype of database being opened (determined by the whichdb function) in the case\nof an existing dbm. If the dbm does not exist and the create or new flag ('c'\nor 'n') was specified, the dbm type will be determined by the availability of\nthe modules (tested in the above order).\n\nIt has the following interface (key and data are strings):\n\n        d[key] = data   # store data at key (may override data at\n                        # existing key)\n        data = d[key]   # retrieve data at key (raise KeyError if no\n                        # such key)\n        del d[key]      # delete data stored at key (raises KeyError\n                        # if no such key)\n        flag = key in d # true if the key exists\n        list = d.keys() # return a list of all existing keys (slow!)\n\nFuture versions may change the order in which implementations are\ntested for existence, and add interfaces to other dbm-like\nimplementations.\n"
__all__ = ["open", "whichdb", "error"]
import io
import os
import struct
import sys


class error(Exception):
    pass


_names = ["dbm.gnu", "dbm.ndbm", "dbm.dumb"]
_defaultmod = None
_modules = {}
error = (error, OSError)
try:
    from dbm import ndbm
except ImportError:
    ndbm = None


def open(file, flag="r", mode=438):
    "Open or create database at path given by *file*.\n\n    Optional argument *flag* can be 'r' (default) for read-only access, 'w'\n    for read-write access of an existing database, 'c' for read-write access\n    to a new or existing database, and 'n' for read-write access to a new\n    database.\n\n    Note: 'r' and 'w' fail if the database doesn't exist; 'c' creates it\n    only if it doesn't exist; and 'n' always creates a new database.\n    "
    global _defaultmod
    if _defaultmod is None:
        for name in _names:
            try:
                mod = __import__(name, fromlist=["open"])
            except ImportError:
                continue
            if not _defaultmod:
                _defaultmod = mod
            _modules[name] = mod
        if not _defaultmod:
            raise ImportError(("no dbm clone found; tried %s" % _names))
    result = whichdb(file) if ("n" not in flag) else None
    if result is None:
        if ("c" in flag) or ("n" in flag):
            mod = _defaultmod
        else:
            raise error[0](
                "db file doesn't exist; use 'c' or 'n' flag to create a new db"
            )
    elif result == "":
        raise error[0]("db type could not be determined")
    elif result not in _modules:
        raise error[0]("db type is {0}, but the module is not available".format(result))
    else:
        mod = _modules[result]
    return mod.open(file, flag, mode)


def whichdb(filename):
    'Guess which db package to use to open a db file.\n\n    Return values:\n\n    - None if the database file can\'t be read;\n    - empty string if the file can be read but can\'t be recognized\n    - the name of the dbm submodule (e.g. "ndbm" or "gnu") if recognized.\n\n    Importing the given module may still fail, and opening the\n    database using that module may still fail.\n    '
    try:
        f = io.open((filename + ".pag"), "rb")
        f.close()
        f = io.open((filename + ".dir"), "rb")
        f.close()
        return "dbm.ndbm"
    except OSError:
        try:
            f = io.open((filename + ".db"), "rb")
            f.close()
            if ndbm is not None:
                d = ndbm.open(filename)
                d.close()
                return "dbm.ndbm"
        except OSError:
            pass
    try:
        os.stat((filename + ".dat"))
        size = os.stat((filename + ".dir")).st_size
        if size == 0:
            return "dbm.dumb"
        f = io.open((filename + ".dir"), "rb")
        try:
            if f.read(1) in (b"'", b'"'):
                return "dbm.dumb"
        finally:
            f.close()
    except OSError:
        pass
    try:
        f = io.open(filename, "rb")
    except OSError:
        return None
    with f:
        s16 = f.read(16)
    s = s16[0:4]
    if len(s) != 4:
        return ""
    try:
        (magic,) = struct.unpack("=l", s)
    except struct.error:
        return ""
    if magic in (324508366, 324508365, 324508367):
        return "dbm.gnu"
    try:
        (magic,) = struct.unpack("=l", s16[(-4):])
    except struct.error:
        return ""
    return ""


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        print((whichdb(filename) or "UNKNOWN"), filename)
