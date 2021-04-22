"Stuff to parse AIFF-C and AIFF files.\n\nUnless explicitly stated otherwise, the description below is true\nboth for AIFF-C files and AIFF files.\n\nAn AIFF-C file has the following structure.\n\n  +-----------------+\n  | FORM            |\n  +-----------------+\n  | <size>          |\n  +----+------------+\n  |    | AIFC       |\n  |    +------------+\n  |    | <chunks>   |\n  |    |    .       |\n  |    |    .       |\n  |    |    .       |\n  +----+------------+\n\nAn AIFF file has the string \"AIFF\" instead of \"AIFC\".\n\nA chunk consists of an identifier (4 bytes) followed by a size (4 bytes,\nbig endian order), followed by the data.  The size field does not include\nthe size of the 8 byte header.\n\nThe following chunk types are recognized.\n\n  FVER\n      <version number of AIFF-C defining document> (AIFF-C only).\n  MARK\n      <# of markers> (2 bytes)\n      list of markers:\n          <marker ID> (2 bytes, must be > 0)\n          <position> (4 bytes)\n          <marker name> (\"pstring\")\n  COMM\n      <# of channels> (2 bytes)\n      <# of sound frames> (4 bytes)\n      <size of the samples> (2 bytes)\n      <sampling frequency> (10 bytes, IEEE 80-bit extended\n          floating point)\n      in AIFF-C files only:\n      <compression type> (4 bytes)\n      <human-readable version of compression type> (\"pstring\")\n  SSND\n      <offset> (4 bytes, not used by this program)\n      <blocksize> (4 bytes, not used by this program)\n      <sound data>\n\nA pstring consists of 1 byte length, a string of characters, and 0 or 1\nbyte pad to make the total length even.\n\nUsage.\n\nReading AIFF files:\n  f = aifc.open(file, 'r')\nwhere file is either the name of a file or an open file pointer.\nThe open file pointer must have methods read(), seek(), and close().\nIn some types of audio files, if the setpos() method is not used,\nthe seek() method is not necessary.\n\nThis returns an instance of a class with the following public methods:\n  getnchannels()  -- returns number of audio channels (1 for\n             mono, 2 for stereo)\n  getsampwidth()  -- returns sample width in bytes\n  getframerate()  -- returns sampling frequency\n  getnframes()    -- returns number of audio frames\n  getcomptype()   -- returns compression type ('NONE' for AIFF files)\n  getcompname()   -- returns human-readable version of\n             compression type ('not compressed' for AIFF files)\n  getparams() -- returns a namedtuple consisting of all of the\n             above in the above order\n  getmarkers()    -- get the list of marks in the audio file or None\n             if there are no marks\n  getmark(id) -- get mark with the specified id (raises an error\n             if the mark does not exist)\n  readframes(n)   -- returns at most n frames of audio\n  rewind()    -- rewind to the beginning of the audio stream\n  setpos(pos) -- seek to the specified position\n  tell()      -- return the current position\n  close()     -- close the instance (make it unusable)\nThe position returned by tell(), the position given to setpos() and\nthe position of marks are all compatible and have nothing to do with\nthe actual position in the file.\nThe close() method is called automatically when the class instance\nis destroyed.\n\nWriting AIFF files:\n  f = aifc.open(file, 'w')\nwhere file is either the name of a file or an open file pointer.\nThe open file pointer must have methods write(), tell(), seek(), and\nclose().\n\nThis returns an instance of a class with the following public methods:\n  aiff()      -- create an AIFF file (AIFF-C default)\n  aifc()      -- create an AIFF-C file\n  setnchannels(n) -- set the number of channels\n  setsampwidth(n) -- set the sample width\n  setframerate(n) -- set the frame rate\n  setnframes(n)   -- set the number of frames\n  setcomptype(type, name)\n          -- set the compression type and the\n             human-readable compression type\n  setparams(tuple)\n          -- set all parameters at once\n  setmark(id, pos, name)\n          -- add specified mark to the list of marks\n  tell()      -- return current position in output file (useful\n             in combination with setmark())\n  writeframesraw(data)\n          -- write audio frames without pathing up the\n             file header\n  writeframes(data)\n          -- write audio frames and patch up the file header\n  close()     -- patch up the file header and close the\n             output file\nYou should set the parameters before the first writeframesraw or\nwriteframes.  The total number of frames does not need to be set,\nbut when it is set to the correct value, the header does not have to\nbe patched up.\nIt is best to first set all parameters, perhaps possibly the\ncompression type, and then write audio frames using writeframesraw.\nWhen all frames have been written, either call writeframes(b'') or\nclose() to patch up the sizes in the header.\nMarks can be added anytime.  If there are any marks, you must call\nclose() after all frames have been written.\nThe close() method is called automatically when the class instance\nis destroyed.\n\nWhen a file is opened with the extension '.aiff', an AIFF file is\nwritten, otherwise an AIFF-C file is written.  This default can be\nchanged by calling aiff() or aifc() before the first writeframes or\nwriteframesraw.\n"
import struct
import builtins
import warnings

