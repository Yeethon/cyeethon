"OS routines for NT or Posix depending on what system we're on.\n\nThis exports:\n  - all functions from posix or nt, e.g. unlink, stat, etc.\n  - os.path is either posixpath or ntpath\n  - os.name is either 'posix' or 'nt'\n  - os.curdir is a string representing the current directory (always '.')\n  - os.pardir is a string representing the parent directory (always '..')\n  - os.sep is the (or a most common) pathname separator ('/' or '\\\\')\n  - os.extsep is the extension separator (always '.')\n  - os.altsep is the alternate pathname separator (None or '/')\n  - os.pathsep is the component separator used in $PATH etc\n  - os.linesep is the line separator in text files ('\\r' or '\\n' or '\\r\\n')\n  - os.defpath is the default search path for executables\n  - os.devnull is the file path of the null device ('/dev/null', etc.)\n\nPrograms that import and use 'os' stand a better chance of being\nportable between different platforms.  Of course, they must then\nonly use functions that are defined by all platforms (e.g., unlink\nand opendir), and leave all pathname manipulation to os.path\n(e.g., split and join).\n"
import abc
import sys
import stat as st
from _collections_abc import _check_methods

GenericAlias = type(list[int])
_names = sys.builtin_module_names
__all__ = [
    "altsep",
    "curdir",
    "pardir",
    "sep",
    "pathsep",
    "linesep",
    "defpath",
    "name",
    "path",
    "devnull",
    "SEEK_SET",
    "SEEK_CUR",
    "SEEK_END",
    "fsencode",
    "fsdecode",
    "get_exec_path",
    "fdopen",
    "extsep",
]


def _exists(name):
    return name in globals()


def _get_exports_list(module):
    try:
        return list(module.__all__)
    except AttributeError:
        return [n for n in dir(module) if (n[0] != "_")]


if "posix" in _names:
    name = "posix"
    linesep = "\n"
    from posix import *

    try:
        from posix import _exit

        __all__.append("_exit")
    except ImportError:
        pass
    import posixpath as path

    try:
        from posix import _have_functions
    except ImportError:
        pass
    import posix

    __all__.extend(_get_exports_list(posix))
    del posix
elif "nt" in _names:
    name = "nt"
    linesep = "\r\n"
    from nt import *

    try:
        from nt import _exit

        __all__.append("_exit")
    except ImportError:
        pass
    import ntpath as path
    import nt

    __all__.extend(_get_exports_list(nt))
    del nt
    try:
        from nt import _have_functions
    except ImportError:
        pass
else:
    raise ImportError("no os specific module found")
sys.modules["os.path"] = path
from os.path import curdir, pardir, sep, pathsep, defpath, extsep, altsep, devnull

del _names
if _exists("_have_functions"):
    _globals = globals()

    def _add(str, fn):
        if (fn in _globals) and (str in _have_functions):
            _set.add(_globals[fn])

    _set = set()
    _add("HAVE_FACCESSAT", "access")
    _add("HAVE_FCHMODAT", "chmod")
    _add("HAVE_FCHOWNAT", "chown")
    _add("HAVE_FSTATAT", "stat")
    _add("HAVE_FUTIMESAT", "utime")
    _add("HAVE_LINKAT", "link")
    _add("HAVE_MKDIRAT", "mkdir")
    _add("HAVE_MKFIFOAT", "mkfifo")
    _add("HAVE_MKNODAT", "mknod")
    _add("HAVE_OPENAT", "open")
    _add("HAVE_READLINKAT", "readlink")
    _add("HAVE_RENAMEAT", "rename")
    _add("HAVE_SYMLINKAT", "symlink")
    _add("HAVE_UNLINKAT", "unlink")
    _add("HAVE_UNLINKAT", "rmdir")
    _add("HAVE_UTIMENSAT", "utime")
    supports_dir_fd = _set
    _set = set()
    _add("HAVE_FACCESSAT", "access")
    supports_effective_ids = _set
    _set = set()
    _add("HAVE_FCHDIR", "chdir")
    _add("HAVE_FCHMOD", "chmod")
    _add("HAVE_FCHOWN", "chown")
    _add("HAVE_FDOPENDIR", "listdir")
    _add("HAVE_FDOPENDIR", "scandir")
    _add("HAVE_FEXECVE", "execve")
    _set.add(stat)
    _add("HAVE_FTRUNCATE", "truncate")
    _add("HAVE_FUTIMENS", "utime")
    _add("HAVE_FUTIMES", "utime")
    _add("HAVE_FPATHCONF", "pathconf")
    if _exists("statvfs") and _exists("fstatvfs"):
        _add("HAVE_FSTATVFS", "statvfs")
    supports_fd = _set
    _set = set()
    _add("HAVE_FACCESSAT", "access")
    _add("HAVE_FCHOWNAT", "chown")
    _add("HAVE_FSTATAT", "stat")
    _add("HAVE_LCHFLAGS", "chflags")
    _add("HAVE_LCHMOD", "chmod")
    if _exists("lchown"):
        _add("HAVE_LCHOWN", "chown")
    _add("HAVE_LINKAT", "link")
    _add("HAVE_LUTIMES", "utime")
    _add("HAVE_LSTAT", "stat")
    _add("HAVE_FSTATAT", "stat")
    _add("HAVE_UTIMENSAT", "utime")
    _add("MS_WINDOWS", "stat")
    supports_follow_symlinks = _set
    del _set
    del _have_functions
    del _globals
    del _add
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2


