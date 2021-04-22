"Functions that read and write gzipped files.\n\nThe user of the file doesn't have to worry about the compression,\nbut random access is not allowed."
import struct, sys, time, os
import zlib
import builtins
import io
import _compression

__all__ = ["BadGzipFile", "GzipFile", "open", "compress", "decompress"]
(FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT) = (1, 2, 4, 8, 16)
(READ, WRITE) = (1, 2)
_COMPRESS_LEVEL_FAST = 1
_COMPRESS_LEVEL_TRADEOFF = 6
_COMPRESS_LEVEL_BEST = 9


def open(
    filename,
    mode="rb",
    compresslevel=_COMPRESS_LEVEL_BEST,
    encoding=None,
    errors=None,
    newline=None,
):
    'Open a gzip-compressed file in binary or text mode.\n\n    The filename argument can be an actual filename (a str or bytes object), or\n    an existing file object to read from or write to.\n\n    The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for\n    binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is\n    "rb", and the default compresslevel is 9.\n\n    For binary mode, this function is equivalent to the GzipFile constructor:\n    GzipFile(filename, mode, compresslevel). In this case, the encoding, errors\n    and newline arguments must not be provided.\n\n    For text mode, a GzipFile object is created, and wrapped in an\n    io.TextIOWrapper instance with the specified encoding, error handling\n    behavior, and line ending(s).\n\n    '
    if "t" in mode:
        if "b" in mode:
            raise ValueError(("Invalid mode: %r" % (mode,)))
    else:
        if encoding is not None:
            raise ValueError("Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")
    gz_mode = mode.replace("t", "")
    if isinstance(filename, (str, bytes, os.PathLike)):
        binary_file = GzipFile(filename, gz_mode, compresslevel)
    elif hasattr(filename, "read") or hasattr(filename, "write"):
        binary_file = GzipFile(None, gz_mode, compresslevel, filename)
    else:
        raise TypeError("filename must be a str or bytes object, or a file")
    if "t" in mode:
        encoding = io.text_encoding(encoding)
        return io.TextIOWrapper(binary_file, encoding, errors, newline)
    else:
        return binary_file


def write32u(output, value):
    output.write(struct.pack("<L", value))


class _PaddedFile:
    "Minimal read-only file object that prepends a string to the contents\n    of an actual file. Shouldn't be used outside of gzip.py, as it lacks\n    essential functionality."

    def __init__(self, f, prepend=b""):
        self._buffer = prepend
        self._length = len(prepend)
        self.file = f
        self._read = 0

    def read(self, size):
        if self._read is None:
            return self.file.read(size)
        if (self._read + size) <= self._length:
            read = self._read
            self._read += size
            return self._buffer[read : self._read]
        else:
            read = self._read
            self._read = None
            return self._buffer[read:] + self.file.read(((size - self._length) + read))

    def prepend(self, prepend=b""):
        if self._read is None:
            self._buffer = prepend
        else:
            self._read -= len(prepend)
            return
        self._length = len(self._buffer)
        self._read = 0

    def seek(self, off):
        self._read = None
        self._buffer = None
        return self.file.seek(off)

    def seekable(self):
        return True


class BadGzipFile(OSError):
    "Exception raised in some cases for invalid gzip files."


