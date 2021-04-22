"The io module provides the Python interfaces to stream handling. The\nbuiltin open function is defined in this module.\n\nAt the top of the I/O hierarchy is the abstract base class IOBase. It\ndefines the basic interface to a stream. Note, however, that there is no\nseparation between reading and writing to streams; implementations are\nallowed to raise an OSError if they do not support a given operation.\n\nExtending IOBase is RawIOBase which deals simply with the reading and\nwriting of raw bytes to a stream. FileIO subclasses RawIOBase to provide\nan interface to OS files.\n\nBufferedIOBase deals with buffering on a raw byte stream (RawIOBase). Its\nsubclasses, BufferedWriter, BufferedReader, and BufferedRWPair buffer\nstreams that are readable, writable, and both respectively.\nBufferedRandom provides a buffered interface to random access\nstreams. BytesIO is a simple stream of in-memory bytes.\n\nAnother IOBase subclass, TextIOBase, deals with the encoding and decoding\nof streams into text. TextIOWrapper, which extends it, is a buffered text\ninterface to a buffered raw stream (`BufferedIOBase`). Finally, StringIO\nis an in-memory stream for text.\n\nArgument names are not part of the specification, and only the arguments\nof open() are intended to be used as keyword arguments.\n\ndata:\n\nDEFAULT_BUFFER_SIZE\n\n   An int containing the default buffer size used by the module's buffered\n   I/O classes. open() uses the file's blksize (as obtained by os.stat) if\n   possible.\n"
__author__ = "Guido van Rossum <guido@python.org>, Mike Verdone <mike.verdone@gmail.com>, Mark Russell <mark.russell@zen.co.uk>, Antoine Pitrou <solipsis@pitrou.net>, Amaury Forgeot d'Arc <amauryfa@gmail.com>, Benjamin Peterson <benjamin@python.org>"
__all__ = [
    "BlockingIOError",
    "open",
    "open_code",
    "IOBase",
    "RawIOBase",
    "FileIO",
    "BytesIO",
    "StringIO",
    "BufferedIOBase",
    "BufferedReader",
    "BufferedWriter",
    "BufferedRWPair",
    "BufferedRandom",
    "TextIOBase",
    "TextIOWrapper",
    "UnsupportedOperation",
    "SEEK_SET",
    "SEEK_CUR",
    "SEEK_END",
]
import _io
import abc
from _io import (
    DEFAULT_BUFFER_SIZE,
    BlockingIOError,
    UnsupportedOperation,
    open,
    open_code,
    FileIO,
    BytesIO,
    StringIO,
    BufferedReader,
    BufferedWriter,
    BufferedRWPair,
    BufferedRandom,
    IncrementalNewlineDecoder,
    text_encoding,
    TextIOWrapper,
)


def __getattr__(name):
    if name == "OpenWrapper":
        import warnings

        warnings.warn(
            "OpenWrapper is deprecated, use open instead",
            DeprecationWarning,
            stacklevel=2,
        )
        global OpenWrapper
        OpenWrapper = open
        return OpenWrapper
    raise AttributeError(name)


UnsupportedOperation.__module__ = "io"
SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2


class IOBase(_io._IOBase, metaclass=abc.ABCMeta):
    __doc__ = _io._IOBase.__doc__


class RawIOBase(_io._RawIOBase, IOBase):
    __doc__ = _io._RawIOBase.__doc__


class BufferedIOBase(_io._BufferedIOBase, IOBase):
    __doc__ = _io._BufferedIOBase.__doc__


class TextIOBase(_io._TextIOBase, IOBase):
    __doc__ = _io._TextIOBase.__doc__


RawIOBase.register(FileIO)
for klass in (BytesIO, BufferedReader, BufferedWriter, BufferedRandom, BufferedRWPair):
    BufferedIOBase.register(klass)
for klass in (StringIO, TextIOWrapper):
    TextIOBase.register(klass)
del klass
try:
    from _io import _WindowsConsoleIO
except ImportError:
    pass
else:
    RawIOBase.register(_WindowsConsoleIO)