def makedirs(name, mode=511, exist_ok=False):
    "makedirs(name [, mode=0o777][, exist_ok=False])\n\n    Super-mkdir; create a leaf directory and all intermediate ones.  Works like\n    mkdir, except that any intermediate path segment (not just the rightmost)\n    will be created if it does not exist. If the target directory already\n    exists, raise an OSError if exist_ok is False. Otherwise no exception is\n    raised.  This is recursive.\n\n    "
    (head, tail) = path.split(name)
    if not tail:
        (head, tail) = path.split(head)
    if head and tail and (not path.exists(head)):
        try:
            makedirs(head, exist_ok=exist_ok)
        except FileExistsError:
            pass
        cdir = curdir
        if isinstance(tail, bytes):
            cdir = bytes(curdir, "ASCII")
        if tail == cdir:
            return
    try:
        mkdir(name, mode)
    except OSError:
        if (not exist_ok) or (not path.isdir(name)):
            raise


def removedirs(name):
    "removedirs(name)\n\n    Super-rmdir; remove a leaf directory and all empty intermediate\n    ones.  Works like rmdir except that, if the leaf directory is\n    successfully removed, directories corresponding to rightmost path\n    segments will be pruned away until either the whole path is\n    consumed or an error occurs.  Errors during this latter phase are\n    ignored -- they generally mean that a directory was not empty.\n\n    "
    rmdir(name)
    (head, tail) = path.split(name)
    if not tail:
        (head, tail) = path.split(head)
    while head and tail:
        try:
            rmdir(head)
        except OSError:
            break
        (head, tail) = path.split(head)


def renames(old, new):
    "renames(old, new)\n\n    Super-rename; create directories as necessary and delete any left\n    empty.  Works like rename, except creation of any intermediate\n    directories needed to make the new pathname good is attempted\n    first.  After the rename, directories corresponding to rightmost\n    path segments of the old name will be pruned until either the\n    whole path is consumed or a nonempty directory is found.\n\n    Note: this function can fail with the new directory structure made\n    if you lack permissions needed to unlink the leaf directory or\n    file.\n\n    "
    (head, tail) = path.split(new)
    if head and tail and (not path.exists(head)):
        makedirs(head)
    rename(old, new)
    (head, tail) = path.split(old)
    if head and tail:
        try:
            removedirs(head)
        except OSError:
            pass


__all__.extend(["makedirs", "removedirs", "renames"])


