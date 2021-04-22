" Unicode Mapping Parser and Codec Generator.\n\nThis script parses Unicode mapping files as available from the Unicode\nsite (ftp://ftp.unicode.org/Public/MAPPINGS/) and creates Python codec\nmodules from them. The codecs use the standard character mapping codec\nto actually apply the mapping.\n\nSynopsis: gencodec.py dir codec_prefix\n\nAll files in dir are scanned and those producing non-empty mappings\nwill be written to <codec_prefix><mapname>.py with <mapname> being the\nfirst part of the map's filename ('a' in a.b.c.txt) converted to\nlowercase with hyphens replaced by underscores.\n\nThe tool also writes marshalled versions of the mapping tables to the\nsame location (with .mapping extension).\n\nWritten by Marc-Andre Lemburg (mal@lemburg.com).\n\n(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.\n(c) Copyright Guido van Rossum, 2000.\n\nTable generation:\n(c) Copyright Marc-Andre Lemburg, 2005.\n    Licensed to PSF under a Contributor Agreement.\n\n"
import re, os, marshal, codecs

MAX_TABLE_SIZE = 8192
UNI_UNDEFINED = chr(65534)
MISSING_CODE = -1
mapRE = re.compile(
    "((?:0x[0-9a-fA-F]+\\+?)+)\\s+((?:(?:0x[0-9a-fA-Z]+|<[A-Za-z]+>)\\+?)*)\\s*(#.+)?"
)


def parsecodes(codes, len=len, range=range):
    " Converts code combinations to either a single code integer\n        or a tuple of integers.\n\n        meta-codes (in angular brackets, e.g. <LR> and <RL>) are\n        ignored.\n\n        Empty codes or illegal ones are returned as None.\n\n    "
    if not codes:
        return MISSING_CODE
    l = codes.split("+")
    if len(l) == 1:
        return int(l[0], 16)
    for i in range(len(l)):
        try:
            l[i] = int(l[i], 16)
        except ValueError:
            l[i] = MISSING_CODE
    l = [x for x in l if (x != MISSING_CODE)]
    if len(l) == 1:
        return l[0]
    else:
        return tuple(l)


def readmap(filename):
    with open(filename) as f:
        lines = f.readlines()
    enc2uni = {}
    identity = []
    unmapped = list(range(256))
    for i in list(range(32)) + [127]:
        identity.append(i)
        unmapped.remove(i)
        enc2uni[i] = (i, "CONTROL CHARACTER")
    for line in lines:
        line = line.strip()
        if (not line) or (line[0] == "#"):
            continue
        m = mapRE.match(line)
        if not m:
            continue
        (enc, uni, comment) = m.groups()
        enc = parsecodes(enc)
        uni = parsecodes(uni)
        if comment is None:
            comment = ""
        else:
            comment = comment[1:].strip()
        if (not isinstance(enc, tuple)) and (enc < 256):
            if enc in unmapped:
                unmapped.remove(enc)
            if enc == uni:
                identity.append(enc)
            enc2uni[enc] = (uni, comment)
        else:
            enc2uni[enc] = (uni, comment)
    if len(identity) >= len(unmapped):
        for enc in unmapped:
            enc2uni[enc] = (MISSING_CODE, "")
        enc2uni["IDENTITY"] = 256
    return enc2uni


def hexrepr(t, precision=4):
    if t is None:
        return "None"
    try:
        len(t)
    except TypeError:
        return "0x%0*X" % (precision, t)
    try:
        return ("(" + ", ".join([("0x%0*X" % (precision, item)) for item in t])) + ")"
    except TypeError as why:
        print(("* failed to convert %r: %s" % (t, why)))
        raise