class GzipFile(_compression.BaseStream):
    "The GzipFile class simulates most of the methods of a file object with\n    the exception of the truncate() method.\n\n    This class only supports opening files in binary mode. If you need to open a\n    compressed file in text mode, use the gzip.open() function.\n\n    "
    myfileobj = None

    def __init__(
        self,
        filename=None,
        mode=None,
        compresslevel=_COMPRESS_LEVEL_BEST,
        fileobj=None,
        mtime=None,
    ):
        "Constructor for the GzipFile class.\n\n        At least one of fileobj and filename must be given a\n        non-trivial value.\n\n        The new class instance is based on fileobj, which can be a regular\n        file, an io.BytesIO object, or any other object which simulates a file.\n        It defaults to None, in which case filename is opened to provide\n        a file object.\n\n        When fileobj is not None, the filename argument is only used to be\n        included in the gzip file header, which may include the original\n        filename of the uncompressed file.  It defaults to the filename of\n        fileobj, if discernible; otherwise, it defaults to the empty string,\n        and in this case the original filename is not included in the header.\n\n        The mode argument can be any of 'r', 'rb', 'a', 'ab', 'w', 'wb', 'x', or\n        'xb' depending on whether the file will be read or written.  The default\n        is the mode of fileobj if discernible; otherwise, the default is 'rb'.\n        A mode of 'r' is equivalent to one of 'rb', and similarly for 'w' and\n        'wb', 'a' and 'ab', and 'x' and 'xb'.\n\n        The compresslevel argument is an integer from 0 to 9 controlling the\n        level of compression; 1 is fastest and produces the least compression,\n        and 9 is slowest and produces the most compression. 0 is no compression\n        at all. The default is 9.\n\n        The mtime argument is an optional numeric timestamp to be written\n        to the last modification time field in the stream when compressing.\n        If omitted or None, the current time is used.\n\n        "
        if mode and (("t" in mode) or ("U" in mode)):
            raise ValueError("Invalid mode: {!r}".format(mode))
        if mode and ("b" not in mode):
            mode += "b"
        if fileobj is None:
            fileobj = self.myfileobj = builtins.open(filename, (mode or "rb"))
        if filename is None:
            filename = getattr(fileobj, "name", "")
            if not isinstance(filename, (str, bytes)):
                filename = ""
        else:
            filename = os.fspath(filename)
        origmode = mode
        if mode is None:
            mode = getattr(fileobj, "mode", "rb")
        if mode.startswith("r"):
            self.mode = READ
            raw = _GzipReader(fileobj)
            self._buffer = io.BufferedReader(raw)
            self.name = filename
        elif mode.startswith(("w", "a", "x")):
            if origmode is None:
                import warnings

                warnings.warn(
                    "GzipFile was opened for writing, but this will change in future Python releases.  Specify the mode argument for opening it for writing.",
                    FutureWarning,
                    2,
                )
            self.mode = WRITE
            self._init_write(filename)
            self.compress = zlib.compressobj(
                compresslevel, zlib.DEFLATED, (-zlib.MAX_WBITS), zlib.DEF_MEM_LEVEL, 0
            )
            self._write_mtime = mtime
        else:
            raise ValueError("Invalid mode: {!r}".format(mode))
        self.fileobj = fileobj
        if self.mode == WRITE:
            self._write_gzip_header(compresslevel)

    @property
    def filename(self):
        import warnings

        warnings.warn("use the name attribute", DeprecationWarning, 2)
        if (self.mode == WRITE) and (self.name[(-3):] != ".gz"):
            return self.name + ".gz"
        return self.name

    @property
    def mtime(self):
        "Last modification time read from stream, or None"
        return self._buffer.raw._last_mtime

    def __repr__(self):
        s = repr(self.fileobj)
        return ((("<gzip " + s[1:(-1)]) + " ") + hex(id(self))) + ">"

    def _init_write(self, filename):
        self.name = filename
        self.crc = zlib.crc32(b"")
        self.size = 0
        self.writebuf = []
        self.bufsize = 0
        self.offset = 0

    def _write_gzip_header(self, compresslevel):
        self.fileobj.write(b"\x1f\x8b")
        self.fileobj.write(b"\x08")
        try:
            fname = os.path.basename(self.name)
            if not isinstance(fname, bytes):
                fname = fname.encode("latin-1")
            if fname.endswith(b".gz"):
                fname = fname[:(-3)]
        except UnicodeEncodeError:
            fname = b""
        flags = 0
        if fname:
            flags = FNAME
        self.fileobj.write(chr(flags).encode("latin-1"))
        mtime = self._write_mtime
        if mtime is None:
            mtime = time.time()
        write32u(self.fileobj, int(mtime))
        if compresslevel == _COMPRESS_LEVEL_BEST:
            xfl = b"\x02"
        elif compresslevel == _COMPRESS_LEVEL_FAST:
            xfl = b"\x04"
        else:
            xfl = b"\x00"
        self.fileobj.write(xfl)
        self.fileobj.write(b"\xff")
        if fname:
            self.fileobj.write((fname + b"\x00"))

    def write(self, data):
        self._check_not_closed()
        if self.mode != WRITE:
            import errno

            raise OSError(errno.EBADF, "write() on read-only GzipFile object")
        if self.fileobj is None:
            raise ValueError("write() on closed GzipFile object")
        if isinstance(data, bytes):
            length = len(data)
        else:
            data = memoryview(data)
            length = data.nbytes
        if length > 0:
            self.fileobj.write(self.compress.compress(data))
            self.size += length
            self.crc = zlib.crc32(data, self.crc)
            self.offset += length
        return length

    def read(self, size=(-1)):
        self._check_not_closed()
        if self.mode != READ:
            import errno

            raise OSError(errno.EBADF, "read() on write-only GzipFile object")
        return self._buffer.read(size)

    def read1(self, size=(-1)):
        "Implements BufferedIOBase.read1()\n\n        Reads up to a buffer's worth of data if size is negative."
        self._check_not_closed()
        if self.mode != READ:
            import errno

            raise OSError(errno.EBADF, "read1() on write-only GzipFile object")
        if size < 0:
            size = io.DEFAULT_BUFFER_SIZE
        return self._buffer.read1(size)

    def peek(self, n):
        self._check_not_closed()
        if self.mode != READ:
            import errno

            raise OSError(errno.EBADF, "peek() on write-only GzipFile object")
        return self._buffer.peek(n)

    @property
    def closed(self):
        return self.fileobj is None

    def close(self):
        fileobj = self.fileobj
        if fileobj is None:
            return
        self.fileobj = None
        try:
            if self.mode == WRITE:
                fileobj.write(self.compress.flush())
                write32u(fileobj, self.crc)
                write32u(fileobj, (self.size & 4294967295))
            elif self.mode == READ:
                self._buffer.close()
        finally:
            myfileobj = self.myfileobj
            if myfileobj:
                self.myfileobj = None
                myfileobj.close()

    def flush(self, zlib_mode=zlib.Z_SYNC_FLUSH):
        self._check_not_closed()
        if self.mode == WRITE:
            self.fileobj.write(self.compress.flush(zlib_mode))
            self.fileobj.flush()

    def fileno(self):
        "Invoke the underlying file object's fileno() method.\n\n        This will raise AttributeError if the underlying file object\n        doesn't support fileno().\n        "
        return self.fileobj.fileno()

    def rewind(self):
        "Return the uncompressed stream file position indicator to the\n        beginning of the file"
        if self.mode != READ:
            raise OSError("Can't rewind in write mode")
        self._buffer.seek(0)

    def readable(self):
        return self.mode == READ

    def writable(self):
        return self.mode == WRITE

    def seekable(self):
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        if self.mode == WRITE:
            if whence != io.SEEK_SET:
                if whence == io.SEEK_CUR:
                    offset = self.offset + offset
                else:
                    raise ValueError("Seek from end not supported")
            if offset < self.offset:
                raise OSError("Negative seek in write mode")
            count = offset - self.offset
            chunk = b"\x00" * 1024
            for i in range((count // 1024)):
                self.write(chunk)
            self.write((b"\x00" * (count % 1024)))
        elif self.mode == READ:
            self._check_not_closed()
            return self._buffer.seek(offset, whence)
        return self.offset

    def readline(self, size=(-1)):
        self._check_not_closed()
        return self._buffer.readline(size)

    def __iter__(self):
        self._check_not_closed()
        return self._buffer.__iter__()


class _GzipReader(_compression.DecompressReader):
    def __init__(self, fp):
        super().__init__(_PaddedFile(fp), zlib.decompressobj, wbits=(-zlib.MAX_WBITS))
        self._new_member = True
        self._last_mtime = None

    def _init_read(self):
        self._crc = zlib.crc32(b"")
        self._stream_size = 0

    def _read_exact(self, n):
        "Read exactly *n* bytes from `self._fp`\n\n        This method is required because self._fp may be unbuffered,\n        i.e. return short reads.\n        "
        data = self._fp.read(n)
        while len(data) < n:
            b = self._fp.read((n - len(data)))
            if not b:
                raise EOFError(
                    "Compressed file ended before the end-of-stream marker was reached"
                )
            data += b
        return data

    def _read_gzip_header(self):
        magic = self._fp.read(2)
        if magic == b"":
            return False
        if magic != b"\x1f\x8b":
            raise BadGzipFile(("Not a gzipped file (%r)" % magic))
        (method, flag, self._last_mtime) = struct.unpack("<BBIxx", self._read_exact(8))
        if method != 8:
            raise BadGzipFile("Unknown compression method")
        if flag & FEXTRA:
            (extra_len,) = struct.unpack("<H", self._read_exact(2))
            self._read_exact(extra_len)
        if flag & FNAME:
            while True:
                s = self._fp.read(1)
                if (not s) or (s == b"\x00"):
                    break
        if flag & FCOMMENT:
            while True:
                s = self._fp.read(1)
                if (not s) or (s == b"\x00"):
                    break
        if flag & FHCRC:
            self._read_exact(2)
        return True

    def read(self, size=(-1)):
        if size < 0:
            return self.readall()
        if not size:
            return b""
        while True:
            if self._decompressor.eof:
                self._read_eof()
                self._new_member = True
                self._decompressor = self._decomp_factory(**self._decomp_args)
            if self._new_member:
                self._init_read()
                if not self._read_gzip_header():
                    self._size = self._pos
                    return b""
                self._new_member = False
            buf = self._fp.read(io.DEFAULT_BUFFER_SIZE)
            uncompress = self._decompressor.decompress(buf, size)
            if self._decompressor.unconsumed_tail != b"":
                self._fp.prepend(self._decompressor.unconsumed_tail)
            elif self._decompressor.unused_data != b"":
                self._fp.prepend(self._decompressor.unused_data)
            if uncompress != b"":
                break
            if buf == b"":
                raise EOFError(
                    "Compressed file ended before the end-of-stream marker was reached"
                )
        self._add_read_data(uncompress)
        self._pos += len(uncompress)
        return uncompress

    def _add_read_data(self, data):
        self._crc = zlib.crc32(data, self._crc)
        self._stream_size = self._stream_size + len(data)

    def _read_eof(self):
        (crc32, isize) = struct.unpack("<II", self._read_exact(8))
        if crc32 != self._crc:
            raise BadGzipFile(
                ("CRC check failed %s != %s" % (hex(crc32), hex(self._crc)))
            )
        elif isize != (self._stream_size & 4294967295):
            raise BadGzipFile("Incorrect length of data produced")
        c = b"\x00"
        while c == b"\x00":
            c = self._fp.read(1)
        if c:
            self._fp.prepend(c)

    def _rewind(self):
        super()._rewind()
        self._new_member = True


def compress(data, compresslevel=_COMPRESS_LEVEL_BEST, *, mtime=None):
    "Compress data in one shot and return the compressed string.\n    Optional argument is the compression level, in range of 0-9.\n    "
    buf = io.BytesIO()
    with GzipFile(
        fileobj=buf, mode="wb", compresslevel=compresslevel, mtime=mtime
    ) as f:
        f.write(data)
    return buf.getvalue()


def decompress(data):
    "Decompress a gzip compressed string in one shot.\n    Return the decompressed string.\n    "
    with GzipFile(fileobj=io.BytesIO(data)) as f:
        return f.read()


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="A simple command line interface for the gzip module: act like gzip, but do not delete the input file."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fast", action="store_true", help="compress faster")
    group.add_argument("--best", action="store_true", help="compress better")
    group.add_argument(
        "-d",
        "--decompress",
        action="store_true",
        help="act like gunzip instead of gzip",
    )
    parser.add_argument("args", nargs="*", default=["-"], metavar="file")
    args = parser.parse_args()
    compresslevel = _COMPRESS_LEVEL_TRADEOFF
    if args.fast:
        compresslevel = _COMPRESS_LEVEL_FAST
    elif args.best:
        compresslevel = _COMPRESS_LEVEL_BEST
    for arg in args.args:
        if args.decompress:
            if arg == "-":
                f = GzipFile(filename="", mode="rb", fileobj=sys.stdin.buffer)
                g = sys.stdout.buffer
            else:
                if arg[(-3):] != ".gz":
                    sys.exit(f"filename doesn't end in .gz: {arg!r}")
                f = open(arg, "rb")
                g = builtins.open(arg[:(-3)], "wb")
        elif arg == "-":
            f = sys.stdin.buffer
            g = GzipFile(
                filename="",
                mode="wb",
                fileobj=sys.stdout.buffer,
                compresslevel=compresslevel,
            )
        else:
            f = builtins.open(arg, "rb")
            g = open((arg + ".gz"), "wb")
        while True:
            chunk = f.read(io.DEFAULT_BUFFER_SIZE)
            if not chunk:
                break
            g.write(chunk)
        if g is not sys.stdout.buffer:
            g.close()
        if f is not sys.stdin.buffer:
            f.close()


if __name__ == "__main__":
    main()