def walk(top, topdown=True, onerror=None, followlinks=False):
    "Directory tree generator.\n\n    For each directory in the directory tree rooted at top (including top\n    itself, but excluding '.' and '..'), yields a 3-tuple\n\n        dirpath, dirnames, filenames\n\n    dirpath is a string, the path to the directory.  dirnames is a list of\n    the names of the subdirectories in dirpath (excluding '.' and '..').\n    filenames is a list of the names of the non-directory files in dirpath.\n    Note that the names in the lists are just names, with no path components.\n    To get a full path (which begins with top) to a file or directory in\n    dirpath, do os.path.join(dirpath, name).\n\n    If optional arg 'topdown' is true or not specified, the triple for a\n    directory is generated before the triples for any of its subdirectories\n    (directories are generated top down).  If topdown is false, the triple\n    for a directory is generated after the triples for all of its\n    subdirectories (directories are generated bottom up).\n\n    When topdown is true, the caller can modify the dirnames list in-place\n    (e.g., via del or slice assignment), and walk will only recurse into the\n    subdirectories whose names remain in dirnames; this can be used to prune the\n    search, or to impose a specific order of visiting.  Modifying dirnames when\n    topdown is false has no effect on the behavior of os.walk(), since the\n    directories in dirnames have already been generated by the time dirnames\n    itself is generated. No matter the value of topdown, the list of\n    subdirectories is retrieved before the tuples for the directory and its\n    subdirectories are generated.\n\n    By default errors from the os.scandir() call are ignored.  If\n    optional arg 'onerror' is specified, it should be a function; it\n    will be called with one argument, an OSError instance.  It can\n    report the error to continue with the walk, or raise the exception\n    to abort the walk.  Note that the filename is available as the\n    filename attribute of the exception object.\n\n    By default, os.walk does not follow symbolic links to subdirectories on\n    systems that support them.  In order to get this functionality, set the\n    optional argument 'followlinks' to true.\n\n    Caution:  if you pass a relative pathname for top, don't change the\n    current working directory between resumptions of walk.  walk never\n    changes the current directory, and assumes that the client doesn't\n    either.\n\n    Example:\n\n    import os\n    from os.path import join, getsize\n    for root, dirs, files in os.walk('python/Lib/email'):\n        print(root, \"consumes\", end=\"\")\n        print(sum(getsize(join(root, name)) for name in files), end=\"\")\n        print(\"bytes in\", len(files), \"non-directory files\")\n        if 'CVS' in dirs:\n            dirs.remove('CVS')  # don't visit CVS directories\n\n    "
    sys.audit("os.walk", top, topdown, onerror, followlinks)
    return _walk(fspath(top), topdown, onerror, followlinks)


def _walk(top, topdown, onerror, followlinks):
    dirs = []
    nondirs = []
    walk_dirs = []
    try:
        scandir_it = scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return
    with scandir_it:
        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except OSError as error:
                if onerror is not None:
                    onerror(error)
                return
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            if is_dir:
                dirs.append(entry.name)
            else:
                nondirs.append(entry.name)
            if (not topdown) and is_dir:
                if followlinks:
                    walk_into = True
                else:
                    try:
                        is_symlink = entry.is_symlink()
                    except OSError:
                        is_symlink = False
                    walk_into = not is_symlink
                if walk_into:
                    walk_dirs.append(entry.path)
    if topdown:
        (yield (top, dirs, nondirs))
        (islink, join) = (path.islink, path.join)
        for dirname in dirs:
            new_path = join(top, dirname)
            if followlinks or (not islink(new_path)):
                (yield from _walk(new_path, topdown, onerror, followlinks))
    else:
        for new_path in walk_dirs:
            (yield from _walk(new_path, topdown, onerror, followlinks))
        (yield (top, dirs, nondirs))


