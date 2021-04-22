"\nRead and write ZIP files.\n\nXXX references to utf-8 need further investigation.\n"
import binascii
import importlib.util
import io
import itertools
import os
import posixpath
import shutil
import stat
import struct
import sys
import threading
import time
import contextlib
import pathlib

try:
    import zlib

    crc32 = zlib.crc32
except ImportError:
    zlib = None
    crc32 = binascii.crc32
try:
    import bz2
except ImportError:
    bz2 = None
try:
    import lzma
except ImportError:
    lzma = None
__all__ = [
    "BadZipFile",
    "BadZipfile",
    "error",
    "ZIP_STORED",
    "ZIP_DEFLATED",
    "ZIP_BZIP2",
    "ZIP_LZMA",
    "is_zipfile",
    "ZipInfo",
    "ZipFile",
    "PyZipFile",
    "LargeZipFile",
    "Path",
]


class BadZipFile(Exception):
    pass


class LargeZipFile(Exception):
    "\n    Raised when writing a zipfile, the zipfile requires ZIP64 extensions\n    and those extensions are disabled.\n    "


error = BadZipfile = BadZipFile
ZIP64_LIMIT = (1 << 31) - 1
ZIP_FILECOUNT_LIMIT = (1 << 16) - 1
ZIP_MAX_COMMENT = (1 << 16) - 1
ZIP_STORED = 0
ZIP_DEFLATED = 8
ZIP_BZIP2 = 12
ZIP_LZMA = 14
DEFAULT_VERSION = 20
ZIP64_VERSION = 45
BZIP2_VERSION = 46
LZMA_VERSION = 63
MAX_EXTRACT_VERSION = 63
structEndArchive = b"<4s4H2LH"
stringEndArchive = b"PK\x05\x06"
sizeEndCentDir = struct.calcsize(structEndArchive)
_ECD_SIGNATURE = 0
_ECD_DISK_NUMBER = 1
_ECD_DISK_START = 2
_ECD_ENTRIES_THIS_DISK = 3
_ECD_ENTRIES_TOTAL = 4
_ECD_SIZE = 5
_ECD_OFFSET = 6
_ECD_COMMENT_SIZE = 7
_ECD_COMMENT = 8
_ECD_LOCATION = 9
structCentralDir = "<4s4B4HL2L5H2L"
stringCentralDir = b"PK\x01\x02"
sizeCentralDir = struct.calcsize(structCentralDir)
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18
structFileHeader = "<4s2B4HL2L2H"
stringFileHeader = b"PK\x03\x04"
sizeFileHeader = struct.calcsize(structFileHeader)
_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11
structEndArchive64Locator = "<4sLQL"
stringEndArchive64Locator = b"PK\x06\x07"
sizeEndCentDir64Locator = struct.calcsize(structEndArchive64Locator)
structEndArchive64 = "<4sQ2H2L4Q"
stringEndArchive64 = b"PK\x06\x06"
sizeEndCentDir64 = struct.calcsize(structEndArchive64)
_CD64_SIGNATURE = 0
_CD64_DIRECTORY_RECSIZE = 1
_CD64_CREATE_VERSION = 2
_CD64_EXTRACT_VERSION = 3
_CD64_DISK_NUMBER = 4
_CD64_DISK_NUMBER_START = 5
_CD64_NUMBER_ENTRIES_THIS_DISK = 6
_CD64_NUMBER_ENTRIES_TOTAL = 7
_CD64_DIRECTORY_SIZE = 8
_CD64_OFFSET_START_CENTDIR = 9
_DD_SIGNATURE = 134695760
_EXTRA_FIELD_STRUCT = struct.Struct("<HH")


def _strip_extra(extra, xids):
    unpack = _EXTRA_FIELD_STRUCT.unpack
    modified = False
    buffer = []
    start = i = 0
    while (i + 4) <= len(extra):
        (xid, xlen) = unpack(extra[i : (i + 4)])
        j = (i + 4) + xlen
        if xid in xids:
            if i != start:
                buffer.append(extra[start:i])
            start = j
            modified = True
        i = j
    if not modified:
        return extra
    return b"".join(buffer)


def _check_zipfile(fp):
    try:
        if _EndRecData(fp):
            return True
    except OSError:
        pass
    return False


def is_zipfile(filename):
    "Quickly see if a file is a ZIP file by checking the magic number.\n\n    The filename argument may be a file or file-like object too.\n    "
    result = False
    try:
        if hasattr(filename, "read"):
            result = _check_zipfile(fp=filename)
        else:
            with open(filename, "rb") as fp:
                result = _check_zipfile(fp)
    except OSError:
        pass
    return result


def _EndRecData64(fpin, offset, endrec):
    "\n    Read the ZIP64 end-of-archive records and use that to update endrec\n    "
    try:
        fpin.seek((offset - sizeEndCentDir64Locator), 2)
    except OSError:
        return endrec
    data = fpin.read(sizeEndCentDir64Locator)
    if len(data) != sizeEndCentDir64Locator:
        return endrec
    (sig, diskno, reloff, disks) = struct.unpack(structEndArchive64Locator, data)
    if sig != stringEndArchive64Locator:
        return endrec
    if (diskno != 0) or (disks > 1):
        raise BadZipFile("zipfiles that span multiple disks are not supported")
    fpin.seek(((offset - sizeEndCentDir64Locator) - sizeEndCentDir64), 2)
    data = fpin.read(sizeEndCentDir64)
    if len(data) != sizeEndCentDir64:
        return endrec
    (
        sig,
        sz,
        create_version,
        read_version,
        disk_num,
        disk_dir,
        dircount,
        dircount2,
        dirsize,
        diroffset,
    ) = struct.unpack(structEndArchive64, data)
    if sig != stringEndArchive64:
        return endrec
    endrec[_ECD_SIGNATURE] = sig
    endrec[_ECD_DISK_NUMBER] = disk_num
    endrec[_ECD_DISK_START] = disk_dir
    endrec[_ECD_ENTRIES_THIS_DISK] = dircount
    endrec[_ECD_ENTRIES_TOTAL] = dircount2
    endrec[_ECD_SIZE] = dirsize
    endrec[_ECD_OFFSET] = diroffset
    return endrec


def _EndRecData(fpin):
    'Return data from the "End of Central Directory" record, or None.\n\n    The data is a list of the nine items in the ZIP "End of central dir"\n    record followed by a tenth item, the file seek offset of this record.'
    fpin.seek(0, 2)
    filesize = fpin.tell()
    try:
        fpin.seek((-sizeEndCentDir), 2)
    except OSError:
        return None
    data = fpin.read()
    if (
        (len(data) == sizeEndCentDir)
        and (data[0:4] == stringEndArchive)
        and (data[(-2):] == b"\x00\x00")
    ):
        endrec = struct.unpack(structEndArchive, data)
        endrec = list(endrec)
        endrec.append(b"")
        endrec.append((filesize - sizeEndCentDir))
        return _EndRecData64(fpin, (-sizeEndCentDir), endrec)
    maxCommentStart = max(((filesize - (1 << 16)) - sizeEndCentDir), 0)
    fpin.seek(maxCommentStart, 0)
    data = fpin.read()
    start = data.rfind(stringEndArchive)
    if start >= 0:
        recData = data[start : (start + sizeEndCentDir)]
        if len(recData) != sizeEndCentDir:
            return None
        endrec = list(struct.unpack(structEndArchive, recData))
        commentSize = endrec[_ECD_COMMENT_SIZE]
        comment = data[
            (start + sizeEndCentDir) : ((start + sizeEndCentDir) + commentSize)
        ]
        endrec.append(comment)
        endrec.append((maxCommentStart + start))
        return _EndRecData64(fpin, ((maxCommentStart + start) - filesize), endrec)
    return None