def python_mapdef_code(varname, map, comments=1, precisions=(2, 4)):
    l = []
    append = l.append
    if "IDENTITY" in map:
        append(
            ("%s = codecs.make_identity_dict(range(%d))" % (varname, map["IDENTITY"]))
        )
        append(("%s.update({" % varname))
        splits = 1
        del map["IDENTITY"]
        identity = 1
    else:
        append(("%s = {" % varname))
        splits = 0
        identity = 0
    mappings = sorted(map.items())
    i = 0
    (key_precision, value_precision) = precisions
    for (mapkey, mapvalue) in mappings:
        mapcomment = ""
        if isinstance(mapkey, tuple):
            (mapkey, mapcomment) = mapkey
        if isinstance(mapvalue, tuple):
            (mapvalue, mapcomment) = mapvalue
        if mapkey is None:
            continue
        if identity and (mapkey == mapvalue) and (mapkey < 256):
            continue
        key = hexrepr(mapkey, key_precision)
        value = hexrepr(mapvalue, value_precision)
        if mapcomment and comments:
            append(("    %s: %s,\t#  %s" % (key, value, mapcomment)))
        else:
            append(("    %s: %s," % (key, value)))
        i += 1
        if i == 4096:
            if splits == 0:
                append("}")
            else:
                append("})")
            append(("%s.update({" % varname))
            i = 0
            splits = splits + 1
    if splits == 0:
        append("}")
    else:
        append("})")
    return l


def python_tabledef_code(varname, map, comments=1, key_precision=2):
    l = []
    append = l.append
    append(("%s = (" % varname))
    mappings = sorted(map.items())
    table = {}
    maxkey = 255
    if "IDENTITY" in map:
        for key in range(256):
            table[key] = (key, "")
        del map["IDENTITY"]
    for (mapkey, mapvalue) in mappings:
        mapcomment = ""
        if isinstance(mapkey, tuple):
            (mapkey, mapcomment) = mapkey
        if isinstance(mapvalue, tuple):
            (mapvalue, mapcomment) = mapvalue
        if mapkey == MISSING_CODE:
            continue
        table[mapkey] = (mapvalue, mapcomment)
        if mapkey > maxkey:
            maxkey = mapkey
    if maxkey > MAX_TABLE_SIZE:
        return None
    maxchar = 0
    for key in range((maxkey + 1)):
        if key not in table:
            mapvalue = MISSING_CODE
            mapcomment = "UNDEFINED"
        else:
            (mapvalue, mapcomment) = table[key]
        if mapvalue == MISSING_CODE:
            mapchar = UNI_UNDEFINED
        elif isinstance(mapvalue, tuple):
            return None
        else:
            mapchar = chr(mapvalue)
        maxchar = max(maxchar, ord(mapchar))
        if mapcomment and comments:
            append(
                (
                    "    %a \t#  %s -> %s"
                    % (mapchar, hexrepr(key, key_precision), mapcomment)
                )
            )
        else:
            append(("    %a" % mapchar))
    if maxchar < 256:
        append(("    %a \t## Widen to UCS2 for optimization" % UNI_UNDEFINED))
    append(")")
    return l