__all__.append("walk")
if ({open, stat} <= supports_dir_fd) and ({scandir, stat} <= supports_fd):

    def fwalk(
        top=".", topdown=True, onerror=None, *, follow_symlinks=False, dir_fd=None
    ):
        'Directory tree generator.\n\n        This behaves exactly like walk(), except that it yields a 4-tuple\n\n            dirpath, dirnames, filenames, dirfd\n\n        `dirpath`, `dirnames` and `filenames` are identical to walk() output,\n        and `dirfd` is a file descriptor referring to the directory `dirpath`.\n\n        The advantage of fwalk() over walk() is that it\'s safe against symlink\n        races (when follow_symlinks is False).\n\n        If dir_fd is not None, it should be a file descriptor open to a directory,\n          and top should be relative; top will then be relative to that directory.\n          (dir_fd is always supported for fwalk.)\n\n        Caution:\n        Since fwalk() yields file descriptors, those are only valid until the\n        next iteration step, so you should dup() them if you want to keep them\n        for a longer period.\n\n        Example:\n\n        import os\n        for root, dirs, files, rootfd in os.fwalk(\'python/Lib/email\'):\n            print(root, "consumes", end="")\n            print(sum(os.stat(name, dir_fd=rootfd).st_size for name in files),\n                  end="")\n            print("bytes in", len(files), "non-directory files")\n            if \'CVS\' in dirs:\n                dirs.remove(\'CVS\')  # don\'t visit CVS directories\n        '
        sys.audit("os.fwalk", top, topdown, onerror, follow_symlinks, dir_fd)
        if (not isinstance(top, int)) or (not hasattr(top, "__index__")):
            top = fspath(top)
        if not follow_symlinks:
            orig_st = stat(top, follow_symlinks=False, dir_fd=dir_fd)
        topfd = open(top, O_RDONLY, dir_fd=dir_fd)
        try:
            if follow_symlinks or (
                st.S_ISDIR(orig_st.st_mode) and path.samestat(orig_st, stat(topfd))
            ):
                (
                    yield from _fwalk(
                        topfd,
                        top,
                        isinstance(top, bytes),
                        topdown,
                        onerror,
                        follow_symlinks,
                    )
                )
        finally:
            close(topfd)

    def _fwalk(topfd, toppath, isbytes, topdown, onerror, follow_symlinks):
        scandir_it = scandir(topfd)
        dirs = []
        nondirs = []
        entries = None if (topdown or follow_symlinks) else []
        for entry in scandir_it:
            name = entry.name
            if isbytes:
                name = fsencode(name)
            try:
                if entry.is_dir():
                    dirs.append(name)
                    if entries is not None:
                        entries.append(entry)
                else:
                    nondirs.append(name)
            except OSError:
                try:
                    if entry.is_symlink():
                        nondirs.append(name)
                except OSError:
                    pass
        if topdown:
            (yield (toppath, dirs, nondirs, topfd))
        for name in dirs if (entries is None) else zip(dirs, entries):
            try:
                if not follow_symlinks:
                    if topdown:
                        orig_st = stat(name, dir_fd=topfd, follow_symlinks=False)
                    else:
                        assert entries is not None
                        (name, entry) = name
                        orig_st = entry.stat(follow_symlinks=False)
                dirfd = open(name, O_RDONLY, dir_fd=topfd)
            except OSError as err:
                if onerror is not None:
                    onerror(err)
                continue
            try:
                if follow_symlinks or path.samestat(orig_st, stat(dirfd)):
                    dirpath = path.join(toppath, name)
                    (
                        yield from _fwalk(
                            dirfd, dirpath, isbytes, topdown, onerror, follow_symlinks
                        )
                    )
            finally:
                close(dirfd)
        if not topdown:
            (yield (toppath, dirs, nondirs, topfd))

    __all__.append("fwalk")


def execl(file, *args):
    "execl(file, *args)\n\n    Execute the executable file with argument list args, replacing the\n    current process. "
    execv(file, args)


def execle(file, *args):
    "execle(file, *args, env)\n\n    Execute the executable file with argument list args and\n    environment env, replacing the current process. "
    env = args[(-1)]
    execve(file, args[:(-1)], env)


def execlp(file, *args):
    "execlp(file, *args)\n\n    Execute the executable file (which is searched for along $PATH)\n    with argument list args, replacing the current process. "
    execvp(file, args)


def execlpe(file, *args):
    "execlpe(file, *args, env)\n\n    Execute the executable file (which is searched for along $PATH)\n    with argument list args and environment env, replacing the current\n    process. "
    env = args[(-1)]
    execvpe(file, args[:(-1)], env)


def execvp(file, args):
    "execvp(file, args)\n\n    Execute the executable file (which is searched for along $PATH)\n    with argument list args, replacing the current process.\n    args may be a list or tuple of strings. "
    _execvpe(file, args)


def execvpe(file, args, env):
    "execvpe(file, args, env)\n\n    Execute the executable file (which is searched for along $PATH)\n    with argument list args and environment env, replacing the\n    current process.\n    args may be a list or tuple of strings. "
    _execvpe(file, args, env)


__all__.extend(["execl", "execle", "execlp", "execlpe", "execvp", "execvpe"])


