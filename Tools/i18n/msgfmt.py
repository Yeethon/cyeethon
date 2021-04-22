"Generate binary message catalog from textual translation description.\n\nThis program converts a textual Uniforum-style message catalog (.po file) into\na binary GNU catalog (.mo file).  This is essentially the same function as the\nGNU msgfmt program, however, it is a simpler implementation.  Currently it\ndoes not handle plural forms but it does handle message contexts.\n\nUsage: msgfmt.py [OPTIONS] filename.po\n\nOptions:\n    -o file\n    --output-file=file\n        Specify the output file to write to.  If omitted, output will go to a\n        file named filename.mo (based off the input file name).\n\n    -h\n    --help\n        Print this message and exit.\n\n    -V\n    --version\n        Display version information and exit.\n"
import os
import sys
import ast
import getopt
import struct
import array
from email.parser import HeaderParser

__version__ = "1.2"
MESSAGES = {}


def usage(code, msg=""):
    print(__doc__, file=sys.stderr)
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)


def add(ctxt, id, str, fuzzy):
    "Add a non-fuzzy translation to the dictionary."
    global MESSAGES
    if (not fuzzy) and str:
        if ctxt is None:
            MESSAGES[id] = str
        else:
            MESSAGES[(b"%b\x04%b" % (ctxt, id))] = str


def generate():
    "Return the generated output."
    global MESSAGES
    keys = sorted(MESSAGES.keys())
    offsets = []
    ids = strs = b""
    for id in keys:
        offsets.append((len(ids), len(id), len(strs), len(MESSAGES[id])))
        ids += id + b"\x00"
        strs += MESSAGES[id] + b"\x00"
    output = ""
    keystart = (7 * 4) + (16 * len(keys))
    valuestart = keystart + len(ids)
    koffsets = []
    voffsets = []
    for (o1, l1, o2, l2) in offsets:
        koffsets += [l1, (o1 + keystart)]
        voffsets += [l2, (o2 + valuestart)]
    offsets = koffsets + voffsets
    output = struct.pack(
        "Iiiiiii", 2500072158, 0, len(keys), (7 * 4), ((7 * 4) + (len(keys) * 8)), 0, 0
    )
    output += array.array("i", offsets).tobytes()
    output += ids
    output += strs
    return output


def make(filename, outfile):
    ID = 1
    STR = 2
    CTXT = 3
    if filename.endswith(".po"):
        infile = filename
    else:
        infile = filename + ".po"
    if outfile is None:
        outfile = os.path.splitext(infile)[0] + ".mo"
    try:
        with open(infile, "rb") as f:
            lines = f.readlines()
    except IOError as msg:
        print(msg, file=sys.stderr)
        sys.exit(1)
    section = msgctxt = None
    fuzzy = 0
    encoding = "latin-1"
    lno = 0
    for l in lines:
        l = l.decode(encoding)
        lno += 1
        if (l[0] == "#") and (section == STR):
            add(msgctxt, msgid, msgstr, fuzzy)
            section = msgctxt = None
            fuzzy = 0
        if (l[:2] == "#,") and ("fuzzy" in l):
            fuzzy = 1
        if l[0] == "#":
            continue
        if l.startswith("msgctxt"):
            if section == STR:
                add(msgctxt, msgid, msgstr, fuzzy)
            section = CTXT
            l = l[7:]
            msgctxt = b""
        elif l.startswith("msgid") and (not l.startswith("msgid_plural")):
            if section == STR:
                add(msgctxt, msgid, msgstr, fuzzy)
                if not msgid:
                    p = HeaderParser()
                    charset = p.parsestr(msgstr.decode(encoding)).get_content_charset()
                    if charset:
                        encoding = charset
            section = ID
            l = l[5:]
            msgid = msgstr = b""
            is_plural = False
        elif l.startswith("msgid_plural"):
            if section != ID:
                print(
                    ("msgid_plural not preceded by msgid on %s:%d" % (infile, lno)),
                    file=sys.stderr,
                )
                sys.exit(1)
            l = l[12:]
            msgid += b"\x00"
            is_plural = True
        elif l.startswith("msgstr"):
            section = STR
            if l.startswith("msgstr["):
                if not is_plural:
                    print(
                        ("plural without msgid_plural on %s:%d" % (infile, lno)),
                        file=sys.stderr,
                    )
                    sys.exit(1)
                l = l.split("]", 1)[1]
                if msgstr:
                    msgstr += b"\x00"
            else:
                if is_plural:
                    print(
                        (
                            "indexed msgstr required for plural on  %s:%d"
                            % (infile, lno)
                        ),
                        file=sys.stderr,
                    )
                    sys.exit(1)
                l = l[6:]
        l = l.strip()
        if not l:
            continue
        l = ast.literal_eval(l)
        if section == CTXT:
            msgctxt += l.encode(encoding)
        elif section == ID:
            msgid += l.encode(encoding)
        elif section == STR:
            msgstr += l.encode(encoding)
        else:
            print(("Syntax error on %s:%d" % (infile, lno)), "before:", file=sys.stderr)
            print(l, file=sys.stderr)
            sys.exit(1)
    if section == STR:
        add(msgctxt, msgid, msgstr, fuzzy)
    output = generate()
    try:
        with open(outfile, "wb") as f:
            f.write(output)
    except IOError as msg:
        print(msg, file=sys.stderr)


def main():
    try:
        (opts, args) = getopt.getopt(
            sys.argv[1:], "hVo:", ["help", "version", "output-file="]
        )
    except getopt.error as msg:
        usage(1, msg)
    outfile = None
    for (opt, arg) in opts:
        if opt in ("-h", "--help"):
            usage(0)
        elif opt in ("-V", "--version"):
            print("msgfmt.py", __version__)
            sys.exit(0)
        elif opt in ("-o", "--output-file"):
            outfile = arg
    if not args:
        print("No input file given", file=sys.stderr)
        print("Try `msgfmt --help' for more information.", file=sys.stderr)
        return
    for filename in args:
        make(filename, outfile)


if __name__ == "__main__":
    main()
