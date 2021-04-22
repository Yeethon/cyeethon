import collections.abc
import contextlib
import errno
import os
import re
import stat
import sys
import time
import unittest
import warnings

if os.name == "java":
    TESTFN_ASCII = "$test"
else:
    TESTFN_ASCII = "@test"
TESTFN_ASCII = "{}_{}_tmp".format(TESTFN_ASCII, os.getpid())
TESTFN_UNICODE = TESTFN_ASCII + "-àòɘŁğ"
if sys.platform == "darwin":
    import unicodedata

    TESTFN_UNICODE = unicodedata.normalize("NFD", TESTFN_UNICODE)
TESTFN_UNENCODABLE = None
if os.name == "nt":
    if sys.getwindowsversion().platform >= 2:
        TESTFN_UNENCODABLE = TESTFN_ASCII + "-共Ł♡ͣ\udc80"
        try:
            TESTFN_UNENCODABLE.encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            pass
        else:
            print(
                (
                    "WARNING: The filename %r CAN be encoded by the filesystem encoding (%s). Unicode filename tests may not be effective"
                    % (TESTFN_UNENCODABLE, sys.getfilesystemencoding())
                )
            )
            TESTFN_UNENCODABLE = None
elif sys.platform != "darwin":
    try:
        b"\xff".decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        TESTFN_UNENCODABLE = TESTFN_ASCII + b"-\xff".decode(
            sys.getfilesystemencoding(), "surrogateescape"
        )
    else:
        pass
FS_NONASCII = ""
for character in ("æ", "İ", "Ł", "φ", "К", "א", "،", "ت", "ก", "\xa0", "€"):
    try:
        if os.fsdecode(os.fsencode(character)) != character:
            raise UnicodeError
    except UnicodeError:
        pass
    else:
        FS_NONASCII = character
        break
SAVEDCWD = os.getcwd()
TESTFN_UNDECODABLE = None
for name in (
    b"\xe7w\xf0",
    b"\xff",
    b"\xae\xd5\xed\xb2\x80",
    b"\xed\xb4\x80",
    b"\x81\x98",
):
    try:
        name.decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        TESTFN_UNDECODABLE = os.fsencode(TESTFN_ASCII) + name
        break
if FS_NONASCII:
    TESTFN_NONASCII = TESTFN_ASCII + FS_NONASCII
else:
    TESTFN_NONASCII = None
TESTFN = TESTFN_NONASCII or TESTFN_ASCII


def make_bad_fd():
    "\n    Create an invalid file descriptor by opening and closing a file and return\n    its fd.\n    "
    file = open(TESTFN, "wb")
    try:
        return file.fileno()
    finally:
        file.close()
        unlink(TESTFN)


_can_symlink = None


def can_symlink():
    global _can_symlink
    if _can_symlink is not None:
        return _can_symlink
    symlink_path = TESTFN + "can_symlink"
    try:
        os.symlink(TESTFN, symlink_path)
        can = True
    except (OSError, NotImplementedError, AttributeError):
        can = False
    else:
        os.remove(symlink_path)
    _can_symlink = can
    return can


def skip_unless_symlink(test):
    "Skip decorator for tests that require functional symlink"
    ok = can_symlink()
    msg = "Requires functional symlink implementation"
    return test if ok else unittest.skip(msg)(test)


_can_xattr = None


def can_xattr():
    import tempfile

    global _can_xattr
    if _can_xattr is not None:
        return _can_xattr
    if not hasattr(os, "setxattr"):
        can = False
    else:
        import platform

        tmp_dir = tempfile.mkdtemp()
        (tmp_fp, tmp_name) = tempfile.mkstemp(dir=tmp_dir)
        try:
            with open(TESTFN, "wb") as fp:
                try:
                    os.setxattr(tmp_fp, b"user.test", b"")
                    os.setxattr(tmp_name, b"trusted.foo", b"42")
                    os.setxattr(fp.fileno(), b"user.test", b"")
                    kernel_version = platform.release()
                    m = re.match("2.6.(\\d{1,2})", kernel_version)
                    can = (m is None) or (int(m.group(1)) >= 39)
                except OSError:
                    can = False
        finally:
            unlink(TESTFN)
            unlink(tmp_name)
            rmdir(tmp_dir)
    _can_xattr = can
    return can


def skip_unless_xattr(test):
    "Skip decorator for tests that require functional extended attributes"
    ok = can_xattr()
    msg = "no non-broken extended attribute support"
    return test if ok else unittest.skip(msg)(test)