class ZipInfo(object):
    "Class with attributes describing each file in the ZIP archive."
    __slots__ = (
        "orig_filename",
        "filename",
        "date_time",
        "compress_type",
        "_compresslevel",
        "comment",
        "extra",
        "create_system",
        "create_version",
        "extract_version",
        "reserved",
        "flag_bits",
        "volume",
        "internal_attr",
        "external_attr",
        "header_offset",
        "CRC",
        "compress_size",
        "file_size",
        "_raw_time",
    )

    def __init__(self, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0)):
        self.orig_filename = filename
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        if (os.sep != "/") and (os.sep in filename):
            filename = filename.replace(os.sep, "/")
        self.filename = filename
        self.date_time = date_time
        if date_time[0] < 1980:
            raise ValueError("ZIP does not support timestamps before 1980")
        self.compress_type = ZIP_STORED
        self._compresslevel = None
        self.comment = b""
        self.extra = b""
        if sys.platform == "win32":
            self.create_system = 0
        else:
            self.create_system = 3
        self.create_version = DEFAULT_VERSION
        self.extract_version = DEFAULT_VERSION
        self.reserved = 0
        self.flag_bits = 0
        self.volume = 0
        self.internal_attr = 0
        self.external_attr = 0
        self.compress_size = 0
        self.file_size = 0

    def __repr__(self):
        result = [("<%s filename=%r" % (self.__class__.__name__, self.filename))]
        if self.compress_type != ZIP_STORED:
            result.append(
                (
                    " compress_type=%s"
                    % compressor_names.get(self.compress_type, self.compress_type)
                )
            )
        hi = self.external_attr >> 16
        lo = self.external_attr & 65535
        if hi:
            result.append((" filemode=%r" % stat.filemode(hi)))
        if lo:
            result.append((" external_attr=%#x" % lo))
        isdir = self.is_dir()
        if (not isdir) or self.file_size:
            result.append((" file_size=%r" % self.file_size))
        if ((not isdir) or self.compress_size) and (
            (self.compress_type != ZIP_STORED) or (self.file_size != self.compress_size)
        ):
            result.append((" compress_size=%r" % self.compress_size))
        result.append(">")
        return "".join(result)

    def FileHeader(self, zip64=None):
        "Return the per-file header as a bytes object."
        dt = self.date_time
        dosdate = (((dt[0] - 1980) << 9) | (dt[1] << 5)) | dt[2]
        dostime = ((dt[3] << 11) | (dt[4] << 5)) | (dt[5] // 2)
        if self.flag_bits & 8:
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size
        extra = self.extra
        min_version = 0
        if zip64 is None:
            zip64 = (file_size > ZIP64_LIMIT) or (compress_size > ZIP64_LIMIT)
        if zip64:
            fmt = "<HHQQ"
            extra = extra + struct.pack(
                fmt, 1, (struct.calcsize(fmt) - 4), file_size, compress_size
            )
        if (file_size > ZIP64_LIMIT) or (compress_size > ZIP64_LIMIT):
            if not zip64:
                raise LargeZipFile("Filesize would require ZIP64 extensions")
            file_size = 4294967295
            compress_size = 4294967295
            min_version = ZIP64_VERSION
        if self.compress_type == ZIP_BZIP2:
            min_version = max(BZIP2_VERSION, min_version)
        elif self.compress_type == ZIP_LZMA:
            min_version = max(LZMA_VERSION, min_version)
        self.extract_version = max(min_version, self.extract_version)
        self.create_version = max(min_version, self.create_version)
        (filename, flag_bits) = self._encodeFilenameFlags()
        header = struct.pack(
            structFileHeader,
            stringFileHeader,
            self.extract_version,
            self.reserved,
            flag_bits,
            self.compress_type,
            dostime,
            dosdate,
            CRC,
            compress_size,
            file_size,
            len(filename),
            len(extra),
        )
        return (header + filename) + extra

    def _encodeFilenameFlags(self):
        try:
            return (self.filename.encode("ascii"), self.flag_bits)
        except UnicodeEncodeError:
            return (self.filename.encode("utf-8"), (self.flag_bits | 2048))

    def _decodeExtra(self):
        extra = self.extra
        unpack = struct.unpack
        while len(extra) >= 4:
            (tp, ln) = unpack("<HH", extra[:4])
            if (ln + 4) > len(extra):
                raise BadZipFile(("Corrupt extra field %04x (size=%d)" % (tp, ln)))
            if tp == 1:
                data = extra[4 : (ln + 4)]
                try:
                    if self.file_size in (18446744073709551615, 4294967295):
                        field = "File size"
                        (self.file_size,) = unpack("<Q", data[:8])
                        data = data[8:]
                    if self.compress_size == 4294967295:
                        field = "Compress size"
                        (self.compress_size,) = unpack("<Q", data[:8])
                        data = data[8:]
                    if self.header_offset == 4294967295:
                        field = "Header offset"
                        (self.header_offset,) = unpack("<Q", data[:8])
                except struct.error:
                    raise BadZipFile(
                        f"Corrupt zip64 extra field. {field} not found."
                    ) from None
            extra = extra[(ln + 4) :]

    @classmethod
    def from_file(cls, filename, arcname=None, *, strict_timestamps=True):
        "Construct an appropriate ZipInfo for a file on the filesystem.\n\n        filename should be the path to a file or directory on the filesystem.\n\n        arcname is the name which it will have within the archive (by default,\n        this will be the same as filename, but without a drive letter and with\n        leading path separators removed).\n        "
        if isinstance(filename, os.PathLike):
            filename = os.fspath(filename)
        st = os.stat(filename)
        isdir = stat.S_ISDIR(st.st_mode)
        mtime = time.localtime(st.st_mtime)
        date_time = mtime[0:6]
        if (not strict_timestamps) and (date_time[0] < 1980):
            date_time = (1980, 1, 1, 0, 0, 0)
        elif (not strict_timestamps) and (date_time[0] > 2107):
            date_time = (2107, 12, 31, 23, 59, 59)
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        if isdir:
            arcname += "/"
        zinfo = cls(arcname, date_time)
        zinfo.external_attr = (st.st_mode & 65535) << 16
        if isdir:
            zinfo.file_size = 0
            zinfo.external_attr |= 16
        else:
            zinfo.file_size = st.st_size
        return zinfo

    def is_dir(self):
        "Return True if this archive member is a directory."
        return self.filename[(-1)] == "/"


_crctable = None


def _gen_crc(crc):
    for j in range(8):
        if crc & 1:
            crc = (crc >> 1) ^ 3988292384
        else:
            crc >>= 1
    return crc


def _ZipDecrypter(pwd):
    key0 = 305419896
    key1 = 591751049
    key2 = 878082192
    global _crctable
    if _crctable is None:
        _crctable = list(map(_gen_crc, range(256)))
    crctable = _crctable

    def crc32(ch, crc):
        "Compute the CRC32 primitive on one byte."
        return (crc >> 8) ^ crctable[((crc ^ ch) & 255)]

    def update_keys(c):
        nonlocal key0, key1, key2
        key0 = crc32(c, key0)
        key1 = (key1 + (key0 & 255)) & 4294967295
        key1 = ((key1 * 134775813) + 1) & 4294967295
        key2 = crc32((key1 >> 24), key2)

    for p in pwd:
        update_keys(p)

    def decrypter(data):
        "Decrypt a bytes object."
        result = bytearray()
        append = result.append
        for c in data:
            k = key2 | 2
            c ^= ((k * (k ^ 1)) >> 8) & 255
            update_keys(c)
            append(c)
        return bytes(result)

    return decrypter


class LZMACompressor:
    def __init__(self):
        self._comp = None

    def _init(self):
        props = lzma._encode_filter_properties({"id": lzma.FILTER_LZMA1})
        self._comp = lzma.LZMACompressor(
            lzma.FORMAT_RAW,
            filters=[lzma._decode_filter_properties(lzma.FILTER_LZMA1, props)],
        )
        return struct.pack("<BBH", 9, 4, len(props)) + props

    def compress(self, data):
        if self._comp is None:
            return self._init() + self._comp.compress(data)
        return self._comp.compress(data)

    def flush(self):
        if self._comp is None:
            return self._init() + self._comp.flush()
        return self._comp.flush()


class LZMADecompressor:
    def __init__(self):
        self._decomp = None
        self._unconsumed = b""
        self.eof = False

    def decompress(self, data):
        if self._decomp is None:
            self._unconsumed += data
            if len(self._unconsumed) <= 4:
                return b""
            (psize,) = struct.unpack("<H", self._unconsumed[2:4])
            if len(self._unconsumed) <= (4 + psize):
                return b""
            self._decomp = lzma.LZMADecompressor(
                lzma.FORMAT_RAW,
                filters=[
                    lzma._decode_filter_properties(
                        lzma.FILTER_LZMA1, self._unconsumed[4 : (4 + psize)]
                    )
                ],
            )
            data = self._unconsumed[(4 + psize) :]
            del self._unconsumed
        result = self._decomp.decompress(data)
        self.eof = self._decomp.eof
        return result


compressor_names = {
    0: "store",
    1: "shrink",
    2: "reduce",
    3: "reduce",
    4: "reduce",
    5: "reduce",
    6: "implode",
    7: "tokenize",
    8: "deflate",
    9: "deflate64",
    10: "implode",
    12: "bzip2",
    14: "lzma",
    18: "terse",
    19: "lz77",
    97: "wavpack",
    98: "ppmd",
}


def _check_compression(compression):
    if compression == ZIP_STORED:
        pass
    elif compression == ZIP_DEFLATED:
        if not zlib:
            raise RuntimeError("Compression requires the (missing) zlib module")
    elif compression == ZIP_BZIP2:
        if not bz2:
            raise RuntimeError("Compression requires the (missing) bz2 module")
    elif compression == ZIP_LZMA:
        if not lzma:
            raise RuntimeError("Compression requires the (missing) lzma module")
    else:
        raise NotImplementedError("That compression method is not supported")


def _get_compressor(compress_type, compresslevel=None):
    if compress_type == ZIP_DEFLATED:
        if compresslevel is not None:
            return zlib.compressobj(compresslevel, zlib.DEFLATED, (-15))
        return zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, (-15))
    elif compress_type == ZIP_BZIP2:
        if compresslevel is not None:
            return bz2.BZ2Compressor(compresslevel)
        return bz2.BZ2Compressor()
    elif compress_type == ZIP_LZMA:
        return LZMACompressor()
    else:
        return None


