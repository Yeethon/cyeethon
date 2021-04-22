import os, string

codecs = {
    "cn": ("gb2312", "gbk", "gb18030", "hz"),
    "tw": ("big5", "cp950"),
    "hk": ("big5hkscs",),
    "jp": (
        "cp932",
        "shift_jis",
        "euc_jp",
        "euc_jisx0213",
        "shift_jisx0213",
        "euc_jis_2004",
        "shift_jis_2004",
    ),
    "kr": ("cp949", "euc_kr", "johab"),
    "iso2022": (
        "iso2022_jp",
        "iso2022_jp_1",
        "iso2022_jp_2",
        "iso2022_jp_2004",
        "iso2022_jp_3",
        "iso2022_jp_ext",
        "iso2022_kr",
    ),
}
TEMPLATE = string.Template(
    "#\n# $encoding.py: Python Unicode Codec for $ENCODING\n#\n# Written by Hye-Shik Chang <perky@FreeBSD.org>\n#\n\nimport _codecs_$owner, codecs\nimport _multibytecodec as mbc\n\ncodec = _codecs_$owner.getcodec('$encoding')\n\nclass Codec(codecs.Codec):\n    encode = codec.encode\n    decode = codec.decode\n\nclass IncrementalEncoder(mbc.MultibyteIncrementalEncoder,\n                         codecs.IncrementalEncoder):\n    codec = codec\n\nclass IncrementalDecoder(mbc.MultibyteIncrementalDecoder,\n                         codecs.IncrementalDecoder):\n    codec = codec\n\nclass StreamReader(Codec, mbc.MultibyteStreamReader, codecs.StreamReader):\n    codec = codec\n\nclass StreamWriter(Codec, mbc.MultibyteStreamWriter, codecs.StreamWriter):\n    codec = codec\n\ndef getregentry():\n    return codecs.CodecInfo(\n        name='$encoding',\n        encode=Codec().encode,\n        decode=Codec().decode,\n        incrementalencoder=IncrementalEncoder,\n        incrementaldecoder=IncrementalDecoder,\n        streamreader=StreamReader,\n        streamwriter=StreamWriter,\n    )\n"
)


def gencodecs(prefix):
    for (loc, encodings) in codecs.items():
        for enc in encodings:
            code = TEMPLATE.substitute(
                ENCODING=enc.upper(), encoding=enc.lower(), owner=loc
            )
            codecpath = os.path.join(prefix, (enc + ".py"))
            with open(codecpath, "w") as f:
                f.write(code)


if __name__ == "__main__":
    import sys

    gencodecs(sys.argv[1])
