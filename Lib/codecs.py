" codecs -- Python Codec Registry, API and helpers.\n\n\nWritten by Marc-Andre Lemburg (mal@lemburg.com).\n\n(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.\n\n"
import builtins
import sys

try:
    from _codecs import *
except ImportError as why:
    raise SystemError(("Failed to load the builtin codecs: %s" % why))
__all__ = [
    "register",
    "lookup",
    "open",
    "EncodedFile",
    "BOM",
    "BOM_BE",
    "BOM_LE",
    "BOM32_BE",
    "BOM32_LE",
    "BOM64_BE",
    "BOM64_LE",
    "BOM_UTF8",
    "BOM_UTF16",
    "BOM_UTF16_LE",
    "BOM_UTF16_BE",
    "BOM_UTF32",
    "BOM_UTF32_LE",
    "BOM_UTF32_BE",
    "CodecInfo",
    "Codec",
    "IncrementalEncoder",
    "IncrementalDecoder",
    "StreamReader",
    "StreamWriter",
    "StreamReaderWriter",
    "StreamRecoder",
    "getencoder",
    "getdecoder",
    "getincrementalencoder",
    "getincrementaldecoder",
    "getreader",
    "getwriter",
    "encode",
    "decode",
    "iterencode",
    "iterdecode",
    "strict_errors",
    "ignore_errors",
    "replace_errors",
    "xmlcharrefreplace_errors",
    "backslashreplace_errors",
    "namereplace_errors",
    "register_error",
    "lookup_error",
]
BOM_UTF8 = b"\xef\xbb\xbf"
BOM_LE = BOM_UTF16_LE = b"\xff\xfe"
BOM_BE = BOM_UTF16_BE = b"\xfe\xff"
BOM_UTF32_LE = b"\xff\xfe\x00\x00"
BOM_UTF32_BE = b"\x00\x00\xfe\xff"
if sys.byteorder == "little":
    BOM = BOM_UTF16 = BOM_UTF16_LE
    BOM_UTF32 = BOM_UTF32_LE
else:
    BOM = BOM_UTF16 = BOM_UTF16_BE
    BOM_UTF32 = BOM_UTF32_BE
BOM32_LE = BOM_UTF16_LE
BOM32_BE = BOM_UTF16_BE
BOM64_LE = BOM_UTF32_LE
BOM64_BE = BOM_UTF32_BE


class CodecInfo(tuple):
    "Codec details when looking up the codec registry"
    _is_text_encoding = True

    def __new__(
        cls,
        encode,
        decode,
        streamreader=None,
        streamwriter=None,
        incrementalencoder=None,
        incrementaldecoder=None,
        name=None,
        *,
        _is_text_encoding=None
    ):
        self = tuple.__new__(cls, (encode, decode, streamreader, streamwriter))
        self.name = name
        self.encode = encode
        self.decode = decode
        self.incrementalencoder = incrementalencoder
        self.incrementaldecoder = incrementaldecoder
        self.streamwriter = streamwriter
        self.streamreader = streamreader
        if _is_text_encoding is not None:
            self._is_text_encoding = _is_text_encoding
        return self

    def __repr__(self):
        return "<%s.%s object for encoding %s at %#x>" % (
            self.__class__.__module__,
            self.__class__.__qualname__,
            self.name,
            id(self),
        )