__all__ = ["Error", "open"]


class Error(Exception):
    pass


_AIFC_version = 2726318400


def _read_long(file):
    try:
        return struct.unpack(">l", file.read(4))[0]
    except struct.error:
        raise EOFError from None


def _read_ulong(file):
    try:
        return struct.unpack(">L", file.read(4))[0]
    except struct.error:
        raise EOFError from None


def _read_short(file):
    try:
        return struct.unpack(">h", file.read(2))[0]
    except struct.error:
        raise EOFError from None


def _read_ushort(file):
    try:
        return struct.unpack(">H", file.read(2))[0]
    except struct.error:
        raise EOFError from None


def _read_string(file):
    length = ord(file.read(1))
    if length == 0:
        data = b""
    else:
        data = file.read(length)
    if (length & 1) == 0:
        dummy = file.read(1)
    return data


_HUGE_VAL = 1.79769313486231e308


def _read_float(f):
    expon = _read_short(f)
    sign = 1
    if expon < 0:
        sign = -1
        expon = expon + 32768
    himant = _read_ulong(f)
    lomant = _read_ulong(f)
    if expon == himant == lomant == 0:
        f = 0.0
    elif expon == 32767:
        f = _HUGE_VAL
    else:
        expon = expon - 16383
        f = ((himant * 4294967296) + lomant) * pow(2.0, (expon - 63))
    return sign * f


def _write_short(f, x):
    f.write(struct.pack(">h", x))


def _write_ushort(f, x):
    f.write(struct.pack(">H", x))


def _write_long(f, x):
    f.write(struct.pack(">l", x))


def _write_ulong(f, x):
    f.write(struct.pack(">L", x))


def _write_string(f, s):
    if len(s) > 255:
        raise ValueError("string exceeds maximum pstring length")
    f.write(struct.pack("B", len(s)))
    f.write(s)
    if (len(s) & 1) == 0:
        f.write(b"\x00")


def _write_float(f, x):
    import math

    if x < 0:
        sign = 32768
        x = x * (-1)
    else:
        sign = 0
    if x == 0:
        expon = 0
        himant = 0
        lomant = 0
    else:
        (fmant, expon) = math.frexp(x)
        if (expon > 16384) or (fmant >= 1) or (fmant != fmant):
            expon = sign | 32767
            himant = 0
            lomant = 0
        else:
            expon = expon + 16382
            if expon < 0:
                fmant = math.ldexp(fmant, expon)
                expon = 0
            expon = expon | sign
            fmant = math.ldexp(fmant, 32)
            fsmant = math.floor(fmant)
            himant = int(fsmant)
            fmant = math.ldexp((fmant - fsmant), 32)
            fsmant = math.floor(fmant)
            lomant = int(fsmant)
    _write_ushort(f, expon)
    _write_ulong(f, himant)
    _write_ulong(f, lomant)


from chunk import Chunk
from collections import namedtuple

_aifc_params = namedtuple(
    "_aifc_params", "nchannels sampwidth framerate nframes comptype compname"
)
_aifc_params.nchannels.__doc__ = "Number of audio channels (1 for mono, 2 for stereo)"
_aifc_params.sampwidth.__doc__ = "Sample width in bytes"
_aifc_params.framerate.__doc__ = "Sampling frequency"
_aifc_params.nframes.__doc__ = "Number of audio frames"
_aifc_params.comptype.__doc__ = 'Compression type ("NONE" for AIFF files)'
_aifc_params.compname.__doc__ = "A human-readable version of the compression type\n('not compressed' for AIFF files)"


