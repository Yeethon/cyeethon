"Filename globbing utility."
import os
import re
import fnmatch
import itertools
import stat
import sys

__all__ = ["glob", "iglob", "escape"]


def glob(pathname, *, root_dir=None, dir_fd=None, recursive=False):
    "Return a list of paths matching a pathname pattern.\n\n    The pattern may contain simple shell-style wildcards a la\n    fnmatch. However, unlike fnmatch, filenames starting with a\n    dot are special cases that are not matched by '*' and '?'\n    patterns.\n\n    If recursive is true, the pattern '**' will match any files and\n    zero or more directories and subdirectories.\n    "
    return list(iglob(pathname, root_dir=root_dir, dir_fd=dir_fd, recursive=recursive))


def iglob(pathname, *, root_dir=None, dir_fd=None, recursive=False):
    "Return an iterator which yields the paths matching a pathname pattern.\n\n    The pattern may contain simple shell-style wildcards a la\n    fnmatch. However, unlike fnmatch, filenames starting with a\n    dot are special cases that are not matched by '*' and '?'\n    patterns.\n\n    If recursive is true, the pattern '**' will match any files and\n    zero or more directories and subdirectories.\n    "
    sys.audit("glob.glob", pathname, recursive)
    sys.audit("glob.glob/2", pathname, recursive, root_dir, dir_fd)
    if root_dir is not None:
        root_dir = os.fspath(root_dir)
    else:
        root_dir = pathname[:0]
    it = _iglob(pathname, root_dir, dir_fd, recursive, False)
    if (not pathname) or (recursive and _isrecursive(pathname[:2])):
        try:
            s = next(it)
            if s:
                it = itertools.chain((s,), it)
        except StopIteration:
            pass
    return it


def _iglob(pathname, root_dir, dir_fd, recursive, dironly):
    (dirname, basename) = os.path.split(pathname)
    if not has_magic(pathname):
        assert not dironly
        if basename:
            if _lexists(_join(root_dir, pathname), dir_fd):
                (yield pathname)
        elif _isdir(_join(root_dir, dirname), dir_fd):
            (yield pathname)
        return
    if not dirname:
        if recursive and _isrecursive(basename):
            (yield from _glob2(root_dir, basename, dir_fd, dironly))
        else:
            (yield from _glob1(root_dir, basename, dir_fd, dironly))
        return
    if (dirname != pathname) and has_magic(dirname):
        dirs = _iglob(dirname, root_dir, dir_fd, recursive, True)
    else:
        dirs = [dirname]
    if has_magic(basename):
        if recursive and _isrecursive(basename):
            glob_in_dir = _glob2
        else:
            glob_in_dir = _glob1
    else:
        glob_in_dir = _glob0
    for dirname in dirs:
        for name in glob_in_dir(_join(root_dir, dirname), basename, dir_fd, dironly):
            (yield os.path.join(dirname, name))


def _glob1(dirname, pattern, dir_fd, dironly):
    names = list(_iterdir(dirname, dir_fd, dironly))
    if not _ishidden(pattern):
        names = (x for x in names if (not _ishidden(x)))
    return fnmatch.filter(names, pattern)


def _glob0(dirname, basename, dir_fd, dironly):
    if basename:
        if _lexists(_join(dirname, basename), dir_fd):
            return [basename]
    elif _isdir(dirname, dir_fd):
        return [basename]
    return []


def glob0(dirname, pattern):
    return _glob0(dirname, pattern, None, False)


def glob1(dirname, pattern):
    return _glob1(dirname, pattern, None, False)


def _glob2(dirname, pattern, dir_fd, dironly):
    assert _isrecursive(pattern)
    (yield pattern[:0])
    (yield from _rlistdir(dirname, dir_fd, dironly))


def _iterdir(dirname, dir_fd, dironly):
    try:
        fd = None
        fsencode = None
        if dir_fd is not None:
            if dirname:
                fd = arg = os.open(dirname, _dir_open_flags, dir_fd=dir_fd)
            else:
                arg = dir_fd
            if isinstance(dirname, bytes):
                fsencode = os.fsencode
        elif dirname:
            arg = dirname
        elif isinstance(dirname, bytes):
            arg = bytes(os.curdir, "ASCII")
        else:
            arg = os.curdir
        try:
            with os.scandir(arg) as it:
                for entry in it:
                    try:
                        if (not dironly) or entry.is_dir():
                            if fsencode is not None:
                                (yield fsencode(entry.name))
                            else:
                                (yield entry.name)
                    except OSError:
                        pass
        finally:
            if fd is not None:
                os.close(fd)
    except OSError:
        return


def _rlistdir(dirname, dir_fd, dironly):
    names = list(_iterdir(dirname, dir_fd, dironly))
    for x in names:
        if not _ishidden(x):
            (yield x)
            path = _join(dirname, x) if dirname else x
            for y in _rlistdir(path, dir_fd, dironly):
                (yield _join(x, y))


def _lexists(pathname, dir_fd):
    if dir_fd is None:
        return os.path.lexists(pathname)
    try:
        os.lstat(pathname, dir_fd=dir_fd)
    except (OSError, ValueError):
        return False
    else:
        return True


def _isdir(pathname, dir_fd):
    if dir_fd is None:
        return os.path.isdir(pathname)
    try:
        st = os.stat(pathname, dir_fd=dir_fd)
    except (OSError, ValueError):
        return False
    else:
        return stat.S_ISDIR(st.st_mode)


def _join(dirname, basename):
    if (not dirname) or (not basename):
        return dirname or basename
    return os.path.join(dirname, basename)


magic_check = re.compile("([*?[])")
magic_check_bytes = re.compile(b"([*?[])")


def has_magic(s):
    if isinstance(s, bytes):
        match = magic_check_bytes.search(s)
    else:
        match = magic_check.search(s)
    return match is not None


def _ishidden(path):
    return path[0] in (".", b"."[0])


def _isrecursive(pattern):
    if isinstance(pattern, bytes):
        return pattern == b"**"
    else:
        return pattern == "**"


def escape(pathname):
    "Escape all special characters.\n    "
    (drive, pathname) = os.path.splitdrive(pathname)
    if isinstance(pathname, bytes):
        pathname = magic_check_bytes.sub(b"[\\1]", pathname)
    else:
        pathname = magic_check.sub("[\\1]", pathname)
    return drive + pathname


_dir_open_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