class Codec:
    " Defines the interface for stateless encoders/decoders.\n\n        The .encode()/.decode() methods may use different error\n        handling schemes by providing the errors argument. These\n        string values are predefined:\n\n         'strict' - raise a ValueError error (or a subclass)\n         'ignore' - ignore the character and continue with the next\n         'replace' - replace with a suitable replacement character;\n                    Python will use the official U+FFFD REPLACEMENT\n                    CHARACTER for the builtin Unicode codecs on\n                    decoding and '?' on encoding.\n         'surrogateescape' - replace with private code points U+DCnn.\n         'xmlcharrefreplace' - Replace with the appropriate XML\n                               character reference (only for encoding).\n         'backslashreplace'  - Replace with backslashed escape sequences.\n         'namereplace'       - Replace with \\N{...} escape sequences\n                               (only for encoding).\n\n        The set of allowed values can be extended via register_error.\n\n    "

    def encode(self, input, errors="strict"):
        " Encodes the object input and returns a tuple (output\n            object, length consumed).\n\n            errors defines the error handling to apply. It defaults to\n            'strict' handling.\n\n            The method may not store state in the Codec instance. Use\n            StreamWriter for codecs which have to keep state in order to\n            make encoding efficient.\n\n            The encoder must be able to handle zero length input and\n            return an empty object of the output object type in this\n            situation.\n\n        "
        raise NotImplementedError

    def decode(self, input, errors="strict"):
        " Decodes the object input and returns a tuple (output\n            object, length consumed).\n\n            input must be an object which provides the bf_getreadbuf\n            buffer slot. Python strings, buffer objects and memory\n            mapped files are examples of objects providing this slot.\n\n            errors defines the error handling to apply. It defaults to\n            'strict' handling.\n\n            The method may not store state in the Codec instance. Use\n            StreamReader for codecs which have to keep state in order to\n            make decoding efficient.\n\n            The decoder must be able to handle zero length input and\n            return an empty object of the output object type in this\n            situation.\n\n        "
        raise NotImplementedError


class IncrementalEncoder(object):
    "\n    An IncrementalEncoder encodes an input in multiple steps. The input can\n    be passed piece by piece to the encode() method. The IncrementalEncoder\n    remembers the state of the encoding process between calls to encode().\n    "

    def __init__(self, errors="strict"):
        "\n        Creates an IncrementalEncoder instance.\n\n        The IncrementalEncoder may use different error handling schemes by\n        providing the errors keyword argument. See the module docstring\n        for a list of possible values.\n        "
        self.errors = errors
        self.buffer = ""

    def encode(self, input, final=False):
        "\n        Encodes input and returns the resulting object.\n        "
        raise NotImplementedError

    def reset(self):
        "\n        Resets the encoder to the initial state.\n        "

    def getstate(self):
        "\n        Return the current state of the encoder.\n        "
        return 0

    def setstate(self, state):
        "\n        Set the current state of the encoder. state must have been\n        returned by getstate().\n        "


class BufferedIncrementalEncoder(IncrementalEncoder):
    "\n    This subclass of IncrementalEncoder can be used as the baseclass for an\n    incremental encoder if the encoder must keep some of the output in a\n    buffer between calls to encode().\n    "

    def __init__(self, errors="strict"):
        IncrementalEncoder.__init__(self, errors)
        self.buffer = ""

    def _buffer_encode(self, input, errors, final):
        raise NotImplementedError

    def encode(self, input, final=False):
        data = self.buffer + input
        (result, consumed) = self._buffer_encode(data, self.errors, final)
        self.buffer = data[consumed:]
        return result

    def reset(self):
        IncrementalEncoder.reset(self)
        self.buffer = ""

    def getstate(self):
        return self.buffer or 0

    def setstate(self, state):
        self.buffer = state or ""


class IncrementalDecoder(object):
    "\n    An IncrementalDecoder decodes an input in multiple steps. The input can\n    be passed piece by piece to the decode() method. The IncrementalDecoder\n    remembers the state of the decoding process between calls to decode().\n    "

    def __init__(self, errors="strict"):
        "\n        Create an IncrementalDecoder instance.\n\n        The IncrementalDecoder may use different error handling schemes by\n        providing the errors keyword argument. See the module docstring\n        for a list of possible values.\n        "
        self.errors = errors

    def decode(self, input, final=False):
        "\n        Decode input and returns the resulting object.\n        "
        raise NotImplementedError

    def reset(self):
        "\n        Reset the decoder to the initial state.\n        "

    def getstate(self):
        '\n        Return the current state of the decoder.\n\n        This must be a (buffered_input, additional_state_info) tuple.\n        buffered_input must be a bytes object containing bytes that\n        were passed to decode() that have not yet been converted.\n        additional_state_info must be a non-negative integer\n        representing the state of the decoder WITHOUT yet having\n        processed the contents of buffered_input.  In the initial state\n        and after reset(), getstate() must return (b"", 0).\n        '
        return (b"", 0)

    def setstate(self, state):
        '\n        Set the current state of the decoder.\n\n        state must have been returned by getstate().  The effect of\n        setstate((b"", 0)) must be equivalent to reset().\n        '


