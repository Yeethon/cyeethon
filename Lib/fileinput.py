'Helper class to quickly write a loop over all standard input files.\n\nTypical use is:\n\n    import fileinput\n    for line in fileinput.input(encoding="utf-8"):\n        process(line)\n\nThis iterates over the lines of all files listed in sys.argv[1:],\ndefaulting to sys.stdin if the list is empty.  If a filename is \'-\' it\nis also replaced by sys.stdin and the optional arguments mode and\nopenhook are ignored.  To specify an alternative list of filenames,\npass it as the argument to input().  A single file name is also allowed.\n\nFunctions filename(), lineno() return the filename and cumulative line\nnumber of the line that has just been read; filelineno() returns its\nline number in the current file; isfirstline() returns true iff the\nline just read is the first line of its file; isstdin() returns true\niff the line was read from sys.stdin.  Function nextfile() closes the\ncurrent file so that the next iteration will read the first line from\nthe next file (if any); lines not read from the file will not count\ntowards the cumulative line count; the filename is not changed until\nafter the first line of the next file has been read.  Function close()\ncloses the sequence.\n\nBefore any lines have been read, filename() returns None and both line\nnumbers are zero; nextfile() has no effect.  After all lines have been\nread, filename() and the line number functions return the values\npertaining to the last line read; nextfile() has no effect.\n\nAll files are opened in text mode by default, you can override this by\nsetting the mode parameter to input() or FileInput.__init__().\nIf an I/O error occurs during opening or reading a file, the OSError\nexception is raised.\n\nIf sys.stdin is used more than once, the second and further use will\nreturn no lines, except perhaps for interactive use, or if it has been\nexplicitly reset (e.g. using sys.stdin.seek(0)).\n\nEmpty files are opened and immediately closed; the only time their\npresence in the list of filenames is noticeable at all is when the\nlast file opened is empty.\n\nIt is possible that the last line of a file doesn\'t end in a newline\ncharacter; otherwise lines are returned including the trailing\nnewline.\n\nClass FileInput is the implementation; its methods filename(),\nlineno(), fileline(), isfirstline(), isstdin(), nextfile() and close()\ncorrespond to the functions in the module.  In addition it has a\nreadline() method which returns the next input line, and a\n__getitem__() method which implements the sequence behavior.  The\nsequence must be accessed in strictly sequential order; sequence\naccess and readline() cannot be mixed.\n\nOptional in-place filtering: if the keyword argument inplace=1 is\npassed to input() or to the FileInput constructor, the file is moved\nto a backup file and standard output is directed to the input file.\nThis makes it possible to write a filter that rewrites its input file\nin place.  If the keyword argument backup=".<some extension>" is also\ngiven, it specifies the extension for the backup file, and the backup\nfile remains around; by default, the extension is ".bak" and it is\ndeleted when the output file is closed.  In-place filtering is\ndisabled when standard input is read.  XXX The current implementation\ndoes not work for MS-DOS 8+3 filesystems.\n'
import io
import sys, os
from types import GenericAlias

__all__ = [
    "input",
    "close",
    "nextfile",
    "filename",
    "lineno",
    "filelineno",
    "fileno",
    "isfirstline",
    "isstdin",
    "FileInput",
    "hook_compressed",
    "hook_encoded",
]
_state = None


def input(
    files=None,
    inplace=False,
    backup="",
    *,
    mode="r",
    openhook=None,
    encoding=None,
    errors=None
):
    "Return an instance of the FileInput class, which can be iterated.\n\n    The parameters are passed to the constructor of the FileInput class.\n    The returned instance, in addition to being an iterator,\n    keeps global state for the functions of this module,.\n    "
    global _state
    if _state and _state._file:
        raise RuntimeError("input() already active")
    _state = FileInput(
        files,
        inplace,
        backup,
        mode=mode,
        openhook=openhook,
        encoding=encoding,
        errors=errors,
    )
    return _state


def close():
    "Close the sequence."
    global _state
    state = _state
    _state = None
    if state:
        state.close()