def _get_decompressor(compress_type):
    _check_compression(compress_type)
    if compress_type == ZIP_STORED:
        return None
    elif compress_type == ZIP_DEFLATED:
        return zlib.decompressobj((-15))
    elif compress_type == ZIP_BZIP2:
        return bz2.BZ2Decompressor()
    elif compress_type == ZIP_LZMA:
        return LZMADecompressor()
    else:
        descr = compressor_names.get(compress_type)
        if descr:
            raise NotImplementedError(
                ("compression type %d (%s)" % (compress_type, descr))
            )
        else:
            raise NotImplementedError(("compression type %d" % (compress_type,)))


class _SharedFile:
    def __init__(self, file, pos, close, lock, writing):
        self._file = file
        self._pos = pos
        self._close = close
        self._lock = lock
        self._writing = writing
        self.seekable = file.seekable
        self.tell = file.tell

    def seek(self, offset, whence=0):
        with self._lock:
            if self._writing():
                raise ValueError(
                    "Can't reposition in the ZIP file while there is an open writing handle on it. Close the writing handle before trying to read."
                )
            self._file.seek(offset, whence)
            self._pos = self._file.tell()
            return self._pos

    def read(self, n=(-1)):
        with self._lock:
            if self._writing():
                raise ValueError(
                    "Can't read from the ZIP file while there is an open writing handle on it. Close the writing handle before trying to read."
                )
            self._file.seek(self._pos)
            data = self._file.read(n)
            self._pos = self._file.tell()
            return data

    def close(self):
        if self._file is not None:
            fileobj = self._file
            self._file = None
            self._close(fileobj)


class _Tellable:
    def __init__(self, fp):
        self.fp = fp
        self.offset = 0

    def write(self, data):
        n = self.fp.write(data)
        self.offset += n
        return n

    def tell(self):
        return self.offset

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class ZipExtFile(io.BufferedIOBase):
    "File-like object for reading an archive member.\n       Is returned by ZipFile.open().\n    "
    MAX_N = 1 << (31 - 1)
    MIN_READ_SIZE = 4096
    MAX_SEEK_READ = 1 << 24

    def __init__(self, fileobj, mode, zipinfo, pwd=None, close_fileobj=False):
        self._fileobj = fileobj
        self._pwd = pwd
        self._close_fileobj = close_fileobj
        self._compress_type = zipinfo.compress_type
        self._compress_left = zipinfo.compress_size
        self._left = zipinfo.file_size
        self._decompressor = _get_decompressor(self._compress_type)
        self._eof = False
        self._readbuffer = b""
        self._offset = 0
        self.newlines = None
        self.mode = mode
        self.name = zipinfo.filename
        if hasattr(zipinfo, "CRC"):
            self._expected_crc = zipinfo.CRC
            self._running_crc = crc32(b"")
        else:
            self._expected_crc = None
        self._seekable = False
        try:
            if fileobj.seekable():
                self._orig_compress_start = fileobj.tell()
                self._orig_compress_size = zipinfo.compress_size
                self._orig_file_size = zipinfo.file_size
                self._orig_start_crc = self._running_crc
                self._seekable = True
        except AttributeError:
            pass
        self._decrypter = None
        if pwd:
            if zipinfo.flag_bits & 8:
                check_byte = (zipinfo._raw_time >> 8) & 255
            else:
                check_byte = (zipinfo.CRC >> 24) & 255
            h = self._init_decrypter()
            if h != check_byte:
                raise RuntimeError(("Bad password for file %r" % zipinfo.orig_filename))

    def _init_decrypter(self):
        self._decrypter = _ZipDecrypter(self._pwd)
        header = self._fileobj.read(12)
        self._compress_left -= 12
        return self._decrypter(header)[11]

    def __repr__(self):
        result = [("<%s.%s" % (self.__class__.__module__, self.__class__.__qualname__))]
        if not self.closed:
            result.append((" name=%r mode=%r" % (self.name, self.mode)))
            if self._compress_type != ZIP_STORED:
                result.append(
                    (
                        " compress_type=%s"
                        % compressor_names.get(self._compress_type, self._compress_type)
                    )
                )
        else:
            result.append(" [closed]")
        result.append(">")
        return "".join(result)

    def readline(self, limit=(-1)):
        "Read and return a line from the stream.\n\n        If limit is specified, at most limit bytes will be read.\n        "
        if limit < 0:
            i = self._readbuffer.find(b"\n", self._offset) + 1
            if i > 0:
                line = self._readbuffer[self._offset : i]
                self._offset = i
                return line
        return io.BufferedIOBase.readline(self, limit)

    def peek(self, n=1):
        "Returns buffered bytes without advancing the position."
        if n > (len(self._readbuffer) - self._offset):
            chunk = self.read(n)
            if len(chunk) > self._offset:
                self._readbuffer = chunk + self._readbuffer[self._offset :]
                self._offset = 0
            else:
                self._offset -= len(chunk)
        return self._readbuffer[self._offset : (self._offset + 512)]

    def readable(self):
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        return True

    def read(self, n=(-1)):
        "Read and return up to n bytes.\n        If the argument is omitted, None, or negative, data is read and returned until EOF is reached.\n        "
        if self.closed:
            raise ValueError("read from closed file.")
        if (n is None) or (n < 0):
            buf = self._readbuffer[self._offset :]
            self._readbuffer = b""
            self._offset = 0
            while not self._eof:
                buf += self._read1(self.MAX_N)
            return buf
        end = n + self._offset
        if end < len(self._readbuffer):
            buf = self._readbuffer[self._offset : end]
            self._offset = end
            return buf
        n = end - len(self._readbuffer)
        buf = self._readbuffer[self._offset :]
        self._readbuffer = b""
        self._offset = 0
        while (n > 0) and (not self._eof):
            data = self._read1(n)
            if n < len(data):
                self._readbuffer = data
                self._offset = n
                buf += data[:n]
                break
            buf += data
            n -= len(data)
        return buf

    def _update_crc(self, newdata):
        if self._expected_crc is None:
            return
        self._running_crc = crc32(newdata, self._running_crc)
        if self._eof and (self._running_crc != self._expected_crc):
            raise BadZipFile(("Bad CRC-32 for file %r" % self.name))

    def read1(self, n):
        "Read up to n bytes with at most one read() system call."
        if (n is None) or (n < 0):
            buf = self._readbuffer[self._offset :]
            self._readbuffer = b""
            self._offset = 0
            while not self._eof:
                data = self._read1(self.MAX_N)
                if data:
                    buf += data
                    break
            return buf
        end = n + self._offset
        if end < len(self._readbuffer):
            buf = self._readbuffer[self._offset : end]
            self._offset = end
            return buf
        n = end - len(self._readbuffer)
        buf = self._readbuffer[self._offset :]
        self._readbuffer = b""
        self._offset = 0
        if n > 0:
            while not self._eof:
                data = self._read1(n)
                if n < len(data):
                    self._readbuffer = data
                    self._offset = n
                    buf += data[:n]
                    break
                if data:
                    buf += data
                    break
        return buf

    def _read1(self, n):
        if self._eof or (n <= 0):
            return b""
        if self._compress_type == ZIP_DEFLATED:
            data = self._decompressor.unconsumed_tail
            if n > len(data):
                data += self._read2((n - len(data)))
        else:
            data = self._read2(n)
        if self._compress_type == ZIP_STORED:
            self._eof = self._compress_left <= 0
        elif self._compress_type == ZIP_DEFLATED:
            n = max(n, self.MIN_READ_SIZE)
            data = self._decompressor.decompress(data, n)
            self._eof = self._decompressor.eof or (
                (self._compress_left <= 0) and (not self._decompressor.unconsumed_tail)
            )
            if self._eof:
                data += self._decompressor.flush()
        else:
            data = self._decompressor.decompress(data)
            self._eof = self._decompressor.eof or (self._compress_left <= 0)
        data = data[: self._left]
        self._left -= len(data)
        if self._left <= 0:
            self._eof = True
        self._update_crc(data)
        return data

    def _read2(self, n):
        if self._compress_left <= 0:
            return b""
        n = max(n, self.MIN_READ_SIZE)
        n = min(n, self._compress_left)
        data = self._fileobj.read(n)
        self._compress_left -= len(data)
        if not data:
            raise EOFError
        if self._decrypter is not None:
            data = self._decrypter(data)
        return data

    def close(self):
        try:
            if self._close_fileobj:
                self._fileobj.close()
        finally:
            super().close()

    def seekable(self):
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        return self._seekable

    def seek(self, offset, whence=0):
        if self.closed:
            raise ValueError("seek on closed file.")
        if not self._seekable:
            raise io.UnsupportedOperation("underlying stream is not seekable")
        curr_pos = self.tell()
        if whence == 0:
            new_pos = offset
        elif whence == 1:
            new_pos = curr_pos + offset
        elif whence == 2:
            new_pos = self._orig_file_size + offset
        else:
            raise ValueError(
                "whence must be os.SEEK_SET (0), os.SEEK_CUR (1), or os.SEEK_END (2)"
            )
        if new_pos > self._orig_file_size:
            new_pos = self._orig_file_size
        if new_pos < 0:
            new_pos = 0
        read_offset = new_pos - curr_pos
        buff_offset = read_offset + self._offset
        if (buff_offset >= 0) and (buff_offset < len(self._readbuffer)):
            self._offset = buff_offset
            read_offset = 0
        elif read_offset < 0:
            self._fileobj.seek(self._orig_compress_start)
            self._running_crc = self._orig_start_crc
            self._compress_left = self._orig_compress_size
            self._left = self._orig_file_size
            self._readbuffer = b""
            self._offset = 0
            self._decompressor = _get_decompressor(self._compress_type)
            self._eof = False
            read_offset = new_pos
            if self._decrypter is not None:
                self._init_decrypter()
        while read_offset > 0:
            read_len = min(self.MAX_SEEK_READ, read_offset)
            self.read(read_len)
            read_offset -= read_len
        return self.tell()

    def tell(self):
        if self.closed:
            raise ValueError("tell on closed file.")
        if not self._seekable:
            raise io.UnsupportedOperation("underlying stream is not seekable")
        filepos = (
            (self._orig_file_size - self._left) - len(self._readbuffer)
        ) + self._offset
        return filepos