def unlink(filename):
    try:
        _unlink(filename)
    except (FileNotFoundError, NotADirectoryError):
        pass


if sys.platform.startswith("win"):

    def _waitfor(func, pathname, waitall=False):
        func(pathname)
        if waitall:
            dirname = pathname
        else:
            (dirname, name) = os.path.split(pathname)
            dirname = dirname or "."
        timeout = 0.001
        while timeout < 1.0:
            L = os.listdir(dirname)
            if not (L if waitall else (name in L)):
                return
            time.sleep(timeout)
            timeout *= 2
        warnings.warn(
            ("tests may fail, delete still pending for " + pathname),
            RuntimeWarning,
            stacklevel=4,
        )

    def _unlink(filename):
        _waitfor(os.unlink, filename)

    def _rmdir(dirname):
        _waitfor(os.rmdir, dirname)

    def _rmtree(path):
        from test.support import _force_run

        def _rmtree_inner(path):
            for name in _force_run(path, os.listdir, path):
                fullname = os.path.join(path, name)
                try:
                    mode = os.lstat(fullname).st_mode
                except OSError as exc:
                    print(
                        (
                            "support.rmtree(): os.lstat(%r) failed with %s"
                            % (fullname, exc)
                        ),
                        file=sys.__stderr__,
                    )
                    mode = 0
                if stat.S_ISDIR(mode):
                    _waitfor(_rmtree_inner, fullname, waitall=True)
                    _force_run(fullname, os.rmdir, fullname)
                else:
                    _force_run(fullname, os.unlink, fullname)

        _waitfor(_rmtree_inner, path, waitall=True)
        _waitfor((lambda p: _force_run(p, os.rmdir, p)), path)

    def _longpath(path):
        try:
            import ctypes
        except ImportError:
            pass
        else:
            buffer = ctypes.create_unicode_buffer((len(path) * 2))
            length = ctypes.windll.kernel32.GetLongPathNameW(path, buffer, len(buffer))
            if length:
                return buffer[:length]
        return path


else:
    _unlink = os.unlink
    _rmdir = os.rmdir

    def _rmtree(path):
        import shutil

        try:
            shutil.rmtree(path)
            return
        except OSError:
            pass

        def _rmtree_inner(path):
            from test.support import _force_run

            for name in _force_run(path, os.listdir, path):
                fullname = os.path.join(path, name)
                try:
                    mode = os.lstat(fullname).st_mode
                except OSError:
                    mode = 0
                if stat.S_ISDIR(mode):
                    _rmtree_inner(fullname)
                    _force_run(path, os.rmdir, fullname)
                else:
                    _force_run(path, os.unlink, fullname)

        _rmtree_inner(path)
        os.rmdir(path)

    def _longpath(path):
        return path


def rmdir(dirname):
    try:
        _rmdir(dirname)
    except FileNotFoundError:
        pass


def rmtree(path):
    try:
        _rmtree(path)
    except FileNotFoundError:
        pass


@contextlib.contextmanager
def temp_dir(path=None, quiet=False):
    "Return a context manager that creates a temporary directory.\n\n    Arguments:\n\n      path: the directory to create temporarily.  If omitted or None,\n        defaults to creating a temporary directory using tempfile.mkdtemp.\n\n      quiet: if False (the default), the context manager raises an exception\n        on error.  Otherwise, if the path is specified and cannot be\n        created, only a warning is issued.\n\n    "
    import tempfile

    dir_created = False
    if path is None:
        path = tempfile.mkdtemp()
        dir_created = True
        path = os.path.realpath(path)
    else:
        try:
            os.mkdir(path)
            dir_created = True
        except OSError as exc:
            if not quiet:
                raise
            warnings.warn(
                f"tests may fail, unable to create temporary directory {path!r}: {exc}",
                RuntimeWarning,
                stacklevel=3,
            )
    if dir_created:
        pid = os.getpid()
    try:
        (yield path)
    finally:
        if dir_created and (pid == os.getpid()):
            rmtree(path)


@contextlib.contextmanager
def change_cwd(path, quiet=False):
    "Return a context manager that changes the current working directory.\n\n    Arguments:\n\n      path: the directory to use as the temporary current working directory.\n\n      quiet: if False (the default), the context manager raises an exception\n        on error.  Otherwise, it issues only a warning and keeps the current\n        working directory the same.\n\n    "
    saved_dir = os.getcwd()
    try:
        os.chdir(os.path.realpath(path))
    except OSError as exc:
        if not quiet:
            raise
        warnings.warn(
            f"tests may fail, unable to change the current working directory to {path!r}: {exc}",
            RuntimeWarning,
            stacklevel=3,
        )
    try:
        (yield os.getcwd())
    finally:
        os.chdir(saved_dir)