def nextfile():
    "\n    Close the current file so that the next iteration will read the first\n    line from the next file (if any); lines not read from the file will\n    not count towards the cumulative line count. The filename is not\n    changed until after the first line of the next file has been read.\n    Before the first line has been read, this function has no effect;\n    it cannot be used to skip the first file. After the last line of the\n    last file has been read, this function has no effect.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.nextfile()


def filename():
    "\n    Return the name of the file currently being read.\n    Before the first line has been read, returns None.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.filename()


def lineno():
    "\n    Return the cumulative line number of the line that has just been read.\n    Before the first line has been read, returns 0. After the last line\n    of the last file has been read, returns the line number of that line.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.lineno()


def filelineno():
    "\n    Return the line number in the current file. Before the first line\n    has been read, returns 0. After the last line of the last file has\n    been read, returns the line number of that line within the file.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.filelineno()


def fileno():
    "\n    Return the file number of the current file. When no file is currently\n    opened, returns -1.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.fileno()


def isfirstline():
    "\n    Returns true the line just read is the first line of its file,\n    otherwise returns false.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.isfirstline()


def isstdin():
    "\n    Returns true if the last line was read from sys.stdin,\n    otherwise returns false.\n    "
    if not _state:
        raise RuntimeError("no active input()")
    return _state.isstdin()


