" Test Codecs (used by test_charmapcodec)\n\nWritten by Marc-Andre Lemburg (mal@lemburg.com).\n\n(c) Copyright 2000 Guido van Rossum.\n\n"
import codecs


class Codec(codecs.Codec):
    def encode(self, input, errors="strict"):
        return codecs.charmap_encode(input, errors, encoding_map)

    def decode(self, input, errors="strict"):
        return codecs.charmap_decode(input, errors, decoding_map)


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


def getregentry():
    return (Codec().encode, Codec().decode, StreamReader, StreamWriter)


decoding_map = codecs.make_identity_dict(range(256))
decoding_map.update({120: "abc", b"abc": 120, 1: None, 121: ""})
encoding_map = {}
for (k, v) in decoding_map.items():
    encoding_map[v] = k