class BufferedIncrementalDecoder(IncrementalDecoder):
    "\n    This subclass of IncrementalDecoder can be used as the baseclass for an\n    incremental decoder if the decoder must be able to handle incomplete\n    byte sequences.\n    "

    def __init__(self, errors="strict"):
        IncrementalDecoder.__init__(self, errors)
        self.buffer = b""

    def _buffer_decode(self, input, errors, final):
        raise NotImplementedError

    def decode(self, input, final=False):
        data = self.buffer + input
        (result, consumed) = self._buffer_decode(data, self.errors, final)
        self.buffer = data[consumed:]
        return result

    def reset(self):
        IncrementalDecoder.reset(self)
        self.buffer = b""

    def getstate(self):
        return (self.buffer, 0)

    def setstate(self, state):
        self.buffer = state[0]


class StreamWriter(Codec):
    def __init__(self, stream, errors="strict"):
        " Creates a StreamWriter instance.\n\n            stream must be a file-like object open for writing.\n\n            The StreamWriter may use different error handling\n            schemes by providing the errors keyword argument. These\n            parameters are predefined:\n\n             'strict' - raise a ValueError (or a subclass)\n             'ignore' - ignore the character and continue with the next\n             'replace'- replace with a suitable replacement character\n             'xmlcharrefreplace' - Replace with the appropriate XML\n                                   character reference.\n             'backslashreplace'  - Replace with backslashed escape\n                                   sequences.\n             'namereplace'       - Replace with \\N{...} escape sequences.\n\n            The set of allowed parameter values can be extended via\n            register_error.\n        "
        self.stream = stream
        self.errors = errors

    def write(self, object):
        " Writes the object's contents encoded to self.stream.\n        "
        (data, consumed) = self.encode(object, self.errors)
        self.stream.write(data)

    def writelines(self, list):
        " Writes the concatenated list of strings to the stream\n            using .write().\n        "
        self.write("".join(list))

    def reset(self):
        " Resets the codec buffers used for keeping internal state.\n\n            Calling this method should ensure that the data on the\n            output is put into a clean state, that allows appending\n            of new fresh data without having to rescan the whole\n            stream to recover state.\n\n        "
        pass

    def seek(self, offset, whence=0):
        self.stream.seek(offset, whence)
        if (whence == 0) and (offset == 0):
            self.reset()

    def __getattr__(self, name, getattr=getattr):
        " Inherit all other methods from the underlying stream.\n        "
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.stream.close()