def _execvpe(file, args, env=None):
    if env is not None:
        exec_func = execve
        argrest = (args, env)
    else:
        exec_func = execv
        argrest = (args,)
        env = environ
    if path.dirname(file):
        exec_func(file, *argrest)
        return
    saved_exc = None
    path_list = get_exec_path(env)
    if name != "nt":
        file = fsencode(file)
        path_list = map(fsencode, path_list)
    for dir in path_list:
        fullname = path.join(dir, file)
        try:
            exec_func(fullname, *argrest)
        except (FileNotFoundError, NotADirectoryError) as e:
            last_exc = e
        except OSError as e:
            last_exc = e
            if saved_exc is None:
                saved_exc = e
    if saved_exc is not None:
        raise saved_exc
    raise last_exc


def get_exec_path(env=None):
    "Returns the sequence of directories that will be searched for the\n    named executable (similar to a shell) when launching a process.\n\n    *env* must be an environment variable dict or None.  If *env* is None,\n    os.environ will be used.\n    "
    import warnings

    if env is None:
        env = environ
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", BytesWarning)
        try:
            path_list = env.get("PATH")
        except TypeError:
            path_list = None
        if supports_bytes_environ:
            try:
                path_listb = env[b"PATH"]
            except (KeyError, TypeError):
                pass
            else:
                if path_list is not None:
                    raise ValueError("env cannot contain 'PATH' and b'PATH' keys")
                path_list = path_listb
            if (path_list is not None) and isinstance(path_list, bytes):
                path_list = fsdecode(path_list)
    if path_list is None:
        path_list = defpath
    return path_list.split(pathsep)


from _collections_abc import MutableMapping, Mapping


class _Environ(MutableMapping):
    def __init__(self, data, encodekey, decodekey, encodevalue, decodevalue):
        self.encodekey = encodekey
        self.decodekey = decodekey
        self.encodevalue = encodevalue
        self.decodevalue = decodevalue
        self._data = data

    def __getitem__(self, key):
        try:
            value = self._data[self.encodekey(key)]
        except KeyError:
            raise KeyError(key) from None
        return self.decodevalue(value)

    def __setitem__(self, key, value):
        key = self.encodekey(key)
        value = self.encodevalue(value)
        putenv(key, value)
        self._data[key] = value

    def __delitem__(self, key):
        encodedkey = self.encodekey(key)
        unsetenv(encodedkey)
        try:
            del self._data[encodedkey]
        except KeyError:
            raise KeyError(key) from None

    def __iter__(self):
        keys = list(self._data)
        for key in keys:
            (yield self.decodekey(key))

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "environ({{{}}})".format(
            ", ".join(
                (
                    "{!r}: {!r}".format(self.decodekey(key), self.decodevalue(value))
                    for (key, value) in self._data.items()
                )
            )
        )

    def copy(self):
        return dict(self)

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
        return self[key]

    def __ior__(self, other):
        self.update(other)
        return self

    def __or__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        new = dict(self)
        new.update(other)
        return new

    def __ror__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        new = dict(other)
        new.update(self)
        return new


def _createenviron():
    if name == "nt":

        def check_str(value):
            if not isinstance(value, str):
                raise TypeError(("str expected, not %s" % type(value).__name__))
            return value

        encode = check_str
        decode = str

        def encodekey(key):
            return encode(key).upper()

        data = {}
        for (key, value) in environ.items():
            data[encodekey(key)] = value
    else:
        encoding = sys.getfilesystemencoding()

        def encode(value):
            if not isinstance(value, str):
                raise TypeError(("str expected, not %s" % type(value).__name__))
            return value.encode(encoding, "surrogateescape")

        def decode(value):
            return value.decode(encoding, "surrogateescape")

        encodekey = encode
        data = environ
    return _Environ(data, encodekey, decode, encode, decode)


environ = _createenviron()
del _createenviron


def getenv(key, default=None):
    "Get an environment variable, return None if it doesn't exist.\n    The optional second argument can specify an alternate default.\n    key, default and the result are str."
    return environ.get(key, default)


supports_bytes_environ = name != "nt"
__all__.extend(("getenv", "supports_bytes_environ"))
if supports_bytes_environ:

    def _check_bytes(value):
        if not isinstance(value, bytes):
            raise TypeError(("bytes expected, not %s" % type(value).__name__))
        return value

    environb = _Environ(environ._data, _check_bytes, bytes, _check_bytes, bytes)
    del _check_bytes

    def getenvb(key, default=None):
        "Get an environment variable, return None if it doesn't exist.\n        The optional second argument can specify an alternate default.\n        key, default and the result are bytes."
        return environb.get(key, default)

    __all__.extend(("environb", "getenvb"))


