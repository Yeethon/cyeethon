"Temporary files.\n\nThis module provides generic, low- and high-level interfaces for\ncreating temporary files and directories.  All of the interfaces\nprovided by this module can be used without fear of race conditions\nexcept for 'mktemp'.  'mktemp' is subject to race conditions and\nshould not be used; it is provided for backward compatibility only.\n\nThe default path names are returned as str.  If you supply bytes as\ninput, all return values will be in bytes.  Ex:\n\n    >>> tempfile.mkstemp()\n    (4, '/tmp/tmptpu9nin8')\n    >>> tempfile.mkdtemp(suffix=b'')\n    b'/tmp/tmppbi8f0hy'\n\nThis module also provides some data items to the user:\n\n  TMP_MAX  - maximum number of names that will be tried before\n             giving up.\n  tempdir  - If this is set to a string before the first use of\n             any routine from this module, it will be considered as\n             another candidate location to store temporary files.\n"
__all__ = [
    "NamedTemporaryFile",
    "TemporaryFile",
    "SpooledTemporaryFile",
    "TemporaryDirectory",
    "mkstemp",
    "mkdtemp",
    "mktemp",
    "TMP_MAX",
    "gettempprefix",
    "tempdir",
    "gettempdir",
    "gettempprefixb",
    "gettempdirb",
]
import functools as _functools
import warnings as _warnings
import io as _io
import os as _os
import shutil as _shutil
import errno as _errno
from random import Random as _Random
import sys as _sys
import types as _types
import weakref as _weakref
import _thread

_allocate_lock = _thread.allocate_lock
_text_openflags = (_os.O_RDWR | _os.O_CREAT) | _os.O_EXCL
if hasattr(_os, "O_NOFOLLOW"):
    _text_openflags |= _os.O_NOFOLLOW
_bin_openflags = _text_openflags
if hasattr(_os, "O_BINARY"):
    _bin_openflags |= _os.O_BINARY
if hasattr(_os, "TMP_MAX"):
    TMP_MAX = _os.TMP_MAX
else:
    TMP_MAX = 10000
template = "tmp"
_once_lock = _allocate_lock()


def _exists(fn):
    try:
        _os.lstat(fn)
    except OSError:
        return False
    else:
        return True


def _infer_return_type(*args):
    "Look at the type of all args and divine their implied return type."
    return_type = None
    for arg in args:
        if arg is None:
            continue
        if isinstance(arg, bytes):
            if return_type is str:
                raise TypeError("Can't mix bytes and non-bytes in path components.")
            return_type = bytes
        else:
            if return_type is bytes:
                raise TypeError("Can't mix bytes and non-bytes in path components.")
            return_type = str
    if return_type is None:
        if (tempdir is None) or isinstance(tempdir, str):
            return str
        else:
            return bytes
    return return_type


def _sanitize_params(prefix, suffix, dir):
    "Common parameter processing for most APIs in this module."
    output_type = _infer_return_type(prefix, suffix, dir)
    if suffix is None:
        suffix = output_type()
    if prefix is None:
        if output_type is str:
            prefix = template
        else:
            prefix = _os.fsencode(template)
    if dir is None:
        if output_type is str:
            dir = gettempdir()
        else:
            dir = gettempdirb()
    return (prefix, suffix, dir, output_type)


class _RandomNameSequence:
    "An instance of _RandomNameSequence generates an endless\n    sequence of unpredictable strings which can safely be incorporated\n    into file names.  Each string is eight characters long.  Multiple\n    threads can safely use the same instance at the same time.\n\n    _RandomNameSequence is an iterator."
    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"

    @property
    def rng(self):
        cur_pid = _os.getpid()
        if cur_pid != getattr(self, "_rng_pid", None):
            self._rng = _Random()
            self._rng_pid = cur_pid
        return self._rng

    def __iter__(self):
        return self

    def __next__(self):
        return "".join(self.rng.choices(self.characters, k=8))