class StreamReader(Codec):
    charbuffertype = str

    def __init__(self, stream, errors="strict"):
        " Creates a StreamReader instance.\n\n            stream must be a file-like object open for reading.\n\n            The StreamReader may use different error handling\n            schemes by providing the errors keyword argument. These\n            parameters are predefined:\n\n             'strict' - raise a ValueError (or a subclass)\n             'ignore' - ignore the character and continue with the next\n             'replace'- replace with a suitable replacement character\n             'backslashreplace' - Replace with backslashed escape sequences;\n\n            The set of allowed parameter values can be extended via\n            register_error.\n        "
        self.stream = stream
        self.errors = errors
        self.bytebuffer = b""
        self._empty_charbuffer = self.charbuffertype()
        self.charbuffer = self._empty_charbuffer
        self.linebuffer = None

    def decode(self, input, errors="strict"):
        raise NotImplementedError

    def read(self, size=(-1), chars=(-1), firstline=False):
        " Decodes data from the stream self.stream and returns the\n            resulting object.\n\n            chars indicates the number of decoded code points or bytes to\n            return. read() will never return more data than requested,\n            but it might return less, if there is not enough available.\n\n            size indicates the approximate maximum number of decoded\n            bytes or code points to read for decoding. The decoder\n            can modify this setting as appropriate. The default value\n            -1 indicates to read and decode as much as possible.  size\n            is intended to prevent having to decode huge files in one\n            step.\n\n            If firstline is true, and a UnicodeDecodeError happens\n            after the first line terminator in the input only the first line\n            will be returned, the rest of the input will be kept until the\n            next call to read().\n\n            The method should use a greedy read strategy, meaning that\n            it should read as much data as is allowed within the\n            definition of the encoding and the given size, e.g.  if\n            optional encoding endings or state markers are available\n            on the stream, these should be read too.\n        "
        if self.linebuffer:
            self.charbuffer = self._empty_charbuffer.join(self.linebuffer)
            self.linebuffer = None
        if chars < 0:
            chars = size
        while True:
            if chars >= 0:
                if len(self.charbuffer) >= chars:
                    break
            if size < 0:
                newdata = self.stream.read()
            else:
                newdata = self.stream.read(size)
            data = self.bytebuffer + newdata
            if not data:
                break
            try:
                (newchars, decodedbytes) = self.decode(data, self.errors)
            except UnicodeDecodeError as exc:
                if firstline:
                    (newchars, decodedbytes) = self.decode(
                        data[: exc.start], self.errors
                    )
                    lines = newchars.splitlines(keepends=True)
                    if len(lines) <= 1:
                        raise
                else:
                    raise
            self.bytebuffer = data[decodedbytes:]
            self.charbuffer += newchars
            if not newdata:
                break
        if chars < 0:
            result = self.charbuffer
            self.charbuffer = self._empty_charbuffer
        else:
            result = self.charbuffer[:chars]
            self.charbuffer = self.charbuffer[chars:]
        return result

    def readline(self, size=None, keepends=True):
        " Read one line from the input stream and return the\n            decoded data.\n\n            size, if given, is passed as size argument to the\n            read() method.\n\n        "
        if self.linebuffer:
            line = self.linebuffer[0]
            del self.linebuffer[0]
            if len(self.linebuffer) == 1:
                self.charbuffer = self.linebuffer[0]
                self.linebuffer = None
            if not keepends:
                line = line.splitlines(keepends=False)[0]
            return line
        readsize = size or 72
        line = self._empty_charbuffer
        while True:
            data = self.read(readsize, firstline=True)
            if data:
                if (isinstance(data, str) and data.endswith("\r")) or (
                    isinstance(data, bytes) and data.endswith(b"\r")
                ):
                    data += self.read(size=1, chars=1)
            line += data
            lines = line.splitlines(keepends=True)
            if lines:
                if len(lines) > 1:
                    line = lines[0]
                    del lines[0]
                    if len(lines) > 1:
                        lines[(-1)] += self.charbuffer
                        self.linebuffer = lines
                        self.charbuffer = None
                    else:
                        self.charbuffer = lines[0] + self.charbuffer
                    if not keepends:
                        line = line.splitlines(keepends=False)[0]
                    break
                line0withend = lines[0]
                line0withoutend = lines[0].splitlines(keepends=False)[0]
                if line0withend != line0withoutend:
                    self.charbuffer = (
                        self._empty_charbuffer.join(lines[1:]) + self.charbuffer
                    )
                    if keepends:
                        line = line0withend
                    else:
                        line = line0withoutend
                    break
            if (not data) or (size is not None):
                if line and (not keepends):
                    line = line.splitlines(keepends=False)[0]
                break
            if readsize < 8000:
                readsize *= 2
        return line

    def readlines(self, sizehint=None, keepends=True):
        " Read all lines available on the input stream\n            and return them as a list.\n\n            Line breaks are implemented using the codec's decoder\n            method and are included in the list entries.\n\n            sizehint, if given, is ignored since there is no efficient\n            way to finding the true end-of-line.\n\n        "
        data = self.read()
        return data.splitlines(keepends)

    def reset(self):
        " Resets the codec buffers used for keeping internal state.\n\n            Note that no stream repositioning should take place.\n            This method is primarily intended to be able to recover\n            from decoding errors.\n\n        "
        self.bytebuffer = b""
        self.charbuffer = self._empty_charbuffer
        self.linebuffer = None

    def seek(self, offset, whence=0):
        " Set the input stream's current position.\n\n            Resets the codec buffers used for keeping state.\n        "
        self.stream.seek(offset, whence)
        self.reset()

    def __next__(self):
        " Return the next decoded line from the input stream."
        line = self.readline()
        if line:
            return line
        raise StopIteration

    def __iter__(self):
        return self

    def __getattr__(self, name, getattr=getattr):
        " Inherit all other methods from the underlying stream.\n        "
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.stream.close()