def _fscodec():
    encoding = sys.getfilesystemencoding()
    errors = sys.getfilesystemencodeerrors()

    def fsencode(filename):
        "Encode filename (an os.PathLike, bytes, or str) to the filesystem\n        encoding with 'surrogateescape' error handler, return bytes unchanged.\n        On Windows, use 'strict' error handler if the file system encoding is\n        'mbcs' (which is the default encoding).\n        "
        filename = fspath(filename)
        if isinstance(filename, str):
            return filename.encode(encoding, errors)
        else:
            return filename

    def fsdecode(filename):
        "Decode filename (an os.PathLike, bytes, or str) from the filesystem\n        encoding with 'surrogateescape' error handler, return str unchanged. On\n        Windows, use 'strict' error handler if the file system encoding is\n        'mbcs' (which is the default encoding).\n        "
        filename = fspath(filename)
        if isinstance(filename, bytes):
            return filename.decode(encoding, errors)
        else:
            return filename

    return (fsencode, fsdecode)


(fsencode, fsdecode) = _fscodec()
del _fscodec
if _exists("fork") and (not _exists("spawnv")) and _exists("execv"):
    P_WAIT = 0
    P_NOWAIT = P_NOWAITO = 1
    __all__.extend(["P_WAIT", "P_NOWAIT", "P_NOWAITO"])

    def _spawnvef(mode, file, args, env, func):
        if not isinstance(args, (tuple, list)):
            raise TypeError("argv must be a tuple or a list")
        if (not args) or (not args[0]):
            raise ValueError("argv first element cannot be empty")
        pid = fork()
        if not pid:
            try:
                if env is None:
                    func(file, args)
                else:
                    func(file, args, env)
            except:
                _exit(127)
        else:
            if mode == P_NOWAIT:
                return pid
            while 1:
                (wpid, sts) = waitpid(pid, 0)
                if WIFSTOPPED(sts):
                    continue
                return waitstatus_to_exitcode(sts)

    def spawnv(mode, file, args):
        "spawnv(mode, file, args) -> integer\n\nExecute file with arguments from args in a subprocess.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return _spawnvef(mode, file, args, None, execv)

    def spawnve(mode, file, args, env):
        "spawnve(mode, file, args, env) -> integer\n\nExecute file with arguments from args in a subprocess with the\nspecified environment.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return _spawnvef(mode, file, args, env, execve)

    def spawnvp(mode, file, args):
        "spawnvp(mode, file, args) -> integer\n\nExecute file (which is looked for along $PATH) with arguments from\nargs in a subprocess.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return _spawnvef(mode, file, args, None, execvp)

    def spawnvpe(mode, file, args, env):
        "spawnvpe(mode, file, args, env) -> integer\n\nExecute file (which is looked for along $PATH) with arguments from\nargs in a subprocess with the supplied environment.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return _spawnvef(mode, file, args, env, execvpe)

    __all__.extend(["spawnv", "spawnve", "spawnvp", "spawnvpe"])
if _exists("spawnv"):

    def spawnl(mode, file, *args):
        "spawnl(mode, file, *args) -> integer\n\nExecute file with arguments from args in a subprocess.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return spawnv(mode, file, args)

    def spawnle(mode, file, *args):
        "spawnle(mode, file, *args, env) -> integer\n\nExecute file with arguments from args in a subprocess with the\nsupplied environment.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        env = args[(-1)]
        return spawnve(mode, file, args[:(-1)], env)

    __all__.extend(["spawnl", "spawnle"])
if _exists("spawnvp"):

    def spawnlp(mode, file, *args):
        "spawnlp(mode, file, *args) -> integer\n\nExecute file (which is looked for along $PATH) with arguments from\nargs in a subprocess with the supplied environment.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        return spawnvp(mode, file, args)

    def spawnlpe(mode, file, *args):
        "spawnlpe(mode, file, *args, env) -> integer\n\nExecute file (which is looked for along $PATH) with arguments from\nargs in a subprocess with the supplied environment.\nIf mode == P_NOWAIT return the pid of the process.\nIf mode == P_WAIT return the process's exit code if it exits normally;\notherwise return -SIG, where SIG is the signal that killed it. "
        env = args[(-1)]
        return spawnvpe(mode, file, args[:(-1)], env)

    __all__.extend(["spawnlp", "spawnlpe"])