class _ZipWriteFile(io.BufferedIOBase):
    def __init__(self, zf, zinfo, zip64):
        self._zinfo = zinfo
        self._zip64 = zip64
        self._zipfile = zf
        self._compressor = _get_compressor(zinfo.compress_type, zinfo._compresslevel)
        self._file_size = 0
        self._compress_size = 0
        self._crc = 0

    @property
    def _fileobj(self):
        return self._zipfile.fp

    def writable(self):
        return True

    def write(self, data):
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        nbytes = len(data)
        self._file_size += nbytes
        self._crc = crc32(data, self._crc)
        if self._compressor:
            data = self._compressor.compress(data)
            self._compress_size += len(data)
        self._fileobj.write(data)
        return nbytes

    def close(self):
        if self.closed:
            return
        try:
            super().close()
            if self._compressor:
                buf = self._compressor.flush()
                self._compress_size += len(buf)
                self._fileobj.write(buf)
                self._zinfo.compress_size = self._compress_size
            else:
                self._zinfo.compress_size = self._file_size
            self._zinfo.CRC = self._crc
            self._zinfo.file_size = self._file_size
            if self._zinfo.flag_bits & 8:
                fmt = "<LLQQ" if self._zip64 else "<LLLL"
                self._fileobj.write(
                    struct.pack(
                        fmt,
                        _DD_SIGNATURE,
                        self._zinfo.CRC,
                        self._zinfo.compress_size,
                        self._zinfo.file_size,
                    )
                )
                self._zipfile.start_dir = self._fileobj.tell()
            else:
                if not self._zip64:
                    if self._file_size > ZIP64_LIMIT:
                        raise RuntimeError(
                            "File size unexpectedly exceeded ZIP64 limit"
                        )
                    if self._compress_size > ZIP64_LIMIT:
                        raise RuntimeError(
                            "Compressed size unexpectedly exceeded ZIP64 limit"
                        )
                self._zipfile.start_dir = self._fileobj.tell()
                self._fileobj.seek(self._zinfo.header_offset)
                self._fileobj.write(self._zinfo.FileHeader(self._zip64))
                self._fileobj.seek(self._zipfile.start_dir)
            self._zipfile.filelist.append(self._zinfo)
            self._zipfile.NameToInfo[self._zinfo.filename] = self._zinfo
        finally:
            self._zipfile._writing = False