class StreamReaderWriter:
    " StreamReaderWriter instances allow wrapping streams which\n        work in both read and write modes.\n\n        The design is such that one can use the factory functions\n        returned by the codec.lookup() function to construct the\n        instance.\n\n    "
    encoding = "unknown"

    def __init__(self, stream, Reader, Writer, errors="strict"):
        " Creates a StreamReaderWriter instance.\n\n            stream must be a Stream-like object.\n\n            Reader, Writer must be factory functions or classes\n            providing the StreamReader, StreamWriter interface resp.\n\n            Error handling is done in the same way as defined for the\n            StreamWriter/Readers.\n\n        "
        self.stream = stream
        self.reader = Reader(stream, errors)
        self.writer = Writer(stream, errors)
        self.errors = errors

    def read(self, size=(-1)):
        return self.reader.read(size)

    def readline(self, size=None):
        return self.reader.readline(size)

    def readlines(self, sizehint=None):
        return self.reader.readlines(sizehint)

    def __next__(self):
        " Return the next decoded line from the input stream."
        return next(self.reader)

    def __iter__(self):
        return self

    def write(self, data):
        return self.writer.write(data)

    def writelines(self, list):
        return self.writer.writelines(list)

    def reset(self):
        self.reader.reset()
        self.writer.reset()

    def seek(self, offset, whence=0):
        self.stream.seek(offset, whence)
        self.reader.reset()
        if (whence == 0) and (offset == 0):
            self.writer.reset()

    def __getattr__(self, name, getattr=getattr):
        " Inherit all other methods from the underlying stream.\n        "
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.stream.close()


class StreamRecoder:
    ' StreamRecoder instances translate data from one encoding to another.\n\n        They use the complete set of APIs returned by the\n        codecs.lookup() function to implement their task.\n\n        Data written to the StreamRecoder is first decoded into an\n        intermediate format (depending on the "decode" codec) and then\n        written to the underlying stream using an instance of the provided\n        Writer class.\n\n        In the other direction, data is read from the underlying stream using\n        a Reader instance and then encoded and returned to the caller.\n\n    '
    data_encoding = "unknown"
    file_encoding = "unknown"

    def __init__(self, stream, encode, decode, Reader, Writer, errors="strict"):
        " Creates a StreamRecoder instance which implements a two-way\n            conversion: encode and decode work on the frontend (the\n            data visible to .read() and .write()) while Reader and Writer\n            work on the backend (the data in stream).\n\n            You can use these objects to do transparent\n            transcodings from e.g. latin-1 to utf-8 and back.\n\n            stream must be a file-like object.\n\n            encode and decode must adhere to the Codec interface; Reader and\n            Writer must be factory functions or classes providing the\n            StreamReader and StreamWriter interfaces resp.\n\n            Error handling is done in the same way as defined for the\n            StreamWriter/Readers.\n\n        "
        self.stream = stream
        self.encode = encode
        self.decode = decode
        self.reader = Reader(stream, errors)
        self.writer = Writer(stream, errors)
        self.errors = errors

    def read(self, size=(-1)):
        data = self.reader.read(size)
        (data, bytesencoded) = self.encode(data, self.errors)
        return data

    def readline(self, size=None):
        if size is None:
            data = self.reader.readline()
        else:
            data = self.reader.readline(size)
        (data, bytesencoded) = self.encode(data, self.errors)
        return data

    def readlines(self, sizehint=None):
        data = self.reader.read()
        (data, bytesencoded) = self.encode(data, self.errors)
        return data.splitlines(keepends=True)

    def __next__(self):
        " Return the next decoded line from the input stream."
        data = next(self.reader)
        (data, bytesencoded) = self.encode(data, self.errors)
        return data

    def __iter__(self):
        return self

    def write(self, data):
        (data, bytesdecoded) = self.decode(data, self.errors)
        return self.writer.write(data)

    def writelines(self, list):
        data = b"".join(list)
        (data, bytesdecoded) = self.decode(data, self.errors)
        return self.writer.write(data)

    def reset(self):
        self.reader.reset()
        self.writer.reset()

    def seek(self, offset, whence=0):
        self.reader.seek(offset, whence)
        self.writer.seek(offset, whence)

    def __getattr__(self, name, getattr=getattr):
        " Inherit all other methods from the underlying stream.\n        "
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.stream.close()