if sys.platform != "vxworks":

    def popen(cmd, mode="r", buffering=(-1)):
        if not isinstance(cmd, str):
            raise TypeError(("invalid cmd type (%s, expected string)" % type(cmd)))
        if mode not in ("r", "w"):
            raise ValueError(("invalid mode %r" % mode))
        if (buffering == 0) or (buffering is None):
            raise ValueError("popen() does not support unbuffered streams")
        import subprocess, io

        if mode == "r":
            proc = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, bufsize=buffering
            )
            return _wrap_close(io.TextIOWrapper(proc.stdout), proc)
        else:
            proc = subprocess.Popen(
                cmd, shell=True, stdin=subprocess.PIPE, bufsize=buffering
            )
            return _wrap_close(io.TextIOWrapper(proc.stdin), proc)

    class _wrap_close:
        def __init__(self, stream, proc):
            self._stream = stream
            self._proc = proc

        def close(self):
            self._stream.close()
            returncode = self._proc.wait()
            if returncode == 0:
                return None
            if name == "nt":
                return returncode
            else:
                return returncode << 8

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def __getattr__(self, name):
            return getattr(self._stream, name)

        def __iter__(self):
            return iter(self._stream)

    __all__.append("popen")


def fdopen(fd, mode="r", buffering=(-1), encoding=None, *args, **kwargs):
    if not isinstance(fd, int):
        raise TypeError(("invalid fd type (%s, expected integer)" % type(fd)))
    import io

    if "b" not in mode:
        encoding = io.text_encoding(encoding)
    return io.open(fd, mode, buffering, encoding, *args, **kwargs)


def _fspath(path):
    "Return the path representation of a path-like object.\n\n    If str or bytes is passed in, it is returned unchanged. Otherwise the\n    os.PathLike interface is used to get the path representation. If the\n    path representation is not str or bytes, TypeError is raised. If the\n    provided path is not str, bytes, or os.PathLike, TypeError is raised.\n    "
    if isinstance(path, (str, bytes)):
        return path
    path_type = type(path)
    try:
        path_repr = path_type.__fspath__(path)
    except AttributeError:
        if hasattr(path_type, "__fspath__"):
            raise
        else:
            raise TypeError(
                ("expected str, bytes or os.PathLike object, not " + path_type.__name__)
            )
    if isinstance(path_repr, (str, bytes)):
        return path_repr
    else:
        raise TypeError(
            "expected {}.__fspath__() to return str or bytes, not {}".format(
                path_type.__name__, type(path_repr).__name__
            )
        )


if not _exists("fspath"):
    fspath = _fspath
    fspath.__name__ = "fspath"


class PathLike(abc.ABC):
    "Abstract base class for implementing the file system path protocol."

    @abc.abstractmethod
    def __fspath__(self):
        "Return the file system path representation of the object."
        raise NotImplementedError

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is PathLike:
            return _check_methods(subclass, "__fspath__")
        return NotImplemented

    __class_getitem__ = classmethod(GenericAlias)


if name == "nt":

    class _AddedDllDirectory:
        def __init__(self, path, cookie, remove_dll_directory):
            self.path = path
            self._cookie = cookie
            self._remove_dll_directory = remove_dll_directory

        def close(self):
            self._remove_dll_directory(self._cookie)
            self.path = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def __repr__(self):
            if self.path:
                return "<AddedDllDirectory({!r})>".format(self.path)
            return "<AddedDllDirectory()>"

    def add_dll_directory(path):
        "Add a path to the DLL search path.\n\n        This search path is used when resolving dependencies for imported\n        extension modules (the module itself is resolved through sys.path),\n        and also by ctypes.\n\n        Remove the directory by calling close() on the returned object or\n        using it in a with statement.\n        "
        import nt

        cookie = nt._add_dll_directory(path)
        return _AddedDllDirectory(path, cookie, nt._remove_dll_directory)