class Aifc_read:
    _file = None

    def initfp(self, file):
        self._version = 0
        self._convert = None
        self._markers = []
        self._soundpos = 0
        self._file = file
        chunk = Chunk(file)
        if chunk.getname() != b"FORM":
            raise Error("file does not start with FORM id")
        formdata = chunk.read(4)
        if formdata == b"AIFF":
            self._aifc = 0
        elif formdata == b"AIFC":
            self._aifc = 1
        else:
            raise Error("not an AIFF or AIFF-C file")
        self._comm_chunk_read = 0
        self._ssnd_chunk = None
        while 1:
            self._ssnd_seek_needed = 1
            try:
                chunk = Chunk(self._file)
            except EOFError:
                break
            chunkname = chunk.getname()
            if chunkname == b"COMM":
                self._read_comm_chunk(chunk)
                self._comm_chunk_read = 1
            elif chunkname == b"SSND":
                self._ssnd_chunk = chunk
                dummy = chunk.read(8)
                self._ssnd_seek_needed = 0
            elif chunkname == b"FVER":
                self._version = _read_ulong(chunk)
            elif chunkname == b"MARK":
                self._readmark(chunk)
            chunk.skip()
        if (not self._comm_chunk_read) or (not self._ssnd_chunk):
            raise Error("COMM chunk and/or SSND chunk missing")

    def __init__(self, f):
        if isinstance(f, str):
            file_object = builtins.open(f, "rb")
            try:
                self.initfp(file_object)
            except:
                file_object.close()
                raise
        else:
            self.initfp(f)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def getfp(self):
        return self._file

    def rewind(self):
        self._ssnd_seek_needed = 1
        self._soundpos = 0

    def close(self):
        file = self._file
        if file is not None:
            self._file = None
            file.close()

    def tell(self):
        return self._soundpos

    def getnchannels(self):
        return self._nchannels

    def getnframes(self):
        return self._nframes

    def getsampwidth(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparams(self):
        return _aifc_params(
            self.getnchannels(),
            self.getsampwidth(),
            self.getframerate(),
            self.getnframes(),
            self.getcomptype(),
            self.getcompname(),
        )

    def getmarkers(self):
        if len(self._markers) == 0:
            return None
        return self._markers

    def getmark(self, id):
        for marker in self._markers:
            if id == marker[0]:
                return marker
        raise Error("marker {0!r} does not exist".format(id))

    def setpos(self, pos):
        if (pos < 0) or (pos > self._nframes):
            raise Error("position not in range")
        self._soundpos = pos
        self._ssnd_seek_needed = 1

    def readframes(self, nframes):
        if self._ssnd_seek_needed:
            self._ssnd_chunk.seek(0)
            dummy = self._ssnd_chunk.read(8)
            pos = self._soundpos * self._framesize
            if pos:
                self._ssnd_chunk.seek((pos + 8))
            self._ssnd_seek_needed = 0
        if nframes == 0:
            return b""
        data = self._ssnd_chunk.read((nframes * self._framesize))
        if self._convert and data:
            data = self._convert(data)
        self._soundpos = self._soundpos + (
            len(data) // (self._nchannels * self._sampwidth)
        )
        return data

    def _alaw2lin(self, data):
        import audioop

        return audioop.alaw2lin(data, 2)

    def _ulaw2lin(self, data):
        import audioop

        return audioop.ulaw2lin(data, 2)

    def _adpcm2lin(self, data):
        import audioop

        if not hasattr(self, "_adpcmstate"):
            self._adpcmstate = None
        (data, self._adpcmstate) = audioop.adpcm2lin(data, 2, self._adpcmstate)
        return data

    def _read_comm_chunk(self, chunk):
        self._nchannels = _read_short(chunk)
        self._nframes = _read_long(chunk)
        self._sampwidth = (_read_short(chunk) + 7) // 8
        self._framerate = int(_read_float(chunk))
        if self._sampwidth <= 0:
            raise Error("bad sample width")
        if self._nchannels <= 0:
            raise Error("bad # of channels")
        self._framesize = self._nchannels * self._sampwidth
        if self._aifc:
            kludge = 0
            if chunk.chunksize == 18:
                kludge = 1
                warnings.warn("Warning: bad COMM chunk size")
                chunk.chunksize = 23
            self._comptype = chunk.read(4)
            if kludge:
                length = ord(chunk.file.read(1))
                if (length & 1) == 0:
                    length = length + 1
                chunk.chunksize = chunk.chunksize + length
                chunk.file.seek((-1), 1)
            self._compname = _read_string(chunk)
            if self._comptype != b"NONE":
                if self._comptype == b"G722":
                    self._convert = self._adpcm2lin
                elif self._comptype in (b"ulaw", b"ULAW"):
                    self._convert = self._ulaw2lin
                elif self._comptype in (b"alaw", b"ALAW"):
                    self._convert = self._alaw2lin
                else:
                    raise Error("unsupported compression type")
                self._sampwidth = 2
        else:
            self._comptype = b"NONE"
            self._compname = b"not compressed"

    def _readmark(self, chunk):
        nmarkers = _read_short(chunk)
        try:
            for i in range(nmarkers):
                id = _read_short(chunk)
                pos = _read_long(chunk)
                name = _read_string(chunk)
                if pos or name:
                    self._markers.append((id, pos, name))
        except EOFError:
            w = "Warning: MARK chunk contains only %s marker%s instead of %s" % (
                len(self._markers),
                ("" if (len(self._markers) == 1) else "s"),
                nmarkers,
            )
            warnings.warn(w)


class Aifc_write:
    _file = None

    def __init__(self, f):
        if isinstance(f, str):
            file_object = builtins.open(f, "wb")
            try:
                self.initfp(file_object)
            except:
                file_object.close()
                raise
            if f.endswith(".aiff"):
                self._aifc = 0
        else:
            self.initfp(f)

    def initfp(self, file):
        self._file = file
        self._version = _AIFC_version
        self._comptype = b"NONE"
        self._compname = b"not compressed"
        self._convert = None
        self._nchannels = 0
        self._sampwidth = 0
        self._framerate = 0
        self._nframes = 0
        self._nframeswritten = 0
        self._datawritten = 0
        self._datalength = 0
        self._markers = []
        self._marklength = 0
        self._aifc = 1

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def aiff(self):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        self._aifc = 0

    def aifc(self):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        self._aifc = 1

    def setnchannels(self, nchannels):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        if nchannels < 1:
            raise Error("bad # of channels")
        self._nchannels = nchannels

    def getnchannels(self):
        if not self._nchannels:
            raise Error("number of channels not set")
        return self._nchannels

    def setsampwidth(self, sampwidth):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        if (sampwidth < 1) or (sampwidth > 4):
            raise Error("bad sample width")
        self._sampwidth = sampwidth

    def getsampwidth(self):
        if not self._sampwidth:
            raise Error("sample width not set")
        return self._sampwidth

    def setframerate(self, framerate):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        if framerate <= 0:
            raise Error("bad frame rate")
        self._framerate = framerate

    def getframerate(self):
        if not self._framerate:
            raise Error("frame rate not set")
        return self._framerate

    def setnframes(self, nframes):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        self._nframes = nframes

    def getnframes(self):
        return self._nframeswritten

    def setcomptype(self, comptype, compname):
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        if comptype not in (b"NONE", b"ulaw", b"ULAW", b"alaw", b"ALAW", b"G722"):
            raise Error("unsupported compression type")
        self._comptype = comptype
        self._compname = compname

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def setparams(self, params):
        (nchannels, sampwidth, framerate, nframes, comptype, compname) = params
        if self._nframeswritten:
            raise Error("cannot change parameters after starting to write")
        if comptype not in (b"NONE", b"ulaw", b"ULAW", b"alaw", b"ALAW", b"G722"):
            raise Error("unsupported compression type")
        self.setnchannels(nchannels)
        self.setsampwidth(sampwidth)
        self.setframerate(framerate)
        self.setnframes(nframes)
        self.setcomptype(comptype, compname)

    def getparams(self):
        if (not self._nchannels) or (not self._sampwidth) or (not self._framerate):
            raise Error("not all parameters set")
        return _aifc_params(
            self._nchannels,
            self._sampwidth,
            self._framerate,
            self._nframes,
            self._comptype,
            self._compname,
        )

    def setmark(self, id, pos, name):
        if id <= 0:
            raise Error("marker ID must be > 0")
        if pos < 0:
            raise Error("marker position must be >= 0")
        if not isinstance(name, bytes):
            raise Error("marker name must be bytes")
        for i in range(len(self._markers)):
            if id == self._markers[i][0]:
                self._markers[i] = (id, pos, name)
                return
        self._markers.append((id, pos, name))

    def getmark(self, id):
        for marker in self._markers:
            if id == marker[0]:
                return marker
        raise Error("marker {0!r} does not exist".format(id))

    def getmarkers(self):
        if len(self._markers) == 0:
            return None
        return self._markers

    def tell(self):
        return self._nframeswritten

    def writeframesraw(self, data):
        if not isinstance(data, (bytes, bytearray)):
            data = memoryview(data).cast("B")
        self._ensure_header_written(len(data))
        nframes = len(data) // (self._sampwidth * self._nchannels)
        if self._convert:
            data = self._convert(data)
        self._file.write(data)
        self._nframeswritten = self._nframeswritten + nframes
        self._datawritten = self._datawritten + len(data)

    def writeframes(self, data):
        self.writeframesraw(data)
        if (self._nframeswritten != self._nframes) or (
            self._datalength != self._datawritten
        ):
            self._patchheader()

    def close(self):
        if self._file is None:
            return
        try:
            self._ensure_header_written(0)
            if self._datawritten & 1:
                self._file.write(b"\x00")
                self._datawritten = self._datawritten + 1
            self._writemarkers()
            if (
                (self._nframeswritten != self._nframes)
                or (self._datalength != self._datawritten)
                or self._marklength
            ):
                self._patchheader()
        finally:
            self._convert = None
            f = self._file
            self._file = None
            f.close()

    def _lin2alaw(self, data):
        import audioop

        return audioop.lin2alaw(data, 2)

    def _lin2ulaw(self, data):
        import audioop

        return audioop.lin2ulaw(data, 2)

    def _lin2adpcm(self, data):
        import audioop

        if not hasattr(self, "_adpcmstate"):
            self._adpcmstate = None
        (data, self._adpcmstate) = audioop.lin2adpcm(data, 2, self._adpcmstate)
        return data

    def _ensure_header_written(self, datasize):
        if not self._nframeswritten:
            if self._comptype in (b"ULAW", b"ulaw", b"ALAW", b"alaw", b"G722"):
                if not self._sampwidth:
                    self._sampwidth = 2
                if self._sampwidth != 2:
                    raise Error(
                        "sample width must be 2 when compressing with ulaw/ULAW, alaw/ALAW or G7.22 (ADPCM)"
                    )
            if not self._nchannels:
                raise Error("# channels not specified")
            if not self._sampwidth:
                raise Error("sample width not specified")
            if not self._framerate:
                raise Error("sampling rate not specified")
            self._write_header(datasize)

    def _init_compression(self):
        if self._comptype == b"G722":
            self._convert = self._lin2adpcm
        elif self._comptype in (b"ulaw", b"ULAW"):
            self._convert = self._lin2ulaw
        elif self._comptype in (b"alaw", b"ALAW"):
            self._convert = self._lin2alaw

    def _write_header(self, initlength):
        if self._aifc and (self._comptype != b"NONE"):
            self._init_compression()
        self._file.write(b"FORM")
        if not self._nframes:
            self._nframes = initlength // (self._nchannels * self._sampwidth)
        self._datalength = (self._nframes * self._nchannels) * self._sampwidth
        if self._datalength & 1:
            self._datalength = self._datalength + 1
        if self._aifc:
            if self._comptype in (b"ulaw", b"ULAW", b"alaw", b"ALAW"):
                self._datalength = self._datalength // 2
                if self._datalength & 1:
                    self._datalength = self._datalength + 1
            elif self._comptype == b"G722":
                self._datalength = (self._datalength + 3) // 4
                if self._datalength & 1:
                    self._datalength = self._datalength + 1
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        commlength = self._write_form_length(self._datalength)
        if self._aifc:
            self._file.write(b"AIFC")
            self._file.write(b"FVER")
            _write_ulong(self._file, 4)
            _write_ulong(self._file, self._version)
        else:
            self._file.write(b"AIFF")
        self._file.write(b"COMM")
        _write_ulong(self._file, commlength)
        _write_short(self._file, self._nchannels)
        if self._form_length_pos is not None:
            self._nframes_pos = self._file.tell()
        _write_ulong(self._file, self._nframes)
        if self._comptype in (b"ULAW", b"ulaw", b"ALAW", b"alaw", b"G722"):
            _write_short(self._file, 8)
        else:
            _write_short(self._file, (self._sampwidth * 8))
        _write_float(self._file, self._framerate)
        if self._aifc:
            self._file.write(self._comptype)
            _write_string(self._file, self._compname)
        self._file.write(b"SSND")
        if self._form_length_pos is not None:
            self._ssnd_length_pos = self._file.tell()
        _write_ulong(self._file, (self._datalength + 8))
        _write_ulong(self._file, 0)
        _write_ulong(self._file, 0)

    def _write_form_length(self, datalength):
        if self._aifc:
            commlength = (18 + 5) + len(self._compname)
            if commlength & 1:
                commlength = commlength + 1
            verslength = 12
        else:
            commlength = 18
            verslength = 0
        _write_ulong(
            self._file,
            (
                (((((4 + verslength) + self._marklength) + 8) + commlength) + 16)
                + datalength
            ),
        )
        return commlength

    def _patchheader(self):
        curpos = self._file.tell()
        if self._datawritten & 1:
            datalength = self._datawritten + 1
            self._file.write(b"\x00")
        else:
            datalength = self._datawritten
        if (
            (datalength == self._datalength)
            and (self._nframes == self._nframeswritten)
            and (self._marklength == 0)
        ):
            self._file.seek(curpos, 0)
            return
        self._file.seek(self._form_length_pos, 0)
        dummy = self._write_form_length(datalength)
        self._file.seek(self._nframes_pos, 0)
        _write_ulong(self._file, self._nframeswritten)
        self._file.seek(self._ssnd_length_pos, 0)
        _write_ulong(self._file, (datalength + 8))
        self._file.seek(curpos, 0)
        self._nframes = self._nframeswritten
        self._datalength = datalength

    def _writemarkers(self):
        if len(self._markers) == 0:
            return
        self._file.write(b"MARK")
        length = 2
        for marker in self._markers:
            (id, pos, name) = marker
            length = ((length + len(name)) + 1) + 6
            if (len(name) & 1) == 0:
                length = length + 1
        _write_ulong(self._file, length)
        self._marklength = length + 8
        _write_short(self._file, len(self._markers))
        for marker in self._markers:
            (id, pos, name) = marker
            _write_short(self._file, id)
            _write_ulong(self._file, pos)
            _write_string(self._file, name)


def open(f, mode=None):
    if mode is None:
        if hasattr(f, "mode"):
            mode = f.mode
        else:
            mode = "rb"
    if mode in ("r", "rb"):
        return Aifc_read(f)
    elif mode in ("w", "wb"):
        return Aifc_write(f)
    else:
        raise Error("mode must be 'r', 'rb', 'w', or 'wb'")


if __name__ == "__main__":
    import sys

    if not sys.argv[1:]:
        sys.argv.append("/usr/demos/data/audio/bach.aiff")
    fn = sys.argv[1]
    with open(fn, "r") as f:
        print("Reading", fn)
        print("nchannels =", f.getnchannels())
        print("nframes   =", f.getnframes())
        print("sampwidth =", f.getsampwidth())
        print("framerate =", f.getframerate())
        print("comptype  =", f.getcomptype())
        print("compname  =", f.getcompname())
        if sys.argv[2:]:
            gn = sys.argv[2]
            print("Writing", gn)
            with open(gn, "w") as g:
                g.setparams(f.getparams())
                while 1:
                    data = f.readframes(1024)
                    if not data:
                        break
                    g.writeframes(data)
            print("Done.")