class ZipFile:
    " Class with methods to open, read, write, close, list zip files.\n\n    z = ZipFile(file, mode=\"r\", compression=ZIP_STORED, allowZip64=True,\n                compresslevel=None)\n\n    file: Either the path to the file, or a file-like object.\n          If it is a path, the file will be opened and closed by ZipFile.\n    mode: The mode can be either read 'r', write 'w', exclusive create 'x',\n          or append 'a'.\n    compression: ZIP_STORED (no compression), ZIP_DEFLATED (requires zlib),\n                 ZIP_BZIP2 (requires bz2) or ZIP_LZMA (requires lzma).\n    allowZip64: if True ZipFile will create files with ZIP64 extensions when\n                needed, otherwise it will raise an exception when this would\n                be necessary.\n    compresslevel: None (default for the given compression type) or an integer\n                   specifying the level to pass to the compressor.\n                   When using ZIP_STORED or ZIP_LZMA this keyword has no effect.\n                   When using ZIP_DEFLATED integers 0 through 9 are accepted.\n                   When using ZIP_BZIP2 integers 1 through 9 are accepted.\n\n    "
    fp = None
    _windows_illegal_name_trans_table = None

    def __init__(
        self,
        file,
        mode="r",
        compression=ZIP_STORED,
        allowZip64=True,
        compresslevel=None,
        *,
        strict_timestamps=True,
    ):
        "Open the ZIP file with mode read 'r', write 'w', exclusive create 'x',\n        or append 'a'."
        if mode not in ("r", "w", "x", "a"):
            raise ValueError("ZipFile requires mode 'r', 'w', 'x', or 'a'")
        _check_compression(compression)
        self._allowZip64 = allowZip64
        self._didModify = False
        self.debug = 0
        self.NameToInfo = {}
        self.filelist = []
        self.compression = compression
        self.compresslevel = compresslevel
        self.mode = mode
        self.pwd = None
        self._comment = b""
        self._strict_timestamps = strict_timestamps
        if isinstance(file, os.PathLike):
            file = os.fspath(file)
        if isinstance(file, str):
            self._filePassed = 0
            self.filename = file
            modeDict = {
                "r": "rb",
                "w": "w+b",
                "x": "x+b",
                "a": "r+b",
                "r+b": "w+b",
                "w+b": "wb",
                "x+b": "xb",
            }
            filemode = modeDict[mode]
            while True:
                try:
                    self.fp = io.open(file, filemode)
                except OSError:
                    if filemode in modeDict:
                        filemode = modeDict[filemode]
                        continue
                    raise
                break
        else:
            self._filePassed = 1
            self.fp = file
            self.filename = getattr(file, "name", None)
        self._fileRefCnt = 1
        self._lock = threading.RLock()
        self._seekable = True
        self._writing = False
        try:
            if mode == "r":
                self._RealGetContents()
            elif mode in ("w", "x"):
                self._didModify = True
                try:
                    self.start_dir = self.fp.tell()
                except (AttributeError, OSError):
                    self.fp = _Tellable(self.fp)
                    self.start_dir = 0
                    self._seekable = False
                else:
                    try:
                        self.fp.seek(self.start_dir)
                    except (AttributeError, OSError):
                        self._seekable = False
            elif mode == "a":
                try:
                    self._RealGetContents()
                    self.fp.seek(self.start_dir)
                except BadZipFile:
                    self.fp.seek(0, 2)
                    self._didModify = True
                    self.start_dir = self.fp.tell()
            else:
                raise ValueError("Mode must be 'r', 'w', 'x', or 'a'")
        except:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)
            raise

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __repr__(self):
        result = [("<%s.%s" % (self.__class__.__module__, self.__class__.__qualname__))]
        if self.fp is not None:
            if self._filePassed:
                result.append((" file=%r" % self.fp))
            elif self.filename is not None:
                result.append((" filename=%r" % self.filename))
            result.append((" mode=%r" % self.mode))
        else:
            result.append(" [closed]")
        result.append(">")
        return "".join(result)

    def _RealGetContents(self):
        "Read in the table of contents for the ZIP file."
        fp = self.fp
        try:
            endrec = _EndRecData(fp)
        except OSError:
            raise BadZipFile("File is not a zip file")
        if not endrec:
            raise BadZipFile("File is not a zip file")
        if self.debug > 1:
            print(endrec)
        size_cd = endrec[_ECD_SIZE]
        offset_cd = endrec[_ECD_OFFSET]
        self._comment = endrec[_ECD_COMMENT]
        concat = (endrec[_ECD_LOCATION] - size_cd) - offset_cd
        if endrec[_ECD_SIGNATURE] == stringEndArchive64:
            concat -= sizeEndCentDir64 + sizeEndCentDir64Locator
        if self.debug > 2:
            inferred = concat + offset_cd
            print("given, inferred, offset", offset_cd, inferred, concat)
        self.start_dir = offset_cd + concat
        fp.seek(self.start_dir, 0)
        data = fp.read(size_cd)
        fp = io.BytesIO(data)
        total = 0
        while total < size_cd:
            centdir = fp.read(sizeCentralDir)
            if len(centdir) != sizeCentralDir:
                raise BadZipFile("Truncated central directory")
            centdir = struct.unpack(structCentralDir, centdir)
            if centdir[_CD_SIGNATURE] != stringCentralDir:
                raise BadZipFile("Bad magic number for central directory")
            if self.debug > 2:
                print(centdir)
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            flags = centdir[5]
            if flags & 2048:
                filename = filename.decode("utf-8")
            else:
                filename = filename.decode("cp437")
            x = ZipInfo(filename)
            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET]
            (
                x.create_version,
                x.create_system,
                x.extract_version,
                x.reserved,
                x.flag_bits,
                x.compress_type,
                t,
                d,
                x.CRC,
                x.compress_size,
                x.file_size,
            ) = centdir[1:12]
            if x.extract_version > MAX_EXTRACT_VERSION:
                raise NotImplementedError(
                    ("zip file version %.1f" % (x.extract_version / 10))
                )
            (x.volume, x.internal_attr, x.external_attr) = centdir[15:18]
            x._raw_time = t
            x.date_time = (
                ((d >> 9) + 1980),
                ((d >> 5) & 15),
                (d & 31),
                (t >> 11),
                ((t >> 5) & 63),
                ((t & 31) * 2),
            )
            x._decodeExtra()
            x.header_offset = x.header_offset + concat
            self.filelist.append(x)
            self.NameToInfo[x.filename] = x
            total = (
                ((total + sizeCentralDir) + centdir[_CD_FILENAME_LENGTH])
                + centdir[_CD_EXTRA_FIELD_LENGTH]
            ) + centdir[_CD_COMMENT_LENGTH]
            if self.debug > 2:
                print("total", total)

    def namelist(self):
        "Return a list of file names in the archive."
        return [data.filename for data in self.filelist]

    def infolist(self):
        "Return a list of class ZipInfo instances for files in the\n        archive."
        return self.filelist

    def printdir(self, file=None):
        "Print a table of contents for the zip file."
        print(("%-46s %19s %12s" % ("File Name", "Modified    ", "Size")), file=file)
        for zinfo in self.filelist:
            date = "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time[:6]
            print(
                ("%-46s %s %12d" % (zinfo.filename, date, zinfo.file_size)), file=file
            )

    def testzip(self):
        "Read all the files and check the CRC."
        chunk_size = 2 ** 20
        for zinfo in self.filelist:
            try:
                with self.open(zinfo.filename, "r") as f:
                    while f.read(chunk_size):
                        pass
            except BadZipFile:
                return zinfo.filename

    def getinfo(self, name):
        "Return the instance of ZipInfo given 'name'."
        info = self.NameToInfo.get(name)
        if info is None:
            raise KeyError(("There is no item named %r in the archive" % name))
        return info

    def setpassword(self, pwd):
        "Set default password for encrypted files."
        if pwd and (not isinstance(pwd, bytes)):
            raise TypeError(("pwd: expected bytes, got %s" % type(pwd).__name__))
        if pwd:
            self.pwd = pwd
        else:
            self.pwd = None

    @property
    def comment(self):
        "The comment text associated with the ZIP file."
        return self._comment

    @comment.setter
    def comment(self, comment):
        if not isinstance(comment, bytes):
            raise TypeError(
                ("comment: expected bytes, got %s" % type(comment).__name__)
            )
        if len(comment) > ZIP_MAX_COMMENT:
            import warnings

            warnings.warn(
                (
                    "Archive comment is too long; truncating to %d bytes"
                    % ZIP_MAX_COMMENT
                ),
                stacklevel=2,
            )
            comment = comment[:ZIP_MAX_COMMENT]
        self._comment = comment
        self._didModify = True

    def read(self, name, pwd=None):
        "Return file bytes for name."
        with self.open(name, "r", pwd) as fp:
            return fp.read()

    def open(self, name, mode="r", pwd=None, *, force_zip64=False):
        "Return file-like object for 'name'.\n\n        name is a string for the file name within the ZIP file, or a ZipInfo\n        object.\n\n        mode should be 'r' to read a file already in the ZIP file, or 'w' to\n        write to a file newly added to the archive.\n\n        pwd is the password to decrypt files (only used for reading).\n\n        When writing, if the file size is not known in advance but may exceed\n        2 GiB, pass force_zip64 to use the ZIP64 format, which can handle large\n        files.  If the size is known in advance, it is best to pass a ZipInfo\n        instance for name, with zinfo.file_size set.\n        "
        if mode not in {"r", "w"}:
            raise ValueError('open() requires mode "r" or "w"')
        if pwd and (not isinstance(pwd, bytes)):
            raise TypeError(("pwd: expected bytes, got %s" % type(pwd).__name__))
        if pwd and (mode == "w"):
            raise ValueError("pwd is only supported for reading files")
        if not self.fp:
            raise ValueError("Attempt to use ZIP archive that was already closed")
        if isinstance(name, ZipInfo):
            zinfo = name
        elif mode == "w":
            zinfo = ZipInfo(name)
            zinfo.compress_type = self.compression
            zinfo._compresslevel = self.compresslevel
        else:
            zinfo = self.getinfo(name)
        if mode == "w":
            return self._open_to_write(zinfo, force_zip64=force_zip64)
        if self._writing:
            raise ValueError(
                "Can't read from the ZIP file while there is an open writing handle on it. Close the writing handle before trying to read."
            )
        self._fileRefCnt += 1
        zef_file = _SharedFile(
            self.fp,
            zinfo.header_offset,
            self._fpclose,
            self._lock,
            (lambda: self._writing),
        )
        try:
            fheader = zef_file.read(sizeFileHeader)
            if len(fheader) != sizeFileHeader:
                raise BadZipFile("Truncated file header")
            fheader = struct.unpack(structFileHeader, fheader)
            if fheader[_FH_SIGNATURE] != stringFileHeader:
                raise BadZipFile("Bad magic number for file header")
            fname = zef_file.read(fheader[_FH_FILENAME_LENGTH])
            if fheader[_FH_EXTRA_FIELD_LENGTH]:
                zef_file.read(fheader[_FH_EXTRA_FIELD_LENGTH])
            if zinfo.flag_bits & 32:
                raise NotImplementedError("compressed patched data (flag bit 5)")
            if zinfo.flag_bits & 64:
                raise NotImplementedError("strong encryption (flag bit 6)")
            if fheader[_FH_GENERAL_PURPOSE_FLAG_BITS] & 2048:
                fname_str = fname.decode("utf-8")
            else:
                fname_str = fname.decode("cp437")
            if fname_str != zinfo.orig_filename:
                raise BadZipFile(
                    (
                        "File name in directory %r and header %r differ."
                        % (zinfo.orig_filename, fname)
                    )
                )
            is_encrypted = zinfo.flag_bits & 1
            if is_encrypted:
                if not pwd:
                    pwd = self.pwd
                if not pwd:
                    raise RuntimeError(
                        (
                            "File %r is encrypted, password required for extraction"
                            % name
                        )
                    )
            else:
                pwd = None
            return ZipExtFile(zef_file, mode, zinfo, pwd, True)
        except:
            zef_file.close()
            raise

    def _open_to_write(self, zinfo, force_zip64=False):
        if force_zip64 and (not self._allowZip64):
            raise ValueError(
                "force_zip64 is True, but allowZip64 was False when opening the ZIP file."
            )
        if self._writing:
            raise ValueError(
                "Can't write to the ZIP file while there is another write handle open on it. Close the first handle before opening another."
            )
        zinfo.compress_size = 0
        zinfo.CRC = 0
        zinfo.flag_bits = 0
        if zinfo.compress_type == ZIP_LZMA:
            zinfo.flag_bits |= 2
        if not self._seekable:
            zinfo.flag_bits |= 8
        if not zinfo.external_attr:
            zinfo.external_attr = 384 << 16
        zip64 = self._allowZip64 and (
            force_zip64 or ((zinfo.file_size * 1.05) > ZIP64_LIMIT)
        )
        if self._seekable:
            self.fp.seek(self.start_dir)
        zinfo.header_offset = self.fp.tell()
        self._writecheck(zinfo)
        self._didModify = True
        self.fp.write(zinfo.FileHeader(zip64))
        self._writing = True
        return _ZipWriteFile(self, zinfo, zip64)

    def extract(self, member, path=None, pwd=None):
        "Extract a member from the archive to the current working directory,\n           using its full name. Its file information is extracted as accurately\n           as possible. `member' may be a filename or a ZipInfo object. You can\n           specify a different directory using `path'.\n        "
        if path is None:
            path = os.getcwd()
        else:
            path = os.fspath(path)
        return self._extract_member(member, path, pwd)

    def extractall(self, path=None, members=None, pwd=None):
        "Extract all members from the archive to the current working\n           directory. `path' specifies a different directory to extract to.\n           `members' is optional and must be a subset of the list returned\n           by namelist().\n        "
        if members is None:
            members = self.namelist()
        if path is None:
            path = os.getcwd()
        else:
            path = os.fspath(path)
        for zipinfo in members:
            self._extract_member(zipinfo, path, pwd)

    @classmethod
    def _sanitize_windows_name(cls, arcname, pathsep):
        "Replace bad characters and remove trailing dots from parts."
        table = cls._windows_illegal_name_trans_table
        if not table:
            illegal = ':<>|"?*'
            table = str.maketrans(illegal, ("_" * len(illegal)))
            cls._windows_illegal_name_trans_table = table
        arcname = arcname.translate(table)
        arcname = (x.rstrip(".") for x in arcname.split(pathsep))
        arcname = pathsep.join((x for x in arcname if x))
        return arcname

    def _extract_member(self, member, targetpath, pwd):
        "Extract the ZipInfo object 'member' to a physical\n           file on the path targetpath.\n        "
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)
        arcname = member.filename.replace("/", os.path.sep)
        if os.path.altsep:
            arcname = arcname.replace(os.path.altsep, os.path.sep)
        arcname = os.path.splitdrive(arcname)[1]
        invalid_path_parts = ("", os.path.curdir, os.path.pardir)
        arcname = os.path.sep.join(
            (x for x in arcname.split(os.path.sep) if (x not in invalid_path_parts))
        )
        if os.path.sep == "\\":
            arcname = self._sanitize_windows_name(arcname, os.path.sep)
        targetpath = os.path.join(targetpath, arcname)
        targetpath = os.path.normpath(targetpath)
        upperdirs = os.path.dirname(targetpath)
        if upperdirs and (not os.path.exists(upperdirs)):
            os.makedirs(upperdirs)
        if member.is_dir():
            if not os.path.isdir(targetpath):
                os.mkdir(targetpath)
            return targetpath
        with self.open(member, pwd=pwd) as source, open(targetpath, "wb") as target:
            shutil.copyfileobj(source, target)
        return targetpath

    def _writecheck(self, zinfo):
        "Check for errors before writing a file to the archive."
        if zinfo.filename in self.NameToInfo:
            import warnings

            warnings.warn(("Duplicate name: %r" % zinfo.filename), stacklevel=3)
        if self.mode not in ("w", "x", "a"):
            raise ValueError("write() requires mode 'w', 'x', or 'a'")
        if not self.fp:
            raise ValueError("Attempt to write ZIP archive that was already closed")
        _check_compression(zinfo.compress_type)
        if not self._allowZip64:
            requires_zip64 = None
            if len(self.filelist) >= ZIP_FILECOUNT_LIMIT:
                requires_zip64 = "Files count"
            elif zinfo.file_size > ZIP64_LIMIT:
                requires_zip64 = "Filesize"
            elif zinfo.header_offset > ZIP64_LIMIT:
                requires_zip64 = "Zipfile size"
            if requires_zip64:
                raise LargeZipFile((requires_zip64 + " would require ZIP64 extensions"))

    def write(self, filename, arcname=None, compress_type=None, compresslevel=None):
        "Put the bytes from filename into the archive under the name\n        arcname."
        if not self.fp:
            raise ValueError("Attempt to write to ZIP archive that was already closed")
        if self._writing:
            raise ValueError(
                "Can't write to ZIP archive while an open writing handle exists"
            )
        zinfo = ZipInfo.from_file(
            filename, arcname, strict_timestamps=self._strict_timestamps
        )
        if zinfo.is_dir():
            zinfo.compress_size = 0
            zinfo.CRC = 0
        else:
            if compress_type is not None:
                zinfo.compress_type = compress_type
            else:
                zinfo.compress_type = self.compression
            if compresslevel is not None:
                zinfo._compresslevel = compresslevel
            else:
                zinfo._compresslevel = self.compresslevel
        if zinfo.is_dir():
            with self._lock:
                if self._seekable:
                    self.fp.seek(self.start_dir)
                zinfo.header_offset = self.fp.tell()
                if zinfo.compress_type == ZIP_LZMA:
                    zinfo.flag_bits |= 2
                self._writecheck(zinfo)
                self._didModify = True
                self.filelist.append(zinfo)
                self.NameToInfo[zinfo.filename] = zinfo
                self.fp.write(zinfo.FileHeader(False))
                self.start_dir = self.fp.tell()
        else:
            with open(filename, "rb") as src, self.open(zinfo, "w") as dest:
                shutil.copyfileobj(src, dest, (1024 * 8))

    def writestr(self, zinfo_or_arcname, data, compress_type=None, compresslevel=None):
        "Write a file into the archive.  The contents is 'data', which\n        may be either a 'str' or a 'bytes' instance; if it is a 'str',\n        it is encoded as UTF-8 first.\n        'zinfo_or_arcname' is either a ZipInfo instance or\n        the name of the file in the archive."
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(zinfo_or_arcname, ZipInfo):
            zinfo = ZipInfo(
                filename=zinfo_or_arcname, date_time=time.localtime(time.time())[:6]
            )
            zinfo.compress_type = self.compression
            zinfo._compresslevel = self.compresslevel
            if zinfo.filename[(-1)] == "/":
                zinfo.external_attr = 16893 << 16
                zinfo.external_attr |= 16
            else:
                zinfo.external_attr = 384 << 16
        else:
            zinfo = zinfo_or_arcname
        if not self.fp:
            raise ValueError("Attempt to write to ZIP archive that was already closed")
        if self._writing:
            raise ValueError(
                "Can't write to ZIP archive while an open writing handle exists."
            )
        if compress_type is not None:
            zinfo.compress_type = compress_type
        if compresslevel is not None:
            zinfo._compresslevel = compresslevel
        zinfo.file_size = len(data)
        with self._lock:
            with self.open(zinfo, mode="w") as dest:
                dest.write(data)

    def __del__(self):
        'Call the "close()" method in case the user forgot.'
        self.close()

    def close(self):
        "Close the file, and for mode 'w', 'x' and 'a' write the ending\n        records."
        if self.fp is None:
            return
        if self._writing:
            raise ValueError(
                "Can't close the ZIP file while there is an open writing handle on it. Close the writing handle before closing the zip."
            )
        try:
            if (self.mode in ("w", "x", "a")) and self._didModify:
                with self._lock:
                    if self._seekable:
                        self.fp.seek(self.start_dir)
                    self._write_end_record()
        finally:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)

    def _write_end_record(self):
        for zinfo in self.filelist:
            dt = zinfo.date_time
            dosdate = (((dt[0] - 1980) << 9) | (dt[1] << 5)) | dt[2]
            dostime = ((dt[3] << 11) | (dt[4] << 5)) | (dt[5] // 2)
            extra = []
            if (zinfo.file_size > ZIP64_LIMIT) or (zinfo.compress_size > ZIP64_LIMIT):
                extra.append(zinfo.file_size)
                extra.append(zinfo.compress_size)
                file_size = 4294967295
                compress_size = 4294967295
            else:
                file_size = zinfo.file_size
                compress_size = zinfo.compress_size
            if zinfo.header_offset > ZIP64_LIMIT:
                extra.append(zinfo.header_offset)
                header_offset = 4294967295
            else:
                header_offset = zinfo.header_offset
            extra_data = zinfo.extra
            min_version = 0
            if extra:
                extra_data = _strip_extra(extra_data, (1,))
                extra_data = (
                    struct.pack(
                        ("<HH" + ("Q" * len(extra))), 1, (8 * len(extra)), *extra
                    )
                    + extra_data
                )
                min_version = ZIP64_VERSION
            if zinfo.compress_type == ZIP_BZIP2:
                min_version = max(BZIP2_VERSION, min_version)
            elif zinfo.compress_type == ZIP_LZMA:
                min_version = max(LZMA_VERSION, min_version)
            extract_version = max(min_version, zinfo.extract_version)
            create_version = max(min_version, zinfo.create_version)
            (filename, flag_bits) = zinfo._encodeFilenameFlags()
            centdir = struct.pack(
                structCentralDir,
                stringCentralDir,
                create_version,
                zinfo.create_system,
                extract_version,
                zinfo.reserved,
                flag_bits,
                zinfo.compress_type,
                dostime,
                dosdate,
                zinfo.CRC,
                compress_size,
                file_size,
                len(filename),
                len(extra_data),
                len(zinfo.comment),
                0,
                zinfo.internal_attr,
                zinfo.external_attr,
                header_offset,
            )
            self.fp.write(centdir)
            self.fp.write(filename)
            self.fp.write(extra_data)
            self.fp.write(zinfo.comment)
        pos2 = self.fp.tell()
        centDirCount = len(self.filelist)
        centDirSize = pos2 - self.start_dir
        centDirOffset = self.start_dir
        requires_zip64 = None
        if centDirCount > ZIP_FILECOUNT_LIMIT:
            requires_zip64 = "Files count"
        elif centDirOffset > ZIP64_LIMIT:
            requires_zip64 = "Central directory offset"
        elif centDirSize > ZIP64_LIMIT:
            requires_zip64 = "Central directory size"
        if requires_zip64:
            if not self._allowZip64:
                raise LargeZipFile((requires_zip64 + " would require ZIP64 extensions"))
            zip64endrec = struct.pack(
                structEndArchive64,
                stringEndArchive64,
                44,
                45,
                45,
                0,
                0,
                centDirCount,
                centDirCount,
                centDirSize,
                centDirOffset,
            )
            self.fp.write(zip64endrec)
            zip64locrec = struct.pack(
                structEndArchive64Locator, stringEndArchive64Locator, 0, pos2, 1
            )
            self.fp.write(zip64locrec)
            centDirCount = min(centDirCount, 65535)
            centDirSize = min(centDirSize, 4294967295)
            centDirOffset = min(centDirOffset, 4294967295)
        endrec = struct.pack(
            structEndArchive,
            stringEndArchive,
            0,
            0,
            centDirCount,
            centDirCount,
            centDirSize,
            centDirOffset,
            len(self._comment),
        )
        self.fp.write(endrec)
        self.fp.write(self._comment)
        if self.mode == "a":
            self.fp.truncate()
        self.fp.flush()

    def _fpclose(self, fp):
        assert self._fileRefCnt > 0
        self._fileRefCnt -= 1
        if (not self._fileRefCnt) and (not self._filePassed):
            fp.close()


class PyZipFile(ZipFile):
    "Class to create ZIP archives with Python library files and packages."

    def __init__(
        self, file, mode="r", compression=ZIP_STORED, allowZip64=True, optimize=(-1)
    ):
        ZipFile.__init__(
            self, file, mode=mode, compression=compression, allowZip64=allowZip64
        )
        self._optimize = optimize

    def writepy(self, pathname, basename="", filterfunc=None):
        'Add all files from "pathname" to the ZIP archive.\n\n        If pathname is a package directory, search the directory and\n        all package subdirectories recursively for all *.py and enter\n        the modules into the archive.  If pathname is a plain\n        directory, listdir *.py and enter all modules.  Else, pathname\n        must be a Python *.py file and the module will be put into the\n        archive.  Added modules are always module.pyc.\n        This method will compile the module.py into module.pyc if\n        necessary.\n        If filterfunc(pathname) is given, it is called with every argument.\n        When it is False, the file or directory is skipped.\n        '
        pathname = os.fspath(pathname)
        if filterfunc and (not filterfunc(pathname)):
            if self.debug:
                label = "path" if os.path.isdir(pathname) else "file"
                print(("%s %r skipped by filterfunc" % (label, pathname)))
            return
        (dir, name) = os.path.split(pathname)
        if os.path.isdir(pathname):
            initname = os.path.join(pathname, "__init__.py")
            if os.path.isfile(initname):
                if basename:
                    basename = "%s/%s" % (basename, name)
                else:
                    basename = name
                if self.debug:
                    print("Adding package in", pathname, "as", basename)
                (fname, arcname) = self._get_codename(initname[0:(-3)], basename)
                if self.debug:
                    print("Adding", arcname)
                self.write(fname, arcname)
                dirlist = sorted(os.listdir(pathname))
                dirlist.remove("__init__.py")
                for filename in dirlist:
                    path = os.path.join(pathname, filename)
                    (root, ext) = os.path.splitext(filename)
                    if os.path.isdir(path):
                        if os.path.isfile(os.path.join(path, "__init__.py")):
                            self.writepy(path, basename, filterfunc=filterfunc)
                    elif ext == ".py":
                        if filterfunc and (not filterfunc(path)):
                            if self.debug:
                                print(("file %r skipped by filterfunc" % path))
                            continue
                        (fname, arcname) = self._get_codename(path[0:(-3)], basename)
                        if self.debug:
                            print("Adding", arcname)
                        self.write(fname, arcname)
            else:
                if self.debug:
                    print("Adding files from directory", pathname)
                for filename in sorted(os.listdir(pathname)):
                    path = os.path.join(pathname, filename)
                    (root, ext) = os.path.splitext(filename)
                    if ext == ".py":
                        if filterfunc and (not filterfunc(path)):
                            if self.debug:
                                print(("file %r skipped by filterfunc" % path))
                            continue
                        (fname, arcname) = self._get_codename(path[0:(-3)], basename)
                        if self.debug:
                            print("Adding", arcname)
                        self.write(fname, arcname)
        else:
            if pathname[(-3):] != ".py":
                raise RuntimeError('Files added with writepy() must end with ".py"')
            (fname, arcname) = self._get_codename(pathname[0:(-3)], basename)
            if self.debug:
                print("Adding file", arcname)
            self.write(fname, arcname)

    def _get_codename(self, pathname, basename):
        "Return (filename, archivename) for the path.\n\n        Given a module name path, return the correct file path and\n        archive name, compiling if necessary.  For example, given\n        /python/lib/string, return (/python/lib/string.pyc, string).\n        "

        def _compile(file, optimize=(-1)):
            import py_compile

            if self.debug:
                print("Compiling", file)
            try:
                py_compile.compile(file, doraise=True, optimize=optimize)
            except py_compile.PyCompileError as err:
                print(err.msg)
                return False
            return True

        file_py = pathname + ".py"
        file_pyc = pathname + ".pyc"
        pycache_opt0 = importlib.util.cache_from_source(file_py, optimization="")
        pycache_opt1 = importlib.util.cache_from_source(file_py, optimization=1)
        pycache_opt2 = importlib.util.cache_from_source(file_py, optimization=2)
        if self._optimize == (-1):
            if os.path.isfile(file_pyc) and (
                os.stat(file_pyc).st_mtime >= os.stat(file_py).st_mtime
            ):
                arcname = fname = file_pyc
            elif os.path.isfile(pycache_opt0) and (
                os.stat(pycache_opt0).st_mtime >= os.stat(file_py).st_mtime
            ):
                fname = pycache_opt0
                arcname = file_pyc
            elif os.path.isfile(pycache_opt1) and (
                os.stat(pycache_opt1).st_mtime >= os.stat(file_py).st_mtime
            ):
                fname = pycache_opt1
                arcname = file_pyc
            elif os.path.isfile(pycache_opt2) and (
                os.stat(pycache_opt2).st_mtime >= os.stat(file_py).st_mtime
            ):
                fname = pycache_opt2
                arcname = file_pyc
            elif _compile(file_py):
                if sys.flags.optimize == 0:
                    fname = pycache_opt0
                elif sys.flags.optimize == 1:
                    fname = pycache_opt1
                else:
                    fname = pycache_opt2
                arcname = file_pyc
            else:
                fname = arcname = file_py
        else:
            if self._optimize == 0:
                fname = pycache_opt0
                arcname = file_pyc
            else:
                arcname = file_pyc
                if self._optimize == 1:
                    fname = pycache_opt1
                elif self._optimize == 2:
                    fname = pycache_opt2
                else:
                    msg = "invalid value for 'optimize': {!r}".format(self._optimize)
                    raise ValueError(msg)
            if not (
                os.path.isfile(fname)
                and (os.stat(fname).st_mtime >= os.stat(file_py).st_mtime)
            ):
                if not _compile(file_py, optimize=self._optimize):
                    fname = arcname = file_py
        archivename = os.path.split(arcname)[1]
        if basename:
            archivename = "%s/%s" % (basename, archivename)
        return (fname, archivename)


def _parents(path):
    "\n    Given a path with elements separated by\n    posixpath.sep, generate all parents of that path.\n\n    >>> list(_parents('b/d'))\n    ['b']\n    >>> list(_parents('/b/d/'))\n    ['/b']\n    >>> list(_parents('b/d/f/'))\n    ['b/d', 'b']\n    >>> list(_parents('b'))\n    []\n    >>> list(_parents(''))\n    []\n    "
    return itertools.islice(_ancestry(path), 1, None)


def _ancestry(path):
    "\n    Given a path with elements separated by\n    posixpath.sep, generate all elements of that path\n\n    >>> list(_ancestry('b/d'))\n    ['b/d', 'b']\n    >>> list(_ancestry('/b/d/'))\n    ['/b/d', '/b']\n    >>> list(_ancestry('b/d/f/'))\n    ['b/d/f', 'b/d', 'b']\n    >>> list(_ancestry('b'))\n    ['b']\n    >>> list(_ancestry(''))\n    []\n    "
    path = path.rstrip(posixpath.sep)
    while path and (path != posixpath.sep):
        (yield path)
        (path, tail) = posixpath.split(path)


_dedupe = dict.fromkeys
"Deduplicate an iterable in original order"


def _difference(minuend, subtrahend):
    "\n    Return items in minuend not in subtrahend, retaining order\n    with O(1) lookup.\n    "
    return itertools.filterfalse(set(subtrahend).__contains__, minuend)


class CompleteDirs(ZipFile):
    "\n    A ZipFile subclass that ensures that implied directories\n    are always included in the namelist.\n    "

    @staticmethod
    def _implied_dirs(names):
        parents = itertools.chain.from_iterable(map(_parents, names))
        as_dirs = ((p + posixpath.sep) for p in parents)
        return _dedupe(_difference(as_dirs, names))

    def namelist(self):
        names = super(CompleteDirs, self).namelist()
        return names + list(self._implied_dirs(names))

    def _name_set(self):
        return set(self.namelist())

    def resolve_dir(self, name):
        "\n        If the name represents a directory, return that name\n        as a directory (with the trailing slash).\n        "
        names = self._name_set()
        dirname = name + "/"
        dir_match = (name not in names) and (dirname in names)
        return dirname if dir_match else name

    @classmethod
    def make(cls, source):
        "\n        Given a source (filename or zipfile), return an\n        appropriate CompleteDirs subclass.\n        "
        if isinstance(source, CompleteDirs):
            return source
        if not isinstance(source, ZipFile):
            return cls(source)
        if "r" not in source.mode:
            cls = CompleteDirs
        source.__class__ = cls
        return source


class FastLookup(CompleteDirs):
    "\n    ZipFile subclass to ensure implicit\n    dirs exist and are resolved rapidly.\n    "

    def namelist(self):
        with contextlib.suppress(AttributeError):
            return self.__names
        self.__names = super(FastLookup, self).namelist()
        return self.__names

    def _name_set(self):
        with contextlib.suppress(AttributeError):
            return self.__lookup
        self.__lookup = super(FastLookup, self)._name_set()
        return self.__lookup


class Path:
    "\n    A pathlib-compatible interface for zip files.\n\n    Consider a zip file with this structure::\n\n        .\n        ├── a.txt\n        └── b\n            ├── c.txt\n            └── d\n                └── e.txt\n\n    >>> data = io.BytesIO()\n    >>> zf = ZipFile(data, 'w')\n    >>> zf.writestr('a.txt', 'content of a')\n    >>> zf.writestr('b/c.txt', 'content of c')\n    >>> zf.writestr('b/d/e.txt', 'content of e')\n    >>> zf.filename = 'mem/abcde.zip'\n\n    Path accepts the zipfile object itself or a filename\n\n    >>> root = Path(zf)\n\n    From there, several path operations are available.\n\n    Directory iteration (including the zip file itself):\n\n    >>> a, b = root.iterdir()\n    >>> a\n    Path('mem/abcde.zip', 'a.txt')\n    >>> b\n    Path('mem/abcde.zip', 'b/')\n\n    name property:\n\n    >>> b.name\n    'b'\n\n    join with divide operator:\n\n    >>> c = b / 'c.txt'\n    >>> c\n    Path('mem/abcde.zip', 'b/c.txt')\n    >>> c.name\n    'c.txt'\n\n    Read text:\n\n    >>> c.read_text()\n    'content of c'\n\n    existence:\n\n    >>> c.exists()\n    True\n    >>> (b / 'missing.txt').exists()\n    False\n\n    Coercion to string:\n\n    >>> import os\n    >>> str(c).replace(os.sep, posixpath.sep)\n    'mem/abcde.zip/b/c.txt'\n\n    At the root, ``name``, ``filename``, and ``parent``\n    resolve to the zipfile. Note these attributes are not\n    valid and will raise a ``ValueError`` if the zipfile\n    has no filename.\n\n    >>> root.name\n    'abcde.zip'\n    >>> str(root.filename).replace(os.sep, posixpath.sep)\n    'mem/abcde.zip'\n    >>> str(root.parent)\n    'mem'\n    "
    __repr = "{self.__class__.__name__}({self.root.filename!r}, {self.at!r})"

    def __init__(self, root, at=""):
        "\n        Construct a Path from a ZipFile or filename.\n\n        Note: When the source is an existing ZipFile object,\n        its type (__class__) will be mutated to a\n        specialized type. If the caller wishes to retain the\n        original type, the caller should either create a\n        separate ZipFile object or pass a filename.\n        "
        self.root = FastLookup.make(root)
        self.at = at

    def open(self, mode="r", *args, pwd=None, **kwargs):
        "\n        Open this entry as text or binary following the semantics\n        of ``pathlib.Path.open()`` by passing arguments through\n        to io.TextIOWrapper().\n        "
        if self.is_dir():
            raise IsADirectoryError(self)
        zip_mode = mode[0]
        if (not self.exists()) and (zip_mode == "r"):
            raise FileNotFoundError(self)
        stream = self.root.open(self.at, zip_mode, pwd=pwd)
        if "b" in mode:
            if args or kwargs:
                raise ValueError("encoding args invalid for binary operation")
            return stream
        return io.TextIOWrapper(stream, *args, **kwargs)

    @property
    def name(self):
        return pathlib.Path(self.at).name or self.filename.name

    @property
    def filename(self):
        return pathlib.Path(self.root.filename).joinpath(self.at)

    def read_text(self, *args, **kwargs):
        with self.open("r", *args, **kwargs) as strm:
            return strm.read()

    def read_bytes(self):
        with self.open("rb") as strm:
            return strm.read()

    def _is_child(self, path):
        return posixpath.dirname(path.at.rstrip("/")) == self.at.rstrip("/")

    def _next(self, at):
        return self.__class__(self.root, at)

    def is_dir(self):
        return (not self.at) or self.at.endswith("/")

    def is_file(self):
        return self.exists() and (not self.is_dir())

    def exists(self):
        return self.at in self.root._name_set()

    def iterdir(self):
        if not self.is_dir():
            raise ValueError("Can't listdir a file")
        subs = map(self._next, self.root.namelist())
        return filter(self._is_child, subs)

    def __str__(self):
        return posixpath.join(self.root.filename, self.at)

    def __repr__(self):
        return self.__repr.format(self=self)

    def joinpath(self, *other):
        next = posixpath.join(self.at, *other)
        return self._next(self.root.resolve_dir(next))

    __truediv__ = joinpath

    @property
    def parent(self):
        if not self.at:
            return self.filename.parent
        parent_at = posixpath.dirname(self.at.rstrip("/"))
        if parent_at:
            parent_at += "/"
        return self._next(parent_at)


def main(args=None):
    import argparse

    description = "A simple command-line interface for zipfile module."
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-l", "--list", metavar="<zipfile>", help="Show listing of a zipfile"
    )
    group.add_argument(
        "-e",
        "--extract",
        nargs=2,
        metavar=("<zipfile>", "<output_dir>"),
        help="Extract zipfile into target dir",
    )
    group.add_argument(
        "-c",
        "--create",
        nargs="+",
        metavar=("<name>", "<file>"),
        help="Create zipfile from sources",
    )
    group.add_argument(
        "-t", "--test", metavar="<zipfile>", help="Test if a zipfile is valid"
    )
    args = parser.parse_args(args)
    if args.test is not None:
        src = args.test
        with ZipFile(src, "r") as zf:
            badfile = zf.testzip()
        if badfile:
            print("The following enclosed file is corrupted: {!r}".format(badfile))
        print("Done testing")
    elif args.list is not None:
        src = args.list
        with ZipFile(src, "r") as zf:
            zf.printdir()
    elif args.extract is not None:
        (src, curdir) = args.extract
        with ZipFile(src, "r") as zf:
            zf.extractall(curdir)
    elif args.create is not None:
        zip_name = args.create.pop(0)
        files = args.create

        def addToZip(zf, path, zippath):
            if os.path.isfile(path):
                zf.write(path, zippath, ZIP_DEFLATED)
            elif os.path.isdir(path):
                if zippath:
                    zf.write(path, zippath)
                for nm in sorted(os.listdir(path)):
                    addToZip(zf, os.path.join(path, nm), os.path.join(zippath, nm))

        with ZipFile(zip_name, "w") as zf:
            for path in files:
                zippath = os.path.basename(path)
                if not zippath:
                    zippath = os.path.basename(os.path.dirname(path))
                if zippath in ("", os.curdir, os.pardir):
                    zippath = ""
                addToZip(zf, path, zippath)


if __name__ == "__main__":
    main()