class FileInput:
    "FileInput([files[, inplace[, backup]]], *, mode=None, openhook=None)\n\n    Class FileInput is the implementation of the module; its methods\n    filename(), lineno(), fileline(), isfirstline(), isstdin(), fileno(),\n    nextfile() and close() correspond to the functions of the same name\n    in the module.\n    In addition it has a readline() method which returns the next\n    input line, and a __getitem__() method which implements the\n    sequence behavior. The sequence must be accessed in strictly\n    sequential order; random access and readline() cannot be mixed.\n    "

    def __init__(
        self,
        files=None,
        inplace=False,
        backup="",
        *,
        mode="r",
        openhook=None,
        encoding=None,
        errors=None
    ):
        if isinstance(files, str):
            files = (files,)
        elif isinstance(files, os.PathLike):
            files = (os.fspath(files),)
        else:
            if files is None:
                files = sys.argv[1:]
            if not files:
                files = ("-",)
            else:
                files = tuple(files)
        self._files = files
        self._inplace = inplace
        self._backup = backup
        self._savestdout = None
        self._output = None
        self._filename = None
        self._startlineno = 0
        self._filelineno = 0
        self._file = None
        self._isstdin = False
        self._backupfilename = None
        self._encoding = encoding
        self._errors = errors
        if ("b" not in mode) and (encoding is None) and sys.flags.warn_default_encoding:
            import warnings

            warnings.warn("'encoding' argument not specified.", EncodingWarning, 2)
        if mode not in ("r", "rU", "U", "rb"):
            raise ValueError(
                "FileInput opening mode must be one of 'r', 'rU', 'U' and 'rb'"
            )
        if "U" in mode:
            import warnings

            warnings.warn("'U' mode is deprecated", DeprecationWarning, 2)
        self._mode = mode
        self._write_mode = mode.replace("r", "w") if ("U" not in mode) else "w"
        if openhook:
            if inplace:
                raise ValueError("FileInput cannot use an opening hook in inplace mode")
            if not callable(openhook):
                raise ValueError("FileInput openhook must be callable")
        self._openhook = openhook

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.nextfile()
        finally:
            self._files = ()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            line = self._readline()
            if line:
                self._filelineno += 1
                return line
            if not self._file:
                raise StopIteration
            self.nextfile()

    def __getitem__(self, i):
        import warnings

        warnings.warn(
            "Support for indexing FileInput objects is deprecated. Use iterator protocol instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if i != self.lineno():
            raise RuntimeError("accessing lines out of order")
        try:
            return self.__next__()
        except StopIteration:
            raise IndexError("end of input reached")

    def nextfile(self):
        savestdout = self._savestdout
        self._savestdout = None
        if savestdout:
            sys.stdout = savestdout
        output = self._output
        self._output = None
        try:
            if output:
                output.close()
        finally:
            file = self._file
            self._file = None
            try:
                del self._readline
            except AttributeError:
                pass
            try:
                if file and (not self._isstdin):
                    file.close()
            finally:
                backupfilename = self._backupfilename
                self._backupfilename = None
                if backupfilename and (not self._backup):
                    try:
                        os.unlink(backupfilename)
                    except OSError:
                        pass
                self._isstdin = False

    def readline(self):
        while True:
            line = self._readline()
            if line:
                self._filelineno += 1
                return line
            if not self._file:
                return line
            self.nextfile()

    def _readline(self):
        if not self._files:
            if "b" in self._mode:
                return b""
            else:
                return ""
        self._filename = self._files[0]
        self._files = self._files[1:]
        self._startlineno = self.lineno()
        self._filelineno = 0
        self._file = None
        self._isstdin = False
        self._backupfilename = 0
        if self._filename == "-":
            self._filename = "<stdin>"
            if "b" in self._mode:
                self._file = getattr(sys.stdin, "buffer", sys.stdin)
            else:
                self._file = sys.stdin
            self._isstdin = True
        elif self._inplace:
            self._backupfilename = os.fspath(self._filename) + (self._backup or ".bak")
            try:
                os.unlink(self._backupfilename)
            except OSError:
                pass
            os.rename(self._filename, self._backupfilename)
            self._file = open(self._backupfilename, self._mode)
            try:
                perm = os.fstat(self._file.fileno()).st_mode
            except OSError:
                self._output = open(self._filename, self._write_mode)
            else:
                mode = (os.O_CREAT | os.O_WRONLY) | os.O_TRUNC
                if hasattr(os, "O_BINARY"):
                    mode |= os.O_BINARY
                fd = os.open(self._filename, mode, perm)
                self._output = os.fdopen(fd, self._write_mode)
                try:
                    os.chmod(self._filename, perm)
                except OSError:
                    pass
            self._savestdout = sys.stdout
            sys.stdout = self._output
        elif self._openhook:
            if self._encoding is None:
                self._file = self._openhook(self._filename, self._mode)
            else:
                self._file = self._openhook(
                    self._filename,
                    self._mode,
                    encoding=self._encoding,
                    errors=self._errors,
                )
        else:
            if "b" not in self._mode:
                encoding = self._encoding or "locale"
            else:
                encoding = None
            self._file = open(
                self._filename, self._mode, encoding=encoding, errors=self._errors
            )
        self._readline = self._file.readline
        return self._readline()

    def filename(self):
        return self._filename

    def lineno(self):
        return self._startlineno + self._filelineno

    def filelineno(self):
        return self._filelineno

    def fileno(self):
        if self._file:
            try:
                return self._file.fileno()
            except ValueError:
                return -1
        else:
            return -1

    def isfirstline(self):
        return self._filelineno == 1

    def isstdin(self):
        return self._isstdin

    __class_getitem__ = classmethod(GenericAlias)


def hook_compressed(filename, mode, *, encoding=None, errors=None):
    if encoding is None:
        encoding = "locale"
    ext = os.path.splitext(filename)[1]
    if ext == ".gz":
        import gzip

        stream = gzip.open(filename, mode)
    elif ext == ".bz2":
        import bz2

        stream = bz2.BZ2File(filename, mode)
    else:
        return open(filename, mode, encoding=encoding, errors=errors)
    if "b" not in mode:
        stream = io.TextIOWrapper(stream, encoding=encoding, errors=errors)
    return stream


def hook_encoded(encoding, errors=None):
    def openhook(filename, mode):
        return open(filename, mode, encoding=encoding, errors=errors)

    return openhook


def _test():
    import getopt

    inplace = False
    backup = False
    (opts, args) = getopt.getopt(sys.argv[1:], "ib:")
    for (o, a) in opts:
        if o == "-i":
            inplace = True
        if o == "-b":
            backup = a
    for line in input(args, inplace=inplace, backup=backup):
        if line[(-1):] == "\n":
            line = line[:(-1)]
        if line[(-1):] == "\r":
            line = line[:(-1)]
        print(
            (
                "%d: %s[%d]%s %s"
                % (
                    lineno(),
                    filename(),
                    filelineno(),
                    ((isfirstline() and "*") or ""),
                    line,
                )
            )
        )
    print(("%d: %s[%d]" % (lineno(), filename(), filelineno())))


if __name__ == "__main__":
    _test()
