" Python 'undefined' Codec\n\n    This codec will always raise a ValueError exception when being\n    used. It is intended for use by the site.py file to switch off\n    automatic string to Unicode coercion.\n\nWritten by Marc-Andre Lemburg (mal@lemburg.com).\n\n(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.\n\n"
import codecs


class Codec(codecs.Codec):
    def encode(self, input, errors="strict"):
        raise UnicodeError("undefined encoding")

    def decode(self, input, errors="strict"):
        raise UnicodeError("undefined encoding")


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        raise UnicodeError("undefined encoding")


class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        raise UnicodeError("undefined encoding")


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


def getregentry():
    return codecs.CodecInfo(
        name="undefined",
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
    )