def open(filename, mode="r", encoding=None, errors="strict", buffering=(-1)):
    " Open an encoded file using the given mode and return\n        a wrapped version providing transparent encoding/decoding.\n\n        Note: The wrapped version will only accept the object format\n        defined by the codecs, i.e. Unicode objects for most builtin\n        codecs. Output is also codec dependent and will usually be\n        Unicode as well.\n\n        Underlying encoded files are always opened in binary mode.\n        The default file mode is 'r', meaning to open the file in read mode.\n\n        encoding specifies the encoding which is to be used for the\n        file.\n\n        errors may be given to define the error handling. It defaults\n        to 'strict' which causes ValueErrors to be raised in case an\n        encoding error occurs.\n\n        buffering has the same meaning as for the builtin open() API.\n        It defaults to -1 which means that the default buffer size will\n        be used.\n\n        The returned wrapped file object provides an extra attribute\n        .encoding which allows querying the used encoding. This\n        attribute is only available if an encoding was specified as\n        parameter.\n\n    "
    if (encoding is not None) and ("b" not in mode):
        mode = mode + "b"
    file = builtins.open(filename, mode, buffering)
    if encoding is None:
        return file
    try:
        info = lookup(encoding)
        srw = StreamReaderWriter(file, info.streamreader, info.streamwriter, errors)
        srw.encoding = encoding
        return srw
    except:
        file.close()
        raise


def EncodedFile(file, data_encoding, file_encoding=None, errors="strict"):
    " Return a wrapped version of file which provides transparent\n        encoding translation.\n\n        Data written to the wrapped file is decoded according\n        to the given data_encoding and then encoded to the underlying\n        file using file_encoding. The intermediate data type\n        will usually be Unicode but depends on the specified codecs.\n\n        Bytes read from the file are decoded using file_encoding and then\n        passed back to the caller encoded using data_encoding.\n\n        If file_encoding is not given, it defaults to data_encoding.\n\n        errors may be given to define the error handling. It defaults\n        to 'strict' which causes ValueErrors to be raised in case an\n        encoding error occurs.\n\n        The returned wrapped file object provides two extra attributes\n        .data_encoding and .file_encoding which reflect the given\n        parameters of the same name. The attributes can be used for\n        introspection by Python programs.\n\n    "
    if file_encoding is None:
        file_encoding = data_encoding
    data_info = lookup(data_encoding)
    file_info = lookup(file_encoding)
    sr = StreamRecoder(
        file,
        data_info.encode,
        data_info.decode,
        file_info.streamreader,
        file_info.streamwriter,
        errors,
    )
    sr.data_encoding = data_encoding
    sr.file_encoding = file_encoding
    return sr


def getencoder(encoding):
    " Lookup up the codec for the given encoding and return\n        its encoder function.\n\n        Raises a LookupError in case the encoding cannot be found.\n\n    "
    return lookup(encoding).encode