def _candidate_tempdir_list():
    "Generate a list of candidate temporary directories which\n    _get_default_tempdir will try."
    dirlist = []
    for envname in ("TMPDIR", "TEMP", "TMP"):
        dirname = _os.getenv(envname)
        if dirname:
            dirlist.append(dirname)
    if _os.name == "nt":
        dirlist.extend(
            [
                _os.path.expanduser("~\\AppData\\Local\\Temp"),
                _os.path.expandvars("%SYSTEMROOT%\\Temp"),
                "c:\\temp",
                "c:\\tmp",
                "\\temp",
                "\\tmp",
            ]
        )
    else:
        dirlist.extend(["/tmp", "/var/tmp", "/usr/tmp"])
    try:
        dirlist.append(_os.getcwd())
    except (AttributeError, OSError):
        dirlist.append(_os.curdir)
    return dirlist


def _get_default_tempdir():
    "Calculate the default directory to use for temporary files.\n    This routine should be called exactly once.\n\n    We determine whether or not a candidate temp dir is usable by\n    trying to create and write to a file in that directory.  If this\n    is successful, the test file is deleted.  To prevent denial of\n    service, the name of the test file must be randomized."
    namer = _RandomNameSequence()
    dirlist = _candidate_tempdir_list()
    for dir in dirlist:
        if dir != _os.curdir:
            dir = _os.path.abspath(dir)
        for seq in range(100):
            name = next(namer)
            filename = _os.path.join(dir, name)
            try:
                fd = _os.open(filename, _bin_openflags, 384)
                try:
                    try:
                        with _io.open(fd, "wb", closefd=False) as fp:
                            fp.write(b"blat")
                    finally:
                        _os.close(fd)
                finally:
                    _os.unlink(filename)
                return dir
            except FileExistsError:
                pass
            except PermissionError:
                if (
                    (_os.name == "nt")
                    and _os.path.isdir(dir)
                    and _os.access(dir, _os.W_OK)
                ):
                    continue
                break
            except OSError:
                break
    raise FileNotFoundError(
        _errno.ENOENT, ("No usable temporary directory found in %s" % dirlist)
    )


_name_sequence = None


def _get_candidate_names():
    "Common setup sequence for all user-callable interfaces."
    global _name_sequence
    if _name_sequence is None:
        _once_lock.acquire()
        try:
            if _name_sequence is None:
                _name_sequence = _RandomNameSequence()
        finally:
            _once_lock.release()
    return _name_sequence


def _mkstemp_inner(dir, pre, suf, flags, output_type):
    "Code common to mkstemp, TemporaryFile, and NamedTemporaryFile."
    names = _get_candidate_names()
    if output_type is bytes:
        names = map(_os.fsencode, names)
    for seq in range(TMP_MAX):
        name = next(names)
        file = _os.path.join(dir, ((pre + name) + suf))
        _sys.audit("tempfile.mkstemp", file)
        try:
            fd = _os.open(file, flags, 384)
        except FileExistsError:
            continue
        except PermissionError:
            if (_os.name == "nt") and _os.path.isdir(dir) and _os.access(dir, _os.W_OK):
                continue
            else:
                raise
        return (fd, _os.path.abspath(file))
    raise FileExistsError(_errno.EEXIST, "No usable temporary file name found")


def gettempprefix():
    "The default prefix for temporary directories as string."
    return _os.fsdecode(template)


def gettempprefixb():
    "The default prefix for temporary directories as bytes."
    return _os.fsencode(template)


tempdir = None


def _gettempdir():
    "Private accessor for tempfile.tempdir."
    global tempdir
    if tempdir is None:
        _once_lock.acquire()
        try:
            if tempdir is None:
                tempdir = _get_default_tempdir()
        finally:
            _once_lock.release()
    return tempdir


def gettempdir():
    "Returns tempfile.tempdir as str."
    return _os.fsdecode(_gettempdir())


def gettempdirb():
    "Returns tempfile.tempdir as bytes."
    return _os.fsencode(_gettempdir())