@contextlib.contextmanager
def temp_cwd(name="tempcwd", quiet=False):
    "\n    Context manager that temporarily creates and changes the CWD.\n\n    The function temporarily changes the current working directory\n    after creating a temporary directory in the current directory with\n    name *name*.  If *name* is None, the temporary directory is\n    created using tempfile.mkdtemp.\n\n    If *quiet* is False (default) and it is not possible to\n    create or change the CWD, an error is raised.  If *quiet* is True,\n    only a warning is raised and the original CWD is used.\n\n    "
    with temp_dir(path=name, quiet=quiet) as temp_path:
        with change_cwd(temp_path, quiet=quiet) as cwd_dir:
            (yield cwd_dir)


def create_empty_file(filename):
    "Create an empty file. If the file already exists, truncate it."
    fd = os.open(filename, ((os.O_WRONLY | os.O_CREAT) | os.O_TRUNC))
    os.close(fd)


def fs_is_case_insensitive(directory):
    "Detects if the file system for the specified directory\n    is case-insensitive."
    import tempfile

    with tempfile.NamedTemporaryFile(dir=directory) as base:
        base_path = base.name
        case_path = base_path.upper()
        if case_path == base_path:
            case_path = base_path.lower()
        try:
            return os.path.samefile(base_path, case_path)
        except FileNotFoundError:
            return False


class FakePath:
    "Simple implementing of the path protocol.\n    "

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f"<FakePath {self.path!r}>"

    def __fspath__(self):
        if isinstance(self.path, BaseException) or (
            isinstance(self.path, type) and issubclass(self.path, BaseException)
        ):
            raise self.path
        else:
            return self.path


def fd_count():
    "Count the number of open file descriptors.\n    "
    if sys.platform.startswith(("linux", "freebsd")):
        try:
            names = os.listdir("/proc/self/fd")
            return len(names) - 1
        except FileNotFoundError:
            pass
    MAXFD = 256
    if hasattr(os, "sysconf"):
        try:
            MAXFD = os.sysconf("SC_OPEN_MAX")
        except OSError:
            pass
    old_modes = None
    if sys.platform == "win32":
        try:
            import msvcrt

            msvcrt.CrtSetReportMode
        except (AttributeError, ImportError):
            pass
        else:
            old_modes = {}
            for report_type in (msvcrt.CRT_WARN, msvcrt.CRT_ERROR, msvcrt.CRT_ASSERT):
                old_modes[report_type] = msvcrt.CrtSetReportMode(report_type, 0)
    try:
        count = 0
        for fd in range(MAXFD):
            try:
                fd2 = os.dup(fd)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            else:
                os.close(fd2)
                count += 1
    finally:
        if old_modes is not None:
            for report_type in (msvcrt.CRT_WARN, msvcrt.CRT_ERROR, msvcrt.CRT_ASSERT):
                msvcrt.CrtSetReportMode(report_type, old_modes[report_type])
    return count


if hasattr(os, "umask"):

    @contextlib.contextmanager
    def temp_umask(umask):
        "Context manager that temporarily sets the process umask."
        oldmask = os.umask(umask)
        try:
            (yield)
        finally:
            os.umask(oldmask)


class EnvironmentVarGuard(collections.abc.MutableMapping):
    "Class to help protect the environment variable properly.  Can be used as\n    a context manager."

    def __init__(self):
        self._environ = os.environ
        self._changed = {}

    def __getitem__(self, envvar):
        return self._environ[envvar]

    def __setitem__(self, envvar, value):
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        self._environ[envvar] = value

    def __delitem__(self, envvar):
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        if envvar in self._environ:
            del self._environ[envvar]

    def keys(self):
        return self._environ.keys()

    def __iter__(self):
        return iter(self._environ)

    def __len__(self):
        return len(self._environ)

    def set(self, envvar, value):
        self[envvar] = value

    def unset(self, envvar):
        del self[envvar]

    def __enter__(self):
        return self

    def __exit__(self, *ignore_exc):
        for (k, v) in self._changed.items():
            if v is None:
                if k in self._environ:
                    del self._environ[k]
            else:
                self._environ[k] = v
        os.environ = self._environ