def getdecoder(encoding):
    " Lookup up the codec for the given encoding and return\n        its decoder function.\n\n        Raises a LookupError in case the encoding cannot be found.\n\n    "
    return lookup(encoding).decode


def getincrementalencoder(encoding):
    " Lookup up the codec for the given encoding and return\n        its IncrementalEncoder class or factory function.\n\n        Raises a LookupError in case the encoding cannot be found\n        or the codecs doesn't provide an incremental encoder.\n\n    "
    encoder = lookup(encoding).incrementalencoder
    if encoder is None:
        raise LookupError(encoding)
    return encoder


def getincrementaldecoder(encoding):
    " Lookup up the codec for the given encoding and return\n        its IncrementalDecoder class or factory function.\n\n        Raises a LookupError in case the encoding cannot be found\n        or the codecs doesn't provide an incremental decoder.\n\n    "
    decoder = lookup(encoding).incrementaldecoder
    if decoder is None:
        raise LookupError(encoding)
    return decoder


def getreader(encoding):
    " Lookup up the codec for the given encoding and return\n        its StreamReader class or factory function.\n\n        Raises a LookupError in case the encoding cannot be found.\n\n    "
    return lookup(encoding).streamreader


def getwriter(encoding):
    " Lookup up the codec for the given encoding and return\n        its StreamWriter class or factory function.\n\n        Raises a LookupError in case the encoding cannot be found.\n\n    "
    return lookup(encoding).streamwriter


def iterencode(iterator, encoding, errors="strict", **kwargs):
    "\n    Encoding iterator.\n\n    Encodes the input strings from the iterator using an IncrementalEncoder.\n\n    errors and kwargs are passed through to the IncrementalEncoder\n    constructor.\n    "
    encoder = getincrementalencoder(encoding)(errors, **kwargs)
    for input in iterator:
        output = encoder.encode(input)
        if output:
            (yield output)
    output = encoder.encode("", True)
    if output:
        (yield output)


def iterdecode(iterator, encoding, errors="strict", **kwargs):
    "\n    Decoding iterator.\n\n    Decodes the input strings from the iterator using an IncrementalDecoder.\n\n    errors and kwargs are passed through to the IncrementalDecoder\n    constructor.\n    "
    decoder = getincrementaldecoder(encoding)(errors, **kwargs)
    for input in iterator:
        output = decoder.decode(input)
        if output:
            (yield output)
    output = decoder.decode(b"", True)
    if output:
        (yield output)


def make_identity_dict(rng):
    " make_identity_dict(rng) -> dict\n\n        Return a dictionary where elements of the rng sequence are\n        mapped to themselves.\n\n    "
    return {i: i for i in rng}


def make_encoding_map(decoding_map):
    " Creates an encoding map from a decoding map.\n\n        If a target mapping in the decoding map occurs multiple\n        times, then that target is mapped to None (undefined mapping),\n        causing an exception when encountered by the charmap codec\n        during translation.\n\n        One example where this happens is cp875.py which decodes\n        multiple character to \\u001a.\n\n    "
    m = {}
    for (k, v) in decoding_map.items():
        if not (v in m):
            m[v] = k
        else:
            m[v] = None
    return m


try:
    strict_errors = lookup_error("strict")
    ignore_errors = lookup_error("ignore")
    replace_errors = lookup_error("replace")
    xmlcharrefreplace_errors = lookup_error("xmlcharrefreplace")
    backslashreplace_errors = lookup_error("backslashreplace")
    namereplace_errors = lookup_error("namereplace")
except LookupError:
    strict_errors = None
    ignore_errors = None
    replace_errors = None
    xmlcharrefreplace_errors = None
    backslashreplace_errors = None
    namereplace_errors = None
_false = 0
if _false:
    import encodings
if __name__ == "__main__":
    sys.stdout = EncodedFile(sys.stdout, "latin-1", "utf-8")
    sys.stdin = EncodedFile(sys.stdin, "utf-8", "latin-1")