def codegen(name, map, encodingname, comments=1):
    " Returns Python source for the given map.\n\n        Comments are included in the source, if comments is true (default).\n\n    "
    decoding_map_code = python_mapdef_code("decoding_map", map, comments=comments)
    decoding_table_code = python_tabledef_code("decoding_table", map, comments=comments)
    encoding_map_code = python_mapdef_code(
        "encoding_map",
        codecs.make_encoding_map(map),
        comments=comments,
        precisions=(4, 2),
    )
    if decoding_table_code:
        suffix = "table"
    else:
        suffix = "map"
    l = [
        (
            '""" Python Character Mapping Codec %s generated from \'%s\' with gencodec.py.\n\n"""#"\n\nimport codecs\n\n### Codec APIs\n\nclass Codec(codecs.Codec):\n\n    def encode(self, input, errors=\'strict\'):\n        return codecs.charmap_encode(input, errors, encoding_%s)\n\n    def decode(self, input, errors=\'strict\'):\n        return codecs.charmap_decode(input, errors, decoding_%s)\n'
            % (encodingname, name, suffix, suffix)
        )
    ]
    l.append(
        (
            "class IncrementalEncoder(codecs.IncrementalEncoder):\n    def encode(self, input, final=False):\n        return codecs.charmap_encode(input, self.errors, encoding_%s)[0]\n\nclass IncrementalDecoder(codecs.IncrementalDecoder):\n    def decode(self, input, final=False):\n        return codecs.charmap_decode(input, self.errors, decoding_%s)[0]"
            % (suffix, suffix)
        )
    )
    l.append(
        (
            "\nclass StreamWriter(Codec, codecs.StreamWriter):\n    pass\n\nclass StreamReader(Codec, codecs.StreamReader):\n    pass\n\n### encodings module API\n\ndef getregentry():\n    return codecs.CodecInfo(\n        name=%r,\n        encode=Codec().encode,\n        decode=Codec().decode,\n        incrementalencoder=IncrementalEncoder,\n        incrementaldecoder=IncrementalDecoder,\n        streamreader=StreamReader,\n        streamwriter=StreamWriter,\n    )\n"
            % encodingname.replace("_", "-")
        )
    )
    if not decoding_table_code:
        l.append("\n### Decoding Map\n")
        l.extend(decoding_map_code)
    else:
        l.append("\n### Decoding Table\n")
        l.extend(decoding_table_code)
    if decoding_table_code:
        l.append(
            "\n### Encoding table\nencoding_table = codecs.charmap_build(decoding_table)\n"
        )
    else:
        l.append("\n### Encoding Map\n")
        l.extend(encoding_map_code)
    l.append("")
    return "\n".join(l).expandtabs()


def pymap(name, map, pyfile, encodingname, comments=1):
    code = codegen(name, map, encodingname, comments)
    with open(pyfile, "w") as f:
        f.write(code)


def marshalmap(name, map, marshalfile):
    d = {}
    for (e, (u, c)) in map.items():
        d[e] = (u, c)
    with open(marshalfile, "wb") as f:
        marshal.dump(d, f)


def convertdir(dir, dirprefix="", nameprefix="", comments=1):
    mapnames = os.listdir(dir)
    for mapname in mapnames:
        mappathname = os.path.join(dir, mapname)
        if not os.path.isfile(mappathname):
            continue
        name = os.path.split(mapname)[1]
        name = name.replace("-", "_")
        name = name.split(".")[0]
        name = name.lower()
        name = nameprefix + name
        codefile = name + ".py"
        marshalfile = name + ".mapping"
        print(
            (
                "converting %s to %s and %s"
                % (mapname, (dirprefix + codefile), (dirprefix + marshalfile))
            )
        )
        try:
            map = readmap(os.path.join(dir, mapname))
            if not map:
                print("* map is empty; skipping")
            else:
                pymap(mappathname, map, (dirprefix + codefile), name, comments)
                marshalmap(mappathname, map, (dirprefix + marshalfile))
        except ValueError as why:
            print(("* conversion failed: %s" % why))
            raise


def rewritepythondir(dir, dirprefix="", comments=1):
    mapnames = os.listdir(dir)
    for mapname in mapnames:
        if not mapname.endswith(".mapping"):
            continue
        name = mapname[: (-len(".mapping"))]
        codefile = name + ".py"
        print(("converting %s to %s" % (mapname, (dirprefix + codefile))))
        try:
            with open(os.path.join(dir, mapname), "rb") as f:
                map = marshal.load(f)
            if not map:
                print("* map is empty; skipping")
            else:
                pymap(mapname, map, (dirprefix + codefile), name, comments)
        except ValueError as why:
            print(("* conversion failed: %s" % why))


if __name__ == "__main__":
    import sys

    if 1:
        convertdir(*sys.argv[1:])
    else:
        rewritepythondir(*sys.argv[1:])