def mkstemp(suffix=None, prefix=None, dir=None, text=False):
    "User-callable function to create and return a unique temporary\n    file.  The return value is a pair (fd, name) where fd is the\n    file descriptor returned by os.open, and name is the filename.\n\n    If 'suffix' is not None, the file name will end with that suffix,\n    otherwise there will be no suffix.\n\n    If 'prefix' is not None, the file name will begin with that prefix,\n    otherwise a default prefix is used.\n\n    If 'dir' is not None, the file will be created in that directory,\n    otherwise a default directory is used.\n\n    If 'text' is specified and true, the file is opened in text\n    mode.  Else (the default) the file is opened in binary mode.\n\n    If any of 'suffix', 'prefix' and 'dir' are not None, they must be the\n    same type.  If they are bytes, the returned name will be bytes; str\n    otherwise.\n\n    The file is readable and writable only by the creating user ID.\n    If the operating system uses permission bits to indicate whether a\n    file is executable, the file is executable by no one. The file\n    descriptor is not inherited by children of this process.\n\n    Caller is responsible for deleting the file when done with it.\n    "
    (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
    if text:
        flags = _text_openflags
    else:
        flags = _bin_openflags
    return _mkstemp_inner(dir, prefix, suffix, flags, output_type)


def mkdtemp(suffix=None, prefix=None, dir=None):
    "User-callable function to create and return a unique temporary\n    directory.  The return value is the pathname of the directory.\n\n    Arguments are as for mkstemp, except that the 'text' argument is\n    not accepted.\n\n    The directory is readable, writable, and searchable only by the\n    creating user.\n\n    Caller is responsible for deleting the directory when done with it.\n    "
    (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
    names = _get_candidate_names()
    if output_type is bytes:
        names = map(_os.fsencode, names)
    for seq in range(TMP_MAX):
        name = next(names)
        file = _os.path.join(dir, ((prefix + name) + suffix))
        _sys.audit("tempfile.mkdtemp", file)
        try:
            _os.mkdir(file, 448)
        except FileExistsError:
            continue
        except PermissionError:
            if (_os.name == "nt") and _os.path.isdir(dir) and _os.access(dir, _os.W_OK):
                continue
            else:
                raise
        return file
    raise FileExistsError(_errno.EEXIST, "No usable temporary directory name found")


def mktemp(suffix="", prefix=template, dir=None):
    "User-callable function to return a unique temporary file name.  The\n    file is not created.\n\n    Arguments are similar to mkstemp, except that the 'text' argument is\n    not accepted, and suffix=None, prefix=None and bytes file names are not\n    supported.\n\n    THIS FUNCTION IS UNSAFE AND SHOULD NOT BE USED.  The file name may\n    refer to a file that did not exist at some point, but by the time\n    you get around to creating it, someone else may have beaten you to\n    the punch.\n    "
    if dir is None:
        dir = gettempdir()
    names = _get_candidate_names()
    for seq in range(TMP_MAX):
        name = next(names)
        file = _os.path.join(dir, ((prefix + name) + suffix))
        if not _exists(file):
            return file
    raise FileExistsError(_errno.EEXIST, "No usable temporary filename found")


class _TemporaryFileCloser:
    "A separate object allowing proper closing of a temporary file's\n    underlying file object, without adding a __del__ method to the\n    temporary file."
    file = None
    close_called = False

    def __init__(self, file, name, delete=True):
        self.file = file
        self.name = name
        self.delete = delete

    if _os.name != "nt":

        def close(self, unlink=_os.unlink):
            if (not self.close_called) and (self.file is not None):
                self.close_called = True
                try:
                    self.file.close()
                finally:
                    if self.delete:
                        unlink(self.name)

        def __del__(self):
            self.close()

    else:

        def close(self):
            if not self.close_called:
                self.close_called = True
                self.file.close()


class _TemporaryFileWrapper:
    "Temporary file wrapper\n\n    This class provides a wrapper around files opened for\n    temporary use.  In particular, it seeks to automatically\n    remove the file when it is no longer needed.\n    "

    def __init__(self, file, name, delete=True):
        self.file = file
        self.name = name
        self.delete = delete
        self._closer = _TemporaryFileCloser(file, name, delete)

    def __getattr__(self, name):
        file = self.__dict__["file"]
        a = getattr(file, name)
        if hasattr(a, "__call__"):
            func = a

            @_functools.wraps(func)
            def func_wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            func_wrapper._closer = self._closer
            a = func_wrapper
        if not isinstance(a, int):
            setattr(self, name, a)
        return a

    def __enter__(self):
        self.file.__enter__()
        return self

    def __exit__(self, exc, value, tb):
        result = self.file.__exit__(exc, value, tb)
        self.close()
        return result

    def close(self):
        "\n        Close the temporary file, possibly deleting it.\n        "
        self._closer.close()

    def __iter__(self):
        for line in self.file:
            (yield line)


def NamedTemporaryFile(
    mode="w+b",
    buffering=(-1),
    encoding=None,
    newline=None,
    suffix=None,
    prefix=None,
    dir=None,
    delete=True,
    *,
    errors=None
):
    "Create and return a temporary file.\n    Arguments:\n    'prefix', 'suffix', 'dir' -- as for mkstemp.\n    'mode' -- the mode argument to io.open (default \"w+b\").\n    'buffering' -- the buffer size argument to io.open (default -1).\n    'encoding' -- the encoding argument to io.open (default None)\n    'newline' -- the newline argument to io.open (default None)\n    'delete' -- whether the file is deleted on close (default True).\n    'errors' -- the errors argument to io.open (default None)\n    The file is created as mkstemp() would do it.\n\n    Returns an object with a file-like interface; the name of the file\n    is accessible as its 'name' attribute.  The file will be automatically\n    deleted when it is closed unless the 'delete' argument is set to False.\n    "
    (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
    flags = _bin_openflags
    if (_os.name == "nt") and delete:
        flags |= _os.O_TEMPORARY
    if "b" not in mode:
        encoding = _io.text_encoding(encoding)
    (fd, name) = _mkstemp_inner(dir, prefix, suffix, flags, output_type)
    try:
        file = _io.open(
            fd,
            mode,
            buffering=buffering,
            newline=newline,
            encoding=encoding,
            errors=errors,
        )
        return _TemporaryFileWrapper(file, name, delete)
    except BaseException:
        _os.unlink(name)
        _os.close(fd)
        raise


if (_os.name != "posix") or (_sys.platform == "cygwin"):
    TemporaryFile = NamedTemporaryFile
else:
    _O_TMPFILE_WORKS = hasattr(_os, "O_TMPFILE")

    def TemporaryFile(
        mode="w+b",
        buffering=(-1),
        encoding=None,
        newline=None,
        suffix=None,
        prefix=None,
        dir=None,
        *,
        errors=None
    ):
        "Create and return a temporary file.\n        Arguments:\n        'prefix', 'suffix', 'dir' -- as for mkstemp.\n        'mode' -- the mode argument to io.open (default \"w+b\").\n        'buffering' -- the buffer size argument to io.open (default -1).\n        'encoding' -- the encoding argument to io.open (default None)\n        'newline' -- the newline argument to io.open (default None)\n        'errors' -- the errors argument to io.open (default None)\n        The file is created as mkstemp() would do it.\n\n        Returns an object with a file-like interface.  The file has no\n        name, and will cease to exist when it is closed.\n        "
        global _O_TMPFILE_WORKS
        if "b" not in mode:
            encoding = _io.text_encoding(encoding)
        (prefix, suffix, dir, output_type) = _sanitize_params(prefix, suffix, dir)
        flags = _bin_openflags
        if _O_TMPFILE_WORKS:
            try:
                flags2 = (flags | _os.O_TMPFILE) & (~_os.O_CREAT)
                fd = _os.open(dir, flags2, 384)
            except IsADirectoryError:
                _O_TMPFILE_WORKS = False
            except OSError:
                pass
            else:
                try:
                    return _io.open(
                        fd,
                        mode,
                        buffering=buffering,
                        newline=newline,
                        encoding=encoding,
                        errors=errors,
                    )
                except:
                    _os.close(fd)
                    raise
        (fd, name) = _mkstemp_inner(dir, prefix, suffix, flags, output_type)
        try:
            _os.unlink(name)
            return _io.open(
                fd,
                mode,
                buffering=buffering,
                newline=newline,
                encoding=encoding,
                errors=errors,
            )
        except:
            _os.close(fd)
            raise


class SpooledTemporaryFile:
    "Temporary file wrapper, specialized to switch from BytesIO\n    or StringIO to a real file when it exceeds a certain size or\n    when a fileno is needed.\n    "
    _rolled = False

    def __init__(
        self,
        max_size=0,
        mode="w+b",
        buffering=(-1),
        encoding=None,
        newline=None,
        suffix=None,
        prefix=None,
        dir=None,
        *,
        errors=None
    ):
        if "b" in mode:
            self._file = _io.BytesIO()
        else:
            encoding = _io.text_encoding(encoding)
            self._file = _io.TextIOWrapper(
                _io.BytesIO(), encoding=encoding, errors=errors, newline=newline
            )
        self._max_size = max_size
        self._rolled = False
        self._TemporaryFileArgs = {
            "mode": mode,
            "buffering": buffering,
            "suffix": suffix,
            "prefix": prefix,
            "encoding": encoding,
            "newline": newline,
            "dir": dir,
            "errors": errors,
        }

    __class_getitem__ = classmethod(_types.GenericAlias)

    def _check(self, file):
        if self._rolled:
            return
        max_size = self._max_size
        if max_size and (file.tell() > max_size):
            self.rollover()

    def rollover(self):
        if self._rolled:
            return
        file = self._file
        newfile = self._file = TemporaryFile(**self._TemporaryFileArgs)
        del self._TemporaryFileArgs
        pos = file.tell()
        if hasattr(newfile, "buffer"):
            newfile.buffer.write(file.detach().getvalue())
        else:
            newfile.write(file.getvalue())
        newfile.seek(pos, 0)
        self._rolled = True

    def __enter__(self):
        if self._file.closed:
            raise ValueError("Cannot enter context with closed file")
        return self

    def __exit__(self, exc, value, tb):
        self._file.close()

    def __iter__(self):
        return self._file.__iter__()

    def close(self):
        self._file.close()

    @property
    def closed(self):
        return self._file.closed

    @property
    def encoding(self):
        return self._file.encoding

    @property
    def errors(self):
        return self._file.errors

    def fileno(self):
        self.rollover()
        return self._file.fileno()

    def flush(self):
        self._file.flush()

    def isatty(self):
        return self._file.isatty()

    @property
    def mode(self):
        try:
            return self._file.mode
        except AttributeError:
            return self._TemporaryFileArgs["mode"]

    @property
    def name(self):
        try:
            return self._file.name
        except AttributeError:
            return None

    @property
    def newlines(self):
        return self._file.newlines

    def read(self, *args):
        return self._file.read(*args)

    def readline(self, *args):
        return self._file.readline(*args)

    def readlines(self, *args):
        return self._file.readlines(*args)

    def seek(self, *args):
        return self._file.seek(*args)

    def tell(self):
        return self._file.tell()

    def truncate(self, size=None):
        if size is None:
            self._file.truncate()
        else:
            if size > self._max_size:
                self.rollover()
            self._file.truncate(size)

    def write(self, s):
        file = self._file
        rv = file.write(s)
        self._check(file)
        return rv

    def writelines(self, iterable):
        file = self._file
        rv = file.writelines(iterable)
        self._check(file)
        return rv


class TemporaryDirectory:
    "Create and return a temporary directory.  This has the same\n    behavior as mkdtemp but can be used as a context manager.  For\n    example:\n\n        with TemporaryDirectory() as tmpdir:\n            ...\n\n    Upon exiting the context, the directory and everything contained\n    in it are removed.\n    "

    def __init__(self, suffix=None, prefix=None, dir=None, ignore_cleanup_errors=False):
        self.name = mkdtemp(suffix, prefix, dir)
        self._ignore_cleanup_errors = ignore_cleanup_errors
        self._finalizer = _weakref.finalize(
            self,
            self._cleanup,
            self.name,
            warn_message="Implicitly cleaning up {!r}".format(self),
            ignore_errors=self._ignore_cleanup_errors,
        )

    @classmethod
    def _rmtree(cls, name, ignore_errors=False):
        def onerror(func, path, exc_info):
            if issubclass(exc_info[0], PermissionError):

                def resetperms(path):
                    try:
                        _os.chflags(path, 0)
                    except AttributeError:
                        pass
                    _os.chmod(path, 448)

                try:
                    if path != name:
                        resetperms(_os.path.dirname(path))
                    resetperms(path)
                    try:
                        _os.unlink(path)
                    except (IsADirectoryError, PermissionError):
                        cls._rmtree(path, ignore_errors=ignore_errors)
                except FileNotFoundError:
                    pass
            elif issubclass(exc_info[0], FileNotFoundError):
                pass
            elif not ignore_errors:
                raise

        _shutil.rmtree(name, onerror=onerror)

    @classmethod
    def _cleanup(cls, name, warn_message, ignore_errors=False):
        cls._rmtree(name, ignore_errors=ignore_errors)
        _warnings.warn(warn_message, ResourceWarning)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self._finalizer.detach() or _os.path.exists(self.name):
            self._rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)

    __class_getitem__ = classmethod(_types.GenericAlias)
